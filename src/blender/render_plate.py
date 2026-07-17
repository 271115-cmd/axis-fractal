"""
render_plate.py — populated Qianmen match-cut plate (Phase 9b, Tier 2, priority shot).

Headless + reproducible:
    build & still:  blender -b -P src/blender/render_plate.py
    long render:    blender -b output/qianmen_plate.blend -a

Meets the brief's FIVE anti-generic requirements:
  1 no empty horizon  -> HDRI sunset + mid-ground silhouettes + pagoda + haze
  2 facade variety    -> POOL of real PolyHaven PBR brick sets (diffuse/normal/rough,
                         box-projected) x per-building tint jitter
  3 building TYPES     -> shopfronts / courtyard+gate / two-storey+balcony / corner / hero paifang,
                         with eaves, sills, recessed frontage
  4 dressed street     -> LIT WINDOWS, strung lanterns, awnings, signage, stalls, crates
  5 dramatic lighting  -> low raking sun + emissive practicals + volumetric haze, Cycles GI

Figures are bronze STATUES driven by CMU mocap (statuesque on purpose — the honest contrast
that makes the match cut land). Mocap: mocap.cs.cmu.edu. Textures/HDRI: PolyHaven (CC0).
"""
import bpy, bmesh, math, os, random
from mathutils import Vector

PROJECT = os.path.abspath(".")
HDRI = os.path.join(PROJECT, "data/raw/assets/belfast_sunset_puresky_2k.hdr")
TEX = os.path.join(PROJECT, "data/raw/assets/tex")
BVH_DIR = os.path.join(PROJECT, "data/raw/mocap")
OUT_BLEND = os.path.join(PROJECT, "output/qianmen_plate.blend")
FRAMES_DIR = os.path.join(PROJECT, "results/video_assets/blender/qianmen_plate/")
STILL = os.path.join(FRAMES_DIR, "still.png")

SEED = 7
FRAME_END = 300           # 10 s @ 30 fps; <= mocap clip length (no looping)
USE_CYCLES = True
SAMPLES = 64          # + denoising: ample for motion, ~1/3 faster than 96 over 300 frames
SCENE = None
random.seed(SEED)


# ---------------- helpers ----------------
def col(): return SCENE.collection

def add_box(name, loc, size, mat=None, rot=(0, 0, 0)):
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, verts=bm.verts, vec=size)
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); col().objects.link(ob)
    ob.location = loc; ob.rotation_euler = rot
    if mat: ob.data.materials.append(mat)
    return ob

def add_pyramid(name, loc, size, rot_z, mat=None):
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    bmesh.ops.create_cone(bm, segments=4, radius1=0.5, radius2=0.0, depth=1.0, cap_ends=True)
    bmesh.ops.scale(bm, verts=bm.verts, vec=size)
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); col().objects.link(ob)
    ob.location = loc; ob.rotation_euler = (0, 0, rot_z)
    if mat: ob.data.materials.append(mat)
    return ob

def principled(name, base, rough=0.8, metal=0.0, emit=None, emit_str=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*base, 1.0)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit is not None:
        b.inputs["Emission Color"].default_value = (*emit, 1.0)
        b.inputs["Emission Strength"].default_value = emit_str
    return m

def pbr_mat(name, tex_id, uv_scale=0.45, tint=(1.0, 1.0, 1.0), rough_boost=0.0):
    """Real PolyHaven PBR set, BOX-projected in object space (metres) — no UVs needed."""
    folder = os.path.join(TEX, tex_id)
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; bsdf = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (uv_scale, uv_scale, uv_scale)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])

    def img(fn, non_color=False):
        p = os.path.join(folder, fn)
        if not os.path.exists(p): return None
        n = nt.nodes.new("ShaderNodeTexImage")
        n.image = bpy.data.images.load(p)
        if non_color: n.image.colorspace_settings.name = 'Non-Color'
        n.projection = 'BOX'; n.projection_blend = 0.3
        nt.links.new(mp.outputs["Vector"], n.inputs["Vector"])
        return n

    d = img("Diffuse.jpg")
    if d:
        mix = nt.nodes.new("ShaderNodeMixRGB"); mix.blend_type = 'MULTIPLY'
        mix.inputs["Fac"].default_value = 1.0
        mix.inputs["Color2"].default_value = (*tint, 1.0)
        nt.links.new(d.outputs["Color"], mix.inputs["Color1"])
        nt.links.new(mix.outputs["Color"], bsdf.inputs["Base Color"])
    r = img("Rough.jpg", non_color=True)
    if r:
        if rough_boost:
            br = nt.nodes.new("ShaderNodeBrightContrast")
            br.inputs["Bright"].default_value = rough_boost
            nt.links.new(r.outputs["Color"], br.inputs["Color"])
            nt.links.new(br.outputs["Color"], bsdf.inputs["Roughness"])
        else:
            nt.links.new(r.outputs["Color"], bsdf.inputs["Roughness"])
    n = img("nor_gl.jpg", non_color=True)
    if n:
        nm = nt.nodes.new("ShaderNodeNormalMap"); nm.inputs["Strength"].default_value = 1.2
        nt.links.new(n.outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    return m


# ---------------- render / world / camera ----------------
def setup_render():
    global SCENE
    SCENE = bpy.context.scene
    if USE_CYCLES:
        SCENE.render.engine = 'CYCLES'
        try:
            prefs = bpy.context.preferences.addons['cycles'].preferences
            prefs.compute_device_type = 'METAL'
            prefs.get_devices()
            for d in prefs.devices: d.use = True
            SCENE.cycles.device = 'GPU'
        except Exception as e:
            print("[cycles gpu note]", e)
        SCENE.cycles.samples = SAMPLES
        SCENE.cycles.use_denoising = True
        SCENE.cycles.max_bounces = 6
    else:
        SCENE.render.engine = 'BLENDER_EEVEE_NEXT'
    SCENE.render.resolution_x, SCENE.render.resolution_y = 1920, 1080
    SCENE.render.fps = 30
    SCENE.frame_start, SCENE.frame_end = 1, FRAME_END
    SCENE.render.image_settings.file_format = 'PNG'
    SCENE.render.filepath = FRAMES_DIR
    SCENE.view_settings.view_transform = 'AgX'
    for lk in ('AgX - Punchy', 'Punchy', 'AgX - High Contrast'):
        try: SCENE.view_settings.look = lk; break
        except Exception: pass

def setup_world():
    w = bpy.data.worlds.new("Sky"); SCENE.world = w; w.use_nodes = True
    nt = w.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputWorld"); bg = nt.nodes.new("ShaderNodeBackground")
    env = nt.nodes.new("ShaderNodeTexEnvironment"); mp = nt.nodes.new("ShaderNodeMapping")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    if os.path.exists(HDRI):
        env.image = bpy.data.images.load(HDRI)
    bg.inputs["Strength"].default_value = 0.85
    mp.inputs["Rotation"].default_value = (0, 0, math.radians(155))
    nt.links.new(tc.outputs["Generated"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], env.inputs["Vector"])
    nt.links.new(env.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])

def setup_camera():
    cd = bpy.data.cameras.new("PlateCam"); cd.lens = 35.0; cd.sensor_width = 36.0
    cd.dof.use_dof = True; cd.dof.aperture_fstop = 2.0; cd.dof.focus_distance = 16.0
    cd.clip_end = 3000.0
    cam = bpy.data.objects.new("PlateCam", cd); col().objects.link(cam)
    cam.location = (1.4, -38.0, 1.55)
    cam.rotation_euler = Vector((-1.4, 52.0, 0.10)).to_track_quat('-Z', 'Y').to_euler()
    SCENE.camera = cam

def setup_sun():
    sd = bpy.data.lights.new("Sun", 'SUN'); sd.energy = 5.5; sd.angle = math.radians(0.8)
    sd.color = (1.0, 0.60, 0.32)
    s = bpy.data.objects.new("Sun", sd); col().objects.link(s)
    s.rotation_euler = (math.radians(80), 0, math.radians(152))   # very low, straight down-street

def add_haze():
    ob = add_box("Haze", (0, 20, 20), (150, 210, 44))
    m = bpy.data.materials.new("Haze"); m.use_nodes = True; nt = m.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    v = nt.nodes.new("ShaderNodeVolumePrincipled"); o = nt.nodes.new("ShaderNodeOutputMaterial")
    v.inputs["Density"].default_value = 0.016
    try: v.inputs["Anisotropy"].default_value = 0.7
    except Exception: pass
    nt.links.new(v.outputs[0], o.inputs["Volume"]); ob.data.materials.append(m)

def add_ground():
    g = add_box("Ground", (0, 20, -0.15), (140, 220, 0.3),
                pbr_mat("Paving", "brick_pavement_02", uv_scale=0.22, tint=(0.75, 0.72, 0.70)))
    return g


# ---------------- content ----------------
def facade_pool():
    """Real brick PBR sets x tints -> genuine facade variety (req 2)."""
    sets = [("brick_wall_003", 0.42), ("brick_wall_001", 0.5),
            ("brick_moss_001", 0.45), ("brick_4", 0.4)]
    tints = [(1.0, 0.95, 0.9), (0.85, 0.62, 0.55), (0.62, 0.60, 0.62),
             (1.0, 0.82, 0.62), (0.5, 0.42, 0.40)]
    pool = []
    for tid, sc in sets:
        for i, t in enumerate(tints):
            pool.append(pbr_mat(f"F_{tid}_{i}", tid, uv_scale=sc, tint=t))
    return pool

def add_windows(x, y_front, w, h, side, glow):
    """Warm lit windows on the street-facing wall — the biggest life-adder at dusk (req 4)."""
    floors = max(1, int((h - 1.6) // 2.6))
    for f in range(floors):
        z = 2.4 + f * 2.6
        if z > h - 0.6: break
        n = max(1, int(w // 2.2))
        for k in range(n):
            if random.random() < 0.30:      # some windows dark — variety
                continue
            wx = x - side * 0.06
            ox = (k - (n - 1) / 2.0) * 2.0
            add_box(f"win_{x:.1f}_{y_front:.1f}_{f}_{k}",
                    (wx, y_front + ox, z), (0.14, 1.0, 1.2), glow)

def build_street(facades, roof_mat, awning_mat, lantern_mat, timber, glow):
    types = ["shop", "shop", "courtyard", "twostorey", "corner", "shop", "twostorey"]
    for side in (-1, 1):
        y = -44.0
        while y < 66.0:
            w = random.uniform(6.5, 11.0); d = random.uniform(7.0, 12.0)
            btype = random.choice(types); setback = random.uniform(0.0, 1.6)
            x = side * (5.5 + setback + w / 2)
            fac = random.choice(facades)
            front_y = y - 0.02
            if btype == "shop":
                h = random.uniform(4.2, 6.8)
                add_box(f"b_{side}_{y:.0f}", (x, y + d/2, h/2), (w, d, h), fac)
                # recessed lit shopfront (small + dim: a warm slot, not a white slab)
                add_box(f"shopf_{side}_{y:.0f}", (x - side*(w/2 - 0.30), y + d*0.18, 1.15),
                        (0.25, d*0.45, 1.9), glow)
                add_box(f"awn_{side}_{y:.0f}", (x - side*0.6, y - 1.0, 2.9),
                        (w*0.85, 1.6, 0.07), awning_mat, rot=(math.radians(-16), 0, 0))
                add_box(f"sign_{side}_{y:.0f}", (x - side*(w/2 - 0.2), y - 0.6, 3.6),
                        (0.12, 0.9, 1.4), principled("sign", (0.45, 0.08, 0.06), rough=0.6,
                                                     emit=(0.9, 0.18, 0.10), emit_str=3.0))
                add_windows(x - side*(w/2), front_y, d*0.7, h, side, glow)
            elif btype == "courtyard":
                h = random.uniform(2.8, 3.6)
                add_box(f"wall_{side}_{y:.0f}", (x, y + d/2, h/2), (w, d, h), fac)
                add_box(f"gate_{side}_{y:.0f}", (x - side*(w/2-0.1), y + d*0.2, 1.3),
                        (0.35, 1.6, 2.6), timber)
                add_pyramid(f"groof_{side}_{y:.0f}", (x, y+d/2, h+0.75), (w*0.95, d*0.95, 1.5),
                            math.radians(45), roof_mat)
            elif btype == "twostorey":
                h = random.uniform(6.5, 8.5)
                add_box(f"b_{side}_{y:.0f}", (x, y + d/2, h/2), (w, d, h), fac)
                add_box(f"bal_{side}_{y:.0f}", (x - side*(w/2+0.2), y+d*0.3, h*0.52),
                        (0.7, d*0.55, 0.16), timber)
                add_pyramid(f"roof_{side}_{y:.0f}", (x, y+d/2, h+0.85), (w*1.05, d*1.05, 1.7),
                            math.radians(45), roof_mat)
                add_windows(x - side*(w/2), front_y, d*0.7, h, side, glow)
            else:
                h = random.uniform(5.0, 7.2)
                add_box(f"b_{side}_{y:.0f}", (x, y + d/2, h/2), (w, d, h), fac)
                add_pyramid(f"roof_{side}_{y:.0f}", (x, y+d/2, h+0.8), (w*1.05, d*1.05, 1.6),
                            math.radians(45), roof_mat)
                add_windows(x - side*(w/2), front_y, d*0.7, h, side, glow)
            # eaves band (relief) + hanging lantern
            add_box(f"eave_{side}_{y:.0f}", (x - side*0.25, y+d/2, h+0.06), (w+0.7, d+0.7, 0.14), timber)
            add_lantern(x - side*(w/2 - 0.25), y - 1.2, random.uniform(2.7, 4.0), lantern_mat)
            y += d + random.uniform(0.4, 2.0)

def add_lantern(x, y, z, mat):
    me = bpy.data.meshes.new("lant"); bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=0.17)
    bmesh.ops.scale(bm, verts=bm.verts, vec=(1, 1, 1.3)); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new("lantern", me); col().objects.link(ob)
    ob.location = (x, y, z); ob.data.materials.append(mat)
    add_box(f"wire_{x:.1f}_{y:.1f}", (x, y, z+0.85), (0.015, 0.015, 1.3),
            principled("wire", (0.02, 0.02, 0.02)))

def build_paifang(y):
    red = principled("paifang_red", (0.35, 0.045, 0.035), rough=0.45)
    grey = principled("paifang_roof", (0.11, 0.12, 0.14), rough=0.55, metal=0.15)
    gold = principled("gold", (0.62, 0.44, 0.12), rough=0.3, metal=0.85)
    for px in (-6.5, -2.4, 2.4, 6.5):
        add_box(f"pil_{px}", (px, y, 4.0), (0.75, 0.75, 8.0), red)
    add_box("beam1", (0, y, 7.4), (15.2, 0.95, 0.95), red)
    add_box("beam2", (0, y, 8.6), (15.2, 0.75, 0.6), gold)
    for i, (w, z) in enumerate([(16.5, 9.2), (11.5, 10.5), (6.8, 11.5)]):
        add_pyramid(f"pr_{i}", (0, y, z), (w, 3.4, 1.35), 0, grey)
    # lanterns on the gate
    lm = principled("gate_lant", (0.9, 0.1, 0.05), rough=0.5, emit=(1.0, 0.14, 0.04), emit_str=4.5)
    for px in (-4.4, 4.4):
        add_lantern(px, y - 0.7, 6.4, lm)

def build_backdrop():
    dark = principled("silhouette", (0.035, 0.035, 0.05), rough=1.0)
    random.seed(SEED + 1)
    for i in range(28):
        x = random.uniform(-75, 75); y = random.uniform(85, 155)
        w = random.uniform(8, 22); h = random.uniform(9, 32)
        add_box(f"far_{i}", (x, y, h/2), (w, random.uniform(8, 18), h), dark)
    for i, (w, z) in enumerate([(10, 8), (8, 18), (6, 27), (4, 34)]):
        add_box(f"tower_{i}", (0, 120, z), (w, w, 9 if i == 0 else 7), dark)
        add_pyramid(f"tr_{i}", (0, 120, z+5.5), (w*1.6, w*1.6, 2.3), math.radians(45), dark)

def add_clutter(lantern_mat, timber):
    random.seed(SEED + 2)
    stall = principled("stall", (0.30, 0.08, 0.06), rough=0.7)
    crate = principled("crate", (0.26, 0.18, 0.11), rough=0.85)
    for _ in range(34):
        side = random.choice((-1, 1)); y = random.uniform(-38, 55)
        x = side * random.uniform(4.6, 5.4); k = random.random()
        if k < 0.4:
            add_box(f"stall_{y:.0f}", (x, y, 2.25), (2.3, 2.1, 0.1), stall,
                    rot=(math.radians(-12), 0, 0))
            add_box(f"stallb_{y:.0f}", (x, y, 0.85), (1.9, 1.7, 0.55), crate)
            for p in (-0.9, 0.9):
                add_box(f"post_{y:.0f}_{p}", (x + p*0.9, y, 1.1), (0.07, 0.07, 2.2), timber)
        elif k < 0.72:
            for j in range(random.randint(1, 3)):
                add_box(f"crate_{y:.0f}_{j}", (x, y + j*0.6, 0.3 + j*0.55),
                        (0.55, 0.55, 0.55), crate)
        else:
            add_lantern(x, y, random.uniform(0.9, 1.5), lantern_mat)


# ---------------- figures ----------------
def clothe(arm, mat):
    for bone in arm.data.bones:
        if bone.length < 0.12: continue
        me = bpy.data.meshes.new("limb"); bm = bmesh.new()
        bmesh.ops.create_cone(bm, segments=8, radius1=0.055, radius2=0.055,
                              depth=bone.length, cap_ends=True)
        bmesh.ops.bevel(bm, geom=bm.edges[:], offset=0.018, segments=2, affect='EDGES')
        bm.to_mesh(me); bm.free()
        c = bpy.data.objects.new("limb", me); col().objects.link(c)
        c.data.materials.append(mat); c.parent = arm; c.parent_type = 'BONE'
        c.parent_bone = bone.name
        c.location = (0, -bone.length/2, 0); c.rotation_euler = (math.radians(90), 0, 0)
    head_bone = max(arm.data.bones, key=lambda b: b.head_local.z)
    me = bpy.data.meshes.new("head"); bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=14, v_segments=12, radius=0.11)
    bm.to_mesh(me); bm.free()
    hd = bpy.data.objects.new("head", me); col().objects.link(hd)
    hd.data.materials.append(mat); hd.parent = arm; hd.parent_type = 'BONE'
    hd.parent_bone = head_bone.name

def spawn_figures(mat, n=8):
    bvhs = sorted(os.path.join(BVH_DIR, f) for f in os.listdir(BVH_DIR)
                  if f.endswith(".bvh")) if os.path.isdir(BVH_DIR) else []
    if not bvhs:
        print("[WARN] no mocap BVH — no figures"); return
    long_clips = [b for b in bvhs if "02_01" not in b] or bvhs
    random.seed(SEED + 3)
    for i in range(n):
        bvh = long_clips[i % len(long_clips)]
        bpy.ops.import_anim.bvh(filepath=bvh, global_scale=0.0675, use_fps_scale=True,
                                axis_forward='-Z', axis_up='Y')
        arm = bpy.context.object
        if i == 0: print(f"[figure height] {arm.dimensions.z:.2f} m")
        arm.location = (random.uniform(-4.2, 4.2), random.uniform(-30, 42), 0)
        arm.rotation_euler = (0, 0, 0.0 if random.random() < 0.6 else math.pi)
        # de-sync gait: push the action onto an NLA strip starting BEFORE frame 1, so figures
        # sharing a clip are at different points in the walk cycle from the first frame.
        try:
            ad = arm.animation_data
            if ad and ad.action:
                act = ad.action
                off = random.randint(5, 90)
                ad.nla_tracks.new().strips.new("walk", -off, act)
                ad.action = None
        except Exception as e:
            print(f"[desync skipped for figure {i}]", e)
        clothe(arm, mat)


def main():
    bpy.ops.wm.read_homefile(use_empty=True)
    setup_render(); setup_world(); setup_camera(); setup_sun()
    add_ground(); add_haze()
    facades = facade_pool()
    roof_mat = principled("Roof", (0.09, 0.10, 0.12), rough=0.5, metal=0.2)
    awning_mat = principled("Awning", (0.42, 0.07, 0.05), rough=0.7)
    lantern_mat = principled("Lantern", (0.9, 0.1, 0.05), rough=0.5,
                             emit=(1.0, 0.14, 0.04), emit_str=4.0)
    timber = principled("Timber", (0.12, 0.08, 0.05), rough=0.65)
    # keep emission low: AgX clips anything hot to flat white "paper"
    glow = principled("WinGlow", (0.9, 0.62, 0.32), rough=0.4,
                      emit=(1.0, 0.60, 0.26), emit_str=1.6)
    build_backdrop(); build_paifang(24.0)
    build_street(facades, roof_mat, awning_mat, lantern_mat, timber, glow)
    add_clutter(lantern_mat, timber)
    spawn_figures(principled("Bronze", (0.30, 0.19, 0.09), rough=0.32, metal=0.9), n=8)

    SCENE.frame_set(60)
    os.makedirs(os.path.dirname(OUT_BLEND), exist_ok=True)
    os.makedirs(FRAMES_DIR, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
    print(f"[OK] scene: {len(bpy.data.objects)} objects, engine {SCENE.render.engine}")
    SCENE.render.filepath = STILL
    bpy.ops.render.render(write_still=True)
    SCENE.render.filepath = FRAMES_DIR      # restore for the animation render
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
    print(f"[OK] still -> {STILL}")


if __name__ == "__main__":
    main()
