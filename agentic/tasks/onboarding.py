"""Onboarding Task: Stage & Robot Asset Physics Audit."""
from __future__ import annotations

from typing import Any
from agentic.base import AgenticTask, IsaacSimMCPBridge, TaskVerificationResult


class StageAuditOnboardingTask(AgenticTask):
    """Introductory developer onboarding task.

    Audits the loaded USD stage in Isaac Sim to verify that the robot prim (/jackal)
    and terrain colliders (/Lunalab/Terrain/terrain_mesh) are composed, valid,
    and have physically realistic mass properties (flagging the unpromoted mass=0 bug).
    """

    task_id = "onboarding_audit"
    name = "Stage Asset & Physics Integrity Audit"
    description = (
        "Inspects the active USD stage in Isaac Sim. Verifies that the /jackal robot prim "
        "has rigid body dynamics enabled, all 4 wheel revolute joints composed, "
        "a valid total mass between 45.0 kg and 60.0 kg, and static triangle mesh collision "
        "on the terrain."
    )

    def __init__(self, min_mass_kg: float = 45.0, max_mass_kg: float = 65.0):
        self.min_mass_kg = min_mass_kg
        self.max_mass_kg = max_mass_kg

    def get_prompt(self, baseline_state: dict[str, Any]) -> str:
        return (
            f"Onboarding Task: {self.description}. "
            "Use the 'isaac_inspect_prim' tool to verify '/jackal' and '/Lunalab/Terrain/terrain_mesh'. "
            "If the rover mass is missing or zero, use 'isaac_set_prim_attribute' to author a realistic mass (53.092 kg)."
        )

    def verify(
        self,
        attempt: int,
        baseline_state: dict[str, Any],
        bridge: IsaacSimMCPBridge,
    ) -> TaskVerificationResult:
        rover_info = bridge.execute_tool("isaac_inspect_prim", {"prim_path": "/jackal"})
        terrain_info = bridge.execute_tool("isaac_inspect_prim", {"prim_path": "/Lunalab/Terrain/terrain_mesh"})

        failure_reasons = []

        # 1. Rover rigid body check
        if not rover_info.get("rigid_body_enabled", False):
            failure_reasons.append("Rover prim '/jackal' does not have rigid body physics enabled.")

        # 2. Wheel joint count check
        joint_count = rover_info.get("wheel_joint_count", 0)
        if joint_count < 4:
            failure_reasons.append(f"Rover has {joint_count} wheel joints; expected 4.")

        # 3. Rover mass check (catches base_link mass=0 unpromoted bug)
        mass_kg = float(rover_info.get("mass_kg", 0.0))
        if mass_kg < self.min_mass_kg or mass_kg > self.max_mass_kg:
            failure_reasons.append(
                f"Rover mass {mass_kg:.1f} kg is outside acceptable physical range [{self.min_mass_kg}, {self.max_mass_kg}] kg."
            )

        # 4. Terrain collider check
        if not terrain_info.get("has_collision", False):
            failure_reasons.append("Terrain mesh '/Lunalab/Terrain/terrain_mesh' lacks static collision.")

        metrics = {
            "rover_rigid_body": rover_info.get("rigid_body_enabled", False),
            "wheel_joints": joint_count,
            "rover_mass_kg": mass_kg,
            "terrain_has_collision": terrain_info.get("has_collision", False),
        }

        return TaskVerificationResult(
            passed=len(failure_reasons) == 0,
            metrics=metrics,
            failure_reasons=failure_reasons,
        )
