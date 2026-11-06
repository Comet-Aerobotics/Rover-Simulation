"""Isaac Sim runtime for visible and colliding wheel-driven sand ruts.

Call ``start(stage)`` after opening a scene made by terrain/build_sand_scene.py.
All USD edits happen from the Kit update thread between physics steps. Only
tiles touched by the wheels are rebuilt; each tile supplies rendering and
collision. The soil model is empirical and requires site calibration.
"""
from __future__ import annotations

import math
from pathlib import Path
import sys
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from terrain.deformation import DirtyRegion, RutField, SoilParameters, WheelSample
from terrain.generate import read_config
from terrain.build_sand_scene import TILE_ROOT

WHEELS = ("front_left", "front_right", "rear_left", "rear_right")
TERRAIN = "/Lunalab/Terrain/terrain_mesh"


def _numpy(value: Any) -> np.ndarray:
    return np.asarray(value.numpy() if hasattr(value, "numpy") else value)


class SandRuntime:
    def __init__(self, stage):
        import omni.kit.app
        import omni.physx
        import omni.timeline
        import omni.usd
        from pxr import Usd, UsdGeom, UsdPhysics

        self.stage = stage
        self.timeline = omni.timeline.get_timeline_interface()
        self.app = omni.kit.app.get_app()
        self.usd_context = omni.usd.get_context()
        self.cfg = read_config()
        self.soil_cfg = self.cfg["deformation"]
        self.interval = float(self.soil_cfg["update_interval_s"])
        self.tile_cells = int(self.soil_cfg["tile_cells"])
        self.mesh = UsdGeom.Mesh(stage.GetPrimAtPath(TERRAIN))
        self.tile_root = stage.GetPrimAtPath(TILE_ROOT)
        if not self.mesh or not self.tile_root or not self.tile_root.IsValid():
            raise RuntimeError("The open stage has no sand collision tiles; build the sand candidate first")
        if UsdPhysics.CollisionAPI(self.mesh.GetPrim()).GetCollisionEnabledAttr().Get() is not False:
            raise RuntimeError("The original full-size terrain collider is still enabled")
        if self.tile_root.GetCustomDataByKey("sand:representation") != "visible_collision_tiles_v1":
            raise RuntimeError("Sand scene needs rebuilding with visible collision tiles")
        height = int(self.tile_root.GetCustomDataByKey("sand:gridHeight"))
        width = int(self.tile_root.GetCustomDataByKey("sand:gridWidth"))
        if int(self.tile_root.GetCustomDataByKey("sand:tileCells")) != self.tile_cells:
            raise RuntimeError("Sand scene tile size differs from config/terrain.yaml")
        self.points = _numpy(self.mesh.GetPointsAttr().Get()).astype(np.float32).reshape(height, width, 3).copy()
        params = SoilParameters(**{
            key: self.soil_cfg[key] for key in SoilParameters.__dataclass_fields__
        })
        self.field = RutField(self.points[:, :, 2], float(self.cfg["resolution_m"]), params)
        self.tile_info = {}
        for prim in self.tile_root.GetChildren():
            row0 = int(prim.GetCustomDataByKey("sand:row0"))
            row1 = int(prim.GetCustomDataByKey("sand:row1"))
            col0 = int(prim.GetCustomDataByKey("sand:col0"))
            col1 = int(prim.GetCustomDataByKey("sand:col1"))
            tile = UsdGeom.Mesh(prim)
            saved_points = _numpy(tile.GetPointsAttr().Get()).reshape(row1 - row0 + 1, col1 - col0 + 1, 3)
            # The original terrain points retain the undeformed DEM. Saved
            # tile points restore any ruts when a sand scene is reopened.
            self.field.height[row0:row1 + 1, col0:col1 + 1] = saved_points[:, :, 2]
            self.tile_info[str(prim.GetPath())] = (
                row0, row1, col0, col1,
                tile.GetFaceVertexCountsAttr().Get(),
                tile.GetFaceVertexIndicesAttr().Get(),
            )
        self.points[:, :, 2] = self.field.height
        self.inverse = UsdGeom.Xformable(self.mesh.GetPrim()).ComputeLocalToWorldTransform(
            Usd.TimeCode.Default()).GetInverse()
        base = stage.GetPrimAtPath("/jackal/base_link")
        base_mass = base.GetAttribute("physics:mass").Get() if base else None
        wheel_mass = 0.477
        self.mass_kg = float(base_mass) + 4 * wheel_mass if base_mass else 55.0
        physics_scene = next((p for p in stage.Traverse() if p.IsA(UsdPhysics.Scene)), None)
        gravity_attr = physics_scene.GetAttribute("physics:gravityMagnitude") if physics_scene else None
        gravity = float(gravity_attr.Get()) if gravity_attr and gravity_attr.Get() else 9.81
        self.load_per_wheel_n = self.mass_kg * gravity / 4.0
        self.scene_query = omni.physx.get_physx_scene_query_interface()
        self.articulation = None
        self.wheel_prims = None
        self.dof_indices = None
        self.previous_positions = {}
        self.last_time = None
        self.changed_tiles = 0
        self._subscription = self.app.get_update_event_stream().create_subscription_to_pop(
            self._update, name="aiaa_sand_deformation")
        print(f"AIAA_SAND_READY tiles={len(self.tile_info)} mass={self.mass_kg:.2f}kg ",
              f"load_per_wheel={self.load_per_wheel_n:.1f}N", flush=True)

    def stop(self):
        self._subscription = None

    def _initialize_wheels(self):
        from isaacsim.core.experimental.prims import Articulation, RigidPrim

        self.articulation = Articulation("/jackal")
        self.wheel_prims = {
            name: RigidPrim(f"/jackal/{name}_wheel_link") for name in WHEELS
        }
        self.dof_indices = self.articulation.get_dof_indices(
            [f"{name}_wheel" for name in WHEELS])

    def _local(self, world_xyz):
        from pxr import Gf

        point = self.inverse.Transform(Gf.Vec3d(*map(float, world_xyz)))
        return np.array((point[0], point[1], point[2]), dtype=float)

    def _heading(self, quat_wxyz):
        from pxr import Gf

        w, x, y, z = map(float, quat_wxyz)
        forward = Gf.Vec3d(1 - 2 * (y*y + z*z), 2 * (x*y + w*z), 2 * (x*z - w*y))
        local = self.inverse.TransformDir(forward)
        return math.atan2(local[1], local[0])

    def _update(self, _event):
        current_stage = self.usd_context.get_stage()
        if not current_stage or current_stage.GetRootLayer().identifier != self.stage.GetRootLayer().identifier:
            self.stop()
            return
        if not self.timeline.is_playing():
            self.last_time = None
            self.previous_positions.clear()
            return
        now = float(self.timeline.get_current_time())
        if self.last_time is None:
            self.last_time = now
            return
        elapsed = now - self.last_time
        if elapsed < 0:
            # The saved stage loops its short timeline during longer drives.
            self.last_time = now
            self.previous_positions.clear()
            return
        if elapsed < self.interval:
            return
        self.last_time = now
        elapsed = min(elapsed, 0.5)
        try:
            if self.articulation is None:
                self._initialize_wheels()
            self._step(elapsed)
        except Exception as error:
            print(f"AIAA_SAND_ERROR {error!r}; disabling sand runtime", flush=True)
            self.stop()

    def _step(self, dt_s: float):
        import carb

        positions, orientations = self.articulation.get_world_poses()
        heading = self._heading(_numpy(orientations)[0])
        spins = _numpy(self.articulation.get_dof_velocities(dof_indices=self.dof_indices))[0]
        dirty = None
        for i, name in enumerate(WHEELS):
            world_positions, _ = self.wheel_prims[name].get_world_poses()
            local = self._local(_numpy(world_positions)[0])
            previous = self.previous_positions.get(name)
            self.previous_positions[name] = (float(local[0]), float(local[1]))
            if previous is None:
                continue
            # Query the nearest surface below the wheel. This rejects rocks and
            # airborne wheels without attaching contact reporters to every wheel.
            hits = []
            def collect(hit):
                if not str(hit.collision).startswith("/jackal/"):
                    hits.append((float(hit.distance), str(hit.collision)))
                return True
            world = _numpy(world_positions)[0]
            self.scene_query.raycast_all(
                carb.Float3(*map(float, world)), carb.Float3(0.0, 0.0, -1.0),
                self.field.parameters.wheel_radius_m + self.field.parameters.contact_tolerance_m,
                collect,
            )
            if not hits or not min(hits)[1].startswith(TILE_ROOT + "/"):
                continue
            distance = math.hypot(local[0] - previous[0], local[1] - previous[1])
            speed = distance / dt_s
            sample = WheelSample(
                x_m=float(local[0]), y_m=float(local[1]), center_height_m=float(local[2]),
                heading_rad=heading, ground_speed_m_s=speed,
                spin_rad_s=float(spins[i]), normal_load_n=self.load_per_wheel_n,
            )
            region = self.field.stamp(sample, dt_s, previous_xy_m=previous)
            if region is not None:
                dirty = region if dirty is None else dirty.merge(region)
        if dirty is not None:
            self._sync(dirty)

    def _sync(self, dirty: DirtyRegion):
        self.points[:, :, 2] = self.field.height
        self._sync_tiles(dirty)

    def _sync_tiles(self, dirty: DirtyRegion):
        from pxr import UsdGeom, UsdPhysics, Vt

        count = 0
        for path, (row0, row1, col0, col1, counts, indices) in self.tile_info.items():
            if row1 < dirty.row_min or row0 > dirty.row_max or col1 < dirty.col_min or col0 > dirty.col_max:
                continue
            tile_points = np.ascontiguousarray(self.points[row0:row1 + 1, col0:col1 + 1].reshape(-1, 3))
            # Updating points on a live PhysX triangle mesh does not move its
            # collider. Replacing this small prim makes PhysX cook new geometry.
            self.stage.RemovePrim(path)
            tile = UsdGeom.Mesh.Define(self.stage, path)
            tile.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(tile_points))
            tile.CreateFaceVertexCountsAttr(counts)
            tile.CreateFaceVertexIndicesAttr(indices)
            tile.CreateVisibilityAttr(UsdGeom.Tokens.inherited)
            tile.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
            tile.CreateExtentAttr(Vt.Vec3fArray.FromNumpy(np.array((tile_points.min(axis=0), tile_points.max(axis=0)), dtype=np.float32)))
            tile.GetPrim().SetCustomDataByKey("sand:row0", row0)
            tile.GetPrim().SetCustomDataByKey("sand:row1", row1)
            tile.GetPrim().SetCustomDataByKey("sand:col0", col0)
            tile.GetPrim().SetCustomDataByKey("sand:col1", col1)
            UsdPhysics.CollisionAPI.Apply(tile.GetPrim()).CreateCollisionEnabledAttr(True)
            UsdPhysics.MeshCollisionAPI.Apply(tile.GetPrim()).CreateApproximationAttr("none")
            count += 1
        self.changed_tiles += count
        if self.changed_tiles % 20 < count:
            print(f"AIAA_SAND_RUT tiles_rebuilt={self.changed_tiles} ",
                  f"max_depth_m={float(np.max(self.field.baseline - self.field.height)):.4f}", flush=True)


_runtime = None


def start(stage=None) -> SandRuntime:
    """Attach at most one runtime to the currently open sand candidate."""
    import omni.usd

    global _runtime
    if _runtime is not None:
        _runtime.stop()
    stage = stage or omni.usd.get_context().get_stage()
    _runtime = SandRuntime(stage)
    return _runtime
