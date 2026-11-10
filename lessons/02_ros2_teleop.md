# Lesson 02: ROS 2 Fast DDS Bridging & Dual-Target Autonomy

## Overview
In this lesson, you will learn how the rover's autonomy stack bridges between containerized ROS 2 Humble nodes and Isaac Sim 6.1. You will also understand the hardware abstraction boundary that enables identical software to drive both physical robots and simulations.

---

## 1. Key Concepts

### The `/cmd_vel` Hardware Boundary
The autonomy software is written to be target-agnostic. The boundary between simulation and real-world execution is drawn strictly at actuation and sensor topics:
* **Physical Target**: `/cmd_vel` $\to$ C++ SocketCAN node $\to$ USB CAN-FD Isolator $\to$ REV SPARK MAX motor controllers $\to$ NEO brushless motors.
* **Simulation Target**: `/cmd_vel` $\to$ Omniverse ROS 2 Bridge $\to$ Action Graph Differential Controller $\to$ PhysX 5 wheel joint drives.

### Fast DDS Middleware & Domain Matching
Isaac Sim and Docker use eProsima Fast DDS (`rmw_fastrtps_cpp`). For nodes to communicate without a central master:
1. `ROS_DOMAIN_ID` must match (default: `0`).
2. Both host and container must share network visibility (WSL 2 host networking).
3. The Isaac Sim timeline must be in **Play** mode so Action Graph ROS subscribers run.

---

## 2. Guided Exercise: Driving & Verifying Sensor Streams

### Step 1: Start Simulation and Press Play
Launch the stack from PowerShell:
```powershell
.\scripts\windows\start_rover_all.ps1
```
In Isaac Sim, press the **Play** button (spacebar) in the left toolbar.

### Step 2: Test Actuation (Keyboard Teleop Fallback)
Inside the running container or in a new WSL terminal:
```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```
Use keys `i` (forward), `j` (left), `l` (right), and `,` (reverse) to command `/cmd_vel`. Observe the wheel joints articulating and the rover moving across the terrain mesh.

### Step 3: Verify Topic Rates
Open another terminal and verify synthetic sensor publication:
```bash
# Check Lidar scan rate (Expected: ~20 Hz)
ros2 topic hz /scan

# Check RGB camera stream rate (Expected: ~20 Hz)
ros2 topic hz /oak_d/rgb/image_raw
```

---

## 3. Hands-On Experiment ("Try It Yourself")

### Experiment: Diagnosing Camera / Point Cloud Desynchronization
* **Context**: When running ROS 2 pointcloud generation nodes (e.g. `PointCloudXyzNode`), you may observe this warning:
  ```text
  [WARN] [PointCloudXyzNode]: [image_transport] Topics '/oak_d/depth' and '/camera_info' do not appear to be synchronized.
      Image messages received: 0
      CameraInfo messages received: 24
      Synchronized pairs: 0
  ```
* **Investigation**:
  1. Inspect the active topic namespaces:
     ```bash
     ros2 topic list | grep camera_info
     ```
  2. Notice that the Action Graph publishes to `/oak_d/camera_info` and `/oak_d/rgb/camera_info`, while the downstream node was listening for `/camera_info`.
* **Fix**: Launch the configured point-cloud node, or remap both subscriptions explicitly:
  ```bash
  ros2 launch cometbot_control pointcloud.launch.py
  # Equivalent direct command:
  ros2 run depth_image_proc point_cloud_xyz_node --ros-args -r image_rect:=/oak_d/depth -r /camera_info:=/oak_d/camera_info
  ```
* **Verify**: Run `python3 scripts/linux/check_camera_sync.py` from the repository root in a ROS-sourced Humble shell. It measures real depth and CameraInfo messages and exact header-stamp pairs. The agentic harness defaults to mock data and is not a live camera test.

---

## 4. Knowledge Check

**Question 1**: Why does the simulation publish a `/clock` topic to ROS 2, and what happens if ROS 2 nodes use system wall-clock time instead of simulation time?
<details>
<summary>Answer</summary>
When simulation physics runs faster or slower than real wall-clock time (or during frame drops), the simulation clock maintains consistent physics time steps. If ROS 2 nodes ignore simulation clock (`use_sim_time:=false`), sensor timestamp buffers and TF transform lookups will fail with extrapolation errors.
</details>

**Question 2**: Why is the Twist Mux placed before the CAN driver node and the Isaac Sim Bridge rather than having separate planners for simulation and physical hardware?
<details>
<summary>Answer</summary>
Placing the abstraction at the Twist Mux guarantees Sim-to-Real parity: the planning, state machine, and safety systems run identical code and undergo identical validation regardless of the deployment target.
</details>
