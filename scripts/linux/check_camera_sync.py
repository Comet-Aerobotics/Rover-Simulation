#!/usr/bin/env python3
"""Measure live OAK depth/CameraInfo delivery and exact ROS header pairing."""

import argparse
from collections import Counter
import json
import time

import rclpy
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CameraInfo, Image


def stamp(message):
    return message.header.stamp.sec, message.header.stamp.nanosec


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=float, default=15.0)
    parser.add_argument("--min-depth-hz", type=float, default=1.0)
    parser.add_argument("--min-pair-ratio", type=float, default=0.95)
    parser.add_argument("--max-info-ratio", type=float, default=1.5)
    args = parser.parse_args()
    if args.seconds <= 0 or args.min_depth_hz < 0:
        parser.error("seconds must be positive and min-depth-hz cannot be negative")

    depth_stamps = Counter()
    info_stamps = Counter()
    rclpy.init()
    node = rclpy.create_node("oak_camera_sync_probe")
    subscriptions = [
        node.create_subscription(Image, "/oak_d/depth", lambda msg: depth_stamps.update([stamp(msg)]), qos_profile_sensor_data),
        node.create_subscription(CameraInfo, "/oak_d/camera_info", lambda msg: info_stamps.update([stamp(msg)]), qos_profile_sensor_data),
    ]
    try:
        start = time.monotonic()
        while time.monotonic() - start < args.seconds:
            rclpy.spin_once(node, timeout_sec=0.1)
        elapsed = time.monotonic() - start
    finally:
        subscriptions.clear()
        node.destroy_node()
        rclpy.shutdown()

    depth_count = depth_stamps.total()
    info_count = info_stamps.total()
    pairs = sum(min(count, info_stamps[key]) for key, count in depth_stamps.items())
    result = {
        "seconds": round(elapsed, 2),
        "depth_messages": depth_count,
        "camera_info_messages": info_count,
        "exact_pairs": pairs,
        "depth_hz": round(depth_count / elapsed, 2),
        "pair_ratio": round(pairs / depth_count, 3) if depth_count else 0.0,
        "info_to_depth_ratio": round(info_count / depth_count, 3) if depth_count else None,
    }
    print(json.dumps(result, sort_keys=True))
    return 0 if (
        depth_count > 0
        and depth_count / elapsed >= args.min_depth_hz
        and pairs / depth_count >= args.min_pair_ratio
        and info_count / depth_count <= args.max_info_ratio
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
