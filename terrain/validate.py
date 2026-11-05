"""Read-only terrain coverage and collision audit for a USD scene."""
import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from terrain.generate import crop_pad, read_config


def validate(scene: Path) -> list[str]:
    try:
        from pxr import Usd, UsdGeom, UsdPhysics
    except ImportError as exc:
        raise RuntimeError("Run with Isaac Sim Python or install usd-core") from exc
    stage = Usd.Stage.Open(str(scene))
    if not stage:
        return [f"Cannot open stage: {scene}"]
    problems = []
    path = "/Lunalab/Terrain/terrain_mesh"
    prim = stage.GetPrimAtPath(path)
    if not prim or not prim.IsValid():
        return [f"Missing terrain prim {path}"]
    mesh = UsdGeom.Mesh(prim)
    counts = list(mesh.GetFaceVertexCountsAttr().Get() or [])
    indices = list(mesh.GetFaceVertexIndicesAttr().Get() or [])
    points = list(mesh.GetPointsAttr().Get() or [])
    if not points or not counts or sum(counts) != len(indices):
        problems.append("Mesh points/faces/indices are empty or inconsistent")
    if any(n != 3 for n in counts):
        problems.append("Terrain mesh contains non-triangle faces")
    config = read_config()
    source = np.load(ROOT / config["source_dem"], allow_pickle=False)
    if config.get("input_policy") == "transpose_then_crop_zero_pad":
        source = source.T
    resolution = float(config["resolution_m"])
    width = round(float(config["width_m"]) / resolution)
    height = round(float(config["length_m"]) / resolution)
    expected = crop_pad(source, height, width).astype(np.float32).ravel()
    actual = np.asarray(points, dtype=np.float32)
    if actual.shape != (expected.size, 3) or not np.allclose(actual[:, 2], expected, atol=1e-6):
        problems.append("Terrain elevations do not match the configured DEM orientation and grid")
    if not prim.HasAPI(UsdPhysics.CollisionAPI):
        problems.append("Terrain mesh lacks CollisionAPI")
    else:
        approximation = prim.GetAttribute("physics:approximation").Get()
        if str(approximation) not in ("none", "MeshApproximation.NONE"):
            problems.append(f"Expected triangle mesh approximation 'none'; got {approximation!r}")
        if prim.GetAttribute("physics:collisionEnabled").Get() is False:
            problems.append("Terrain collision is disabled")
    if "PhysicsMeshCollisionAPI" not in prim.GetAppliedSchemas():
        problems.append("Terrain mesh lacks PhysicsMeshCollisionAPI")
    colliders = [p.GetPath().pathString for p in stage.Traverse()
                 if p.HasAPI(UsdPhysics.CollisionAPI) and str(p.GetPath()).startswith("/Lunalab/Terrain/")]
    if colliders != [path]:
        problems.append(f"Expected exactly one terrain collider ({path}); found {colliders}")
    rock_meshes = [p for p in stage.Traverse()
                   if p.IsA(UsdGeom.Mesh) and str(p.GetPath()).startswith("/package/rock")]
    rock_colliders = []
    for rock in rock_meshes:
        if (rock.HasAPI(UsdPhysics.CollisionAPI)
                and "PhysicsMeshCollisionAPI" in rock.GetAppliedSchemas()
                and rock.GetAttribute("physics:collisionEnabled").Get() is True
                and rock.GetAttribute("physics:approximation").Get() == "convexHull"):
            rock_colliders.append(str(rock.GetPath()))
    if len(rock_meshes) != 7 or len(rock_colliders) != len(rock_meshes):
        problems.append(
            f"Expected enabled convex-hull colliders on all seven placed rock meshes; "
            f"found {len(rock_colliders)} of {len(rock_meshes)}"
        )
    body = prim.GetAppliedSchemas()
    if any("RigidBodyAPI" in schema for schema in body):
        problems.append("Static terrain unexpectedly has RigidBodyAPI")
    forbidden = stage.GetPrimAtPath("/World/Lab/Lab/CurvedWall/Cube_003")
    if forbidden and forbidden.IsValid() and forbidden.IsActive():
        problems.append("Cube_003 unexpectedly exists; do not auto-delete it")
    print(f"Scene: {scene}\nTerrain points={len(points)} faces={len(counts)} indices={len(indices)}\n"
          f"Terrain colliders={colliders}\nPlaced rock meshes={len(rock_meshes)} colliders={len(rock_colliders)}")
    return problems

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("scene", nargs="?", default="scenes/CAMERASYNCSSMOETIMES.usd", type=Path)
    args = parser.parse_args()
    issues = validate(args.scene)
    for issue in issues: print(f"ERROR: {issue}")
    raise SystemExit(bool(issues))
