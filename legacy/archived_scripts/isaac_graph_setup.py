# ═══════════════════════════════════════════════════════════════
# OAK-D PRO CAMERA SETUP — Run once after Isaac Sim loads
# Safe to re-run — guards prevent double-creation of everything
# ═══════════════════════════════════════════════════════════════

import omni.graph.core as og
import omni.kit.commands
import omni.timeline
import omni.kit.app
import omni.usd
import carb.settings
import isaacsim.core.utils.prims as prim_utils
from isaacsim.sensors.camera import Camera
from pxr import UsdGeom, UsdRender, Sdf, Vt, Gf, Usd

# ── 0. GUARD: ROS2 must be healthy ────────────────────────────
try:
    import rclpy
    if not rclpy.ok():
        raise RuntimeError(
            "rclpy not initialized.\n"
            "Wait for Isaac Sim to fully load, then re-run.\n"
            "If this persists, restart Isaac Sim."
        )
    print("[OK] rclpy healthy")
except ImportError:
    raise RuntimeError("rclpy not found — is the ROS2 bridge extension enabled?")

# ── 1. CONSTANTS ──────────────────────────────────────────────
CAMERA_PATH = "/World/DM9098Pro_enclosure/OAK_D_Pro_RGB"
GRAPH_PATH  = "/ActionGraph"
TOPIC       = "/oak_d/depth"
FRAME_ID    = "oak_d_optical_frame"
PROTECTED   = {"/Render/OmniverseKit/HydraTextures/omni_kit_widget_viewport_ViewportTexture_0"}

WIDTH, HEIGHT   = 640, 400
PIXEL_SIZE_MM   = 0.003
FX, FY          = 797.057, 796.776
CX, CY          = 324.796, 192.369
DIST_COEFFS     = [21.182, -29.720, 0.00025, -0.00006, 10.933, 20.632, -28.153, 9.791]
H_APERTURE_MM   = PIXEL_SIZE_MM * WIDTH
V_APERTURE_MM   = H_APERTURE_MM / (WIDTH / HEIGHT)
FOCAL_LENGTH_MM = ((FX + FY) / 2.0) * PIXEL_SIZE_MM

stage    = omni.usd.get_context().get_stage()
timeline = omni.timeline.get_timeline_interface()
settings = carb.settings.get_settings()

# ── 2. PERFORMANCE SETTINGS ───────────────────────────────────
settings.set("/rtx/rendermode",               "RasterizedLighting")
settings.set("/app/window/vsyncEnabled",      False)
settings.set("/app/asyncRendering",           True)
settings.set("/app/asyncRenderingLowLatency", True)
settings.set("/rtx/post/aa/op",               0)
settings.set("/rtx/ambientOcclusion/enabled", False)
settings.set("/rtx/reflections/enabled",      False)
settings.set("/rtx/shadows/enabled",          False)
settings.set("/rtx/indirectDiffuse/enabled",  False)
settings.set("/physics/numThreads",           16)
settings.set("/physics/timeStepsPerSecond",   60)
settings.set("/persistent/app/omniverse/saveRenderProducts", False)
print("[OK] Performance settings applied")

# ── 3. GUARD: remove stale render products from USD layer ─────
layer = stage.GetRootLayer()
stale = []
for path in [
    "/Render/OmniverseKit/HydraTextures/Replicator",
    "/Render/OmniverseKit/HydraTextures/Replicator_01",
    "/Render/OmniverseKit/HydraTextures/Replicator_02",
    "/Render/OmniverseKit/HydraTextures/Replicator_03",
    "/Render/OmniverseKit/HydraTextures/Replicator_04",
]:
    if layer.GetPrimAtPath(path):
        stale.append(path)

if stale:
    edit = Sdf.BatchNamespaceEdit()
    for path in stale:
        edit.Add(Sdf.Path(path), Sdf.Path.emptyPath)
    result = layer.Apply(edit)
    if result:
        layer.Save()
        print(f"[OK] Removed {len(stale)} stale render product(s) from USD layer")
    else:
        print(f"[WARN] Could not remove stale render products from layer — may accumulate")
else:
    print("[OK] No stale render products in USD layer")

# ── 4. GUARD: check for runtime render product duplicates ──────
existing_rps = []
for prim in stage.Traverse():
    if prim.GetTypeName() != "RenderProduct": continue
    path = str(prim.GetPath())
    if path in PROTECTED: continue
    rp   = UsdRender.Product(prim)
    tgts = rp.GetCameraRel().GetTargets()
    if tgts and str(tgts[0]) == CAMERA_PATH:
        existing_rps.append(path)

if len(existing_rps) > 1:
    print(f"[ABORT] {len(existing_rps)} duplicate render products exist at runtime.")
    print("        These are locked by Hydra and cannot be deleted without restarting Isaac Sim.")
    for p in existing_rps: print(f"        {p}")
    raise SystemExit("Restart Isaac Sim, then re-run this script.")
elif len(existing_rps) == 1:
    print(f"[OK] 1 render product already exists: {existing_rps[0]}")
else:
    print("[OK] No existing render products — will create fresh")

# ── 5. CAMERA PRIM ────────────────────────────────────────────
if not prim_utils.is_prim_path_valid(CAMERA_PATH):
    prim_utils.create_prim(CAMERA_PATH, "Camera")
    print(f"[OK] Created camera prim: {CAMERA_PATH}")
else:
    print(f"[OK] Camera prim exists: {CAMERA_PATH}")

# Fix scale — parent enclosure has 0.001 scale, counter with 1000x
cam_prim = stage.GetPrimAtPath(CAMERA_PATH)

# Only reset xform if scale is wrong
world_xform = UsdGeom.Xformable(cam_prim).ComputeLocalToWorldTransform(Usd.TimeCode.Default())
world_scale = world_xform.GetRow3(0).GetLength()

if abs(world_scale - 1.0) > 0.01:
    cam_prim.GetAttribute("xformOpOrder").Set(Vt.TokenArray([]))
    xform = UsdGeom.Xformable(cam_prim)
    xform.AddTranslateOp(UsdGeom.XformOp.PrecisionDouble).Set(Gf.Vec3d(0, 0, 0))
    xform.AddScaleOp(UsdGeom.XformOp.PrecisionDouble).Set(Gf.Vec3d(1000, 1000, 1000))
    print(f"[OK] Camera scale fixed: {world_scale:.4f} → 1.0")
else:
    print(f"[OK] Camera scale already correct: {world_scale:.4f}")

# Apply calibration — always set, idempotent
cam_usd = UsdGeom.Camera(cam_prim)
cam_usd.GetHorizontalApertureAttr().Set(H_APERTURE_MM)
cam_usd.GetVerticalApertureAttr().Set(V_APERTURE_MM)
cam_usd.GetFocalLengthAttr().Set(FOCAL_LENGTH_MM)
cam_usd.GetClippingRangeAttr().Set((1.0, 500000.0))

camera = Camera(prim_path=CAMERA_PATH, resolution=(WIDTH, HEIGHT))
camera.initialize()
camera.set_focal_length(FOCAL_LENGTH_MM)
camera.set_horizontal_aperture(H_APERTURE_MM)
camera.set_vertical_aperture(V_APERTURE_MM)
camera.set_lens_distortion_model("OmniLensDistortionFthetaAPI")
camera.set_rational_polynomial_properties(WIDTH, HEIGHT, CX, CY, 89.5, DIST_COEFFS)
print(f"[OK] Camera calibrated: {WIDTH}x{HEIGHT}  f={FOCAL_LENGTH_MM:.3f}mm")

# ── 6. GUARD: action graph ────────────────────────────────────
graph_exists  = prim_utils.is_prim_path_valid(GRAPH_PATH)
nodes_valid   = False

if graph_exists:
    graph = og.get_graph_by_path(GRAPH_PATH)
    try:
        n1 = og.Controller.node(f"{GRAPH_PATH}/OnTick")
        n2 = og.Controller.node(f"{GRAPH_PATH}/CreateRP")
        n3 = og.Controller.node(f"{GRAPH_PATH}/CamHelper")
        nodes_valid = all(n and n.is_valid() for n in [n1, n2, n3])

        # Check topic matches what we want
        current_topic = n3.get_attribute("inputs:topicName").get()
        current_type  = n3.get_attribute("inputs:type").get()
        current_cam   = n2.get_attribute("inputs:cameraPrim").get()
        cam_match     = current_cam and str(current_cam[0]) == CAMERA_PATH
        config_match  = (current_topic == TOPIC and
                        current_type  == "depth" and
                        cam_match)
    except Exception:
        nodes_valid  = False
        config_match = False
else:
    config_match = False

if graph_exists and nodes_valid and config_match:
    print(f"[OK] Graph already configured correctly — skipping recreation")
    print(f"     topic={current_topic}  type={current_type}")
else:
    if graph_exists:
        reason = "nodes invalid" if not nodes_valid else f"config mismatch (topic={current_topic}, type={current_type})"
        print(f"[INFO] Recreating graph — {reason}")
        prim_utils.delete_prim(GRAPH_PATH)
    else:
        print("[INFO] Creating graph fresh")

    keys = og.Controller.Keys
    og.Controller.edit(
        {"graph_path": GRAPH_PATH, "evaluator_name": "execution"},
        {
            keys.CREATE_NODES: [
                ("OnTick",    "omni.graph.action.OnTick"),
                ("CreateRP",  "isaacsim.core.nodes.IsaacCreateRenderProduct"),
                ("CamHelper", "isaacsim.ros2.bridge.ROS2CameraHelper"),
            ],
            keys.SET_VALUES: [
                ("CreateRP.inputs:width",                      WIDTH),
                ("CreateRP.inputs:height",                     HEIGHT),
                ("CreateRP.inputs:cameraPrim",                 [CAMERA_PATH]),
                ("CamHelper.inputs:type",                      "depth"),
                ("CamHelper.inputs:topicName",                 TOPIC),
                ("CamHelper.inputs:frameId",                   FRAME_ID),
                ("CamHelper.inputs:resetSimulationTimeOnStop", True),
                ("OnTick.inputs:onlyPlayback",                 True),
            ],
            keys.CONNECT: [
                ("OnTick.outputs:tick",                "CreateRP.inputs:execIn"),
                ("CreateRP.outputs:execOut",           "CamHelper.inputs:execIn"),
                ("CreateRP.outputs:renderProductPath", "CamHelper.inputs:renderProductPath"),
            ],
        },
    )

    val = og.Controller.node(f"{GRAPH_PATH}/CreateRP").get_attribute("inputs:cameraPrim").get()
    print(f"[OK] Graph created — cameraPrim={val}")

# ── 7. FINAL STATUS ───────────────────────────────────────────
rp_count = sum(
    1 for p in stage.Traverse()
    if p.GetTypeName() == "RenderProduct"
    and str(p.GetPath()) not in PROTECTED
)

print(f"\n{'─'*50}")
print(f"Camera:    {CAMERA_PATH}")
print(f"Graph:     {GRAPH_PATH}")
print(f"Topic:     {TOPIC}  (depth image)")
print(f"Frame ID:  {FRAME_ID}")
print(f"Resolution:{WIDTH}x{HEIGHT}")
print(f"Render products (non-viewport): {rp_count}")
print(f"{'─'*50}")

if rp_count <= 1:
    print("✓ Setup complete — hit Play")
    print("\nIn Docker, run the pointcloud converter:")
    print("  ros2 run depth_image_proc point_cloud_xyz_node \\")
    print("    --ros-args \\")
    print("    -r image_rect:=/oak_d/depth \\")
    print("    -r camera_info:=/oak_d/camera_info \\")
    print("    -p queue_size:=1 &")
else:
    print("⚠ Multiple render products — restart Isaac Sim and re-run")
