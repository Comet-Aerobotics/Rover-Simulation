"""Explicit offline repair. Writes a new USD copy and never changes wall geometry."""
import argparse
import shutil
from pathlib import Path

def repair(source: Path, output: Path) -> None:
    from pxr import Usd, UsdPhysics
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite existing output: {output}")
    if source.resolve().parent != output.resolve().parent:
        raise ValueError("Output must stay beside source so relative USD assets resolve unchanged")
    source_stage = Usd.Stage.Open(str(source))
    prim = source_stage.GetPrimAtPath("/Lunalab/Terrain/terrain_mesh") if source_stage else None
    if not prim or not prim.IsValid():
        raise RuntimeError("Terrain prim is absent; source left untouched")
    if not prim.HasAPI(UsdPhysics.CollisionAPI):
        raise RuntimeError("No existing collider; refusing to synthesize one")
    if "PhysicsMeshCollisionAPI" not in prim.GetAppliedSchemas():
        raise RuntimeError("No existing mesh-collision API; refusing to synthesize one")
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, output)
    stage = Usd.Stage.Open(str(output))
    prim = stage.GetPrimAtPath("/Lunalab/Terrain/terrain_mesh")
    prim.GetAttribute("physics:approximation").Set("none")
    prim.GetAttribute("physics:collisionEnabled").Set(True)
    stage.GetRootLayer().Save()
    print(f"Wrote repaired copy: {output}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--apply", action="store_true", help="Required explicit opt-in; source is never modified")
    args = parser.parse_args()
    if not args.apply:
        parser.error("pass --apply to write a new output copy")
    repair(args.source, args.output)
