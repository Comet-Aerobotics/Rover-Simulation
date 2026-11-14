# Rover model and motion

The selected robot is a local Jackal USD asset composed under `/jackal`. Its body, four wheel links, collision shapes, revolute joints, and sensor mounts are in the USD hierarchy. ROS supplies a desired planar velocity; an Isaac Sim differential controller turns it into wheel commands. The saved scene, not `config/simulation.yaml`, determines the actual physics values at runtime.

## Motion path

```text
/cmd_vel (linear.x, angular.z) → ROS2SubscribeTwist → stage-unit conversion
  → DifferentialController → IsaacArticulationController
  → four revolute wheel joints → contact with terrain and obstacles
```

| Part | Saved path or value | Why it matters |
| --- | --- | --- |
| Articulation root | `/jackal` | Target for wheel commands and pose reads |
| Chassis | `/jackal/base_link` | Main mass and rover-mounted sensor parent |
| Wheel links | `/jackal/{front,rear}_{left,right}_wheel_link` | Wheel pose and collision; sand runtime samples these links |
| Wheel joint tokens passed to controller | `front_left_wheel`, `front_right_wheel`, `rear_left_wheel`, `rear_right_wheel` | These match the four composed revolute joints under `/jackal/base_link/` |
| Active intended drive graph | `/jackal/ActionGraph` | Subscribes to `/cmd_vel`; radius 0.098 m, wheel separation 0.3755 m |
| Imported standalone drive graph | `/jackal/ROS2_Graph/DriveGraph` | Kept active in the reusable Jackal asset, but inactive in composed rover scenes; it does not compete with the scene controller |
| Wheel collision | Four cylinder colliders | Contact geometry is distinct from wheel render meshes |

The intended drive graph's numerical acceleration and speed limits are stage-authored values that have not been calibrated as SI limits. Do not retune them just because they appear large; the user has observed controller-driven motion in the 55 kg candidate. [Action Graphs](isaac/action-graph.md) lists the duplicate graph and audit procedure.

## Mass and physics variants

| Scene | Authored base-link mass | Wheel mass | Interpretation |
| --- | ---: | ---: | --- |
| Canonical `scenes/CAMERASYNCSSMOETIMES.usd` | `0.0` kg | About `0.477` kg per wheel | A zero authored base mass is not a measured total vehicle mass; PhysX may infer mass from shapes and densities. Dynamic acceptance is still needed. |
| `in work` 55 kg candidate | About `53.092` kg | Four × `0.477` kg | About 55 kg total by this explicit accounting. User-confirmed controller motion applies to this candidate. |
| Generated sand candidate | Copied from 55 kg candidate | Same four wheel values | Sand changes the ground representation, not the stated mass target. |

`config/simulation.yaml` records the 55 kg estimate, wheel radius, separation, and expected joint names as project intent. It does not automatically patch the canonical USD. `isaac/diagnostics/set_rover_mass.py` is a scene-editing helper; read its target and save behavior before use. The tracked canonical stage remains separate from the working candidate.

The stage is Z-up, 1 m per USD unit. The saved `/physicsScene` now uses CPU dynamics and MBP broadphase with 60 physics steps per second. A headless comparison found CPU dynamics substantially faster for this small rover scene while retaining powered motion. Use `-GpuPhysics` for a comparison launch; GUI handling and soil calibration still need acceptance. See [performance analysis](performance-analysis.md).

## Checks to make after a change

| Test | Observe | If it fails, inspect |
| --- | --- | --- |
| Joint mapping | Four wheel DOFs present and commanded by one graph | Graph joint tokens, articulation target, referenced asset variant |
| At rest | Wheels settle on visible terrain without persistent bounce or sinking | Body mass, wheel collision, terrain collider, overlapping obstacles |
| Straight command | Base moves forward and wheels rotate in the expected direction | `/cmd_vel`, imported graph activation, wheel ordering, radius |
| Turn command | Rover yaws in the commanded direction | Left/right order, angular axis mapping, wheel separation |
| Sand traversal | Ruts form beneath contacted wheels and rover responds to them | Sand runtime readiness, tile collision, wheel pose/ground query |
| Stop input | Motion command returns to zero after stale Joy input | Teleop's 0.5 s freshness timeout and ROS topic flow |

Use `isaac/diagnostics/validate_action_graph.py` for saved graph structure and `isaac/diagnostics/runtime_acceptance.py` for a controlled runtime contact check. A structural pass cannot establish traction or safe driving. Record the exact scene variant and physics setting with every handling result.

**Terms:** an *articulation* is the connected rigid-body/joint model; a *revolute joint* lets a wheel rotate about one axis; a *collider* is the contact shape PhysX uses; a *render mesh* is what the camera/viewport sees. These can disagree even when the scene looks correct.
