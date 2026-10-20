"""
Automated unit tests for workspace artifact directory resolution and file saving.
"""

import shutil
import unittest
from pathlib import Path

from src.paths import PROJECT_ROOT, ARTIFACTS_DIR, get_artifacts_dir, get_run_directory
import build123d as b3d
import gmsh


class TestStorage(unittest.TestCase):
    def test_01_paths_anchored_to_project(self):
        """Verify artifact paths anchor to the Materials-MCP root."""
        self.assertTrue(PROJECT_ROOT.exists(), "PROJECT_ROOT does not exist.")
        self.assertEqual(PROJECT_ROOT.name, "Materials-MCP")

        artifacts = get_artifacts_dir()
        self.assertTrue(artifacts.exists(), "ARTIFACTS_DIR was not created.")
        self.assertEqual(artifacts.parent, PROJECT_ROOT)

    def test_02_run_directory_creation(self):
        """Verify isolated run folders are generated inside artifacts/."""
        run_name = "test_run_isolation"
        run_dir = get_run_directory(run_name, update_latest=False)
        try:
            self.assertTrue(run_dir.exists())
            self.assertEqual(run_dir.parent, ARTIFACTS_DIR)
        finally:
            if run_dir.exists():
                shutil.rmtree(run_dir)

    def test_03_cad_and_mesh_saved_to_workspace(self):
        """Verify build123d and Gmsh save real files into the designated run directory."""
        run_name = "test_cad_mesh_storage"
        run_dir = get_run_directory(run_name, update_latest=False)
        step_file = run_dir / "geometry.step"
        mesh_file = run_dir / "mesh.msh"

        try:
            # 1. Export CAD
            beam = b3d.Box(60.0, 12.0, 8.0)
            b3d.export_step(beam, str(step_file))
            self.assertTrue(step_file.exists())
            self.assertGreater(step_file.stat().st_size, 0)

            # 2. Export Mesh
            gmsh.initialize()
            try:
                gmsh.option.setNumber("General.Terminal", 0)
                gmsh.open(str(step_file))
                gmsh.model.mesh.generate(3)
                gmsh.write(str(mesh_file))

                node_tags, _, _ = gmsh.model.mesh.getNodes()
                self.assertTrue(mesh_file.exists())
                self.assertGreater(mesh_file.stat().st_size, 0)
                self.assertGreater(len(node_tags), 0)
            finally:
                gmsh.finalize()
        finally:
            if run_dir.exists():
                shutil.rmtree(run_dir)


if __name__ == "__main__":
    unittest.main()
