"""Generic Agentic Simulation-in-the-Loop (SiTL) Test Harness.

Provides abstract base classes for defining arbitrary robotics simulation test tasks,
evaluation metrics, and verification functions, paired with an iterative closed-loop
LLM self-healing engine.
"""
from __future__ import annotations

import abc
import json
import logging
import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("sitl_agent_harness")


@dataclass
class TaskVerificationResult:
    """Outcome of an arbitrary verification check on the simulation state."""
    passed: bool
    metrics: dict[str, Any] = field(default_factory=dict)
    failure_reasons: list[str] = field(default_factory=list)

    @property
    def failure_summary(self) -> str:
        return "; ".join(self.failure_reasons) if self.failure_reasons else "None"


class AgenticTask(abc.ABC):
    """Abstract base class for an arbitrary simulation test task."""

    task_id: str = "base_task"
    name: str = "Base Simulation Task"
    description: str = "Abstract simulation test task"

    @abc.abstractmethod
    def get_prompt(self, baseline_state: dict[str, Any]) -> str:
        """Construct the prompt / goal instruction dispatched to the LLM agent."""
        pass

    def get_initial_state(self, bridge: "IsaacSimMCPBridge") -> dict[str, Any]:
        """Capture baseline telemetry or scene configuration before the agent acts."""
        return {}

    @abc.abstractmethod
    def verify(self, attempt: int, baseline_state: dict[str, Any], bridge: "IsaacSimMCPBridge") -> TaskVerificationResult:
        """Execute arbitrary verification logic against the simulation state."""
        pass

    def format_failure_feedback(
        self,
        attempt: int,
        last_decision: dict[str, Any],
        verification: TaskVerificationResult,
    ) -> str:
        """Construct telemetry feedback provided to the LLM agent on failure."""
        return (
            f"Physical assertion failed on iteration {attempt}. "
            f"Reasons: {verification.failure_summary}. "
            f"Commanded: {json.dumps(last_decision)}. "
            f"Measured metrics: {json.dumps(verification.metrics)}. "
            "Analyze the failure cause and adjust parameters or issue corrective tools."
        )


class IsaacSimMCPBridge:
    """Client interface for interacting with Isaac Sim through MCP or direct socket/scripting."""

    def __init__(self, mcp_host: str = "127.0.0.1", mcp_port: int = 8211, use_mock: bool = False):
        self.mcp_host = mcp_host
        self.mcp_port = mcp_port
        self.use_mock = use_mock
        self._mock_pos_x = 0.0
        self._mock_wheel_speed = 0.0
        self._mock_stage_properties: dict[str, Any] = {
            "/jackal": {
                "has_collision": True,
                "rigid_body_enabled": True,
                "mass_kg": 53.092,
                "wheel_joint_count": 4,
            },
            "/Lunalab/Terrain/terrain_mesh": {
                "has_collision": True,
                "approximation": "none",
            },
            "/ActionGraph": {
                "active_render_product": "/Render/RenderProduct_OAK_RGB",
                "width": 640,
                "height": 400,
                "camera_prim": "/jackal/base_link/DM9098Pro_enclosure/OAK_D_Pro_RGB",
                "rgb_publishing": True,
                "depth_publishing": True,
                "clock_sync_active": True,
                "fps": 20.0,
            },
        }

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
                "name": "isaac_set_prim_attribute",
                "description": "Set an authored attribute on a USD prim in the stage.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "prim_path": {"type": "string"},
                        "attribute_name": {"type": "string"},
                        "value": {"type": ["string", "number", "boolean"]},
                    },
                    "required": ["prim_path", "attribute_name", "value"],
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
            {
                "name": "isaac_inspect_camera_stream",
                "description": "Inspect active render product, frame rate, resolution, and ROS 2 publish state.",
                "parameters": {
                    "type": "object",
                    "properties": {"action_graph_path": {"type": "string", "default": "/ActionGraph"}},
                },
            },
        ]

    def execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool call against Isaac Sim."""
        logger.info(f"Executing MCP Tool: {tool_name} with args: {arguments}")
        if self.use_mock:
            return self._mock_tool_execution(tool_name, arguments)

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
            prim_path = arguments.get("prim_path", "/jackal")
            return self._mock_stage_properties.get(prim_path, {"prim_path": prim_path, "exists": False})

        elif tool_name == "isaac_set_prim_attribute":
            prim_path = arguments.get("prim_path", "")
            attr = arguments.get("attribute_name", "")
            val = arguments.get("value")
            if prim_path in self._mock_stage_properties:
                self._mock_stage_properties[prim_path][attr] = val
                return {"status": "ok", "prim_path": prim_path, "attribute": attr, "set_value": val}
            return {"status": "error", "message": f"Prim not found: {prim_path}"}

        elif tool_name == "isaac_inspect_camera_stream":
            graph_path = arguments.get("action_graph_path", "/ActionGraph")
            return self._mock_stage_properties.get(graph_path, {"graph_path": graph_path, "active": False})

        return {"error": f"Unknown tool: {tool_name}"}


class LocalLlmAgent:
    """Interacts with local LLMs (e.g. Llama 3) via an OpenAI-compatible endpoint."""

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
        """Deterministic heuristic solver for offline and test runs."""
        # Check task type from prompt
        if "onboarding" in prompt.lower() or "mass" in prompt.lower() or "inspect" in prompt.lower():
            # If previous failed on mass = 0, fix mass to 53.092 kg
            for msg in reversed(history):
                if "Physical assertion failed" in msg.get("content", ""):
                    return {
                        "tool": "isaac_set_prim_attribute",
                        "arguments": {
                            "prim_path": "/jackal",
                            "attribute_name": "mass_kg",
                            "value": 53.092,
                        },
                    }
            return {
                "tool": "isaac_inspect_prim",
                "arguments": {"prim_path": "/jackal"},
            }

        elif "camera" in prompt.lower() or "render" in prompt.lower():
            return {
                "tool": "isaac_inspect_camera_stream",
                "arguments": {"action_graph_path": "/ActionGraph"},
            }

        # Default wheel drive task
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
                        "target_velocity": 4.0,
                    },
                }

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


class GenericAgenticHarness:
    """Generic harness capable of executing any arbitrary AgenticTask with closed-loop feedback."""

    def __init__(self, bridge: IsaacSimMCPBridge, agent: LocalLlmAgent, max_retries: int = 3):
        self.bridge = bridge
        self.agent = agent
        self.max_retries = max_retries

    def run_task(self, task: AgenticTask) -> dict[str, Any]:
        """Execute any AgenticTask with automated assertion checking and self-healing."""
        logger.info(f"=== Starting Task: [{task.task_id}] {task.name} ===")
        logger.info(f"Description: {task.description}")

        conversation_history: list[dict[str, str]] = []
        tools = self.bridge.query_available_tools()
        attempt_logs: list[dict[str, Any]] = []

        # 1. Capture initial baseline state
        baseline_state = task.get_initial_state(self.bridge)

        for iteration in range(1, self.max_retries + 1):
            logger.info(f"--- Iteration {iteration}/{self.max_retries} ---")

            # 2. Query Agent for action based on task prompt
            prompt_text = task.get_prompt(baseline_state)
            decision = self.agent.prompt_agent(
                task_instruction=prompt_text,
                tools=tools,
                history=conversation_history,
            )
            tool_name = decision.get("tool", "")
            tool_args = decision.get("arguments", {})

            # 3. Apply tool action via MCP
            tool_res = self.bridge.execute_tool(tool_name, tool_args)

            # 4. Verify simulation state using task's custom verification function
            verification = task.verify(
                attempt=iteration,
                baseline_state=baseline_state,
                bridge=self.bridge,
            )

            attempt_logs.append({
                "iteration": iteration,
                "agent_decision": decision,
                "tool_result": tool_res,
                "metrics": verification.metrics,
                "passed": verification.passed,
                "failure_reasons": verification.failure_reasons,
            })

            if verification.passed:
                logger.info(f"✅ Task [{task.task_id}] PASSED on iteration {iteration}!")
                break
            else:
                logger.warning(f"❌ Task [{task.task_id}] FAILED on iteration {iteration}: {verification.failure_summary}")
                error_feedback = task.format_failure_feedback(
                    attempt=iteration,
                    last_decision=decision,
                    verification=verification,
                )
                conversation_history.append({"role": "assistant", "content": json.dumps(decision)})
                conversation_history.append({"role": "user", "content": error_feedback})

        overall_success = attempt_logs[-1]["passed"]
        return {
            "task_id": task.task_id,
            "task_name": task.name,
            "overall_success": overall_success,
            "iterations_taken": len(attempt_logs),
            "attempts": attempt_logs,
            "final_metrics": attempt_logs[-1]["metrics"],
        }
