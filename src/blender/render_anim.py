"""
render_anim.py — Populated street scene builder (Qianmen match-cut plate)
==========================================================================
Builds a stylized "clay city" street scene populated with CMU mocap walkers,
configures the match-cut camera and render settings, saves the .blend, exits.

WORKFLOW (two steps, per project convention):
  1) Build & save the .blend:
       blender -b -P render_anim.py
  2) Render the animation headless from the saved file:
       blender -b output/qianmen_plate.blend -a

This is a TEMPLATE for Claude Code to adapt per shot. All tunable values are
in the CONFIG block. Log final values in parameters.md (project rule).

Pedestrians are deliberately STYLIZED (capsule-limb clay figures driven by
real mocap): motion reads as human, look stays in the series aesthetic, and
we never enter uncanny valley — which would kill the match cut.

Mocap: CMU Graphics Lab Motion Capture Database (mocap.cs.cmu.edu).
Free to copy/modify/redistribute. Credit in video description:
"Motion data from mocap.cs.cmu.edu (CMU Graphics Lab)".
Use BVH conversions (see the site's Resources page); Blender imports BVH natively.
"""

import bpy
import json
import math
import os
import random

# ============================== CONFIG =====================================
PROJECT_DIR   = os.path.abspath(".")                       # repo root when run by Claude Code
FOOTPRINTS    = os.path.join(PROJECT_DIR, "data/exports/qianmen_context.geojson")
                # Phase 10 export: building footprints, METERS, LOCAL ORIGIN. Generate with:
                #   python src/blender/export_context.py --area beijing --lat 39.899 --lon 116.395 --half 220
                # (absolute UTM coords sit ~4.4e6 from origin and wreck Blender precision).
BVH_DIR       = os.path.join(PROJECT_DIR, "data/raw/mocap")  # put walk-cycle .bvh files here
BVH_SCALE     = 0.056444        # CMU data is inches at ASF scale 0.45 -> meters (per CMU FAQ).
                                # If your BVH conversion is already metric, set 1.0. CHECK a
                                # figure against a building: humans should be ~1.7 units tall.
OUT_BLEND     = os.path.join(PROJECT_DIR, "output/qianmen_plate.blend")
OUT_FRAMES    = os.path.join(PROJECT_DIR, "results/video_assets/blender/qianmen_plate/")

N_WALKERS     = 14              # crowd size for the plate
STREET_START  = (0.0,  -40.0)   # street centerline in local meters (match your export origin)
STREET_END    = (0.0,   40.0)
STREET_WIDTH  = 12.0            # walkers scatter across this width
SEED          = 42              # deterministic crowds (reproducibility rule)

# MATCH-CUT CAMERA — copy these from the REAL plate you shot on site.
# Phone main lens ~24mm full-frame equivalent; eye height ~1.6 m.
# For precise solves from a still, use fSpy (free) and replace these values.
CAM_LOCATION  = (2.0, -35.0, 1.6)
CAM_LOOK_AT   = (0.0,  10.0, 1.5)
CAM_FOCAL_MM  = 24.0

FPS           = 30
FRAME_START   = 1
FRAME_END     = 300             # 10 s plate. Keep <= shortest BVH clip length so
                                # no looping/retargeting is needed (walkers just walk).
RES_X, RES_Y  = 1920, 1080
DEFAULT_H     = 6.0             # extrusion height (m) when footprint lacks height attr
# ===========================================================================

random.seed(SEED)

# ---------- helpers --------------------------------------------------------

def clean_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)

def make_material(name, gray, roughness=0.9):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (gray, gray, gray, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    return m

def add_ground(mat):
    bpy.ops.mesh.primitive_plane_add(size=600, location=(0, 0, 0))
    g = bpy.context.object
    g.name = "Ground"
    g.data.materials.append(mat)
    return g

def load_footprints(path, mat):
    """GeoJSON polygons (meters, local origin) -> extruded clay blocks.
    Exterior rings only — holes don't read at plate distance (stylized look)."""
    if not os.path.exists(path):
        print(f"[WARN] footprints not found: {path} — building placeholder blocks")
        return build_placeholder_street(mat)
    with open(path) as f:
        gj = json.load(f)
    for i, feat in enumerate(gj.get("features", [])):
        geom = feat.get("geometry", {})
        polys = ([geom["coordinates"]] if geom.get("type") == "Polygon"
                 else geom.get("coordinates", []) if geom.get("type") == "MultiPolygon"
                 else [])
        h = float(feat.get("properties", {}).get("height") or DEFAULT_H)
        for ring_set in polys:
            ring = ring_set[0]                     # exterior ring
            verts = [(x, y, 0.0) for x, y in (p[:2] for p in ring)]
            if len(verts) < 3:
                continue
            mesh = bpy.data.meshes.new(f"bldg_{i}")
            mesh.from_pydata(verts, [], [list(range(len(verts)))])
            obj = bpy.data.objects.new(f"bldg_{i}", mesh)
            bpy.context.collection.objects.link(obj)
            obj.data.materials.append(mat)
            # extrude up by h via solidify-style: use simple extrude with bmesh
            import bmesh
            bm = bmesh.new(); bm.from_mesh(mesh)
            faces = list(bm.faces)
            r = bmesh.ops.extrude_face_region(bm, geom=faces)
            up = [v for v in r["geom"] if isinstance(v, bmesh.types.BMVert)]
            bmesh.ops.translate(bm, verts=up, vec=(0, 0, h))
            bm.to_mesh(mesh); bm.free()

def build_placeholder_street(mat):
    """Two rows of varied blocks flanking the street — lets the template run
    before Phase 10 exports exist."""
    for side in (-1, 1):
        y = STREET_START[1]
        while y < STREET_END[1]:
            d = random.uniform(6, 14)
            w = random.uniform(6, 12)
            h = random.uniform(4, 9)
            x = side * (STREET_WIDTH / 2 + w / 2 + 1.5)
            bpy.ops.mesh.primitive_cube_add(location=(x, y + d / 2, h / 2))
            b = bpy.context.object
            b.scale = (w / 2, d / 2, h / 2)
            b.data.materials.append(mat)
            y += d + random.uniform(0.5, 2.0)

def clothe_armature(arm, mat, min_bone=0.12):
    """Real mocap motion + capsule limbs = readable clay human, no uncanny valley.
    One capsule per bone longer than min_bone (skips fingers/toes)."""
    for bone in arm.data.bones:
        if bone.length < min_bone:
            continue
        bpy.ops.mesh.primitive_cylinder_add(radius=0.05, depth=bone.length,
                                            location=(0, 0, 0))
        c = bpy.context.object
        c.data.materials.append(mat)
        c.parent = arm
        c.parent_type = 'BONE'
        c.parent_bone = bone.name
        # bone-parenting attaches at bone TAIL; shift capsule back to bone center
        c.location = (0.0, -bone.length / 2.0, 0.0)
        c.rotation_euler = (math.radians(90), 0, 0)

def spawn_walkers(bvh_files, figure_mat):
    """Each walker: import a BVH, place along the street with lateral scatter,
    face down-street, random start-frame offset. Shot length <= clip length,
    so captured root motion carries them — no looping, no retargeting."""
    for i in range(N_WALKERS):
        bvh = random.choice(bvh_files)
        bpy.ops.import_anim.bvh(filepath=bvh, global_scale=BVH_SCALE,
                                frame_start=1, use_fps_scale=True,
                                rotate_mode='NATIVE', axis_forward='-Z', axis_up='Y')
        arm = bpy.context.object
        arm.name = f"walker_{i:02d}"
        t = random.uniform(0.05, 0.85)   # position along street
        arm.location = (
            random.uniform(-STREET_WIDTH/2 + 1, STREET_WIDTH/2 - 1),
            STREET_START[1] + t * (STREET_END[1] - STREET_START[1]),
            0.0,
        )
        heading = 0.0 if random.random() < 0.6 else math.pi   # 60/40 direction mix
        arm.rotation_euler = (0, 0, heading + random.uniform(-0.15, 0.15))
        # de-sync the crowd: offset each walker's action in time
        if arm.animation_data and arm.animation_data.action:
            off = random.randint(0, 60)
            for fc in arm.animation_data.action.fcurves:
                for kp in fc.keyframe_points:
                    kp.co.x += off
                    kp.handle_left.x += off
                    kp.handle_right.x += off
        clothe_armature(arm, figure_mat)

def add_camera():
    cam_data = bpy.data.cameras.new("PlateCam")
    cam_data.lens = CAM_FOCAL_MM
    cam_data.sensor_width = 36.0     # full-frame equivalence — matches phone eq. focal
    cam = bpy.data.objects.new("PlateCam", cam_data)
    bpy.context.collection.objects.link(cam)
    cam.location = CAM_LOCATION
    direction = [CAM_LOOK_AT[k] - CAM_LOCATION[k] for k in range(3)]
    rot = math.atan2(direction[0], -direction[1])   # yaw toward target
    pitch = math.atan2(direction[2],
                       math.hypot(direction[0], direction[1])) + math.pi / 2
    cam.rotation_euler = (pitch, 0.0, -rot)
    bpy.context.scene.camera = cam

def add_lighting():
    bpy.ops.object.light_add(type='SUN', location=(30, -30, 60))
    sun = bpy.context.object
    sun.data.energy = 3.0
    sun.rotation_euler = (math.radians(50), 0, math.radians(35))
    world = bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.02, 0.02, 0.025, 1.0)   # dark ground/sky
    bg.inputs[1].default_value = 1.0

def configure_render():
    s = bpy.context.scene
    s.render.engine = 'BLENDER_EEVEE_NEXT' if hasattr(bpy.types, 'SceneEEVEE') else 'BLENDER_EEVEE'
    s.render.resolution_x, s.render.resolution_y = RES_X, RES_Y
    s.render.fps = FPS
    s.frame_start, s.frame_end = FRAME_START, FRAME_END
    s.render.image_settings.file_format = 'PNG'
    s.render.filepath = OUT_FRAMES        # baked in, so `blender -b file.blend -a` just works

# ---------- build ----------------------------------------------------------

def main():
    clean_scene()
    clay   = make_material("Clay",   0.85)
    ground = make_material("Ground", 0.06)
    figure = make_material("Figure", 0.35)

    add_ground(ground)
    load_footprints(FOOTPRINTS, clay)

    bvh_files = sorted(
        os.path.join(BVH_DIR, f) for f in (os.listdir(BVH_DIR) if os.path.isdir(BVH_DIR) else [])
        if f.lower().endswith(".bvh")
    )
    if bvh_files:
        spawn_walkers(bvh_files, figure)
    else:
        print(f"[WARN] no .bvh files in {BVH_DIR} — scene saved without walkers")

    add_camera()
    add_lighting()
    configure_render()

    os.makedirs(os.path.dirname(OUT_BLEND), exist_ok=True)
    os.makedirs(OUT_FRAMES, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
    print(f"[OK] saved {OUT_BLEND}")
    print(f"[NEXT] render with:  blender -b {OUT_BLEND} -a")

if __name__ == "__main__":
    main()
