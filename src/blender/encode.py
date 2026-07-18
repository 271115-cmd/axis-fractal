"""
encode.py — stitch a PNG frame sequence into an H.264 MP4 via Blender's FFmpeg.  [PHASE 9b]

No separate ffmpeg needed (Blender ships it). Reproducible:
    blender -b -P src/blender/encode.py -- <frames_dir> <out.mp4> <fps>

Defaults to the Qianmen plate at 30 fps. Frames must be zero-padded PNGs (0001.png ...).
"""
import bpy, os, sys, glob

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
FRAMES_DIR = argv[0] if len(argv) > 0 else "results/video_assets/blender/qianmen_plate"
OUT = argv[1] if len(argv) > 1 else "results/video_assets/qianmen_plate_10s.mp4"
FPS = int(argv[2]) if len(argv) > 2 else 30

files = sorted(glob.glob(os.path.join(FRAMES_DIR, "[0-9]" * 4 + ".png"))) \
    or sorted(glob.glob(os.path.join(FRAMES_DIR, "*.png")))
if not files:
    raise SystemExit(f"no PNG frames found in {FRAMES_DIR}")
n = len(files)

sc = bpy.context.scene
sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
sc.render.resolution_percentage = 100
sc.render.fps = FPS
sc.frame_start, sc.frame_end = 1, n
sc.render.use_sequencer = True
try:
    sc.render.image_settings.media_type = 'VIDEO'   # Blender 5.x: unlocks FFMPEG file_format
except (TypeError, AttributeError):
    pass
sc.render.image_settings.file_format = 'FFMPEG'
sc.render.ffmpeg.format = 'MPEG4'
sc.render.ffmpeg.codec = 'H264'
sc.render.ffmpeg.constant_rate_factor = 'HIGH'   # visually lossless-ish, reasonable size
sc.render.ffmpeg.ffmpeg_preset = 'GOOD'
sc.render.ffmpeg.gopsize = 12
sc.render.ffmpeg.audio_codec = 'NONE'
os.makedirs(os.path.dirname(OUT), exist_ok=True)
sc.render.filepath = OUT

se = sc.sequence_editor_create()
strips = se.strips if hasattr(se, "strips") else se.sequences   # renamed in Blender 5.x
img = strips.new_image(name="plate", filepath=files[0], channel=1, frame_start=1)
for f in files[1:]:
    img.elements.append(os.path.basename(f))

print(f"[encode] {n} frames @ {FPS} fps -> {OUT}")
bpy.ops.render.render(animation=True)
print(f"[OK] wrote {OUT}")
