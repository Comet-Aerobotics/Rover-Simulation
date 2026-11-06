"""Build an opt-in scene with small collision tiles for live wheel ruts.

The original terrain mesh remains the sole rendered surface. Its collision is
disabled and replaced by non-rendered, static triangle-mesh tiles with exactly
the same initial vertices. The source scene is never modified.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from terrain.generate import ROOT, read_config

DEFAULT_SOURCE = ROOT / "scenes/in work/CAMERASYNCSSMOETIMES_55KG_CANDIDATE.usd"
DEFAULT_OUTPUT = ROOT / "scenes/in work/CAMERASYNCSSMOETIMES_55KG_SAND_CANDIDATE.usd"
TILE_ROOT = "/Lunalab/Terrain/terrain_mesh/RutCollisionTiles"


def tile_bounds(height: int, width: int, cells: int):
    if cells < 4:
        raise ValueError("tile_cells must be at least 4")
    for row0 in range(0, height - 1, cells):
        row1 = min(row0 + cells, height - 1)
        for col0 in range(0, width - 1, cells):
            col1 = min(col0 + cells, width - 1)
            yield row0, row1, col0, col1


def tile_name(row0: int, col0: int) -> str:
    return f"Tile_{row0:04d}_{col0:04d}"


def tile_faces(rows: int, cols: int) -> tuple[np.ndarray, np.ndarray]:
    grid = np.arange(rows * cols, dtype=np.int32).reshape(rows, cols)
    a, b, c, d = grid[:-1, :-1], grid[:-1, 1:], grid[1:, :-1], grid[1:, 1:]
    faces = np.stack((np.stack((b, d, a), axis=-1),
                      np.stack((d, c, a), axis=-1)), axis=2).reshape(-1, 3)
    return np.full(len(faces), 3, dtype=np.int32), faces.ravel()


def build(source: Path = DEFAULT_SOURCE, output: Path = DEFAULT_OUTPUT,
          *, archive: Path | None = None, overwrite: bool = False) -> Path:
    from pxr import Usd, UsdGeom, UsdPhysics, Vt

    source, output = source.resolve(), output.resolve()
    if source == output or source.parent != output.parent:
        raise ValueError("Output must differ from source and stay beside it for relative USD references")
    if output.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite {output}; pass --overwrite explicitly")
    cfg = read_config()
    height = round(float(cfg["length_m"]) / float(cfg["resolution_m"]))
    width = round(float(cfg["width_m"]) / float(cfg["resolution_m"]))
    cells = int(cfg["deformation"]["tile_cells"])
    source_stage = Usd.Stage.Open(str(source))
    if not source_stage:
        raise RuntimeError(f"Could not open source stage: {source}")
    path = cfg["mesh_prim"]
    source_prim = source_stage.GetPrimAtPath(path)
    if not source_prim or not source_prim.IsA(UsdGeom.Mesh):
        raise RuntimeError(f"Expected terrain mesh is missing: {path}")
    source_points = np.asarray(UsdGeom.Mesh(source_prim).GetPointsAttr().Get(), dtype=np.float32)
    if source_points.shape != (height * width, 3):
        raise RuntimeError(f"Expected {height * width} terrain points, found {source_points.shape}")
    points = source_points.reshape(height, width, 3).copy()
    if archive is not None:
        with np.load(archive, allow_pickle=False) as data:
            dem = np.asarray(data["dem"], dtype=np.float32)
        if dem.shape != (height, width):
            raise ValueError(f"Archive DEM has shape {dem.shape}, expected {(height, width)}")
        points[:, :, 2] = dem

    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, output)
    stage = Usd.Stage.Open(str(output))
    mesh = UsdGeom.Mesh(stage.GetPrimAtPath(path))
    if archive is not None:
        mesh.GetPointsAttr().Set(Vt.Vec3fArray.FromNumpy(points.reshape(-1, 3)))
    collision = UsdPhysics.CollisionAPI(mesh.GetPrim())
    if not collision:
        raise RuntimeError("Source terrain has no CollisionAPI")
    collision.GetCollisionEnabledAttr().Set(False)
    root = UsdGeom.Xform.Define(stage, TILE_ROOT).GetPrim()
    root.SetCustomDataByKey("sand:gridHeight", height)
    root.SetCustomDataByKey("sand:gridWidth", width)
    root.SetCustomDataByKey("sand:tileCells", cells)
    root.SetCustomDataByKey("sand:resolutionMeters", float(cfg["resolution_m"]))

    tile_count = 0
    for row0, row1, col0, col1 in tile_bounds(height, width, cells):
        tile_points = np.ascontiguousarray(points[row0:row1 + 1, col0:col1 + 1].reshape(-1, 3))
        counts, indices = tile_faces(row1 - row0 + 1, col1 - col0 + 1)
        tile = UsdGeom.Mesh.Define(stage, f"{TILE_ROOT}/{tile_name(row0, col0)}")
        tile.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(tile_points))
        tile.CreateFaceVertexCountsAttr(Vt.IntArray.FromNumpy(counts))
        tile.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(indices))
        tile.CreateVisibilityAttr(UsdGeom.Tokens.invisible)
        tile.GetPrim().SetCustomDataByKey("sand:row0", row0)
        tile.GetPrim().SetCustomDataByKey("sand:row1", row1)
        tile.GetPrim().SetCustomDataByKey("sand:col0", col0)
        tile.GetPrim().SetCustomDataByKey("sand:col1", col1)
        UsdPhysics.CollisionAPI.Apply(tile.GetPrim()).CreateCollisionEnabledAttr(True)
        UsdPhysics.MeshCollisionAPI.Apply(tile.GetPrim()).CreateApproximationAttr("none")
        tile_count += 1
    stage.GetRootLayer().Save()
    print(f"Built {output} with {tile_count} sand collision tiles; original terrain collider disabled")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--archive", type=Path, help="Optional terrain/generate.py NPZ for initial heights")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    try:
        from pxr import Usd  # noqa: F401
        app = None
    except ImportError:
        from isaacsim import SimulationApp
        app = SimulationApp({"headless": True, "width": 32, "height": 32})
    try:
        build(args.source, args.output, archive=args.archive, overwrite=args.overwrite)
    finally:
        if app is not None:
            app.close()
