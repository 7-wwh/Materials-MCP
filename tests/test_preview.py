"""
Test suite for src/preview/renderer.py

Tests cover:
  1. Happy path (default ortho6): composite 2x3 preview.png + 6 individual view PNGs.
  2. Semantic face metadata: passing face dicts overrides label positions.
  3. Disabling face labels (label_faces=False).
  4. Missing STEP file: returns False, no exception raised.
  5. Empty STEP file: returns False, no exception raised.
  6. Memory safety: no matplotlib figures left open after multi-view renders.
  7. No figure leak on failure paths.
  8. Custom DPI support.
  9. Quad view mode (view_mode="quad").
  10. Single view mode (view_mode="single").
  11. Disabling individual view export (export_individual=False).
"""

import os
import struct
import tempfile
import unittest
from pathlib import Path

import matplotlib.pyplot as plt


def _open_figure_count() -> int:
    """Return the number of currently open matplotlib figures."""
    return len(plt.get_fignums())


class TestStepPreviewRenderer(unittest.TestCase):
    """Unit tests for the headless multi-view STEP → PNG renderer."""

    @classmethod
    def setUpClass(cls):
        """
        Build a minimal STEP file once for the entire test class so that
        each individual test doesn't pay the OCC import cost.
        """
        import build123d as b3d

        cls._tmp = tempfile.TemporaryDirectory()
        cls.tmp_dir = Path(cls._tmp.name)

        cls.step_path = cls.tmp_dir / "test_box.step"
        beam = b3d.Box(100.0, 20.0, 10.0)
        b3d.export_step(beam, str(cls.step_path))

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _fresh_run_dir(self) -> Path:
        """Create a dedicated unique subfolder for a run to test sibling file exports."""
        import uuid
        run_dir = self.tmp_dir / f"run_{uuid.uuid4().hex[:8]}"
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

    def _is_valid_png(self, path: Path) -> bool:
        """Check the PNG magic bytes (first 8 bytes)."""
        PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
        try:
            with open(path, "rb") as f:
                return f.read(8) == PNG_MAGIC
        except OSError:
            return False

    # ── Test cases ───────────────────────────────────────────────────────────

    def test_01_happy_path_creates_composite_and_individual_pngs(self):
        """
        render_step_preview with default settings must create the composite
        preview.png (2x3 orthographic sheet) as well as the 6 individual view PNGs.
        """
        from src.preview.renderer import render_step_preview

        run_dir = self._fresh_run_dir()
        output = run_dir / "preview.png"
        result = render_step_preview(self.step_path, output)

        self.assertTrue(result, "render_step_preview should return True on success.")
        self.assertTrue(output.exists(), "preview.png was not created.")
        self.assertGreater(output.stat().st_size, 0, "preview.png is empty.")
        self.assertTrue(self._is_valid_png(output), "preview.png is not a valid PNG.")

        # Check that individual view files were also exported
        expected_views = ["iso", "top", "bottom", "front", "right", "back"]
        for vid in expected_views:
            ind_path = run_dir / f"preview_{vid}.png"
            self.assertTrue(ind_path.exists(), f"Individual view {ind_path.name} was not created.")
            self.assertGreater(ind_path.stat().st_size, 0, f"Individual view {ind_path.name} is empty.")
            self.assertTrue(self._is_valid_png(ind_path), f"{ind_path.name} is not a valid PNG.")

    def test_02_with_semantic_face_metadata(self):
        """
        Passing a semantic_faces list from metadata.json must still produce
        valid images without raising.
        """
        from src.preview.renderer import render_step_preview

        semantic_faces = [
            {
                "face_id": "FACE_MIN_X",
                "normal": [-1.0, 0.0, 0.0],
                "center_mm": [-50.0, 0.0, 0.0],
                "area_mm2": 200.0,
                "description": "Left end face (fixed wall)",
            },
            {
                "face_id": "FACE_MAX_X",
                "normal": [1.0, 0.0, 0.0],
                "center_mm": [50.0, 0.0, 0.0],
                "area_mm2": 200.0,
                "description": "Right end face (load application)",
            },
        ]

        run_dir = self._fresh_run_dir()
        output = run_dir / "preview.png"
        result = render_step_preview(
            self.step_path, output, semantic_faces=semantic_faces, label_faces=True
        )

        self.assertTrue(result)
        self.assertTrue(self._is_valid_png(output))

    def test_03_label_faces_false(self):
        """
        Disabling face labels must still produce valid PNGs.
        """
        from src.preview.renderer import render_step_preview

        run_dir = self._fresh_run_dir()
        output = run_dir / "preview.png"
        result = render_step_preview(self.step_path, output, label_faces=False)

        self.assertTrue(result)
        self.assertTrue(self._is_valid_png(output))

    def test_04_missing_step_file_returns_false(self):
        """
        render_step_preview must return False (not raise) when the STEP
        file does not exist.
        """
        from src.preview.renderer import render_step_preview

        missing = self.tmp_dir / "nonexistent_geometry.step"
        run_dir = self._fresh_run_dir()
        output = run_dir / "preview.png"

        result = render_step_preview(missing, output)

        self.assertFalse(result, "Should return False for missing STEP file.")
        self.assertFalse(output.exists(), "Should not create output for missing input.")

    def test_05_empty_step_file_returns_false(self):
        """
        render_step_preview must return False (not raise) when the STEP
        file exists but is zero bytes.
        """
        from src.preview.renderer import render_step_preview

        empty_step = self.tmp_dir / "empty.step"
        empty_step.write_bytes(b"")
        run_dir = self._fresh_run_dir()
        output = run_dir / "preview.png"

        result = render_step_preview(empty_step, output)

        self.assertFalse(result, "Should return False for zero-byte STEP file.")

    def test_06_no_matplotlib_figure_leak(self):
        """
        Every call to render_step_preview must close all figure handles (both
        composite and individual). The open figure count must be identical before and after.
        """
        from src.preview.renderer import render_step_preview

        before = _open_figure_count()

        # Two back-to-back renders with full 6-view and individual exports
        for _ in range(2):
            run_dir = self._fresh_run_dir()
            output = run_dir / "preview.png"
            render_step_preview(self.step_path, output, export_individual=True)

        after = _open_figure_count()
        self.assertEqual(
            before,
            after,
            f"Figure leak detected: {before} figures before, {after} after render calls.",
        )

    def test_07_no_figure_leak_on_failure(self):
        """
        Even when render fails (missing STEP), no figure handle must leak.
        """
        from src.preview.renderer import render_step_preview

        before = _open_figure_count()
        missing = self.tmp_dir / "ghost.step"
        run_dir = self._fresh_run_dir()
        render_step_preview(missing, run_dir / "preview.png")
        after = _open_figure_count()

        self.assertEqual(before, after, "Figure leak on failure path.")

    def test_08_custom_dpi(self):
        """
        Specifying a non-default DPI must still produce valid PNGs.
        """
        from src.preview.renderer import render_step_preview

        run_dir = self._fresh_run_dir()
        output = run_dir / "preview.png"
        result = render_step_preview(self.step_path, output, dpi=72)

        self.assertTrue(result)
        self.assertTrue(self._is_valid_png(output))

    def test_09_view_mode_quad(self):
        """
        view_mode="quad" must generate a valid 2x2 quad sheet.
        """
        from src.preview.renderer import render_step_preview

        run_dir = self._fresh_run_dir()
        output = run_dir / "preview.png"
        result = render_step_preview(
            self.step_path, output, view_mode="quad", export_individual=False
        )

        self.assertTrue(result)
        self.assertTrue(self._is_valid_png(output))

    def test_10_view_mode_single(self):
        """
        view_mode="single" must generate a single isometric preview image.
        """
        from src.preview.renderer import render_step_preview

        run_dir = self._fresh_run_dir()
        output = run_dir / "preview.png"
        result = render_step_preview(
            self.step_path, output, view_mode="single", export_individual=False
        )

        self.assertTrue(result)
        self.assertTrue(self._is_valid_png(output))

    def test_11_export_individual_false(self):
        """
        When export_individual is False, only preview.png must be created,
        and no preview_<view>.png sibling files.
        """
        from src.preview.renderer import render_step_preview

        run_dir = self._fresh_run_dir()
        output = run_dir / "preview.png"
        result = render_step_preview(
            self.step_path, output, export_individual=False
        )

        self.assertTrue(result)
        self.assertTrue(output.exists())

        # Sibling files should NOT exist
        for vid in ["iso", "top", "bottom", "front", "right", "back"]:
            self.assertFalse(
                (run_dir / f"preview_{vid}.png").exists(),
                f"Sibling preview_{vid}.png should not exist when export_individual=False",
            )


if __name__ == "__main__":
    unittest.main()
