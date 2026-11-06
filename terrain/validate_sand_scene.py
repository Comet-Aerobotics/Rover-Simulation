"""Read-only check that visible sand tiles match collision and height bounds."""
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
    if len(mesh.GetFaceVertexCountsAttr().Get()) or len(mesh.GetFaceVertexIndicesAttr().Get()):
        problems.append("Original terrain faces must be removed so tiled ruts are visible")
    if root.GetCustomDataByKey("sand:representation") != "visible_collision_tiles_v1":
        problems.append("Sand tile representation is outdated")
    expected = list(tile_bounds(height, width, cells))
    tiled_height = np.full((height, width), np.nan, dtype=np.float32)
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
        if tile_points.shape != expected_points.shape:
            problems.append(f"Tile has wrong point count: {path}")
            continue
        if not np.allclose(tile_points[:, :2], expected_points[:, :2]):
            problems.append(f"Tile XY grid differs from terrain: {path}")
        local_height = tile_points[:, 2].reshape(row1 - row0 + 1, col1 - col0 + 1)
        prior = tiled_height[row0:row1 + 1, col0:col1 + 1]
        if np.any(np.isfinite(prior) & (np.abs(prior - local_height) > 1e-4)):
            problems.append(f"Tile boundary height mismatch: {path}")
        prior[:] = local_height
        if tile.GetVisibilityAttr().Get() != UsdGeom.Tokens.inherited:
            problems.append(f"Tile is not visible: {path}")
        prim = tile.GetPrim()
        if not prim.HasAPI(UsdPhysics.CollisionAPI) or prim.GetAttribute("physics:collisionEnabled").Get() is not True:
            problems.append(f"Tile collision is disabled: {path}")
        if prim.GetAttribute("physics:approximation").Get() != "none":
            problems.append(f"Tile is not a triangle mesh collider: {path}")
        if prim.HasAPI(UsdPhysics.RigidBodyAPI):
            problems.append(f"Tile is not static: {path}")
    if np.any(~np.isfinite(tiled_height)):
        problems.append("Tiles leave gaps in the terrain grid")
    else:
        difference = tiled_height - points[:, :, 2]
        soil = cfg["deformation"]
        if float(difference.min()) < -float(soil["maximum_sinkage_m"]) - 1e-3:
            problems.append("Sand rut exceeds configured maximum sinkage")
        if float(difference.max()) > float(soil["maximum_berm_m"]) + 1e-3:
            problems.append("Sand berm exceeds configured maximum height")
    print(f"Scene: {scene}\nVisual/collision tiles={len(expected)}; baseline points={height * width}")
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
