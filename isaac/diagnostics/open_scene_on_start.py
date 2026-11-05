"""Open the requested rover USD inside the running Isaac Sim application.

This is passed to ``isaac-sim.bat --exec`` by the Windows launcher because a
bare USD positional argument starts Isaac Sim but does not open that stage.
"""
from __future__ import annotations

import os

import omni.usd


scene_path = os.environ.get("AIAA_ROVER_SCENE")
if not scene_path:
    raise RuntimeError("AIAA_ROVER_SCENE is not set")

if not omni.usd.get_context().open_stage(scene_path):
    raise RuntimeError(f"Isaac Sim could not open the rover scene: {scene_path}")

print(f"AIAA rover scene opened: {scene_path}")
