"""Read-only structural audit for the canonical USD terrain mesh."""
import argparse
from pathlib import Path


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
    body = prim.GetAppliedSchemas()
    if any("RigidBodyAPI" in schema for schema in body):
        problems.append("Static terrain unexpectedly has RigidBodyAPI")
    forbidden = stage.GetPrimAtPath("/World/Lab/Lab/CurvedWall/Cube_003")
    if forbidden and forbidden.IsValid() and forbidden.IsActive():
        problems.append("Cube_003 unexpectedly exists; do not auto-delete it")
    print(f"Scene: {scene}\nTerrain points={len(points)} faces={len(counts)} indices={len(indices)}\nColliders={colliders}")
    return problems

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("scene", nargs="?", default="scenes/CAMERASYNCSSMOETIMES.usd", type=Path)
    args = parser.parse_args()
    issues = validate(args.scene)
    for issue in issues: print(f"ERROR: {issue}")
    raise SystemExit(bool(issues))
