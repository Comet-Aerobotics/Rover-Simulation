"""Open the requested rover USD inside the running Isaac Sim application.

This is passed to ``isaac-sim.bat --exec`` by the Windows launcher because a
bare USD positional argument starts Isaac Sim but does not open that stage.
"""
from __future__ import annotations

import os
import asyncio
import math
from pathlib import Path
import sys

import omni.kit.app
import omni.usd
from pxr import Sdf


scene_path = os.environ.get("AIAA_ROVER_SCENE")
if not scene_path:
    raise RuntimeError("AIAA_ROVER_SCENE is not set")

if not omni.usd.get_context().open_stage(scene_path):
    raise RuntimeError(f"Isaac Sim could not open the rover scene: {scene_path}")

print(f"AIAA rover scene opened: {scene_path}")

physics_mode = os.environ.get("AIAA_ROVER_CPU_PHYSICS", "1")
if physics_mode not in ("0", "1"):
    raise ValueError("AIAA_ROVER_CPU_PHYSICS must be 1 (CPU) or 0 (GPU)")
cpu_physics = physics_mode == "1"
sand_deformation = os.environ.get("AIAA_ROVER_SAND_DEFORMATION") == "1"
oak_enabled = os.environ.get("AIAA_ROVER_OAK_ENABLED", "1") != "0"
oak_tick_rate = float(os.environ.get("AIAA_ROVER_OAK_TICK_RATE_HZ", "10"))
if not math.isfinite(oak_tick_rate) or oak_tick_rate < 0:
    raise ValueError("AIAA_ROVER_OAK_TICK_RATE_HZ must be nonnegative")


async def _configure_scene():
    app = omni.kit.app.get_app()
    for _ in range(180):
        await app.next_update_async()
        stage = omni.usd.get_context().get_stage()
        if not stage or not stage.GetPrimAtPath("/physicsScene").IsValid():
            continue
        if sand_deformation and not stage.GetPrimAtPath(
                "/Lunalab/Terrain/terrain_mesh/RutCollisionTiles").IsValid():
            continue

        # The scene owns the /cmd_vel controller. Its USD layer must deactivate
        # the imported Jackal asset's standalone drive graph before playback.
        main_drive = stage.GetPrimAtPath("/jackal/ActionGraph")
        legacy_drive = stage.GetPrimAtPath("/jackal/ROS2_Graph/DriveGraph")
        if (main_drive.IsValid() and main_drive.IsActive() and
                legacy_drive.IsValid() and legacy_drive.IsActive()):
            raise RuntimeError("Scene has two active drive graphs; deactivate "
                               "/jackal/ROS2_Graph/DriveGraph in the USD scene layer")

        if not oak_enabled:
            for graph_path in ("/ActionGraph", "/CameraActionGraph"):
                camera_graph = stage.GetPrimAtPath(graph_path)
                if camera_graph.IsValid() and camera_graph.IsActive():
                    camera_graph.SetActive(False)
                    print(f"AIAA_OAK_CAMERA enabled=False graph={graph_path}", flush=True)
        camera = stage.GetPrimAtPath("/jackal/base_link/DM9098Pro_enclosure/OAK_D_Pro_RGB")
        if oak_enabled and camera.IsValid() and oak_tick_rate > 0:
            camera.ApplyAPI("OmniSensorAPI")
            camera.CreateAttribute("omni:sensor:tickRate", Sdf.ValueTypeNames.Float).Set(
                oak_tick_rate)
            print(f"AIAA_OAK_TICK_RATE_HZ {oak_tick_rate:g}", flush=True)

        physics_scene = stage.GetPrimAtPath("/physicsScene")
        gpu_dynamics = physics_scene.GetAttribute("physxScene:enableGPUDynamics")
        broadphase = physics_scene.GetAttribute("physxScene:broadphaseType")
        if not gpu_dynamics or not broadphase:
            raise RuntimeError("Physics scene is missing GPU dynamics or broadphase attributes")
        gpu_dynamics.Set(not cpu_physics)
        broadphase.Set("MBP" if cpu_physics else "GPU")
        print(f"AIAA_PHYSICS_MODE cpu_dynamics={cpu_physics} "
              f"broadphase={'MBP' if cpu_physics else 'GPU'}", flush=True)
        if sand_deformation:
            repo = Path(__file__).resolve().parents[2]
            if str(repo) not in sys.path:
                sys.path.insert(0, str(repo))
            from isaac.terrain.sand_runtime import start
            start(stage)
        return
    if not cpu_physics and not sand_deformation:
        print("AIAA_SCENE_CONFIG skipped: no rover physics scene", flush=True)
        return
    raise RuntimeError("Physics scene or sand tiles did not compose within 180 Kit updates")


asyncio.ensure_future(_configure_scene())
