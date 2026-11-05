#!/usr/bin/env python3
"""
Load original terrain and EXTEND it to fill the entire area,
then add random craters everywhere
"""

from omni.usd import get_context
from pxr import UsdGeom
import numpy as np
import os
import time

try:
    print("="*70)
    print("EXTENDED TERRAIN + RANDOM CRATERS (FULL AREA)")
    print("="*70)
    
    repo_root = r"C:\Users\AIAA UT Dallas\Documents\OmniLRS"
    dem_file = os.path.join(repo_root, "assets", "Terrains", "Lunalab", "Terrain_lidar01", "dem.npy")
    
    RESOLUTION = 0.01
    SIM_WIDTH, SIM_LENGTH = 1000, 650
    MESH_PATH = "/Lunalab/Terrain/terrain_extended_craters"
    
    seed = int(time.time() * 1000) % 1000000
    print(f"\n[SEED] {seed}")
    
    rng = np.random.default_rng(seed)
    
    # =========================================================================
    # Load original DEM and extend to fill full area
    # =========================================================================
    print(f"\n[1] Loading and extending terrain...")
    dem = np.load(dem_file)
    print(f"  ✓ Original DEM shape: {dem.shape}")
    
    # Create full-size array
    dem_full = np.zeros((SIM_LENGTH, SIM_WIDTH), dtype=np.float32)
    
    # Copy available DEM data
    crop_h, crop_w = min(dem.shape[0], SIM_LENGTH), min(dem.shape[1], SIM_WIDTH)
    dem_full[:crop_h, :crop_w] = dem[:crop_h, :crop_w]
    
    # Extend/pad the empty areas
    print(f"    Extending terrain to fill entire area...")
    
    # Method: Mirror the available data to fill empty spaces
    if crop_w < SIM_WIDTH:
        # Fill right side by mirroring from left
        for x in range(crop_w, SIM_WIDTH):
            mirror_x = 2 * crop_w - x - 1
            if mirror_x >= 0 and mirror_x < crop_w:
                dem_full[:crop_h, x] = dem_full[:crop_h, mirror_x]
            else:
                # Use edge value if mirroring goes out of bounds
                dem_full[:crop_h, x] = dem_full[:crop_h, crop_w - 1]
    
    if crop_h < SIM_LENGTH:
        # Fill bottom by mirroring from top
        for y in range(crop_h, SIM_LENGTH):
            mirror_y = 2 * crop_h - y - 1
            if mirror_y >= 0 and mirror_y < crop_h:
                dem_full[y, :] = dem_full[mirror_y, :]
            else:
                dem_full[y, :] = dem_full[crop_h - 1, :]
    
    # Smooth transitions at edges with aggressive feathering at boundary
    print(f"    Smooth-feathering transitions...")
    
    # Apply aggressive smoothing in transition band around boundaries
    transition_band = 80  # Pixels from edge to blend over
    
    # First apply multi-scale smoothing passes
    dem_smooth = dem_full.copy()
    for pass_num in range(20):  # Increased from 5 to 20 passes
        for y in range(1, SIM_LENGTH - 1):
            for x in range(1, SIM_WIDTH - 1):
                neighbors = [
                    dem_full[y-1, x-1], dem_full[y-1, x], dem_full[y-1, x+1],
                    dem_full[y, x-1],   dem_full[y, x],   dem_full[y, x+1],
                    dem_full[y+1, x-1], dem_full[y+1, x], dem_full[y+1, x+1]
                ]
                dem_smooth[y, x] = np.mean(neighbors)
        dem_full = dem_smooth.copy()
    
    # Apply extra smoothing specifically at transition zones
    for y in range(SIM_LENGTH):
        for x in range(SIM_WIDTH):
            # Distance to nearest boundary
            dist_to_boundary = min(
                abs(x - crop_w),
                abs(y - crop_h),
                abs(SIM_WIDTH - x),
                abs(SIM_LENGTH - y)
            )
            
            # Extra blending near boundaries
            if dist_to_boundary < transition_band:
                # Fade factor: more blending near edges
                fade = dist_to_boundary / transition_band
                
                # Wider neighborhood for boundary smoothing
                window_size = 15
                neighbors = []
                for dy in range(-window_size, window_size + 1):
                    for dx in range(-window_size, window_size + 1):
                        ny = y + dy
                        nx = x + dx
                        if 0 <= ny < SIM_LENGTH and 0 <= nx < SIM_WIDTH:
                            neighbors.append(dem_full[ny, nx])
                
                if neighbors:
                    smoothed_val = np.mean(neighbors)
                    # Blend between original and smoothed
                    dem_full[y, x] = dem_full[y, x] * fade + smoothed_val * (1 - fade)
    
    print(f"  ✓ Terrain extended to: {dem_full.shape}")
    print(f"  ✓ Range: [{dem_full.min():.4f}, {dem_full.max():.4f}]")
    
    # =========================================================================
    # Add random craters everywhere
    # =========================================================================
    print(f"\n[2] Adding random craters...")
    
    num_craters = rng.integers(40, 70)  # More craters, more spread out
    print(f"    Carving {num_craters} craters across full terrain...")
    
    for i in range(num_craters):
        # Random position across ENTIRE surface - smaller margin for better spread
        margin = 100
        cx = rng.integers(margin, SIM_WIDTH - margin)
        cy = rng.integers(margin, SIM_LENGTH - margin)
        
        # Random crater size
        radius_m = rng.uniform(0.2, 1.5)
        radius_px = max(5, int(radius_m / RESOLUTION))
        
        # Random crater depth
        depth = rng.uniform(0.04, 0.30)
        
        # Create realistic crater with rim and terraced walls
        for y in range(max(0, cy - int(radius_px * 1.3)), min(SIM_LENGTH, cy + int(radius_px * 1.3) + 1)):
            for x in range(max(0, cx - int(radius_px * 1.3)), min(SIM_WIDTH, cx + int(radius_px * 1.3) + 1)):
                dist = np.sqrt((x - cx)**2 + (y - cy)**2)
                
                # Crater rim (raised edge at outer edge)
                if radius_px <= dist <= radius_px * 1.2:
                    rim_strength = 0.5 * (1.0 - (dist - radius_px) / (radius_px * 0.2))
                    dem_full[y, x] += depth * 0.15 * rim_strength
                
                # Crater bowl with terraced walls
                elif dist <= radius_px:
                    # Multi-step terracing for more realistic crater
                    normalized = dist / radius_px
                    
                    # Terraced profile with steps
                    if normalized < 0.3:
                        # Inner deep zone
                        profile = 1.0
                    elif normalized < 0.5:
                        # First terrace
                        profile = 0.8 + 0.2 * np.sin((normalized - 0.3) / 0.2 * np.pi)
                    elif normalized < 0.7:
                        # Second terrace
                        profile = 0.6 + 0.2 * np.sin((normalized - 0.5) / 0.2 * np.pi)
                    else:
                        # Outer terrace to rim
                        profile = 0.3 + 0.3 * np.sin((normalized - 0.7) / 0.3 * np.pi)
                    
                    dem_full[y, x] -= depth * profile
        
        if (i + 1) % 10 == 0:
            print(f"    {i+1}/{num_craters} craters")
    
    print(f"  ✓ All craters carved")
    print(f"  ✓ Final range: [{dem_full.min():.4f}, {dem_full.max():.4f}]")
    
    # =========================================================================
    # Build mesh
    # =========================================================================
    print(f"\n[3] Building mesh...")
    vertices, indices = [], []
    
    for y in range(SIM_LENGTH):
        for x in range(SIM_WIDTH):
            z = dem_full[y, x]
            vertices.append((float(x) * RESOLUTION, float(y) * RESOLUTION, float(z)))
            
            if x > 0 and y > 0:
                idx = lambda gx, gy: gy * SIM_WIDTH + gx
                indices.extend([
                    idx(x, y-1), idx(x, y), idx(x-1, y-1),
                    idx(x, y), idx(x-1, y), idx(x-1, y-1)
                ])
    
    vertices = np.array(vertices, dtype=np.float32)
    indices = np.array(indices, dtype=np.uint32)
    print(f"  ✓ {len(vertices):,} vertices, {len(indices)//3:,} triangles")
    
    # =========================================================================
    # Render
    # =========================================================================
    print(f"\n[4] Rendering mesh...")
    stage = get_context().get_stage()
    
    for path in ["/Lunalab", "/Lunalab/Terrain"]:
        if not stage.GetPrimAtPath(path):
            UsdGeom.Xform.Define(stage, path)
    
    if stage.GetPrimAtPath(MESH_PATH):
        stage.RemovePrim(MESH_PATH)
    
    mesh = UsdGeom.Mesh.Define(stage, MESH_PATH)
    mesh.GetPointsAttr().Set(vertices)
    mesh.GetFaceVertexIndicesAttr().Set(indices.reshape(-1, 3))
    mesh.GetFaceVertexCountsAttr().Set([3] * (len(indices) // 3))
    
    print(f"  ✓ Mesh created: {MESH_PATH}")
    
    print(f"\n" + "="*70)
    print(f"✓✓✓ FULL TERRAIN WITH CRATERS ✓✓✓")
    print(f"="*70)
    print(f"\n  Seed: {seed}")
    print(f"  Craters: {num_craters} (everywhere)")
    print(f"  Z-range: {vertices[:, 2].min():.4f}m to {vertices[:, 2].max():.4f}m")
    print(f"\n→ ENTIRE surface textured")
    print(f"→ No flat areas")
    print(f"→ Random craters scattered throughout")
    print(f"→ Run again for different crater positions!")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()


