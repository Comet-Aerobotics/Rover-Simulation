# Scene assets

| Folder | Role | Main guide |
| --- | --- | --- |
| `robots/` | Local Jackal models, lidar, and camera enclosure | [Rover](../docs/rover.md), [sensors](../docs/sensors.md) |
| `terrain/` | Preserved DEM, mask, and source heightmap | [Terrain](../docs/terrain.md) |
| `environments/` | LunaLab structures, rocks, configuration layers, and textures | [Environment](../docs/environment.md) |
| `materials/` | Additional project material resources | [Environment](../docs/environment.md) |

The scene's relative USD references depend on these files staying in the expected tree. Visible assets, collision APIs, and sensor publishers are separate: repairing one does not automatically repair the others. Preserve accompanying licenses and read [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) before redistributing assets. The [source manifest](../docs/source-manifest.md) records provenance.
