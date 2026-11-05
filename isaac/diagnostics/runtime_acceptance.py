"""Run an Isaac Sim runtime smoke test against the local Jackal candidate.

The script is intended for Isaac Sim's ``--exec`` startup hook. It opens the
candidate scene, checks the rover articulation and wheel/terrain contacts,
captures a rendered view, and samples wheel motion while a separate ROS 2
publisher sends a short, low-speed ``/cmd_vel`` test.
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import traceback

import numpy as np
import omni.kit.app
import omni.timeline
import omni.usd
import omni.graph.core as og
from pxr import PhysicsSchemaTools, Usd, UsdGeom, UsdPhysics


async def _run() -> None:
    app = omni.kit.app.get_app()
    scene_path = os.environ.get("AIAA_ROVER_SCENE")
    report_path = Path(os.environ.get("AIAA_ROVER_REPORT", "work/isaac-runtime-report.json"))
    ready_path = report_path.with_suffix(".ready.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report: dict[str, object] = {"scene": scene_path, "checks": {}}
    try:
        if not scene_path:
            raise RuntimeError("AIAA_ROVER_SCENE is not set")
        if not omni.usd.get_context().open_stage(scene_path):
            raise RuntimeError(f"Could not open stage: {scene_path}")
        for _ in range(120):
            await app.next_update_async()
            stage = omni.usd.get_context().get_stage()
            if stage and stage.GetPrimAtPath("/jackal").IsValid():
                break
        else:
            raise RuntimeError("Timed out waiting for /jackal to compose")

        stage = omni.usd.get_context().get_stage()
        checks = report["checks"]
        assert isinstance(checks, dict)
        checks["stage_opened"] = True
        checks["stage_up_axis"] = UsdGeom.GetStageUpAxis(stage)
        checks["meters_per_unit"] = float(UsdGeom.GetStageMetersPerUnit(stage))

        terrain_path = "/Lunalab/Terrain/terrain_mesh"
        terrain = stage.GetPrimAtPath(terrain_path)
        if not terrain.IsValid() or not terrain.HasAPI(UsdPhysics.CollisionAPI):
            raise RuntimeError(f"Terrain collider is missing: {terrain_path}")
        checks["terrain_collider"] = terrain_path

        collision_count = 0
        for prim in Usd.PrimRange(stage.GetPseudoRoot()):
            if prim.HasAPI(UsdPhysics.CollisionAPI):
                collision_count += 1
        checks["collision_prim_count"] = collision_count

        from isaacsim.core.experimental.prims import Articulation
        from isaacsim.sensors.experimental.physics import Contact, ContactSensor

        articulation = Articulation("/jackal")
        expected_wheels = [
            "front_left_wheel", "front_right_wheel",
            "rear_left_wheel", "rear_right_wheel",
        ]
        missing_wheels = [name for name in expected_wheels if name not in articulation.dof_names]
        if missing_wheels:
            raise RuntimeError(f"Wheel DOFs missing from articulation: {missing_wheels}; found {articulation.dof_names}")
        wheel_indices = articulation.get_dof_indices(expected_wheels)
        checks["wheel_dofs"] = expected_wheels

        wheel_links = dict(zip(articulation.link_names, articulation.link_paths[0]))
        expected_wheel_links = [name + "_link" for name in expected_wheels]
        wheel_link = next((wheel_links[name] for name in expected_wheel_links if name in wheel_links), None)
        if not wheel_link:
            raise RuntimeError(f"No wheel rigid-body links found; available links: {articulation.link_names}")
        sensor_path = wheel_link + "/CodexRuntimeContactSensor"
        contact_sensor = ContactSensor(
            Contact.create(
                sensor_path,
                translations=[[0.0, 0.0, 0.0]],
                min_threshold=0.0,
                max_threshold=1000000.0,
                radius=-1.0,
            )
        )

        timeline = omni.timeline.get_timeline_interface()
        timeline.play()
        for _ in range(90):
            await app.next_update_async()

        def as_numpy(value):
            return value.numpy() if hasattr(value, "numpy") else np.asarray(value)

        graph_read_errors: dict[str, str] = {}

        def graph_value(node, attribute_name):
            """Read the current OmniGraph value, including values held in Fabric."""
            usd_attribute = node.GetAttribute(attribute_name)
            try:
                return og.Controller.get(og.Controller.attribute(usd_attribute))
            except Exception as error:
                # Some legacy-authored graph prims in Isaac Sim 6.1 are readable
                # through USD but are not registered as runtime OmniGraph nodes.
                # Preserve the lookup error and fall back to the authored USD
                # value so the remaining contact and articulation checks finish.
                graph_read_errors[attribute_name] = repr(error)
                return usd_attribute.Get()

        initial_position = as_numpy(articulation.get_world_poses()[0])[0].astype(float)
        initial_wheel_velocities = as_numpy(articulation.get_dof_velocities(dof_indices=wheel_indices))[0].astype(float)
        checks["initial_root_position_m"] = initial_position.tolist()
        checks["initial_wheel_speeds_rad_s"] = initial_wheel_velocities.tolist()

        screenshot = report_path.with_suffix(".png")
        try:
            from isaacsim.test.utils.image_capture import capture_rgb_data_async
            from isaacsim.test.utils.image_io import save_rgb_image

            camera_position = initial_position + np.asarray([3.5, -4.0, 2.5])
            rgb = await capture_rgb_data_async(
                camera_position=tuple(camera_position.tolist()),
                camera_look_at=tuple(initial_position.tolist()),
                resolution=(960, 540),
            )
            save_rgb_image(rgb, str(screenshot.parent), screenshot.name)
            checks["render_capture"] = {"ok": screenshot.exists(), "path": str(screenshot), "shape": list(rgb.shape)}
        except Exception as error:
            checks["render_capture"] = {"ok": False, "error": repr(error)}

        report["status"] = "ready_for_ros_twist"
        ready_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"AIAA_RUNTIME_READY: {ready_path}", flush=True)

        subscriber = stage.GetPrimAtPath("/jackal/ActionGraph/ros2_subscribe_twist")
        differential = stage.GetPrimAtPath("/jackal/ActionGraph/differential_controller")
        local_ros_result: dict[str, object] = {"tested": False}
        try:
            import rclpy
            from geometry_msgs.msg import Twist

            rclpy.init(args=None)
            ros_node = rclpy.create_node("aiaa_runtime_twist_probe")
            ros_publisher = ros_node.create_publisher(Twist, "/cmd_vel", 10)
            local_max_subscriber_linear_x = 0.0
            local_max_controller_wheel_target = 0.0
            for frame in range(240):
                message = Twist()
                if frame < 90:
                    message.linear.x = 0.05
                ros_publisher.publish(message)
                rclpy.spin_once(ros_node, timeout_sec=0.0)
                await app.next_update_async()
                value = graph_value(subscriber, "outputs:linearVelocity")
                if value is not None:
                    local_max_subscriber_linear_x = max(local_max_subscriber_linear_x, abs(float(value[0])))
                target = graph_value(differential, "outputs:velocityCommand")
                if target is not None and len(target):
                    local_max_controller_wheel_target = max(
                        local_max_controller_wheel_target,
                        float(np.max(np.abs(np.asarray(target, dtype=float)))),
                    )
            local_ros_result = {
                "tested": True,
                "matched_subscriptions": int(ros_publisher.get_subscription_count()),
                "max_subscriber_linear_x_m_s": local_max_subscriber_linear_x,
                "max_differential_wheel_target_rad_s": local_max_controller_wheel_target,
            }
            ros_node.destroy_node()
            rclpy.shutdown()
        except Exception as error:
            local_ros_result = {"tested": False, "error": repr(error)}
            try:
                if "rclpy" in locals() and rclpy.ok():
                    rclpy.shutdown()
            except Exception:
                pass
        checks["same_host_ros_probe"] = local_ros_result
        report["status"] = "ready_for_external_ros_twist"
        ready_path.with_name(ready_path.stem + ".external.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
        print(f"AIAA_EXTERNAL_ROS_READY: {ready_path.with_name(ready_path.stem + '.external.json')}", flush=True)

        peak_wheel_speed = 0.0
        max_translation = 0.0
        contact_seen = False
        contact_reading_valid = False
        max_contact_force = 0.0
        raw_contact_count = 0
        raw_contact_bodies: set[str] = set()
        max_subscriber_linear_x = 0.0
        max_controller_wheel_target = 0.0
        # A few simulated seconds are sufficient to observe the short velocity
        # pulse and resulting wheel/root motion without leaving a headless Kit
        # instance running for an unnecessarily long acceptance window.
        for _ in range(600):
            await app.next_update_async()
            velocities = as_numpy(articulation.get_dof_velocities(dof_indices=wheel_indices))
            peak_wheel_speed = max(peak_wheel_speed, float(np.max(np.abs(velocities))))
            linear_velocity = graph_value(subscriber, "outputs:linearVelocity")
            if linear_velocity is not None:
                max_subscriber_linear_x = max(max_subscriber_linear_x, abs(float(linear_velocity[0])))
            wheel_target = graph_value(differential, "outputs:velocityCommand")
            if wheel_target is not None and len(wheel_target):
                max_controller_wheel_target = max(
                    max_controller_wheel_target,
                    float(np.max(np.abs(np.asarray(wheel_target, dtype=float)))),
                )
            position = as_numpy(articulation.get_world_poses()[0])[0].astype(float)
            max_translation = max(max_translation, float(np.linalg.norm(position - initial_position)))
            reading = contact_sensor.get_sensor_reading()
            if reading.is_valid:
                contact_reading_valid = True
                contact_seen = contact_seen or bool(reading.in_contact)
                max_contact_force = max(max_contact_force, float(reading.value))
                raw_contacts = contact_sensor.get_raw_data()
                raw_contact_count = max(raw_contact_count, len(raw_contacts))
                for raw_contact in raw_contacts:
                    for key in ("body0", "body1"):
                        body_id = raw_contact.get(key)
                        if body_id:
                            try:
                                raw_contact_bodies.add(str(PhysicsSchemaTools.intToSdfPath(int(body_id))))
                            except Exception:
                                raw_contact_bodies.add(str(body_id))

        final_position = as_numpy(articulation.get_world_poses()[0])[0].astype(float)
        timeline.pause()
        checks["peak_wheel_speed_rad_s"] = peak_wheel_speed
        checks["max_root_translation_m"] = max_translation
        checks["final_root_position_m"] = final_position.tolist()
        checks["wheel_contact_seen"] = contact_seen
        checks["contact_sensor_reading_valid"] = contact_reading_valid
        checks["max_wheel_contact_force_n"] = max_contact_force
        checks["max_raw_contact_count"] = raw_contact_count
        checks["contact_body_paths"] = sorted(raw_contact_bodies)
        checks["wheel_terrain_contact_verified"] = (
            wheel_link in raw_contact_bodies and terrain_path in raw_contact_bodies
        )
        checks["max_ros_subscriber_linear_x_m_s"] = max_subscriber_linear_x
        checks["max_differential_wheel_target_rad_s"] = max_controller_wheel_target
        checks["contact_sensor_path"] = sensor_path
        checks["graph_runtime_read_errors"] = graph_read_errors
        checks["ros_cmd_vel_received"] = max_subscriber_linear_x > 0.01
        checks["ros_cmd_vel_motion_observed"] = checks["ros_cmd_vel_received"] and max_translation > 0.003
        report["status"] = "complete"
    except Exception as error:
        report["status"] = "error"
        report["error"] = repr(error)
        report["traceback"] = traceback.format_exc()
        print("AIAA_RUNTIME_ERROR:", traceback.format_exc(), flush=True)
    finally:
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"AIAA_RUNTIME_REPORT: {report_path}", flush=True)
        await app.next_update_async()
        app.post_quit()


asyncio.ensure_future(_run())
