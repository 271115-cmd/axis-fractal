"""
render_zoom.py — "The Zoom" descent/ascent (Phase 9b, shot 1; reused every episode).

One continuous camera move from street level up over the extruded Zone-B (Central Axis /
Forbidden City) fabric, easing into a top-down plan that match-frames the figure-ground.
Stylized clay look on a dark ground, EEVEE. Deterministic + headless-reproducible.

Two-step workflow (project convention):
  1) build & save the .blend:   blender -b -P src/blender/render_zoom.py
  2) render headless:           blender -b output/zoom_descent.blend -a      (frames 1..480)
     ...or a quick preview:     blender -b output/zoom_descent.blend -f 1 -f 480

Reverse the move (ascent) by rendering the frame range backwards in the edit, or set REVERSE.
Parameterize the target tile by pointing FOOTPRINTS at another export from export_context.py.
"""
import bpy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_anim import make_material, load_footprints, add_lighting  # reuse the clay loader

# ============================== CONFIG =====================================
PROJECT_DIR = os.path.abspath(".")
FOOTPRINTS  = os.path.join(PROJECT_DIR, "data/exports/forbidden_city_context.geojson")
OUT_BLEND   = os.path.join(PROJECT_DIR, "output/zoom_descent.blend")
OUT_FRAMES  = os.path.join(PROJECT_DIR, "results/video_assets/blender/zoom_descent/")
EXTENT      = 1000.0        # local metres (export_context --half 500 -> 1000 m box)
FPS, FRAMES = 60, 480       # ~8 s
RES_X, RES_Y = 1920, 1080
FOCAL_MM    = 35.0
CAM_START   = None          # set below from EXTENT
CAM_END     = None
# ===========================================================================


def clean():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def add_ground(mat):
    c = EXTENT / 2.0
    bpy.ops.mesh.primitive_plane_add(size=EXTENT * 3, location=(c, c, 0))
    g = bpy.context.object
    g.name = "Ground"
    g.data.materials.append(mat)


def build_camera_move():
    c = EXTENT / 2.0
    tgt = bpy.data.objects.new("ZoomTarget", None)
    bpy.context.collection.objects.link(tgt)
    tgt.location = (c, c, 12.0)                       # aim at the massing height

    cam_data = bpy.data.cameras.new("ZoomCam")
    cam_data.lens = FOCAL_MM
    cam_data.sensor_width = 36.0
    cam_data.clip_start = 0.1
    cam_data.clip_end = 5000.0        # the plan view sits ~1150 m up — default 1000 m clips it away
    cam = bpy.data.objects.new("ZoomCam", cam_data)
    bpy.context.collection.objects.link(cam)
    con = cam.constraints.new("TRACK_TO")            # always aim at target -> auto look-down at top
    con.target = tgt
    con.track_axis = "TRACK_NEGATIVE_Z"
    con.up_axis = "UP_Y"
    bpy.context.scene.camera = cam

    # default keyframe interpolation is Bezier (auto ease-in/out) — cinematic without
    # touching fcurves, which moved under slotted Actions in Blender 4.4+/5.x.
    cam.location = (c, -90.0, 5.0)                    # frame 1: street level, south edge
    cam.keyframe_insert("location", frame=1)
    cam.location = (c, c + 0.01, 1150.0)             # frame N: high, ~top-down plan
    cam.keyframe_insert("location", frame=FRAMES)


def configure():
    s = bpy.context.scene
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            s.render.engine = eng
            break
        except TypeError:
            continue
    s.render.resolution_x, s.render.resolution_y = RES_X, RES_Y
    s.render.fps = FPS
    s.frame_start, s.frame_end = 1, FRAMES
    s.render.image_settings.file_format = "PNG"
    s.render.filepath = OUT_FRAMES


def main():
    clean()
    clay = make_material("Clay", 0.85)
    ground = make_material("Ground", 0.05)
    add_ground(ground)
    load_footprints(FOOTPRINTS, clay)
    build_camera_move()
    add_lighting()
    configure()
    os.makedirs(os.path.dirname(OUT_BLEND), exist_ok=True)
    os.makedirs(OUT_FRAMES, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
    print(f"[OK] saved {OUT_BLEND}")
    print(f"[NEXT] render with:  blender -b {OUT_BLEND} -a")


if __name__ == "__main__":
    main()
