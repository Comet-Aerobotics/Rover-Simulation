# Lesson 01: OpenUSD Scene Composition & PhysX Dynamics

## Overview
In this lesson, you will explore the canonical USD stage (`scenes/CAMERASYNCSSMOETIMES.usd`), understand how NVIDIA Isaac Sim composes robot and environment assets using OpenUSD, and verify physics collider and mass properties.

---

## 1. Key Concepts

### OpenUSD Stage Hierarchy
In OpenUSD, 3D scenes are composed of primitive objects called **Prims**. The rover simulation organizes prims hierarchically:
* `/jackal`: The root robot prim referencing the Jackal chassis, wheel revolute joints, and sensors.
* `/Lunalab/Terrain/terrain_mesh`: The 1 cm digital elevation model (DEM) representing lunar surface topography.
* `/ActionGraph`: The Omniverse OmniGraph network translating between ROS 2 topics and Isaac Sim sensor/actuation nodes.

### Physics: Approximation Modes & Vehicle Mass
* **Terrain Collision**: The lunar terrain uses `physics:approximation = "none"`, meaning contact is computed directly against the irregular triangle mesh. Applying a convex hull to terrain would bridge depressions and make the rover appear to float.
* **Mass Configuration**: A common defect in unpromoted candidate stages is `physics:mass = 0` authored on `/jackal/base_link`. For realistic contact dynamics, the vehicle requires an authored total mass of approximately 53–55 kg (~53.09 kg chassis + 4 × 0.48 kg wheels).

---

## 2. Guided Exercise: Inspecting & Auditing Stage Properties

### Step 1: Open the Stage in Isaac Sim
Launch the simulation from PowerShell:
```powershell
.\scripts\windows\start_rover_all.ps1
```

### Step 2: Audit Scene Prims
1. In the **Stage Tree** panel (top right), expand `/jackal`.
2. Select `/jackal/base_link` and look at the **Property** panel under `Physics`:
   * Notice whether `Mass` is authored or inherited.
3. Select `/Lunalab/Terrain/terrain_mesh`:
   * Confirm `Collision Enabled` is checked and `Approximation` is set to `None`.

### Step 3: Run the Automated Onboarding Audit Task
Instead of inspecting manually, run our automated onboarding verification task:
```powershell
py agentic/sitl_harness.py --task onboarding
```

*Expected Terminal Output*:
```text
[INFO] === Starting Task: [onboarding_audit] Stage Asset & Physics Integrity Audit ===
[INFO] Executing MCP Tool: isaac_inspect_prim with args: {'prim_path': '/jackal'}
[INFO] Executing MCP Tool: isaac_inspect_prim with args: {'prim_path': '/Lunalab/Terrain/terrain_mesh'}
[INFO] ✅ Task [onboarding_audit] PASSED on iteration 1!
```

---

## 3. Hands-On Experiment ("Try It Yourself")

### Experiment: Predict Mass Impact on Ground Contact
* **Action**: In `agentic/tasks/onboarding.py`, modify `self.min_mass_kg = 55.0` (setting the threshold higher than 53.09 kg).
* **Prediction**: What will the harness report when you re-run the onboarding task?
* **Verify**: Run `py agentic/sitl_harness.py --task onboarding` and check `work/sitl_test_report.json` to observe the assertion failure diff and the agent's corrective suggestion.

---

## 4. Knowledge Check

**Question 1**: Why must the lunar terrain mesh use `physics:approximation = "none"` instead of a `convexHull` collider?
<details>
<summary>Answer</summary>
A convex hull wraps the outermost vertices of a mesh, bridging cavities, craters, and depressions. Using a convex hull on irregular ground prevents the rover wheels from tracking terrain contours and causes the chassis to float above crater hollows.
</details>

**Question 2**: If an authored stage has `physics:mass = 0` on the chassis root, what does PhysX do during runtime?
<details>
<summary>Answer</summary>
When mass is 0 or unauthored, PhysX attempts to infer mass from the volume of collision geometries and default material densities. This often produces unrealistic vehicle weight, erratic suspension dynamics, or severe wheel slippage.
</details>
