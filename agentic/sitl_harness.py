"""CLI Runner for the Generic Simulation-in-the-Loop (SiTL) Agentic Harness."""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from agentic.base import (
    AgenticTask,
    GenericAgenticHarness,
    IsaacSimMCPBridge,
    LocalLlmAgent,
    TaskVerificationResult,
)
from agentic.tasks import TASK_REGISTRY

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s")
logger = logging.getLogger("sitl_agent_harness")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generic Closed-Loop SiTL Agentic Test Harness for Isaac Sim",
    )
    parser.add_argument(
        "--task",
        default="wheel_motion",
        choices=list(TASK_REGISTRY.keys()),
        help=f"Task to execute: {list(TASK_REGISTRY.keys())}",
    )
    parser.add_argument(
        "--endpoint",
        default="http://127.0.0.1:8080/v1",
        help="Local llama.cpp API base URL",
    )
    parser.add_argument(
        "--model",
        default="Meta-Llama-3-8B-Instruct",
        help="Local model name",
    )
    parser.add_argument(
        "--mock-sim",
        action="store_true",
        default=True,
        help="Use mock physics simulation bridge (default True for offline/CI)",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum self-healing retry iterations",
    )
    parser.add_argument(
        "--output-report",
        default="work/sitl_test_report.json",
        help="Path to save verification report",
    )
    args = parser.parse_args()

    # Instantiate bridge, agent, and generic harness
    bridge = IsaacSimMCPBridge(use_mock=args.mock_sim)
    agent = LocalLlmAgent(endpoint_url=args.endpoint, model_name=args.model)
    harness = GenericAgenticHarness(bridge=bridge, agent=agent, max_retries=args.max_retries)

    # Select task from registry
    task_cls = TASK_REGISTRY[args.task]
    task_instance = task_cls()

    report = harness.run_task(task_instance)

    out_path = Path(args.output_report)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    logger.info(f"Task run completed. Report written to {out_path.resolve()}")
    if not report["overall_success"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
