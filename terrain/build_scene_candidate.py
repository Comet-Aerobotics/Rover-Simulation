"""Create a corrected USD scene copy without modifying the source stage."""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from terrain.generate import build_mesh, crop_pad, read_config
DEFAULT_SOURCE = ROOT / "scenes/CAMERASYNCSSMOETIMES.usd"
DEFAULT_OUTPUT = ROOT / "scenes/CAMERASYNCSSMOETIMES_REBUILT_CANDIDATE.usd"


def build_candidate(source: Path = DEFAULT_SOURCE, output: Path = DEFAULT_OUTPUT) -> Path:
    try:
        from pxr import Usd, UsdGeom, UsdPhysics, Vt
    except ImportError as exc:
        raise RuntimeError("Run with Isaac Sim Python or install the usd-audit extra") from exc

    source = source.resolve()
    output = output.resolve()
    if source.parent != output.parent:
        raise ValueError("Output must stay beside source so relative USD assets resolve unchanged")
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite existing output: {output}")

    config = read_config()
    if config.get("input_policy") != "transpose_then_crop_zero_pad":
        raise ValueError("Scene builder requires input_policy: transpose_then_crop_zero_pad")
    resolution = float(config["resolution_m"])
    width = round(float(config["width_m"]) / resolution)
    height = round(float(config["length_m"]) / resolution)
    source_dem = np.load(ROOT / config["source_dem"], allow_pickle=False).T
    dem = crop_pad(source_dem, height, width).astype(np.float32)
    vertices, _, _ = build_mesh(dem, resolution)

    stage = Usd.Stage.Open(str(source))
    terrain_path = config["mesh_prim"]
    terrain_prim = stage.GetPrimAtPath(terrain_path) if stage else None
    if not terrain_prim or not terrain_prim.IsValid() or not terrain_prim.IsA(UsdGeom.Mesh):
        raise RuntimeError(f"Source stage has no terrain mesh at {terrain_path}")
    terrain_mesh = UsdGeom.Mesh(terrain_prim)
    existing_points = terrain_mesh.GetPointsAttr().Get() or []
    if len(existing_points) != len(vertices):
        raise RuntimeError(
            f"Terrain topology has {len(existing_points)} points; generated grid has {len(vertices)}"
        )

    rock_meshes = [
        prim for prim in stage.Traverse()
        if prim.IsA(UsdGeom.Mesh)
        and str(prim.GetPath()).startswith("/package/rock")
        and "/_materials/" not in str(prim.GetPath())
    ]
    if len(rock_meshes) != 7:
        raise RuntimeError(f"Expected seven placed /package rock meshes; found {len(rock_meshes)}")

    shutil.copy2(source, output)
    stage = Usd.Stage.Open(str(output))
    terrain_mesh = UsdGeom.Mesh(stage.GetPrimAtPath(terrain_path))
    terrain_mesh.GetPointsAttr().Set(Vt.Vec3fArray.FromNumpy(vertices))

    collider_paths = []
    for original_prim in rock_meshes:
        prim = stage.GetPrimAtPath(original_prim.GetPath())
        UsdPhysics.CollisionAPI.Apply(prim).GetCollisionEnabledAttr().Set(True)
        mesh_collision = UsdPhysics.MeshCollisionAPI.Apply(prim)
        mesh_collision.GetApproximationAttr().Set("convexHull")
        collider_paths.append(str(prim.GetPath()))

    stage.GetRootLayer().Save()
    print(f"Wrote corrected scene: {output}")
    print(f"Terrain: {len(vertices):,} points; source DEM transposed before fitting the configured grid")
    print(f"Rock colliders: {len(collider_paths)} convex hulls")
    for path in collider_paths:
        print(f"  {path}")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    build_candidate(args.source, args.output)
