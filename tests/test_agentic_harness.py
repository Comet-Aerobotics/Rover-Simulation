"""Unit tests for the Generic SiTL Agentic Test Harness and Task Suite."""
import pytest
from agentic.base import (
    GenericAgenticHarness,
    IsaacSimMCPBridge,
    LocalLlmAgent,
    TaskVerificationResult,
)
from agentic.tasks import (
    CameraSyncTask,
    StageAuditOnboardingTask,
    TASK_REGISTRY,
    WheelMotionTask,
)


def test_mcp_bridge_tool_discovery():
    bridge = IsaacSimMCPBridge(use_mock=True)
    tools = bridge.query_available_tools()
    tool_names = [t["name"] for t in tools]
    assert "isaac_set_joint_velocity" in tool_names
    assert "isaac_step_simulation" in tool_names
    assert "isaac_get_rover_telemetry" in tool_names
    assert "isaac_inspect_prim" in tool_names
    assert "isaac_inspect_camera_stream" in tool_names


def test_wheel_motion_task_pass():
    bridge = IsaacSimMCPBridge(use_mock=True)
    agent = LocalLlmAgent(endpoint_url="http://mock-offline")
    harness = GenericAgenticHarness(bridge=bridge, agent=agent, max_retries=2)

    task = WheelMotionTask(min_displacement_expected=0.1)
    report = harness.run_task(task)

    assert report["overall_success"] is True
    assert report["final_metrics"]["displacement_m"] > 0.1
    assert report["iterations_taken"] == 1


def test_wheel_motion_task_retry_on_failure():
    bridge = IsaacSimMCPBridge(use_mock=True)
    agent = LocalLlmAgent(endpoint_url="http://mock-offline")
    harness = GenericAgenticHarness(bridge=bridge, agent=agent, max_retries=3)

    # Set threshold to 10m to force assertion failure
    task = WheelMotionTask(min_displacement_expected=10.0)
    report = harness.run_task(task)

    assert report["iterations_taken"] == 3
    assert report["overall_success"] is False
    for attempt in report["attempts"]:
        assert attempt["passed"] is False


def test_onboarding_audit_task_pass():
    bridge = IsaacSimMCPBridge(use_mock=True)
    agent = LocalLlmAgent(endpoint_url="http://mock-offline")
    harness = GenericAgenticHarness(bridge=bridge, agent=agent, max_retries=2)

    task = StageAuditOnboardingTask()
    report = harness.run_task(task)

    assert report["overall_success"] is True
    assert report["final_metrics"]["rover_rigid_body"] is True
    assert report["final_metrics"]["wheel_joints"] == 4
    assert 45.0 <= report["final_metrics"]["rover_mass_kg"] <= 65.0
    assert report["final_metrics"]["terrain_has_collision"] is True


def test_camera_sync_task_pass():
    bridge = IsaacSimMCPBridge(use_mock=True)
    agent = LocalLlmAgent(endpoint_url="http://mock-offline")
    harness = GenericAgenticHarness(bridge=bridge, agent=agent, max_retries=2)

    task = CameraSyncTask()
    report = harness.run_task(task)

    assert report["overall_success"] is True
    assert report["final_metrics"]["resolution"] == "640x400"
    assert report["final_metrics"]["depth_publishing"] is True
    assert report["final_metrics"]["clock_sync_active"] is True
