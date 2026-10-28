"""
Test suite for src/preview/renderer.py

Tests cover:
  1. Happy path: Box STEP → preview.png is written, non-empty, valid image.
  2. Semantic face metadata: passing face dicts overrides label positions.
  3. Failure path — missing STEP file: returns False, no exception raised.
  4. Failure path — empty STEP file: returns False, no exception raised.
  5. Memory safety: no matplotlib figures left open after each call.
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
    """Unit tests for the headless STEP → PNG renderer."""

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

    def _fresh_output(self) -> Path:
        """Return a unique output path in the temp directory."""
        import uuid
        return self.tmp_dir / f"preview_{uuid.uuid4().hex[:8]}.png"

    def _is_valid_png(self, path: Path) -> bool:
        """Check the PNG magic bytes (first 8 bytes)."""
        PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
        try:
            with open(path, "rb") as f:
                return f.read(8) == PNG_MAGIC
        except OSError:
            return False

    # ── Test cases ───────────────────────────────────────────────────────────

    def test_01_happy_path_creates_png(self):
        """
        render_step_preview with a valid STEP file must return True and
        write a non-empty PNG to the specified output path.
        """
        from src.preview.renderer import render_step_preview

        output = self._fresh_output()
        result = render_step_preview(self.step_path, output)

        self.assertTrue(result, "render_step_preview should return True on success.")
        self.assertTrue(output.exists(), "preview.png was not created.")
        self.assertGreater(output.stat().st_size, 0, "preview.png is empty.")
        self.assertTrue(self._is_valid_png(output), "Output file is not a valid PNG.")

    def test_02_with_semantic_face_metadata(self):
        """
        Passing a semantic_faces list from metadata.json must still produce
        a valid PNG without raising.
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

        output = self._fresh_output()
        result = render_step_preview(
            self.step_path, output, semantic_faces=semantic_faces, label_faces=True
        )

        self.assertTrue(result)
        self.assertTrue(self._is_valid_png(output))

    def test_03_label_faces_false(self):
        """
        Disabling face labels must still produce a valid PNG.
        """
        from src.preview.renderer import render_step_preview

        output = self._fresh_output()
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
        output = self._fresh_output()

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
        output = self._fresh_output()

        result = render_step_preview(empty_step, output)

        self.assertFalse(result, "Should return False for zero-byte STEP file.")

    def test_06_no_matplotlib_figure_leak(self):
        """
        Every call to render_step_preview must close its figure handle.
        The number of open figures must be identical before and after.
        """
        from src.preview.renderer import render_step_preview

        before = _open_figure_count()

        # Two back-to-back renders
        for _ in range(2):
            output = self._fresh_output()
            render_step_preview(self.step_path, output)

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
        render_step_preview(missing, self._fresh_output())
        after = _open_figure_count()

        self.assertEqual(before, after, "Figure leak on failure path.")

    def test_08_custom_dpi(self):
        """
        Specifying a non-default DPI must still produce a valid PNG.
        """
        from src.preview.renderer import render_step_preview

        output = self._fresh_output()
        result = render_step_preview(self.step_path, output, dpi=72)

        self.assertTrue(result)
        self.assertTrue(self._is_valid_png(output))


if __name__ == "__main__":
    unittest.main()
