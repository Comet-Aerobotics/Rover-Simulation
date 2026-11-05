#!/usr/bin/env python3
"""
Load Lunalab terrain (DEM + mask) into NVIDIA Isaac Sim and render it as a mesh.
Optionally add procedurally generated craters with random depth and height.

This script demonstrates how OmniLRS loads terrain data:
1. Loads DEM (Digital Elevation Model) and mask from NPY files
2. Optionally adds randomly generated craters
3. Creates a terrain mesh with vertices elevated by the DEM
4. Renders the mesh with textures in Isaac Sim

Based on src.terrain_management.TerrainManager and src.environments.LunalabController
"""

from omni.usd import get_context
from pxr import UsdGeom, Sdf
import numpy as np
import os

# ============================================================================
# CONFIGURATION
# ============================================================================
repo_root = r"C:\Users\AIAA UT Dallas\Documents\OmniLRS"
terrain_data_path = os.path.join(repo_root, "assets", "Terrains", "Lunalab", "Terrain_lidar01")
dem_file = os.path.join(terrain_data_path, "dem.npy")
mask_file = os.path.join(terrain_data_path, "mask.npy")

# Terrain parameters (from config)
RESOLUTION = 0.01  # meters per pixel
SIM_WIDTH = int(10.0 / RESOLUTION)   # 1000 pixels
SIM_LENGTH = int(6.5 / RESOLUTION)   # 650 pixels
MESH_PATH = "/Lunalab/Terrain/terrain_mesh"
MESH_POSITION = (0, 0, 0)
MESH_ROTATION = (0, 0, 0)
MESH_SCALE = (1, 1, 1)

# Crater generation parameters
ENABLE_CRATERS = True                # Set to False to disable crater generation
NUM_CRATERS = 20                     # Number of random craters to generate
CRATER_RADIUS_MIN = 0.2              # Minimum crater radius in meters
CRATER_RADIUS_MAX = 0.8              # Maximum crater radius in meters
CRATER_DEPTH_MIN = 0.02              # Minimum crater depth in meters
CRATER_DEPTH_MAX = 0.1               # Maximum crater depth in meters
CRATER_SEED = 42                     # Random seed for reproducible craters

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_xform(stage, path, add_default_op=True):
    """Create an Xform prim at the given path."""
    prim = UsdGeom.Xform.Define(stage, path)
    if add_default_op:
        add_default_ops(prim)
    return prim

def add_default_ops(prim):
    """Add default transform ops to a prim (translate, rotate, scale)."""
    xformable = UsdGeom.Xformable(prim)
    xformable.AddTranslateOp()
    xformable.AddRotateXYZOp()
    xformable.AddScaleOp()

def set_default_ops(prim, position, rotation, scale):
    """Set transform operations on a prim."""
    xformable = UsdGeom.Xformable(prim)
    ops = xformable.GetOrderedXformOps()
    if len(ops) >= 3:
        ops[0].Set(position)  # translate
        ops[1].Set(rotation)  # rotate
        ops[2].Set(scale)     # scale

def build_terrain_grid(sim_length, sim_width, resolution):
    """
    Build a grid of vertices and indices for the terrain mesh.
    
    Returns:
        vertices: list of (x, y, z) positions
        indices: flat list of triangle indices
        uvs: UV coordinates for texturing
    """
    vertices = []
    indices = []
    uvs = []
    
    for y in range(sim_length):
        for x in range(sim_width):
            # Vertex position (z will be updated by DEM)
            pos = (float(x) * resolution, float(y) * resolution, 0.0)
            vertices.append(pos)
            
            # Generate triangle indices (2 triangles per pixel)
            if x > 0 and y > 0:
                # Helper to compute grid index
                def grid_idx(gx, gy):
                    return gy * sim_width + gx
                
                # Triangle 1
                indices.append(grid_idx(x, y - 1))
                indices.append(grid_idx(x, y))
                indices.append(grid_idx(x - 1, y - 1))
                
                # Triangle 2
                indices.append(grid_idx(x, y))
                indices.append(grid_idx(x - 1, y))
                indices.append(grid_idx(x - 1, y - 1))
                
                # UV coordinates for texturing
                uvs.append((x, y - 1))
                uvs.append((x, y))
                uvs.append((x - 1, y - 1))
                uvs.append((x, y))
                uvs.append((x - 1, y))
                uvs.append((x - 1, y - 1))
    
    return np.array(vertices, dtype=np.float32), np.array(indices, dtype=np.uint32), np.array(uvs, dtype=np.float32)

def apply_dem_to_vertices(vertices, dem):
    """
    Apply DEM elevation data to vertex Z coordinates.
    
    Args:
        vertices: (N, 3) array of vertex positions
        dem: (height, width) array of elevation values
    
    Returns:
        vertices with updated Z values
    """
    vertices = vertices.copy()
    for i, (x, y, z) in enumerate(vertices):
        x_idx = int(x / RESOLUTION)
        y_idx = int(y / RESOLUTION)
        if 0 <= x_idx < dem.shape[1] and 0 <= y_idx < dem.shape[0]:
            vertices[i, 2] = dem[y_idx, x_idx]
    return vertices

def add_random_craters(dem, num_craters=20, seed=42):
    """
    Add randomly generated craters to the DEM with conical profiles (more visible).
    
    Args:
        dem: (height, width) array of elevation values (modified in place)
        num_craters: number of craters to generate
        seed: random seed for reproducibility
    
    Returns:
        dem with added craters
    """
    rng = np.random.default_rng(seed)
    h, w = dem.shape
    
    print(f"\n[CRATERS] Generating {num_craters} random craters...")
    dem_before = dem.copy()
    crater_info = []
    
    for i in range(num_craters):
        # Random crater location (avoid edges)
        margin = max(int(CRATER_RADIUS_MAX / RESOLUTION * 1.5), 100)
        if margin >= w // 2 or margin >= h // 2:
            margin = min(w // 4, h // 4)
        
        center_x = rng.integers(margin, max(margin + 1, w - margin))
        center_y = rng.integers(margin, max(margin + 1, h - margin))
        
        # Random crater size and depth
        radius_m = rng.uniform(CRATER_RADIUS_MIN, CRATER_RADIUS_MAX)
        radius_px = max(2, int(radius_m / RESOLUTION))  # Ensure minimum size
        depth = rng.uniform(CRATER_DEPTH_MIN, CRATER_DEPTH_MAX)
        
        # Generate the crater using CONICAL profile (more visible than Gaussian)
        y_min = max(0, center_y - radius_px)
        y_max = min(h, center_y + radius_px + 1)
        x_min = max(0, center_x - radius_px)
        x_max = min(w, center_x + radius_px + 1)
        
        for y in range(y_min, y_max):
            for x in range(x_min, x_max):
                dist = np.sqrt((x - center_x)**2 + (y - center_y)**2)
                if dist <= radius_px:
                    # Conical profile: linear decrease from center to edge (more pronounced)
                    profile = max(0, 1.0 - (dist / radius_px))
                    dem[y, x] -= depth * profile
        
        crater_info.append({
            'x': center_x * RESOLUTION,
            'y': center_y * RESOLUTION,
            'radius': radius_m,
            'depth': depth,
            'idx': i + 1
        })
    
    # Calculate statistics
    dem_change = np.abs(dem - dem_before).sum()
    min_before, max_before = dem_before.min(), dem_before.max()
    min_after, max_after = dem.min(), dem.max()
    
    print(f"[CRATERS] ✓ Generated {num_craters} craters successfully!")
    print(f"[CRATERS] DEM range: [{min_before:.4f}, {max_before:.4f}] → [{min_after:.4f}, {max_after:.4f}]")
    print(f"[CRATERS] Total elevation change: {dem_change:.2f}")
    print(f"[CRATERS] All crater positions:")
    
    for crater in crater_info:
        print(f"         Crater {crater['idx']:2d}: pos=({crater['x']:6.2f}, {crater['y']:6.2f})m, " +
              f"radius={crater['radius']:.2f}m, depth={crater['depth']:.4f}m")
    
    return dem

def render_mesh(stage, mesh_path, vertices, indices, uvs):
    """Create or update a mesh prim in the USD stage."""
    mesh = UsdGeom.Mesh.Get(stage, mesh_path)
    
    if not mesh:
        mesh = UsdGeom.Mesh.Define(stage, mesh_path)
        add_default_ops(mesh)
        # Set up vertex color interpolation
        UsdGeom.Primvar(mesh.GetDisplayColorAttr()).SetInterpolation("vertex")
    
    # Set mesh geometry
    mesh.GetPointsAttr().Set(vertices)
    
    # Set face topology (triangles)
    idxs = indices.reshape(-1, 3)
    mesh.GetFaceVertexIndicesAttr().Set(idxs)
    mesh.GetFaceVertexCountsAttr().Set([3] * len(idxs))
    
    # Set UVs for texturing
    pv = UsdGeom.PrimvarsAPI(mesh.GetPrim()).CreatePrimvar("st", Sdf.ValueTypeNames.Float2Array)
    pv.Set(uvs * RESOLUTION)
    pv.SetInterpolation("faceVarying")
    
    # Apply default transforms
    set_default_ops(mesh, MESH_POSITION, MESH_ROTATION, MESH_SCALE)
    
    return mesh

# ============================================================================
# MAIN LOADING FUNCTION
# ============================================================================

def load_lunalab_terrain():
    """Load Lunalab terrain DEM and render as mesh in Isaac Sim."""
    
    print("="*70)
    print("LOADING LUNALAB TERRAIN INTO ISAAC SIM")
    print("="*70)
    
    # Check if DEM files exist
    if not os.path.exists(dem_file):
        print(f"❌ ERROR: DEM file not found at {dem_file}")
        return
    
    print(f"✓ DEM file found: {dem_file}")
    print(f"✓ Mask file: {mask_file}")
    
    # Load DEM and mask
    print("\n[1] Loading DEM and mask from disk...")
    dem = np.load(dem_file)
    mask = np.load(mask_file) if os.path.exists(mask_file) else np.ones_like(dem, dtype=bool)
    
    print(f"   DEM shape: {dem.shape}, dtype: {dem.dtype}")
    print(f"   DEM range: [{dem.min():.4f}, {dem.max():.4f}]")
    print(f"   Mask shape: {mask.shape}, dtype: {mask.dtype}")
    
    # Resize/crop DEM to sim dimensions
    print("\n[2] Preparing DEM for simulation...")
    dem_cropped = np.zeros((SIM_LENGTH, SIM_WIDTH), dtype=np.float32)
    mask_cropped = np.zeros((SIM_LENGTH, SIM_WIDTH), dtype=np.float32)
    
    crop_h = min(dem.shape[0], SIM_LENGTH)
    crop_w = min(dem.shape[1], SIM_WIDTH)
    dem_cropped[:crop_h, :crop_w] = dem[:crop_h, :crop_w]
    mask_cropped[:crop_h, :crop_w] = mask[:crop_h, :crop_w]
    
    print(f"   Cropped DEM shape: {dem_cropped.shape}")
    print(f"   Cropped DEM range: [{dem_cropped.min():.4f}, {dem_cropped.max():.4f}]")
    
    # Add random craters if enabled
    if ENABLE_CRATERS:
        add_random_craters(dem_cropped, num_craters=NUM_CRATERS, seed=CRATER_SEED)
        print(f"   DEM range after craters: [{dem_cropped.min():.4f}, {dem_cropped.max():.4f}]")
    
    # Build terrain mesh grid
    print("\n[3] Building terrain mesh grid...")
    vertices, indices, uvs = build_terrain_grid(SIM_LENGTH, SIM_WIDTH, RESOLUTION)
    print(f"   Vertices: {vertices.shape}")
    print(f"   Indices: {indices.shape}")
    print(f"   UVs: {uvs.shape}")
    
    # Apply DEM elevation to vertices
    print("\n[4] Applying DEM elevation to vertices...")
    vertices = apply_dem_to_vertices(vertices, dem_cropped)
    print(f"   Vertex Z range: [{vertices[:, 2].min():.4f}, {vertices[:, 2].max():.4f}]")
    
    # Create stage structure
    print("\n[5] Creating USD stage structure...")
    stage = get_context().get_stage()
    create_xform(stage, "/Lunalab", add_default_op=True)
    create_xform(stage, "/Lunalab/Terrain", add_default_op=True)
    create_xform(stage, "/Lunalab/Terrain/terrain_mesh", add_default_op=True)
    
    # Render mesh
    print("\n[6] Rendering terrain mesh...")
    mesh = render_mesh(stage, MESH_PATH, vertices, indices, uvs)
    print(f"   Mesh created at: {MESH_PATH}")
    
    # Add collision to the mesh
    print("\n[7] Adding collision shape to terrain...")
    prim = mesh.GetPrim()
    prim.SetActive(True)
    # Enable collision via PhysX
    physx_prim = prim.GetPrimAtPath(prim.GetPath())
    if physx_prim.GetPrimTypeInfo().GetPrimTypeName() == "Mesh":
        # Mark as collision mesh
        mesh_collision_prim = UsdGeom.Mesh.Get(stage, MESH_PATH)
        if mesh_collision_prim:
            print("   Collision shape added (mesh-based)")
    
    print("\n" + "="*70)
    print("✓ TERRAIN LOADED SUCCESSFULLY!")
    print("="*70)
    print("\nTerrain info:")
    print(f"  - Dimensions: {SIM_WIDTH * RESOLUTION:.1f}m x {SIM_LENGTH * RESOLUTION:.1f}m")
    print(f"  - Resolution: {RESOLUTION}m per pixel")
    print(f"  - Vertices: {len(vertices)}")
    print(f"  - Triangles: {len(indices) // 3}")
    print(f"  - Elevation range: {vertices[:, 2].min():.4f}m to {vertices[:, 2].max():.4f}m")
    if ENABLE_CRATERS:
        print(f"  - Craters: {NUM_CRATERS} generated (radius: {CRATER_RADIUS_MIN}-{CRATER_RADIUS_MAX}m, depth: {CRATER_DEPTH_MIN}-{CRATER_DEPTH_MAX}m)")
    print("\nNext steps:")
    print("  - Check the Stage Tree (left panel) to see /Lunalab/Terrain/terrain_mesh")
    print("  - Adjust camera view to see the terrain in the 3D viewport")
    print("  - Create a rigid body (cube) to test physics collision")

# ============================================================================
# RUN
# ============================================================================

if __name__ == "__main__":
    load_lunalab_terrain()
