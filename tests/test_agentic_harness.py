"""Unit tests for the Closed-Loop SiTL Agentic Test Harness."""
import pytest
from agentic.sitl_harness import (
    IsaacSimMCPBridge,
    LocalLlmAgent,
    ClosedLoopSitlFuzzer,
    PhysicalAssertionResult,
)


def test_mcp_bridge_tool_discovery():
    bridge = IsaacSimMCPBridge(use_mock=True)
    tools = bridge.query_available_tools()
    tool_names = [t["name"] for t in tools]
    assert "isaac_set_joint_velocity" in tool_names
    assert "isaac_step_simulation" in tool_names
    assert "isaac_get_rover_telemetry" in tool_names


def test_fuzzer_successful_pass():
    bridge = IsaacSimMCPBridge(use_mock=True)
    agent = LocalLlmAgent(endpoint_url="http://mock-offline")
    fuzzer = ClosedLoopSitlFuzzer(bridge=bridge, agent=agent, max_retries=2)

    report = fuzzer.run_goal_test(
        goal_name="test_pass",
        goal_description="Drive forward at 2.0 rad/s",
        min_displacement_expected=0.1,
    )
    assert report["overall_success"] is True
    assert report["final_displacement_m"] > 0.1
    assert report["iterations_taken"] == 1


def test_fuzzer_assertion_failure_and_retry():
    bridge = IsaacSimMCPBridge(use_mock=True)
    agent = LocalLlmAgent(endpoint_url="http://mock-offline")
    fuzzer = ClosedLoopSitlFuzzer(bridge=bridge, agent=agent, max_retries=3)

    # Set an impossible threshold on the first attempt (10 meters) to force retry
    report = fuzzer.run_goal_test(
        goal_name="test_high_threshold",
        goal_description="Drive forward to reach 10 meters in 1 second",
        min_displacement_expected=10.0,
    )
    # Should attempt all retries and log failures
    assert report["iterations_taken"] == 3
    assert report["overall_success"] is False
    assert len(report["attempts"]) == 3
    for attempt in report["attempts"]:
        assert attempt["passed"] is False
