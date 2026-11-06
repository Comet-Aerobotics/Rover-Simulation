"""Read-only structural checks for the canonical rover and camera OmniGraphs."""
import argparse
from pathlib import Path
from pxr import Gf, Usd, UsdGeom


def validate(scene: Path, *, local_jackal: bool = False) -> list[str]:
    stage = Usd.Stage.Open(str(scene))
    if not stage:
        return [f"Unable to open USD stage: {scene}"]
    issues = []

    def node(path, node_type):
        prim = stage.GetPrimAtPath(path)
        if not prim or not prim.IsValid():
            issues.append(f"Missing node {path}")
            return None
        actual = prim.GetAttribute("node:type").Get()
        if actual != node_type:
            issues.append(f"{path}: expected node:type {node_type}, got {actual}")
        return prim

    def value(prim, name, expected):
        if prim is None: return
        actual = prim.GetAttribute(name).Get()
        if actual != expected:
            issues.append(f"{prim.GetPath()} {name}: expected {expected!r}, got {actual!r}")

    def connection(prim, attr_name, expected):
        if prim is None: return
        actual = [str(x) for x in prim.GetAttribute(attr_name).GetConnections()]
        if actual != [expected]:
            issues.append(f"{prim.GetPath()} {attr_name}: expected connection {expected}, got {actual}")

    g = "/jackal/ActionGraph"
    sub = node(g+"/ros2_subscribe_twist", "isaacsim.ros2.bridge.ROS2SubscribeTwist")
    value(sub, "inputs:topicName", "/cmd_vel")
    scale = node(g+"/scale_to_from_stage_units", "isaacsim.core.nodes.OgnIsaacScaleToFromStageUnit")
    connection(scale, "inputs:value", g+"/ros2_subscribe_twist.outputs:linearVelocity")
    linear = node(g+"/break_3_vector_01", "omni.graph.nodes.BreakVector3")
    connection(linear, "inputs:tuple", g+"/scale_to_from_stage_units.outputs:result")
    angular = node(g+"/break_3_vector", "omni.graph.nodes.BreakVector3")
    connection(angular, "inputs:tuple", g+"/ros2_subscribe_twist.outputs:angularVelocity")
    diff = node(g+"/differential_controller", "isaacsim.robot.wheeled_robots.DifferentialController")
    value(diff, "inputs:wheelRadius", 0.098)
    value(diff, "inputs:wheelDistance", 0.3755)
    connection(diff, "inputs:linearVelocity", g+"/break_3_vector_01.outputs:x")
    connection(diff, "inputs:angularVelocity", g+"/break_3_vector.outputs:z")
    expected_joints = (["front_left_wheel", "front_right_wheel", "rear_left_wheel", "rear_right_wheel"]
                       if local_jackal else
                       ["front_left_wheel_joint", "front_right_wheel_joint",
                        "rear_left_wheel_joint", "rear_right_wheel_joint"])
    token_paths = [g+"/constant_token",g+"/constant_token_01",g+"/constant_token_02",g+"/constant_token_03"]
    for path, joint in zip(token_paths, expected_joints):
        value(stage.GetPrimAtPath(path), "inputs:value", joint)
        if local_jackal:
            joint_prim = stage.GetPrimAtPath("/jackal/base_link/" + joint)
            if not joint_prim or not joint_prim.IsValid() or joint_prim.GetTypeName() != "PhysicsRevoluteJoint":
                issues.append(f"Local Jackal wheel joint is missing or not revolute: /jackal/base_link/{joint}")
    for suffix, token_pair in (("", token_paths[:2]),("_01", token_paths[2:])):
        arr=node(g+"/make_array"+suffix,"omni.graph.nodes.ConstructArray")
        value(arr,"inputs:arraySize",2)
        connection(arr,"inputs:input0",token_pair[0]+".inputs:value")
        connection(arr,"inputs:input1",token_pair[1]+".inputs:value")
        ctrl=node(g+"/articulation_controller"+suffix,"isaacsim.core.nodes.IsaacArticulationController")
        connection(ctrl,"inputs:jointNames",g+"/make_array"+suffix+".outputs:array")
        connection(ctrl,"inputs:velocityCommand",g+"/differential_controller.outputs:velocityCommand")

    cam="/ActionGraph"
    tick=node(cam+"/OnTick", "omni.graph.action.OnTick")
    value(tick,"inputs:onlyPlayback",True)
    rp=node(cam+"/CreateRP","isaacsim.core.nodes.IsaacCreateRenderProduct")
    value(rp,"inputs:width",640); value(rp,"inputs:height",400)
    connection(rp,"inputs:execIn",cam+"/OnTick.outputs:tick")
    camera_path = "/jackal/base_link/DM9098Pro_enclosure/OAK_D_Pro_RGB"
    if rp:
        targets = [str(path) for path in rp.GetRelationship("inputs:cameraPrim").GetTargets()]
        if targets != [camera_path]:
            issues.append(f"{rp.GetPath()} camera target: expected {camera_path}, got {targets}")
    camera = stage.GetPrimAtPath(camera_path)
    mount = stage.GetPrimAtPath("/jackal/base_link/DM9098Pro_enclosure")
    if not camera or not camera.IsA(UsdGeom.Camera) or not mount:
        issues.append(f"Missing camera or mount: {camera_path}")
    else:
        camera_world = UsdGeom.Xformable(camera).ComputeLocalToWorldTransform(Usd.TimeCode.Default())
        mount_world = UsdGeom.Xformable(mount).ComputeLocalToWorldTransform(Usd.TimeCode.Default())
        offset = camera_world.ExtractTranslation() - mount_world.ExtractTranslation()
        if offset.GetLength() > 1.0:
            issues.append(f"Camera is {offset.GetLength():.3f} m from its mount; expected within 1 m")
        forward = camera_world.TransformDir(Gf.Vec3d(0, 0, -1)).GetNormalized()
        mount_forward = mount_world.TransformDir(Gf.Vec3d(1, 0, 0)).GetNormalized()
        if Gf.Dot(forward, mount_forward) < 0.99:
            issues.append("Camera optical axis does not face forward along its mount")
        clipping = UsdGeom.Camera(camera).GetClippingRangeAttr().Get()
        if not clipping or not 0 < clipping[0] <= 0.1 or clipping[1] <= clipping[0]:
            issues.append(f"Invalid camera clipping range: {clipping}")
    depth=node(cam+"/CamHelper","isaacsim.ros2.bridge.ROS2CameraHelper")
    value(depth,"inputs:topicName","/oak_d/depth"); value(depth,"inputs:type","depth")
    value(depth,"inputs:frameId","oak_d_optical_frame")
    rgb=node(cam+"/RGBHelper","isaacsim.ros2.bridge.ROS2CameraHelper")
    value(rgb,"inputs:topicName","/oak_d/rgb/image_raw"); value(rgb,"inputs:type","rgb")
    value(rgb,"inputs:frameId","oak_d_optical_frame")
    info=node(cam+"/ros2_camera_info_helper","isaacsim.ros2.bridge.ROS2CameraInfoHelper")
    value(info,"inputs:topicName","oak_d/camera_info")
    value(info,"inputs:frameId","oak_d_optical_frame")
    rgb_info=node(cam+"/RGBInfoHelper","isaacsim.ros2.bridge.ROS2CameraInfoHelper")
    value(rgb_info,"inputs:topicName","/oak_d/rgb/camera_info")
    value(rgb_info,"inputs:frameId","oak_d_optical_frame")
    for helper in (depth, rgb, info, rgb_info):
        connection(helper,"inputs:execIn",cam+"/CreateRP.outputs:execOut")
        connection(helper,"inputs:renderProductPath",cam+"/CreateRP.outputs:renderProductPath")
        if helper:
            enabled = helper.GetAttribute("inputs:enabled")
            if enabled and enabled.HasAuthoredValueOpinion() and enabled.Get() is False:
                issues.append(f"{helper.GetPath()} is disabled")
    print(f"Scene: {scene}\nRover graph: /cmd_vel to differential controller to 2 articulation controllers\nCamera graph: 640x400, /oak_d/depth, /oak_d/rgb/image_raw, oak_d/camera_info")
    return issues


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("scene",nargs="?",type=Path,default=Path("scenes/CAMERASYNCSSMOETIMES.usd"))
    parser.add_argument("--local-jackal",action="store_true",
        help="Validate the local OmniLRS Jackal candidate's wheel-joint names and prims")
    args=parser.parse_args()
    errors=validate(args.scene,local_jackal=args.local_jackal)
    for error in errors: print("ERROR:",error)
    raise SystemExit(bool(errors))
