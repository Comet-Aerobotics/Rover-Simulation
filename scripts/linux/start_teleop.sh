#!/usr/bin/env bash
set -euo pipefail
source /opt/ros/humble/setup.bash
ws=${ROS_WORKSPACE:-/root/CAN/cometbot_ws}
[[ -f "$ws/install/setup.bash" ]] || { echo "ROS workspace is not built: $ws" >&2; exit 2; }
source "$ws/install/setup.bash"
nodes=$(ros2 node list 2>/dev/null || true)
if grep -Eq '^/(joy_node|teleop_publisher)$' <<<"$nodes"; then echo 'Existing joy/teleop node found; refusing duplicate launch.' >&2; exit 3; fi
exec ros2 launch cometbot_control teleop.launch.py
