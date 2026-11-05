"""Reproducibly process the Lunalab lidar01 DEM using the original loader's rules.

This is an offline asset generator. It never opens or edits an Isaac Sim stage.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import Any
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def read_config(path: Path = ROOT / "config/terrain.yaml") -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("Install the terrain extra: pip install -e '.[terrain]'") from exc
    with path.open("r", encoding="utf-8") as stream:
        return yaml.safe_load(stream)["terrain"]


def crop_pad(array: np.ndarray, height: int, width: int, *, fill: float = 0) -> np.ndarray:
    """Match load_lunalab_terrain.py: copy the top-left overlap, zero-fill remainder."""
    if array.ndim != 2:
        raise ValueError("DEM and mask must be two-dimensional arrays")
    out = np.full((height, width), fill, dtype=array.dtype)
    copy_h, copy_w = min(height, array.shape[0]), min(width, array.shape[1])
    out[:copy_h, :copy_w] = array[:copy_h, :copy_w]
    return out


def add_conical_craters(dem: np.ndarray, *, count: int, seed: int,
                        resolution: float, radius_min: float, radius_max: float,
                        depth_min: float, depth_max: float) -> np.ndarray:
    """Port the seeded conical crater procedure from OmniLRS load_lunalab_terrain.py."""
    result = np.asarray(dem, dtype=np.float32).copy()
    rng = np.random.default_rng(seed)
    h, w = result.shape
    for _ in range(count):
        margin = max(int(radius_max / resolution * 1.5), 100)
        if margin >= w // 2 or margin >= h // 2:
            margin = min(w // 4, h // 4)
        center_x = rng.integers(margin, max(margin + 1, w - margin))
        center_y = rng.integers(margin, max(margin + 1, h - margin))
        radius_m = rng.uniform(radius_min, radius_max)
        radius_px = max(2, int(radius_m / resolution))
        depth = rng.uniform(depth_min, depth_max)
        for y in range(max(0, center_y-radius_px), min(h, center_y+radius_px+1)):
            for x in range(max(0, center_x-radius_px), min(w, center_x+radius_px+1)):
                distance = np.sqrt((x-center_x)**2 + (y-center_y)**2)
                if distance <= radius_px:
                    result[y, x] -= depth * max(0.0, 1.0-distance/radius_px)
    return result


def build_mesh(dem: np.ndarray, resolution: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Build vertices, triangle indices, and face-varying UVs in legacy vertex order."""
    height, width = dem.shape
    yy, xx = np.indices((height, width), dtype=np.float32)
    vertices = np.column_stack((xx.ravel()*resolution, yy.ravel()*resolution,
                                np.asarray(dem, dtype=np.float32).ravel()))
    grid = np.arange(height*width, dtype=np.uint32).reshape(height, width)
    a, b, c = grid[:-1, 1:], grid[1:, 1:], grid[:-1, :-1]
    d = grid[1:, 1:]
    e = grid[1:, :-1]
    faces = np.stack((np.stack((a,b,c),axis=-1), np.stack((d,e,c),axis=-1)),axis=2).reshape(-1,3)
    # Legacy face-varying UVs use the same x/y locations as vertices, in metres.
    face_uvs = vertices[faces, :2].copy()
    return vertices, faces, face_uvs


def generate(config: dict[str, Any], output: Path | None = None,
             *, add_craters: bool | None = None) -> Path:
    dem_path = ROOT / config["source_dem"]
    mask_path = ROOT / config["source_mask"]
    output = output or (ROOT / config["output_archive"])
    resolution = float(config["resolution_m"])
    width = round(float(config["width_m"])/resolution)
    height = round(float(config["length_m"])/resolution)
    original = np.load(dem_path, allow_pickle=False)
    raw_mask = np.load(mask_path, allow_pickle=False) if mask_path.exists() else np.ones_like(original, dtype=np.uint8)
    dem = crop_pad(original, height, width).astype(np.float32)
    mask = crop_pad(raw_mask, height, width)
    crater_cfg = config["craters"]
    enabled = bool(crater_cfg["enabled"]) if add_craters is None else add_craters
    if enabled:
        dem = add_conical_craters(dem, count=int(crater_cfg["count"]), seed=int(crater_cfg["seed"]),
            resolution=resolution, radius_min=float(crater_cfg["radius_min_m"]),
            radius_max=float(crater_cfg["radius_max_m"]), depth_min=float(crater_cfg["depth_min_m"]),
            depth_max=float(crater_cfg["depth_max_m"]))
    vertices, faces, face_uvs = build_mesh(dem, resolution)
    metadata = {"source_dem": str(config["source_dem"]), "source_mask": str(config["source_mask"]),
        "legacy_rule": "top-left crop and zero-pad; mask is retained but not applied to height",
        "width_m": float(config["width_m"]), "length_m": float(config["length_m"]),
        "resolution_m": resolution, "height_samples": height, "width_samples": width,
        "craters_enabled": enabled, "craters": crater_cfg if enabled else None,
        "mesh_prim": config["mesh_prim"]}
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output, vertices=vertices, faces=faces, face_uvs=face_uvs,
        dem=dem, mask=mask, metadata_json=json.dumps(metadata, sort_keys=True))
    print(f"Wrote {output}: {len(vertices):,} vertices, {len(faces):,} triangles; z=[{dem.min():.5f},{dem.max():.5f}]")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT/"config/terrain.yaml")
    parser.add_argument("--output", type=Path)
    crater_mode = parser.add_mutually_exclusive_group()
    crater_mode.add_argument("--craters", dest="add_craters", action="store_true",
        help="Apply the configured seeded craters, overriding config")
    crater_mode.add_argument("--no-craters", dest="add_craters", action="store_false",
        help="Disable craters, overriding config")
    parser.set_defaults(add_craters=None)
    args = parser.parse_args()
    generate(read_config(args.config), args.output, add_craters=args.add_craters)
