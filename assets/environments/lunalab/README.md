# LunaLab dependency closure

This folder holds local USD geometry, MDL materials, maps, rock assets, and `LICENSE.txt` used by the composed room. Keep the relative paths together when moving or copying a stage.

| Folder | Content | Effect in simulation |
| --- | --- | --- |
| `USD_Assets/lunalab/` | Wall, door, curtain, grill, and other modular room geometry | Visual landmarks and, for selected prims, rigid obstacles |
| `USD_Assets/rocks/` | Rock source assets and textures | Seven placed `/package/rock*` meshes have convex-hull collision in the canonical scene |
| `Textures/` | MDL materials, normal/base-color maps, projector resources | RGB/viewport appearance; unresolved texture paths do not by themselves remove physics contact |

The former invisible obstruction prim `/World/Lab/Lab/CurvedWall/Cube_003` is inactive in the canonical composition. The terrain collider belongs to `/Lunalab/Terrain/terrain_mesh`, outside this room-asset folder. See [environment](../../../docs/environment.md), [terrain](../../../docs/terrain.md), and [source manifest](../../../docs/source-manifest.md).
