#!/usr/bin/env bash
set -u
source /opt/ros/humble/setup.bash
if [[ -f /root/CAN/cometbot_ws/install/setup.bash ]]; then source /root/CAN/cometbot_ws/install/setup.bash; fi
printf 'ROS_DISTRO=%s ROS_DOMAIN_ID=%s RMW_IMPLEMENTATION=%s\n' "${ROS_DISTRO:-unset}" "${ROS_DOMAIN_ID:-unset}" "${RMW_IMPLEMENTATION:-unset}"
printf '\nNodes:\n'; ros2 node list || exit 1
for topic in /joy /cmd_vel; do printf '\n%s:\n' "$topic"; ros2 topic info "$topic" || true; done
printf '\nInput devices:\n'; ls -l /dev/input/js* /dev/input/event* 2>/dev/null || true
