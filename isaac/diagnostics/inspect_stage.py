"""Read-only summary of rover graph, terrain collider, and forbidden prim."""
import argparse
from pxr import Usd, UsdGeom, UsdPhysics

p=argparse.ArgumentParser()
p.add_argument("scene", nargs="?", default="scenes/CAMERASYNCSSMOETIMES.usd")
a=p.parse_args()
stage=Usd.Stage.Open(a.scene)
if not stage: raise SystemExit(f"Unable to open {a.scene}")
print("upAxis:", UsdGeom.GetStageUpAxis(stage), "metersPerUnit:", UsdGeom.GetStageMetersPerUnit(stage))
for root in ("/jackal/ActionGraph","/ActionGraph"):
    prim=stage.GetPrimAtPath(root)
    if prim and prim.IsValid():
        print("Graph",root)
        for node in Usd.PrimRange(prim):
            if node.GetAttribute("node:type").IsValid():
                print(" ",node.GetPath(),node.GetAttribute("node:type").Get())
                for attr in node.GetAttributes():
                    if any(k in attr.GetName().lower() for k in ("topic","joint","wheel","radius","distance","speed")):
                        print("    ",attr.GetName(),attr.Get())
terrain=stage.GetPrimAtPath("/Lunalab/Terrain/terrain_mesh")
if terrain and terrain.IsValid():
    mesh=UsdGeom.Mesh(terrain)
    print("Terrain",len(mesh.GetPointsAttr().Get() or []),"points",len(mesh.GetFaceVertexCountsAttr().Get() or []),"faces")
    print("Collision",terrain.GetAttribute("physics:approximation").Get(),terrain.GetAttribute("physics:collisionEnabled").Get())
print("Cube_003 exists:",bool(stage.GetPrimAtPath("/World/Lab/Lab/CurvedWall/Cube_003")))
