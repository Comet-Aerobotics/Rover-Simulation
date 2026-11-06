"""Open the requested rover USD inside the running Isaac Sim application.

This is passed to ``isaac-sim.bat --exec`` by the Windows launcher because a
bare USD positional argument starts Isaac Sim but does not open that stage.
"""
from __future__ import annotations

import os
import asyncio
from pathlib import Path
import sys

import omni.kit.app
import omni.usd


scene_path = os.environ.get("AIAA_ROVER_SCENE")
if not scene_path:
    raise RuntimeError("AIAA_ROVER_SCENE is not set")

if not omni.usd.get_context().open_stage(scene_path):
    raise RuntimeError(f"Isaac Sim could not open the rover scene: {scene_path}")

print(f"AIAA rover scene opened: {scene_path}")

if os.environ.get("AIAA_ROVER_SAND_DEFORMATION") == "1":
    async def _attach_sand():
        app = omni.kit.app.get_app()
        for _ in range(180):
            await app.next_update_async()
            stage = omni.usd.get_context().get_stage()
            if stage and stage.GetPrimAtPath(
                    "/Lunalab/Terrain/terrain_mesh/RutCollisionTiles").IsValid():
                repo = Path(__file__).resolve().parents[2]
                if str(repo) not in sys.path:
                    sys.path.insert(0, str(repo))
                from isaac.terrain.sand_runtime import start
                start(stage)
                return
        raise RuntimeError("Sand collision tiles did not compose within 180 Kit updates")

    asyncio.ensure_future(_attach_sand())
