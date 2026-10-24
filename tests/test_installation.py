"""
Test suite to verify local and CI installation of Materials-MCP dependencies:
1. CalculiX (ccx) solver availability
2. build123d CAD generation & STEP export
3. Gmsh meshing pipeline
4. Integrated CAD -> Mesh workflow
"""

import os
import subprocess
import tempfile
import unittest


class TestInstallation(unittest.TestCase):
    def test_01_calculix_solver(self):
        """Verify CalculiX ccx CLI solver is installed and executable."""
        try:
            result = subprocess.run(
                ["ccx", "-v"],
                capture_output=True,
                text=True,
                check=False
            )
            combined_output = (result.stdout + result.stderr).lower()
            self.assertIn(
                "version",
                combined_output,
                f"Expected CalculiX version output, got: {combined_output}"
            )
        except FileNotFoundError:
            self.fail("CalculiX solver binary 'ccx' not found in PATH.")

    def test_02_build123d_cad(self):
        """Verify build123d can model 3D geometry and export to STEP."""
        import build123d as b3d

        with tempfile.TemporaryDirectory() as tmpdir:
            step_file = os.path.join(tmpdir, "test_beam.step")
            beam = b3d.Box(100.0, 20.0, 10.0)
            self.assertIsNotNone(beam)
            self.assertAlmostEqual(beam.volume, 100.0 * 20.0 * 10.0, delta=1.0)

            b3d.export_step(beam, step_file)
            self.assertTrue(os.path.exists(step_file))
            self.assertGreater(os.path.getsize(step_file), 0)

    def test_03_gmsh_meshing(self):
        """Verify Gmsh Python API can initialize and mesh a simple 3D shape."""
        import gmsh

        gmsh.initialize()
        try:
            gmsh.option.setNumber("General.Terminal", 0)
            gmsh.model.add("test_box")
            gmsh.model.occ.addBox(0, 0, 0, 50, 10, 10)
            gmsh.model.occ.synchronize()
            gmsh.model.mesh.generate(3)

            # Node count and element count check
            node_tags, _, _ = gmsh.model.mesh.getNodes()
            self.assertGreater(len(node_tags), 0, "Gmsh produced 0 mesh nodes.")
        finally:
            gmsh.finalize()

    def test_04_integrated_cad_to_mesh(self):
        """Verify build123d STEP export can be imported and meshed by Gmsh."""
        import build123d as b3d
        import gmsh

        with tempfile.TemporaryDirectory() as tmpdir:
            step_file = os.path.join(tmpdir, "integrated_beam.step")
            beam = b3d.Box(80.0, 15.0, 10.0)
            b3d.export_step(beam, step_file)

            gmsh.initialize()
            try:
                gmsh.option.setNumber("General.Terminal", 0)
                gmsh.open(step_file)
                gmsh.model.mesh.generate(3)

                node_tags, _, _ = gmsh.model.mesh.getNodes()
                self.assertGreater(len(node_tags), 0, "Failed to mesh STEP imported geometry.")
            finally:
                gmsh.finalize()


if __name__ == "__main__":
    unittest.main()
