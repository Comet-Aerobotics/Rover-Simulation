"""Regression checks for the authored camera graph (no Isaac runtime required)."""
from pathlib import Path
import tempfile
import unittest

try:
    from pxr import Gf, Sdf, Usd
    from isaac.diagnostics.validate_action_graph import validate
except ImportError:
    Usd = None


ROOT = Path(__file__).resolve().parents[2]
SCENE = ROOT / "scenes/CAMERASYNCSSMOETIMES.usd"
CAMERA = "/jackal/base_link/DM9098Pro_enclosure/OAK_D_Pro_RGB"


@unittest.skipIf(Usd is None, "usd-core is required")
class CameraGraphTests(unittest.TestCase):
    def check_mutation(self, mutate, expected):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "override.usda"
            layer = Sdf.Layer.CreateNew(str(path))
            layer.subLayerPaths = [str(SCENE).replace("\\", "/")]
            layer.Save()
            stage = Usd.Stage.Open(str(path))
            mutate(stage)
            stage.GetRootLayer().Save()
            self.assertTrue(any(expected in issue for issue in validate(path, local_jackal=True)))

    def test_canonical_graph_passes(self):
        self.assertEqual(validate(SCENE, local_jackal=True), [])

    def test_detects_camera_far_from_mount(self):
        self.check_mutation(
            lambda stage: stage.GetPrimAtPath(CAMERA).GetAttribute("xformOp:translate").Set(Gf.Vec3d(1e9, 0, 0)),
            "from its mount",
        )

    def test_detects_wrong_camera_target(self):
        self.check_mutation(
            lambda stage: stage.GetPrimAtPath("/ActionGraph/CreateRP").GetRelationship("inputs:cameraPrim").SetTargets(["/World/Cameras/FrontView"]),
            "camera target",
        )

    def test_detects_missing_rgb_render_product_connection(self):
        self.check_mutation(
            lambda stage: stage.GetPrimAtPath("/ActionGraph/RGBHelper").GetAttribute("inputs:renderProductPath").SetConnections([]),
            "inputs:renderProductPath",
        )


if __name__ == "__main__":
    unittest.main()
