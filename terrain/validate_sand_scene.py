"""Read-only check that the sand scene's visual surface matches its colliders."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from terrain.build_sand_scene import DEFAULT_OUTPUT, TILE_ROOT, tile_bounds, tile_name
from terrain.generate import read_config


def validate(scene: Path) -> list[str]:
    from pxr import Usd, UsdGeom, UsdPhysics

    stage = Usd.Stage.Open(str(scene))
    if not stage:
        return [f"Cannot open stage: {scene}"]
    cfg = read_config()
    resolution = float(cfg["resolution_m"])
    height = round(float(cfg["length_m"]) / resolution)
    width = round(float(cfg["width_m"]) / resolution)
    cells = int(cfg["deformation"]["tile_cells"])
    mesh = UsdGeom.Mesh(stage.GetPrimAtPath(cfg["mesh_prim"]))
    root = stage.GetPrimAtPath(TILE_ROOT)
    if not mesh or not root or not root.IsValid():
        return ["Sand mesh or tile root is missing"]
    problems = []
    points = np.asarray(mesh.GetPointsAttr().Get(), dtype=np.float32)
    if points.shape != (height * width, 3):
        return [f"Terrain points have shape {points.shape}, expected {(height * width, 3)}"]
    points = points.reshape(height, width, 3)
    if UsdPhysics.CollisionAPI(mesh.GetPrim()).GetCollisionEnabledAttr().Get() is not False:
        problems.append("Full visual mesh collider must be disabled")
    expected = list(tile_bounds(height, width, cells))
    if len(root.GetChildren()) != len(expected):
        problems.append(f"Expected {len(expected)} collision tiles, found {len(root.GetChildren())}")
    for row0, row1, col0, col1 in expected:
        path = f"{TILE_ROOT}/{tile_name(row0, col0)}"
        tile = UsdGeom.Mesh(stage.GetPrimAtPath(path))
        if not tile:
            problems.append(f"Missing tile {path}")
            continue
        tile_points = np.asarray(tile.GetPointsAttr().Get(), dtype=np.float32)
        expected_points = points[row0:row1 + 1, col0:col1 + 1].reshape(-1, 3)
        if tile_points.shape != expected_points.shape or not np.allclose(tile_points, expected_points):
            problems.append(f"Tile surface differs from rendered surface: {path}")
        prim = tile.GetPrim()
        if not prim.HasAPI(UsdPhysics.CollisionAPI) or prim.GetAttribute("physics:collisionEnabled").Get() is not True:
            problems.append(f"Tile collision is disabled: {path}")
        if prim.GetAttribute("physics:approximation").Get() != "none":
            problems.append(f"Tile is not a triangle mesh collider: {path}")
        if prim.HasAPI(UsdPhysics.RigidBodyAPI):
            problems.append(f"Tile is not static: {path}")
    print(f"Scene: {scene}\nVisual points={height * width}; collision tiles={len(expected)}")
    return problems


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scene", type=Path, nargs="?", default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        from pxr import Usd  # noqa: F401
        app = None
    except ImportError:
        from isaacsim import SimulationApp
        app = SimulationApp({"headless": True, "width": 32, "height": 32})
    try:
        issues = validate(args.scene)
        for issue in issues:
            print(f"ERROR: {issue}")
    finally:
        if app is not None:
            app.close()
    raise SystemExit(bool(issues))
