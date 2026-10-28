"""
Headless offscreen 3D STEP file visualizer for Materials-MCP.

Reads a geometry.step file from a run directory, tessellates each
topological face using build123d's OCC kernel, and renders an isometric
preview.png using matplotlib's Agg backend.

Design invariants:
  - Pure function: reads step_path, writes output_path, no global state.
  - Never raises: all exceptions are caught; returns False on failure.
  - No X11/display dependencies: Agg backend enforced at import time.
  - Figure handles always closed in `finally` to prevent memory leaks.
"""

# ── Backend must be set BEFORE any other matplotlib import ──────────────────
import matplotlib
matplotlib.use("Agg")
# ────────────────────────────────────────────────────────────────────────────

import logging
from pathlib import Path
from typing import Optional

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
            # Convert to list of (v0, v1, v2) vertex triples (numpy arrays)
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


def render_step_preview(
    step_path: Path,
    output_path: Path,
    semantic_faces: Optional[list] = None,
    label_faces: bool = True,
    dpi: int = 150,
    figure_size: tuple = (10, 8),
) -> bool:
    """
    Render an isometric 3D preview of a STEP file and save as PNG.

    This function is the single public entry point of this module. It is a
    pure function: it reads from ``step_path``, writes to ``output_path``,
    and has no persistent side effects. It never raises — all exceptions are
    caught and logged; the return value indicates success or failure.

    Args:
        step_path:      Absolute path to an existing ``geometry.step`` file.
        output_path:    Absolute path where ``preview.png`` will be written.
                        The parent directory must already exist.
        semantic_faces: Optional list of face dicts from ``metadata.json``
                        (expected keys: ``face_id``, ``normal``,
                        ``center_mm``, ``description``). When supplied,
                        face labels are anchored to the provided centroids
                        rather than computed from the geometry centroid.
        label_faces:    If ``True`` (default), annotate the six canonical
                        semantic face positions with text labels.
        dpi:            Output image resolution (default 150 DPI).
        figure_size:    Matplotlib figure size in inches ``(width, height)``.

    Returns:
        ``True`` if ``output_path`` was written successfully.
        ``False`` on any failure (missing input, tessellation error, I/O
        error). A warning is logged in all failure cases.
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

    # ── Import build123d only when needed (avoid top-level OCC init cost) ───
    try:
        import build123d as b3d
    except ImportError as e:
        log.warning("render_step_preview: build123d not available: %s", e)
        return False

    # ── Main render block ────────────────────────────────────────────────────
    fig = None
    try:
        # 1. Import STEP
        log.debug("Importing STEP: %s", step_path)
        shape = b3d.import_step(str(step_path))
        if shape is None:
            log.warning("render_step_preview: import_step returned None for %s", step_path)
            return False

        # 2. Get bounding box for face classification & axis limits
        bounding_box = shape.bounding_box()

        # 3. Tessellate each face
        poly_verts = []   # list of triangle vertex lists per collection
        poly_colors = []  # matching colour for each polygon collection

        label_positions: list[tuple[float, float, float, str, str]] = []
        # (x, y, z, face_id, description)

        for face in shape.faces():
            face_id = _classify_face(face, bounding_box)
            color = _get_face_color(face_id)

            triangles = _tessellate_face(face)
            if not triangles:
                log.debug("Skipping face %s — tessellation returned no triangles.", face_id)
                continue

            poly_verts.append(triangles)
            poly_colors.append(color)

            # Record centroid for label placement (from geometry centroid)
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

        # 5. Build matplotlib figure
        fig = plt.figure(figsize=figure_size, facecolor="#1A1A2E")
        ax = fig.add_subplot(111, projection="3d", facecolor="#1A1A2E")

        # 6. Add each face as a Poly3DCollection
        for triangles, color in zip(poly_verts, poly_colors):
            col = Poly3DCollection(
                triangles,
                alpha=0.88,
                facecolor=color,
                edgecolor="#333355",
                linewidth=0.2,
            )
            ax.add_collection3d(col)

        # 7. Set axis limits from bounding box
        bb = bounding_box
        padding = max(
            bb.max.X - bb.min.X,
            bb.max.Y - bb.min.Y,
            bb.max.Z - bb.min.Z,
        ) * 0.1

        ax.set_xlim(bb.min.X - padding, bb.max.X + padding)
        ax.set_ylim(bb.min.Y - padding, bb.max.Y + padding)
        ax.set_zlim(bb.min.Z - padding, bb.max.Z + padding)

        # 8. Isometric view angle
        ax.view_init(elev=28, azim=45)
        ax.set_proj_type("ortho")

        # 9. Styling — dark theme with subtle grid
        ax.set_xlabel("X (mm)", color="#8888AA", fontsize=8, labelpad=6)
        ax.set_ylabel("Y (mm)", color="#8888AA", fontsize=8, labelpad=6)
        ax.set_zlabel("Z (mm)", color="#8888AA", fontsize=8, labelpad=6)
        ax.tick_params(colors="#666688", labelsize=7)
        for spine in ax.spines.values():
            spine.set_edgecolor("#333355")
        ax.xaxis.pane.fill = False
        ax.yaxis.pane.fill = False
        ax.zaxis.pane.fill = False
        ax.xaxis.pane.set_edgecolor("#2A2A4A")
        ax.yaxis.pane.set_edgecolor("#2A2A4A")
        ax.zaxis.pane.set_edgecolor("#2A2A4A")
        ax.grid(True, color="#2A2A4A", linewidth=0.5)

        # 10. Face labels (deduped — one label per face_id)
        if label_faces:
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
                        boxstyle="round,pad=0.25",
                        facecolor=_get_face_color(face_id),
                        alpha=0.85,
                        edgecolor="none",
                    ),
                    zorder=10,
                )

        # 11. Legend for semantic face colours
        legend_entries = [
            mpatches.Patch(color=color, label=fid)
            for fid, color in _FACE_COLORS.items()
        ]
        ax.legend(
            handles=legend_entries,
            loc="upper left",
            fontsize=6.5,
            framealpha=0.5,
            facecolor="#1A1A2E",
            edgecolor="#333355",
            labelcolor="white",
        )

        # 12. Title
        bb_dims = (
            f"{bb.max.X - bb.min.X:.1f} × "
            f"{bb.max.Y - bb.min.Y:.1f} × "
            f"{bb.max.Z - bb.min.Z:.1f} mm"
        )
        ax.set_title(
            f"Geometry Preview  ·  {bb_dims}",
            color="white",
            fontsize=9,
            pad=10,
        )

        # 13. Save
        fig.savefig(
            str(output_path),
            dpi=dpi,
            bbox_inches="tight",
            facecolor=fig.get_facecolor(),
        )
        log.info("render_step_preview: preview written to %s", output_path)
        return True

    except Exception as e:
        log.warning("render_step_preview: unexpected error: %s", e, exc_info=True)
        return False

    finally:
        # CRITICAL: always release the figure to prevent memory leaks in
        # long-running MCP server processes.
        if fig is not None:
            plt.close(fig)
