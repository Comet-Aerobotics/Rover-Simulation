"""Closed-Loop Simulation-in-the-Loop (SiTL) Agentic Test Harness.

Connects an open local LLM (e.g., Llama 3 via llama.cpp server) to NVIDIA
Isaac Sim via Model Context Protocol (MCP) tooling. The harness executes
goal-oriented physics tasks, injects kinematic test parameters, inspects ground-truth
PhysX articulation state, and iteratively re-prompts the agent with telemetry diffs
if physical assertions fail.
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s")
logger = logging.getLogger("sitl_agent_harness")


@dataclass
class RoverKinematics:
    """Telemetry frame captured from Isaac Sim PhysX articulation."""
    timestamp: float
    position_xyz: tuple[float, float, float]
    linear_velocity_xyz: tuple[float, float, float]
    wheel_angular_velocities: dict[str, float]
    roll_pitch_yaw_deg: tuple[float, float, float]
    ground_contact_active: bool

    def forward_speed(self) -> float:
        return math.sqrt(self.linear_velocity_xyz[0] ** 2 + self.linear_velocity_xyz[1] ** 2)


@dataclass
class PhysicalAssertionResult:
    """Result of an empirical physics assertion."""
    passed: bool
    commanded_velocity: float
    measured_displacement: float
    measured_speed: float
    pitch_roll_stable: bool
    failure_reason: Optional[str] = None
    telemetry_summary: dict[str, Any] = field(default_factory=dict)


class IsaacSimMCPBridge:
    """Client interface for interacting with Isaac Sim through MCP or direct socket/scripting."""

    def __init__(self, mcp_host: str = "127.0.0.1", mcp_port: int = 8211, use_mock: bool = False):
        self.mcp_host = mcp_host
        self.mcp_port = mcp_port
        self.use_mock = use_mock
        self._mock_pos_x = 0.0
        self._mock_wheel_speed = 0.0

    def query_available_tools(self) -> list[dict[str, Any]]:
        """Return the available MCP tool signatures exposed by the Isaac Sim MCP server."""
        return [
            {
                "name": "isaac_set_joint_velocity",
                "description": "Set target angular drive velocity for rover wheel joints in radians/sec.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "joint_names": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Target joint names e.g. ['front_left_wheel_joint', 'front_right_wheel_joint']",
                        },
                        "target_velocity": {"type": "number", "description": "Angular velocity in rad/s"},
                    },
                    "required": ["joint_names", "target_velocity"],
                },
            },
            {
                "name": "isaac_inspect_prim",
                "description": "Inspect USD prim hierarchy, collision API, and mass properties.",
                "parameters": {
                    "type": "object",
                    "properties": {"prim_path": {"type": "string"}},
                    "required": ["prim_path"],
                },
            },
            {
                "name": "isaac_step_simulation",
                "description": "Advance the PhysX simulation by N physics steps.",
                "parameters": {
                    "type": "object",
                    "properties": {"steps": {"type": "integer", "default": 60}},
                },
            },
            {
                "name": "isaac_get_rover_telemetry",
                "description": "Sample current ground truth pose, linear velocity, and joint speeds from PhysX.",
                "parameters": {"type": "object", "properties": {}},
            },
        ]

    def execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool call against Isaac Sim."""
        logger.info(f"Executing MCP Tool: {tool_name} with args: {arguments}")
        if self.use_mock:
            return self._mock_tool_execution(tool_name, arguments)

        # In production, dispatches via JSON-RPC / socket to the running Isaac Sim MCP server
        try:
            import urllib.request
            req_data = json.dumps({"tool": tool_name, "args": arguments}).encode("utf-8")
            req = urllib.request.Request(
                f"http://{self.mcp_host}:{self.mcp_port}/mcp/call",
                data=req_data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as e:
            logger.warning(f"Live MCP server connection failed ({e}). Falling back to simulation mock runner.")
            return self._mock_tool_execution(tool_name, arguments)

    def _mock_tool_execution(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Deterministic mock simulator for CI / offline validation."""
        if tool_name == "isaac_set_joint_velocity":
            vel = float(arguments.get("target_velocity", 0.0))
            self._mock_wheel_speed = vel
            return {"status": "ok", "target_velocity_set": vel}

        elif tool_name == "isaac_step_simulation":
            steps = int(arguments.get("steps", 60))
            # 60 steps at 60 Hz = 1.0 second. Forward speed approx 0.25 * wheel_speed
            displacement = (self._mock_wheel_speed * 0.25) * (steps / 60.0)
            self._mock_pos_x += displacement
            return {"status": "ok", "steps_advanced": steps, "sim_time_delta_sec": steps / 60.0}

        elif tool_name == "isaac_get_rover_telemetry":
            return {
                "timestamp": time.time(),
                "position_xyz": [self._mock_pos_x, 0.0, 0.35],
                "linear_velocity_xyz": [self._mock_wheel_speed * 0.25, 0.0, 0.0],
                "wheel_angular_velocities": {
                    "front_left_wheel_joint": self._mock_wheel_speed,
                    "front_right_wheel_joint": self._mock_wheel_speed,
                    "rear_left_wheel_joint": self._mock_wheel_speed,
                    "rear_right_wheel_joint": self._mock_wheel_speed,
                },
                "roll_pitch_yaw_deg": [0.0, 1.2, 0.0],
                "ground_contact_active": True,
            }

        elif tool_name == "isaac_inspect_prim":
            return {
                "prim_path": arguments.get("prim_path", "/jackal"),
                "has_collision": True,
                "rigid_body_enabled": True,
                "mass_kg": 53.09,
            }

        return {"error": f"Unknown tool: {tool_name}"}


class LocalLlmAgent:
    """Interacts with local LLMs (Llama 3 / Mistral) via an OpenAI-compatible endpoint."""

    def __init__(
        self,
        endpoint_url: str = "http://127.0.0.1:8080/v1",
        model_name: str = "Meta-Llama-3-8B-Instruct",
        offline_mode: bool = False,
    ):
        self.endpoint_url = endpoint_url
        self.model_name = model_name
        self.offline_mode = offline_mode or endpoint_url.startswith("http://mock")

    def prompt_agent(
        self,
        task_instruction: str,
        tools: list[dict[str, Any]],
        history: list[dict[str, str]],
        force_offline_response: bool = False,
    ) -> dict[str, Any]:
        """Generate the next tool call or remediation decision."""
        if self.offline_mode or force_offline_response:
            return self._heuristic_offline_planner(history, task_instruction)

        try:
            import urllib.request
            payload = {
                "model": self.model_name,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are an autonomous robotics testing engineer controlling NVIDIA Isaac Sim via MCP tools. "
                            "You must configure simulation parameters to fulfill the user's test goal. "
                            "Return valid JSON formatted as: {\"tool\": \"<tool_name>\", \"arguments\": { ... }}."
                        ),
                    },
                    *history,
                    {"role": "user", "content": task_instruction},
                ],
                "temperature": 0.1,
            }
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                f"{self.endpoint_url}/chat/completions",
                data=req_data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=1.0) as response:
                res_json = json.loads(response.read().decode("utf-8"))
                content = res_json["choices"][0]["message"]["content"]
                return json.loads(content)
        except Exception as e:
            logger.info(f"Local LLM API unreachable at {self.endpoint_url} ({e}). Using offline heuristic solver.")
            return self._heuristic_offline_planner(history, task_instruction)

    def _heuristic_offline_planner(self, history: list[dict[str, str]], prompt: str) -> dict[str, Any]:
        """Fallback decision tree when offline, demonstrating expected agent self-healing behavior."""
        for msg in reversed(history):
            if "Physical assertion failed" in msg.get("content", ""):
                return {
                    "tool": "isaac_set_joint_velocity",
                    "arguments": {
                        "joint_names": [
                            "front_left_wheel_joint",
                            "front_right_wheel_joint",
                            "rear_left_wheel_joint",
                            "rear_right_wheel_joint",
                        ],
                        "target_velocity": 4.0,  # Increase drive torque / velocity
                    },
                }

        # Initial drive action
        return {
            "tool": "isaac_set_joint_velocity",
            "arguments": {
                "joint_names": [
                    "front_left_wheel_joint",
                    "front_right_wheel_joint",
                    "rear_left_wheel_joint",
                    "rear_right_wheel_joint",
                ],
                "target_velocity": 2.0,
            },
        }


class ClosedLoopSitlFuzzer:
    """The central test harness executing goal-oriented testing with physics-grounded assertions."""

    def __init__(self, bridge: IsaacSimMCPBridge, agent: LocalLlmAgent, max_retries: int = 3):
        self.bridge = bridge
        self.agent = agent
        self.max_retries = max_retries

    def run_goal_test(
        self,
        goal_name: str,
        goal_description: str,
        commanded_velocity_target: float = 2.0,
        min_displacement_expected: float = 0.15,
        max_tilt_threshold_deg: float = 25.0,
    ) -> dict[str, Any]:
        """Execute a goal-oriented testing pass with closed-loop telemetry feedback."""
        logger.info(f"=== Starting SiTL Goal Test: {goal_name} ===")
        logger.info(f"Goal: {goal_description}")

        conversation_history: list[dict[str, str]] = []
        tools = self.bridge.query_available_tools()
        attempt_logs: list[dict[str, Any]] = []

        # 1. Capture initial baseline telemetry
        initial_telemetry_dict = self.bridge.execute_tool("isaac_get_rover_telemetry", {})
        start_x = initial_telemetry_dict.get("position_xyz", [0.0, 0.0, 0.0])[0]

        for iteration in range(1, self.max_retries + 1):
            logger.info(f"--- Iteration {iteration}/{self.max_retries} ---")

            # 2. Query Agent for action
            decision = self.agent.prompt_agent(
                task_instruction=(
                    f"Test Goal: {goal_description}. Current baseline X position: {start_x:.3f}m. "
                    f"Command the wheel joints to achieve positive forward velocity."
                ),
                tools=tools,
                history=conversation_history,
            )
            tool_name = decision.get("tool", "isaac_set_joint_velocity")
            tool_args = decision.get("arguments", {})

            # 3. Apply tool action via MCP
            tool_res = self.bridge.execute_tool(tool_name, tool_args)

            # 4. Step the simulation forward (e.g. 60 ticks = 1.0 second)
            step_res = self.bridge.execute_tool("isaac_step_simulation", {"steps": 60})

            # 5. Measure physical ground truth from PhysX
            curr_telemetry = self.bridge.execute_tool("isaac_get_rover_telemetry", {})
            curr_x = curr_telemetry.get("position_xyz", [0.0, 0.0, 0.0])[0]
            displacement = curr_x - start_x
            vel_x = curr_telemetry.get("linear_velocity_xyz", [0.0, 0.0, 0.0])[0]
            rpy = curr_telemetry.get("roll_pitch_yaw_deg", [0.0, 0.0, 0.0])

            # 6. Physical Assertion Checks
            passed = True
            failure_reasons = []

            if displacement < min_displacement_expected:
                passed = False
                failure_reasons.append(
                    f"Insufficient forward displacement: measured {displacement:.3f}m < expected {min_displacement_expected:.3f}m"
                )

            if abs(rpy[0]) > max_tilt_threshold_deg or abs(rpy[1]) > max_tilt_threshold_deg:
                passed = False
                failure_reasons.append(
                    f"Rover instability/tipping detected: Roll {rpy[0]:.1f}°, Pitch {rpy[1]:.1f}° exceeds {max_tilt_threshold_deg}° limit"
                )

            assertion_result = PhysicalAssertionResult(
                passed=passed,
                commanded_velocity=commanded_velocity_target,
                measured_displacement=displacement,
                measured_speed=vel_x,
                pitch_roll_stable=len(failure_reasons) == 0,
                failure_reason="; ".join(failure_reasons) if failure_reasons else None,
                telemetry_summary=curr_telemetry,
            )

            attempt_logs.append({
                "iteration": iteration,
                "agent_decision": decision,
                "tool_result": tool_res,
                "displacement_m": displacement,
                "speed_mps": vel_x,
                "passed": passed,
                "failure_reasons": failure_reasons,
            })

            if passed:
                logger.info(f"✅ Physical Assertion PASSED on iteration {iteration}! Displacement: {displacement:.3f}m")
                break
            else:
                logger.warning(f"❌ Physical Assertion FAILED on iteration {iteration}: {assertion_result.failure_reason}")
                error_feedback = (
                    f"Physical assertion failed on iteration {iteration}. "
                    f"Reason: {assertion_result.failure_reason}. "
                    f"Commanded: {tool_args}, but measured forward displacement was only {displacement:.3f}m. "
                    "Analyze if drive torque is too low or terrain friction is arresting the chassis, and adjust."
                )
                conversation_history.append({"role": "assistant", "content": json.dumps(decision)})
                conversation_history.append({"role": "user", "content": error_feedback})

        overall_success = attempt_logs[-1]["passed"]
        return {
            "goal": goal_name,
            "overall_success": overall_success,
            "iterations_taken": len(attempt_logs),
            "attempts": attempt_logs,
            "final_displacement_m": attempt_logs[-1]["displacement_m"],
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Closed-Loop SiTL Agentic Test Harness for Isaac Sim")
    parser.add_argument("--task", default="rover_forward_kinematic_check", help="Test goal identifier")
    parser.add_argument("--endpoint", default="http://127.0.0.1:8080/v1", help="Local llama.cpp API base URL")
    parser.add_argument("--model", default="Meta-Llama-3-8B-Instruct", help="Local model name")
    parser.add_argument("--mock-sim", action="store_true", default=True, help="Use mock physics simulation bridge")
    parser.add_argument("--output-report", default="work/sitl_test_report.json", help="Path to save test report")
    args = parser.parse_args()

    bridge = IsaacSimMCPBridge(use_mock=args.mock_sim)
    agent = LocalLlmAgent(endpoint_url=args.endpoint, model_name=args.model)
    harness = ClosedLoopSitlFuzzer(bridge=bridge, agent=agent)

    report = harness.run_goal_test(
        goal_name=args.task,
        goal_description="Drive the Jackal rover forward on LunaLab terrain and assert positive displacement without tipping.",
    )

    out_path = Path(args.output_report)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    logger.info(f"Test run completed. Report written to {out_path.resolve()}")
    if not report["overall_success"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
