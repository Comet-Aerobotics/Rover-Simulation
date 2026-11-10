"""Wheel Motion & Articulation Verification Task."""
from __future__ import annotations

from typing import Any
from agentic.base import AgenticTask, IsaacSimMCPBridge, TaskVerificationResult


class WheelMotionTask(AgenticTask):
    """Verifies that commanded wheel joint velocities produce forward motion in PhysX."""

    task_id = "wheel_motion"
    name = "Rover Forward Drive Kinematics"
    description = (
        "Commands wheel joints on the /jackal articulation and verifies that positive "
        "angular drive produces forward displacement without chassis tipping or terrain snag."
    )

    def __init__(
        self,
        target_velocity: float = 2.0,
        min_displacement_expected: float = 0.15,
        max_tilt_threshold_deg: float = 25.0,
        sim_steps: int = 60,
    ):
        self.target_velocity = target_velocity
        self.min_displacement_expected = min_displacement_expected
        self.max_tilt_threshold_deg = max_tilt_threshold_deg
        self.sim_steps = sim_steps

    def get_initial_state(self, bridge: IsaacSimMCPBridge) -> dict[str, Any]:
        telemetry = bridge.execute_tool("isaac_get_rover_telemetry", {})
        return {
            "start_x": telemetry.get("position_xyz", [0.0, 0.0, 0.0])[0],
            "start_y": telemetry.get("position_xyz", [0.0, 0.0, 0.0])[1],
        }

    def get_prompt(self, baseline_state: dict[str, Any]) -> str:
        start_x = baseline_state.get("start_x", 0.0)
        return (
            f"Test Goal: {self.description}. "
            f"Current baseline X position: {start_x:.3f}m. "
            f"Command the four wheel joints to achieve positive forward velocity (target: {self.target_velocity} rad/s)."
        )

    def verify(
        self,
        attempt: int,
        baseline_state: dict[str, Any],
        bridge: IsaacSimMCPBridge,
    ) -> TaskVerificationResult:
        # Advance simulation
        bridge.execute_tool("isaac_step_simulation", {"steps": self.sim_steps})

        # Sample ground-truth telemetry
        telemetry = bridge.execute_tool("isaac_get_rover_telemetry", {})
        curr_x = telemetry.get("position_xyz", [0.0, 0.0, 0.0])[0]
        start_x = baseline_state.get("start_x", 0.0)
        displacement = curr_x - start_x
        vel_x = telemetry.get("linear_velocity_xyz", [0.0, 0.0, 0.0])[0]
        rpy = telemetry.get("roll_pitch_yaw_deg", [0.0, 0.0, 0.0])

        failure_reasons = []
        if displacement < self.min_displacement_expected:
            failure_reasons.append(
                f"Displacement {displacement:.3f}m below minimum threshold {self.min_displacement_expected:.3f}m"
            )

        if abs(rpy[0]) > self.max_tilt_threshold_deg or abs(rpy[1]) > self.max_tilt_threshold_deg:
            failure_reasons.append(
                f"Chassis instability: roll={rpy[0]:.1f}°, pitch={rpy[1]:.1f}° exceeds {self.max_tilt_threshold_deg}° limit"
            )

        metrics = {
            "displacement_m": displacement,
            "linear_speed_mps": vel_x,
            "roll_deg": rpy[0],
            "pitch_deg": rpy[1],
            "ground_contact": telemetry.get("ground_contact_active", False),
        }

        return TaskVerificationResult(
            passed=len(failure_reasons) == 0,
            metrics=metrics,
            failure_reasons=failure_reasons,
        )
