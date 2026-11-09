"""Agentic Task Suite."""
from agentic.tasks.wheel_motion import WheelMotionTask
from agentic.tasks.onboarding import StageAuditOnboardingTask
from agentic.tasks.camera_sync import CameraSyncTask

TASK_REGISTRY = {
    "wheel_motion": WheelMotionTask,
    "onboarding_audit": StageAuditOnboardingTask,
    "camera_sync": CameraSyncTask,
    # Friendly aliases
    "drive": WheelMotionTask,
    "onboarding": StageAuditOnboardingTask,
    "camera": CameraSyncTask,
}

__all__ = [
    "WheelMotionTask",
    "StageAuditOnboardingTask",
    "CameraSyncTask",
    "TASK_REGISTRY",
]
