"""
Headless offscreen Multi-View STEP file visualizer for Materials-MCP.

Reads a geometry.step file from a run directory, tessellates each
topological face using build123d's OCC kernel once, and renders comprehensive
multi-view CAD preview images using matplotlib's Agg backend.

Supported View Modes:
  - 'ortho6' / 'all' (default): 2x3 engineering sheet with 6 views:
      Row 1: Top (XY), Isometric 3D, Bottom (XY)
      Row 2: Front (XZ), Right (YZ), Back (XZ)
  - 'quad': 2x2 standard CAD drawing sheet:
      Row 1: Top (XY), Isometric 3D
      Row 2: Front (XZ), Right (YZ)
  - 'single' / 'isometric': Single isometric 3D view (backward compatible).

Design invariants:
  - Pure function: reads step_path, writes output_path, no global state.
  - Never raises: all exceptions are caught; returns False on failure.
  - No X11/display dependencies: Agg backend enforced at import time.
  - Figure handles always closed in `finally` to prevent memory leaks.
  - Single-pass tessellation: geometry triangulated once and reused across all views.
"""

# ── Backend must be set BEFORE any other matplotlib import ──────────────────
import matplotlib
matplotlib.use("Agg")
# ────────────────────────────────────────────────────────────────────────────

import logging
from pathlib import Path
from typing import Optional, Union

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np

log = logging.getLogger(__name__)


# ── Semantic face colour palette ─────────────────────────────────────────────
#  Keys match the face_id strings produced by generate_cad_model.
_FACE_COLORS: dict[str, str] = {
    "FACE_MIN_X": "#4A90D9",   # Steel blue   — typical fixed/support face
    "FACE_MAX_X": "#E05252",   # Tomato red   — typical load application face
    "FACE_MIN_Y": "#C8C8C8",   # Light grey   — bottom
    "FACE_MAX_Y": "#E0E0E0",   # Lighter grey — top
    "FACE_MIN_Z": "#BBBBBB",   # Mid grey     — back
    "FACE_MAX_Z": "#D5D5D5",   # Mid-light    — front
}
_DEFAULT_COLOR = "#AAAAAA"

# ── View specifications ──────────────────────────────────────────────────────
# Format: view_id -> (title, elev, azim, hidden_axis, default_show_labels)
_VIEW_SPECS: dict[str, tuple[str, float, float, Optional[str], bool]] = {
    "iso":    ("Isometric 3D View", 28.0, 45.0, None, True),
    "top":    ("Top View (XY · Look Down -Z)", 90.0, -90.0, "z", False),
    "bottom": ("Bottom View (XY · Look Up +Z)", -90.0, -90.0, "z", False),
    "front":  ("Front View (XZ · Look Along +Y)", 0.0, -90.0, "y", False),
    "right":  ("Right View (YZ · Look Along -X)", 0.0, 0.0, "x", False),
    "back":   ("Back View (XZ · Look Along -Y)", 0.0, 90.0, "y", False),
}

SUPPORTED_VIEW_MODES = ("ortho6", "quad", "single")


def _get_face_color(face_id: Optional[str]) -> str:
    """Return the display colour for a given semantic face ID."""
    if face_id is None:
        return _DEFAULT_COLOR
    return _FACE_COLORS.get(face_id, _DEFAULT_COLOR)


def _classify_face(face, bounding_box) -> Optional[str]:
    """
    Classify a build123d Face into a semantic face ID using its centroid
    relative to the bounding box of the overall shape.

    Returns one of the six FACE_* constants, or None if classification fails.
    """
    try:
        centroid = face.center()
        cx, cy, cz = centroid.X, centroid.Y, centroid.Z

        bb = bounding_box
        xmin, xmax = bb.min.X, bb.max.X
        ymin, ymax = bb.min.Y, bb.max.Y
        zmin, zmax = bb.min.Z, bb.max.Z

        # Tolerances: 15% of each dimension
        tol_x = max((xmax - xmin) * 0.15, 0.1)
        tol_y = max((ymax - ymin) * 0.15, 0.1)
        tol_z = max((zmax - zmin) * 0.15, 0.1)

        if abs(cx - xmin) < tol_x:
            return "FACE_MIN_X"
        if abs(cx - xmax) < tol_x:
            return "FACE_MAX_X"
        if abs(cy - ymin) < tol_y:
            return "FACE_MIN_Y"
        if abs(cy - ymax) < tol_y:
            return "FACE_MAX_Y"
        if abs(cz - zmin) < tol_z:
            return "FACE_MIN_Z"
        if abs(cz - zmax) < tol_z:
            return "FACE_MAX_Z"
        return None
    except Exception:
        return None


def _tessellate_face(face, tolerances=(0.1, 0.5, 1.0)):
    """
    Tessellate a build123d Face into triangles, retrying with progressively
    coarser tolerances if fine tessellation fails or returns empty.

    Returns a list of triangle vertex triples, or an empty list on failure.
    """
    for tol in tolerances:
        try:
            vertices, triangles = face.tessellate(tol)
            if not vertices or not triangles:
                continue
            tri_list = []
            for tri in triangles:
                pts = [
                    np.array([vertices[i].X, vertices[i].Y, vertices[i].Z])
                    for i in tri
                ]
                tri_list.append(pts)
            if tri_list:
                return tri_list
        except Exception as e:
            log.debug("Tessellation at tolerance %.2f failed: %s", tol, e)
            continue
    return []


def _style_and_populate_axis(
    ax,
    view_spec: tuple[str, float, float, Optional[str], bool],
    poly_verts: list,
    poly_colors: list,
    label_positions: list[tuple[float, float, float, str, str]],
    xlim: tuple[float, float],
    ylim: tuple[float, float],
    zlim: tuple[float, float],
    force_labels: Optional[bool] = None,
):
    """
    Populate a single 3D Axes with tessellated geometry, orientation, and styling.
    """
    title, elev, azim, hidden_axis, default_show_labels = view_spec
    show_labels = default_show_labels if force_labels is None else force_labels

    ax.view_init(elev=elev, azim=azim)
    ax.set_proj_type("ortho")
    ax.set_xlim(xlim)
    ax.set_ylim(ylim)
    ax.set_zlim(zlim)

    # 1. Add tessellated faces
    for triangles, color in zip(poly_verts, poly_colors):
        col = Poly3DCollection(
            triangles,
            alpha=0.90,
            facecolor=color,
            edgecolor="#2A2A44",
            linewidth=0.2,
        )
        ax.add_collection3d(col)

    # 2. Add semantic face badges if enabled
    if show_labels and label_positions:
        seen_ids: set[str] = set()
        for lx, ly, lz, face_id, desc in label_positions:
            if face_id in seen_ids:
                continue
            seen_ids.add(face_id)
            ax.text(
                lx, ly, lz,
                face_id,
                fontsize=6.5,
                color="white",
                fontweight="bold",
                ha="center",
                va="center",
                bbox=dict(
                    boxstyle="round,pad=0.22",
                    facecolor=_get_face_color(face_id),
                    alpha=0.85,
                    edgecolor="none",
                ),
                zorder=10,
            )

    # 3. Styling — panes & grid
    ax.xaxis.pane.fill = False
    ax.yaxis.pane.fill = False
    ax.zaxis.pane.fill = False
    ax.xaxis.pane.set_edgecolor("#2A2A4A")
    ax.yaxis.pane.set_edgecolor("#2A2A4A")
    ax.zaxis.pane.set_edgecolor("#2A2A4A")
    ax.grid(True, color="#25253E", linewidth=0.4)

    # 4. Hide perpendicular projection axis to prevent tick clutter
    if hidden_axis == "z":
        ax.set_xlabel("X (mm)", color="#8888AA", fontsize=7.5, labelpad=2)
        ax.set_ylabel("Y (mm)", color="#8888AA", fontsize=7.5, labelpad=2)
        ax.set_zticklabels([])
        ax.set_zlabel("")
        ax.zaxis.line.set_lw(0.0)
        ax.zaxis.pane.set_visible(False)
    elif hidden_axis == "y":
        ax.set_xlabel("X (mm)", color="#8888AA", fontsize=7.5, labelpad=2)
        ax.set_zlabel("Z (mm)", color="#8888AA", fontsize=7.5, labelpad=2)
        ax.set_yticklabels([])
        ax.set_ylabel("")
        ax.yaxis.line.set_lw(0.0)
        ax.yaxis.pane.set_visible(False)
    elif hidden_axis == "x":
        ax.set_ylabel("Y (mm)", color="#8888AA", fontsize=7.5, labelpad=2)
        ax.set_zlabel("Z (mm)", color="#8888AA", fontsize=7.5, labelpad=2)
        ax.set_xticklabels([])
        ax.set_xlabel("")
        ax.xaxis.line.set_lw(0.0)
        ax.xaxis.pane.set_visible(False)
    else:
        # Full 3D Isometric View
        ax.set_xlabel("X (mm)", color="#8888AA", fontsize=7.5, labelpad=4)
        ax.set_ylabel("Y (mm)", color="#8888AA", fontsize=7.5, labelpad=4)
        ax.set_zlabel("Z (mm)", color="#8888AA", fontsize=7.5, labelpad=4)

    ax.tick_params(colors="#666688", labelsize=6.5, pad=1)
    for spine in ax.spines.values():
        spine.set_edgecolor("#333355")

    ax.set_title(title, color="#E2E8F0", fontsize=8.5, fontweight="bold", pad=4)


def render_step_preview(
    step_path: Union[Path, str],
    output_path: Union[Path, str],
    semantic_faces: Optional[list] = None,
    label_faces: bool = True,
    view_mode: str = "ortho6",
    export_individual: bool = True,
    dpi: int = 150,
    figure_size: Optional[tuple[int, int]] = None,
) -> bool:
    """
    Render offscreen multi-view 3D previews of a STEP file and save as PNG.

    This function is the primary public entry point. It is a pure function:
    it reads from ``step_path``, writes to ``output_path`` (and optional individual
    sibling views), and has no persistent side effects. It never raises — all
    exceptions are caught and logged; the return value indicates success or failure.

    Args:
        step_path:         Absolute path to an existing ``geometry.step`` file.
        output_path:       Absolute path where ``preview.png`` will be written.
                           The parent directory must already exist.
        semantic_faces:    Optional list of face dicts from ``metadata.json``
                           (keys: ``face_id``, ``normal``, ``center_mm``, ``description``).
        label_faces:       If ``True`` (default), annotate semantic face badges.
        view_mode:         Layout of composite image:
                           - ``"ortho6"`` or ``"all"`` (default): 2x3 grid with Top,
                             Isometric, Bottom, Front, Right, Back views.
                           - ``"quad"``: 2x2 grid with Top, Isometric, Front, Right.
                           - ``"single"`` or ``"isometric"``: Single isometric view.
        export_individual: If ``True`` (default), also exports individual view
                           images (``preview_iso.png``, ``preview_top.png``, etc.)
                           into the same directory as ``output_path``.
        dpi:               Output image resolution (default 150 DPI).
        figure_size:       Optional Matplotlib figure size ``(width, height)`` in inches.

    Returns:
        ``True`` if ``output_path`` was written successfully.
        ``False`` on any failure (missing input, tessellation error, I/O error).
    """
    # ── Pre-flight checks ────────────────────────────────────────────────────
    step_path = Path(step_path)
    output_path = Path(output_path)

    if not step_path.exists():
        log.warning("render_step_preview: STEP file not found: %s", step_path)
        return False

    if step_path.stat().st_size == 0:
        log.warning("render_step_preview: STEP file is empty: %s", step_path)
        return False

    # ── Normalize view mode ──────────────────────────────────────────────────
    mode = view_mode.lower()
    if mode in ("all", "ortho6", "6view", "hex"):
        mode = "ortho6"
    elif mode in ("quad", "4view", "2x2"):
        mode = "quad"
    elif mode in ("single", "iso", "isometric", "1view"):
        mode = "single"
    else:
        log.warning("render_step_preview: Unknown view_mode '%s'; defaulting to 'ortho6'", view_mode)
        mode = "ortho6"

    # ── Import build123d lazily ──────────────────────────────────────────────
    try:
        import build123d as b3d
    except ImportError as e:
        log.warning("render_step_preview: build123d not available: %s", e)
        return False

    # Track all open figures to ensure zero figure leaks in `finally`
    open_figures: list[plt.Figure] = []

    try:
        # 1. Import STEP
        log.debug("Importing STEP: %s", step_path)
        shape = b3d.import_step(str(step_path))
        if shape is None:
            log.warning("render_step_preview: import_step returned None for %s", step_path)
            return False

        # 2. Bounding box & uniform aspect span
        bb = shape.bounding_box()
        dx = bb.max.X - bb.min.X
        dy = bb.max.Y - bb.min.Y
        dz = bb.max.Z - bb.min.Z
        cx = (bb.min.X + bb.max.X) / 2.0
        cy = (bb.min.Y + bb.max.Y) / 2.0
        cz = (bb.min.Z + bb.max.Z) / 2.0

        span = max(dx, dy, dz) / 2.0 * 1.15
        xlim = (cx - span, cx + span)
        ylim = (cy - span, cy + span)
        zlim = (cz - span, cz + span)

        # 3. Tessellate each face once
        poly_verts = []
        poly_colors = []
        label_positions: list[tuple[float, float, float, str, str]] = []

        for face in shape.faces():
            face_id = _classify_face(face, bb)
            color = _get_face_color(face_id)
            triangles = _tessellate_face(face)
            if not triangles:
                continue

            poly_verts.append(triangles)
            poly_colors.append(color)

            if label_faces and face_id is not None:
                try:
                    c = face.center()
                    label_positions.append((c.X, c.Y, c.Z, face_id, face_id))
                except Exception:
                    pass

        if not poly_verts:
            log.warning("render_step_preview: No tessellated faces produced for %s", step_path)
            return False

        # 4. Override label positions from metadata.json if supplied
        if semantic_faces and label_faces:
            label_positions = []
            for fd in semantic_faces:
                face_id = fd.get("face_id", "")
                center = fd.get("center_mm")
                desc = fd.get("description", face_id)
                if center and len(center) == 3:
                    label_positions.append((center[0], center[1], center[2], face_id, desc))

        # ── Render Composite Figure ──────────────────────────────────────────
        envelope_str = f"Envelope: {dx:.1f} × {dy:.1f} × {dz:.1f} mm"

        if mode == "ortho6":
            figsize = figure_size or (15, 10)
            fig = plt.figure(figsize=figsize, facecolor="#141424")
            open_figures.append(fig)

            fig.suptitle(
                f"CAD Multi-View Inspection Sheet  ·  {envelope_str}",
                color="#F8FAFC",
                fontsize=11.5,
                fontweight="bold",
                y=0.97,
            )

            views_layout = [
                ("top", 1),
                ("iso", 2),
                ("bottom", 3),
                ("front", 4),
                ("right", 5),
                ("back", 6),
            ]
            for vid, pos in views_layout:
                ax = fig.add_subplot(2, 3, pos, projection="3d", facecolor="#141424")
                vspec = _VIEW_SPECS[vid]
                _style_and_populate_axis(
                    ax=ax,
                    view_spec=vspec,
                    poly_verts=poly_verts,
                    poly_colors=poly_colors,
                    label_positions=label_positions,
                    xlim=xlim,
                    ylim=ylim,
                    zlim=zlim,
                    force_labels=vspec[4] if label_faces else False,
                )

            # Shared Legend at bottom
            legend_entries = [
                mpatches.Patch(color=color, label=fid)
                for fid, color in _FACE_COLORS.items()
            ]
            fig.legend(
                handles=legend_entries,
                loc="lower center",
                ncol=6,
                fontsize=7.5,
                framealpha=0.6,
                facecolor="#141424",
                edgecolor="#333355",
                labelcolor="#F1F5F9",
                bbox_to_anchor=(0.5, 0.015),
            )
            fig.subplots_adjust(left=0.04, right=0.96, top=0.92, bottom=0.08, wspace=0.20, hspace=0.25)

        elif mode == "quad":
            figsize = figure_size or (11, 10)
            fig = plt.figure(figsize=figsize, facecolor="#141424")
            open_figures.append(fig)

            fig.suptitle(
                f"CAD Multi-View Quad Sheet  ·  {envelope_str}",
                color="#F8FAFC",
                fontsize=11.0,
                fontweight="bold",
                y=0.97,
            )

            quad_views = [
                ("top", 1),
                ("iso", 2),
                ("front", 3),
                ("right", 4),
            ]
            for vid, pos in quad_views:
                ax = fig.add_subplot(2, 2, pos, projection="3d", facecolor="#141424")
                vspec = _VIEW_SPECS[vid]
                _style_and_populate_axis(
                    ax=ax,
                    view_spec=vspec,
                    poly_verts=poly_verts,
                    poly_colors=poly_colors,
                    label_positions=label_positions,
                    xlim=xlim,
                    ylim=ylim,
                    zlim=zlim,
                    force_labels=vspec[4] if label_faces else False,
                )

            legend_entries = [
                mpatches.Patch(color=color, label=fid)
                for fid, color in _FACE_COLORS.items()
            ]
            fig.legend(
                handles=legend_entries,
                loc="lower center",
                ncol=6,
                fontsize=7.0,
                framealpha=0.6,
                facecolor="#141424",
                edgecolor="#333355",
                labelcolor="#F1F5F9",
                bbox_to_anchor=(0.5, 0.015),
            )
            fig.subplots_adjust(left=0.05, right=0.95, top=0.92, bottom=0.08, wspace=0.22, hspace=0.25)

        else:  # single view mode
            figsize = figure_size or (9, 7)
            fig = plt.figure(figsize=figsize, facecolor="#141424")
            open_figures.append(fig)

            ax = fig.add_subplot(111, projection="3d", facecolor="#141424")
            vspec = _VIEW_SPECS["iso"]
            _style_and_populate_axis(
                ax=ax,
                view_spec=vspec,
                poly_verts=poly_verts,
                poly_colors=poly_colors,
                label_positions=label_positions,
                xlim=xlim,
                ylim=ylim,
                zlim=zlim,
                force_labels=label_faces,
            )
            ax.set_title(f"Geometry Preview  ·  {envelope_str}", color="white", fontsize=9.5, pad=10)

            legend_entries = [
                mpatches.Patch(color=color, label=fid)
                for fid, color in _FACE_COLORS.items()
            ]
            ax.legend(
                handles=legend_entries,
                loc="upper left",
                fontsize=7.0,
                framealpha=0.5,
                facecolor="#141424",
                edgecolor="#333355",
                labelcolor="white",
            )
            fig.subplots_adjust(left=0.05, right=0.95, top=0.92, bottom=0.08)

        # Save composite image
        fig.savefig(
            str(output_path),
            dpi=dpi,
            facecolor=fig.get_facecolor(),
        )
        log.info("render_step_preview: composite preview written to %s (mode=%s)", output_path, mode)

        # ── Render Individual Views (if requested) ───────────────────────────
        if export_individual:
            out_dir = output_path.parent
            base_stem = output_path.stem  # usually "preview"

            for vid, vspec in _VIEW_SPECS.items():
                ind_path = out_dir / f"{base_stem}_{vid}.png"
                fig_ind = plt.figure(figsize=(7, 6), facecolor="#141424")
                open_figures.append(fig_ind)

                ax_ind = fig_ind.add_subplot(111, projection="3d", facecolor="#141424")
                _style_and_populate_axis(
                    ax=ax_ind,
                    view_spec=vspec,
                    poly_verts=poly_verts,
                    poly_colors=poly_colors,
                    label_positions=label_positions,
                    xlim=xlim,
                    ylim=ylim,
                    zlim=zlim,
                    force_labels=label_faces,
                )
                ax_ind.set_title(f"{vspec[0]}  ·  {envelope_str}", color="#F8FAFC", fontsize=8.5, pad=6)

                fig_ind.savefig(
                    str(ind_path),
                    dpi=dpi,
                    bbox_inches="tight",
                    facecolor=fig_ind.get_facecolor(),
                )
                log.debug("render_step_preview: individual view written to %s", ind_path)

        return True

    except Exception as e:
        log.warning("render_step_preview: unexpected error: %s", e, exc_info=True)
        return False

    finally:
        # CRITICAL: Always release every figure handle to prevent memory leaks
        for f in open_figures:
            try:
                plt.close(f)
            except Exception:
                pass
