# Comet Rover Simulation Onboarding Curriculum

A progressive, hands-on learning path designed to onboard engineers and researchers onto the AIAA Isaac Sim rover stack, ROS 2 autonomy integration, and closed-loop agentic testing.

---

## Curriculum Structure

| Module | Title | Primary Objectives | Hands-On Exercise |
| :--- | :--- | :--- | :--- |
| **[Lesson 01](01_sim_environment.md)** | **OpenUSD & PhysX Stage Composition** | Understand USD prim hierarchies, GPU PhysX dynamics, and mass properties | Audit scene geometry & correct vehicle mass properties |
| **[Lesson 02](02_ros2_teleop.md)** | **ROS 2 Bridging & Dual-Target Autonomy** | Learn Fast DDS bridging, sensor streaming, and Sim-to-Real hardware boundary | Run teleop, sample sensor feeds, and diagnose camera sync warnings |
| **[Lesson 03](03_agentic_testing.md)** | **Closed-Loop Agentic Testing (SiTL)** | Connect local LLMs (`llama.cpp`) to Isaac Sim via MCP for automated testing | Write a custom physical assertion task and trigger self-healing |

---

## Prerequisites Before Starting
Before starting Lesson 01, ensure you have:
1. Windows 10/11 with WSL 2 (Ubuntu 22.04) and Docker Desktop running.
2. NVIDIA GPU with RTX driver 535+ installed.
3. NVIDIA Isaac Sim 6.1 installed via Omniverse Launcher.
4. Cloned this repository and verified basic diagnostics:
   ```powershell
   .\scripts\windows\start_rover_all.ps1 -Mode Diagnostics
   ```

---

## Learner Testing & Continuous Improvement Log
To ensure this onboarding curriculum remains friction-free, each lesson is cold-tested by incoming student engineers and interns. Key improvements made from learner feedback:

1. **WSL Joystick Permissions**: New learners frequently encountered permission errors accessing `/dev/input/js0`. We updated `scripts/windows/start_rover.ps1` to automatically assign container user permissions and added a zero-hardware keyboard teleop fallback (`teleop_twist_keyboard`).
2. **Timeline Play Requirement**: Learners observed `/cmd_vel` topics appearing active while the rover remained motionless. We added clear UI callouts emphasizing that Isaac Sim's timeline **Play** button must be running for PhysX and Action Graph subscribers to execute.
3. **CameraInfo Topic Namespaces**: Diagnosed and resolved the `PointCloudXyzNode` desynchronization warning when learners attempted pointcloud generation.
