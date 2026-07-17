"""
gpu_prefs.py — enable Cycles GPU (Metal) for headless renders.  [PHASE 9b helper]

WHY THIS EXISTS (a real gotcha, logged in parameters.md):
    `scene.cycles.device = 'GPU'` is saved in the .blend, but the *device selection itself*
    lives in USER PREFERENCES, which a headless `blender -b file.blend -a` does NOT load.
    Result: Cycles silently falls back to CPU (~2.8 min/frame here vs ~1 min on GPU).
    Run this before the render so the GPU is actually used:

        blender -b output/qianmen_plate.blend -P src/blender/gpu_prefs.py -a
"""
import bpy

prefs = bpy.context.preferences.addons["cycles"].preferences
enabled = []
for dev_type in ("METAL", "OPTIX", "CUDA", "HIP", "ONEAPI"):
    try:
        prefs.compute_device_type = dev_type
        prefs.get_devices()
        gpus = [d for d in prefs.devices if d.type != "CPU"]
        if gpus:
            for d in prefs.devices:
                d.use = (d.type != "CPU")          # GPU only; CPU adds little and costs sync
            enabled = [f"{d.name} [{d.type}]" for d in prefs.devices if d.use]
            break
    except (TypeError, AttributeError):
        continue

for sc in bpy.data.scenes:
    sc.cycles.device = "GPU" if enabled else "CPU"

print(f"[gpu_prefs] compute_device_type={prefs.compute_device_type} | "
      f"devices={enabled or 'NONE -> CPU fallback'} | scene.device={bpy.context.scene.cycles.device}")
