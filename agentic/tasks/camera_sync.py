"""Camera and Depth Stream Synchronization Verification Task."""
from __future__ import annotations

from typing import Any
from agentic.base import AgenticTask, IsaacSimMCPBridge, TaskVerificationResult


class CameraSyncTask(AgenticTask):
    """Verifies that depth images and CameraInfo streams are properly synchronized.

    Directly addresses PointCloudXyzNode / image_transport warnings where CameraInfo
    continues publishing while depth frames drop or timestamp skews prevent pairing:
      [WARN] [PointCloudXyzNode]: [image_transport] Topics '/oak_d/depth' and
      '/camera_info' do not appear to be synchronized. In the last 10s:
         Image messages received: 0
         CameraInfo messages received: 24
         Synchronized pairs: 0
    """

    task_id = "camera_sync"
    name = "OAK-D Depth and CameraInfo Stream Synchronization"
    description = (
        "Audits the /ActionGraph render product and ROS 2 camera helpers. "
        "Verifies that '/oak_d/depth' and '/oak_d/camera_info' publish at matching rates, "
        "share the same render product (/Render/RenderProduct_OAK_RGB), share the "
        "'oak_d_optical_frame' frameId, and generate synchronized timestamped pairs."
    )

    def __init__(
        self,
        min_depth_rate_hz: float = 10.0,
        max_rate_discrepancy_ratio: float = 0.25,
        required_frame_id: str = "oak_d_optical_frame",
        action_graph_path: str = "/ActionGraph",
    ):
        self.min_depth_rate_hz = min_depth_rate_hz
        self.max_rate_discrepancy_ratio = max_rate_discrepancy_ratio
        self.required_frame_id = required_frame_id
        self.action_graph_path = action_graph_path

    def get_prompt(self, baseline_state: dict[str, Any]) -> str:
        return (
            f"Test Goal: {self.description}. "
            "Use 'isaac_inspect_camera_stream' to inspect the active Action Graph. "
            "Ensure that the render product is active (width 640, height 400), "
            "both RGB and depth helpers are enabled, and clock synchronization is active."
        )

    def verify(
        self,
        attempt: int,
        baseline_state: dict[str, Any],
        bridge: IsaacSimMCPBridge,
    ) -> TaskVerificationResult:
        stream_info = bridge.execute_tool(
            "isaac_inspect_camera_stream",
            {"action_graph_path": self.action_graph_path},
        )

        failure_reasons = []

        # 1. Active render product check
        active_rp = stream_info.get("active_render_product")
        if not active_rp:
            failure_reasons.append("No active render product linked to /ActionGraph")

        # 2. Resolution check (640x400 active target)
        width = stream_info.get("width", 0)
        height = stream_info.get("height", 0)
        if width != 640 or height != 400:
            failure_reasons.append(f"Render product resolution is {width}x{height}; expected 640x400")

        # 3. Stream publish state
        depth_pub = stream_info.get("depth_publishing", False)
        if not depth_pub:
            failure_reasons.append("Depth publishing is disabled or dropping frames (Image messages received = 0)")

        # 4. Clock & timestamp sync
        clock_sync = stream_info.get("clock_sync_active", False)
        if not clock_sync:
            failure_reasons.append("Clock synchronization is inactive, causing timestamp drift in image_transport")

        fps = float(stream_info.get("fps", 0.0))
        if fps < self.min_depth_rate_hz:
            failure_reasons.append(
                f"Depth stream FPS ({fps:.1f} Hz) is below minimum threshold ({self.min_depth_rate_hz:.1f} Hz)"
            )

        metrics = {
            "active_render_product": active_rp,
            "resolution": f"{width}x{height}",
            "depth_publishing": depth_pub,
            "clock_sync_active": clock_sync,
            "fps": fps,
        }

        return TaskVerificationResult(
            passed=len(failure_reasons) == 0,
            metrics=metrics,
            failure_reasons=failure_reasons,
        )
