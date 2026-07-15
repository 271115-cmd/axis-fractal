"""
render_plate.py — populated Qianmen match-cut plate (Phase 9b, Tier 2, priority shot).

Headless, reproducible:  blender -b -P src/blender/render_plate.py
Renders one approval still to results/video_assets/blender/qianmen_plate/still.png; the long
animation render is gated on approval (blender -b output/qianmen_plate.blend -a).

Built against the brief's FIVE anti-generic requirements:
  1 no empty horizon  -> HDRI sunset sky + mid-ground silhouettes + haze gradient
  2 facade variety    -> pool of procedural facade materials + per-building colour jitter
  3 building TYPES     -> shopfronts / courtyard-wall+gate / two-storey+balcony / corner / hero paifang
  4 dressed street     -> strung red lanterns, awnings, market stalls, crates (seeded clutter)
  5 dramatic lighting  -> low raking warm sun + emissive practicals + volumetric haze

Figures are STATUES on purpose (bronze), mocap-driven — the honest contrast that makes the cut land.
Assets: HDRI in data/raw/assets/ (curl'd from PolyHaven), mocap BVH in data/raw/mocap/ (CMU).
Mocap credit: "Motion data from mocap.cs.cmu.edu (CMU Graphics Lab)".
"""
import bpy, bmesh, math, os, random
from mathutils import Vector

PROJECT = os.path.abspath(".")
HDRI = os.path.join(PROJECT, "data/raw/assets/belfast_sunset_puresky_2k.hdr")
BVH_DIR = os.path.join(PROJECT, "data/raw/mocap")
OUT_BLEND = os.path.join(PROJECT, "output/qianmen_plate.blend")
STILL = os.path.join(PROJECT, "results/video_assets/blender/qianmen_plate/still.png")
SEED = 7
random.seed(SEED)
SCENE = None


# ---------------- low-level helpers ----------------
def col():
    return SCENE.collection

def add_box(name, loc, size, mat=None):
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, verts=bm.verts, vec=size)
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); col().objects.link(ob); ob.location = loc
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
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*base, 1.0)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit is not None:
        b.inputs["Emission Color"].default_value = (*emit, 1.0)
        b.inputs["Emission Strength"].default_value = emit_str
    return m

def facade_mat(name, base, rough=0.85):
    """Colour-varied facade with subtle noise grunge + micro-bump (no barcode stripes)."""
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; bsdf = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise"); noise.inputs["Scale"].default_value = 4.0
    noise.inputs["Detail"].default_value = 6.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.35; ramp.color_ramp.elements[0].color = (0.7, 0.7, 0.7, 1)
    ramp.color_ramp.elements[1].color = (1.05, 1.05, 1.05, 1)
    mix = nt.nodes.new("ShaderNodeMixRGB"); mix.blend_type = 'MULTIPLY'; mix.inputs["Fac"].default_value = 0.55
    mix.inputs["Color1"].default_value = (*base, 1.0)
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.08
    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], mix.inputs["Color2"])
    nt.links.new(mix.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    bsdf.inputs["Roughness"].default_value = rough
    return m


# ---------------- world / camera / atmosphere ----------------
def setup_render():
    global SCENE
    SCENE = bpy.context.scene
    try: SCENE.render.engine = 'BLENDER_EEVEE_NEXT'
    except Exception: SCENE.render.engine = 'BLENDER_EEVEE'
    SCENE.render.resolution_x, SCENE.render.resolution_y = 1920, 1080
    SCENE.render.fps = 30
    SCENE.view_settings.view_transform = 'AgX'
    for lk in ('AgX - Punchy', 'Punchy', 'AgX - High Contrast'):
        try: SCENE.view_settings.look = lk; break
        except Exception: pass
    ee = SCENE.eevee
    for attr, val in (("volumetric_start", 0.1), ("volumetric_end", 400.0)):
        try: setattr(ee, attr, val)
        except Exception: pass
    try: ee.use_bloom = True
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
        bg.inputs["Strength"].default_value = 1.0
    else:
        bg.inputs["Color"].default_value = (0.9, 0.55, 0.3, 1.0)
    mp.inputs["Rotation"].default_value = (0, 0, math.radians(155))  # put the sun glow up-street
    nt.links.new(tc.outputs["Generated"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], env.inputs["Vector"])
    nt.links.new(env.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])

def setup_camera():
    cd = bpy.data.cameras.new("PlateCam"); cd.lens = 35.0; cd.sensor_width = 36.0
    cd.dof.use_dof = True; cd.dof.aperture_fstop = 2.2; cd.dof.focus_distance = 14.0
    cd.clip_end = 3000.0
    cam = bpy.data.objects.new("PlateCam", cd); col().objects.link(cam)
    cam.location = (1.4, -38.0, 1.55)
    cam.rotation_euler = Vector((-1.4, 52.0, 0.15)).to_track_quat('-Z', 'Y').to_euler()
    SCENE.camera = cam

def setup_sun():
    sd = bpy.data.lights.new("Sun", 'SUN'); sd.energy = 3.4; sd.angle = math.radians(1.2)
    sd.color = (1.0, 0.66, 0.40)
    s = bpy.data.objects.new("Sun", sd); col().objects.link(s)
    s.rotation_euler = (math.radians(76), 0, math.radians(150))  # low, from up-street

def add_haze():
    ob = add_box("Haze", (0, 18, 20), (150, 200, 44))
    m = bpy.data.materials.new("Haze"); m.use_nodes = True; nt = m.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    v = nt.nodes.new("ShaderNodeVolumePrincipled"); o = nt.nodes.new("ShaderNodeOutputMaterial")
    v.inputs["Density"].default_value = 0.012
    try: v.inputs["Anisotropy"].default_value = 0.6
    except Exception: pass
    nt.links.new(v.outputs[0], o.inputs["Volume"]); ob.data.materials.append(m)

def add_ground():
    g = add_box("Ground", (0, 20, -0.15), (140, 200, 0.3))
    m = bpy.data.materials.new("Ground"); m.use_nodes = True; nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    noise = nt.nodes.new("ShaderNodeTexNoise"); noise.inputs["Scale"].default_value = 2.5
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.06, 0.055, 0.05, 1); ramp.color_ramp.elements[0].position = 0.3
    ramp.color_ramp.elements[1].color = (0.14, 0.12, 0.11, 1)
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.15
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    bsdf.inputs["Roughness"].default_value = 0.85
    g.data.materials.append(m)


# ---------------- content ----------------
def facade_pool():
    return [
        facade_mat("Facade_grey", (0.40, 0.38, 0.36)),
        facade_mat("Facade_red", (0.45, 0.22, 0.17)),
        facade_mat("Facade_buff", (0.60, 0.50, 0.37)),
        facade_mat("Facade_plaster", (0.72, 0.66, 0.55)),
        facade_mat("Facade_slate", (0.26, 0.26, 0.30)),
    ]

def jitter(mat):
    """Per-building colour jitter so no two facades match."""
    m = mat.copy()
    b = m.node_tree.nodes["Principled BSDF"]
    j = random.uniform(-0.06, 0.06)
    c = list(b.inputs["Base Color"].default_value)
    b.inputs["Base Color"].default_value = (max(0, c[0]+j), max(0, c[1]+j*0.8), max(0, c[2]+j*0.6), 1)
    return m

def add_awning(x, y, w, top, mat):
    a = add_box(f"awn_{x:.0f}_{y:.0f}", (x, y, top), (w*0.9, 1.4, 0.08), mat)
    a.rotation_euler = (math.radians(-18), 0, 0)

def build_street(facades, roof_mat, awning_mat, lantern_mat, timber):
    """Two rows of varied building TYPES flanking the street (+Y), with roofs + dressing."""
    types = ["shop", "shop", "courtyard", "twostorey", "corner", "shop", "twostorey"]
    for side in (-1, 1):
        y = -44.0
        while y < 66.0:
            w = random.uniform(6.5, 11.0)
            d = random.uniform(7.0, 12.0)
            btype = random.choice(types)
            setback = random.uniform(0.0, 1.6)
            x = side * (5.5 + setback + w/2)
            fac = jitter(random.choice(facades))
            if btype == "shop":
                h = random.uniform(4.0, 6.5)
                add_box(f"b_{side}_{y:.0f}", (x, y+d/2, h/2), (w, d, h), fac)
                # recessed lit shopfront + awning + sign
                gx = x - side*(w/2 - 0.4)
                front = add_box(f"shopf_{side}_{y:.0f}", (gx, y-0.2, 1.3), (w*0.7, 0.5, 2.4),
                                principled("shoplit", (0.9, 0.75, 0.45), rough=0.5,
                                           emit=(1.0, 0.8, 0.45), emit_str=3.5))
                add_awning(x, y-0.7, w, h+0.2, awning_mat)
                add_box(f"sign_{side}_{y:.0f}", (x, y-0.9, h+0.5), (w*0.5, 0.15, 0.7),
                        principled("sign", (0.5, 0.1, 0.08), rough=0.6,
                                   emit=(0.9, 0.2, 0.12), emit_str=2.0))
            elif btype == "courtyard":
                h = random.uniform(2.6, 3.4)
                add_box(f"wall_{side}_{y:.0f}", (x, y+d/2, h/2), (w, d, h), fac)
                add_box(f"gate_{side}_{y:.0f}", (x - side*(w/2-0.1), y-0.1, 1.3), (0.4, 1.2, 2.6), timber)
                add_pyramid(f"groof_{side}_{y:.0f}", (x, y+d/2, h+0.7), (w*0.8, d*0.8, 1.4),
                            math.radians(45), roof_mat)
            elif btype == "twostorey":
                h = random.uniform(6.5, 8.5)
                add_box(f"b_{side}_{y:.0f}", (x, y+d/2, h/2), (w, d, h), fac)
                # balcony band
                add_box(f"bal_{side}_{y:.0f}", (x - side*(w/2), y-0.1, h*0.55), (0.5, d*0.7, 0.3), timber)
                add_pyramid(f"roof_{side}_{y:.0f}", (x, y+d/2, h+0.9), (w*0.85, d*0.85, 1.8),
                            math.radians(45), roof_mat)
            else:  # corner
                h = random.uniform(5.0, 7.0)
                add_box(f"b_{side}_{y:.0f}", (x, y+d/2, h/2), (w, d, h), fac)
                add_pyramid(f"roof_{side}_{y:.0f}", (x, y+d/2, h+0.8), (w*0.85, d*0.85, 1.6),
                            math.radians(45), roof_mat)
            # hanging lantern near frontage, varied height
            add_lantern(x - side*(w/2 - 0.3), y - 1.0, random.uniform(2.6, 3.8), lantern_mat)
            y += d + random.uniform(0.4, 2.0)

def add_lantern(x, y, z, mat):
    me = bpy.data.meshes.new("lant"); bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=8, radius=0.16)
    bmesh.ops.scale(bm, verts=bm.verts, vec=(1, 1, 1.25)); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new("lantern", me); col().objects.link(ob); ob.location = (x, y, z)
    ob.data.materials.append(mat)
    add_box(f"wire_{x:.1f}_{y:.1f}", (x, y, z+0.9), (0.02, 0.02, 1.4),
            principled("wire", (0.02, 0.02, 0.02)))

def build_paifang(y):
    """Hero gate spanning the street — the mid-ground focal structure (req 1 & 3)."""
    red = principled("paifang_red", (0.5, 0.06, 0.05), rough=0.5)
    grey = principled("paifang_roof", (0.16, 0.17, 0.19), rough=0.6, metal=0.1)
    gold = principled("gold", (0.7, 0.5, 0.15), rough=0.35, metal=0.8)
    for px in (-6.5, -2.4, 2.4, 6.5):
        add_box(f"pil_{px}", (px, y, 4.0), (0.7, 0.7, 8.0), red)
    add_box("beam1", (0, y, 7.4), (15.0, 0.9, 0.9), red)
    add_box("beam2", (0, y, 8.6), (15.0, 0.7, 0.6), gold)
    for i, (w, z) in enumerate([(16, 9.2), (11, 10.4), (6.5, 11.4)]):
        add_pyramid(f"pr_{i}", (0, y, z), (w, 3.2, 1.3), 0, grey)

def build_backdrop():
    """Mid-ground silhouettes + a pagoda tower so the horizon never reads as void (req 1)."""
    dark = principled("silhouette", (0.05, 0.05, 0.07), rough=1.0)
    random.seed(SEED + 1)
    for i in range(26):
        x = random.uniform(-70, 70); y = random.uniform(80, 150)
        w = random.uniform(8, 22); h = random.uniform(8, 30)
        add_box(f"far_{i}", (x, y, h/2), (w, random.uniform(8, 18), h), dark)
    # a pagoda-ish tower on the axis, up-street
    for i, (w, z) in enumerate([(10, 8), (8, 18), (6, 27), (4, 34)]):
        add_box(f"tower_{i}", (0, 120, z), (w, w, 9 if i == 0 else 7), dark)
        add_pyramid(f"tr_{i}", (0, 120, z+5.5), (w*1.5, w*1.5, 2.2), math.radians(45), dark)

def add_clutter(lantern_mat):
    """Seeded eye-level dressing: market stalls, crates, AC units (req 4)."""
    random.seed(SEED + 2)
    stall = principled("stall", (0.35, 0.12, 0.1), rough=0.7)
    crate = principled("crate", (0.3, 0.22, 0.13), rough=0.85)
    for _ in range(34):
        side = random.choice((-1, 1)); y = random.uniform(-40, 55)
        x = side * random.uniform(4.6, 5.4)
        kind = random.random()
        if kind < 0.4:                       # market stall canopy
            add_box(f"stall_{y:.0f}", (x, y, 2.2), (2.2, 2.0, 0.12), stall).rotation_euler = (math.radians(-10), 0, 0)
            add_box(f"stallb_{y:.0f}", (x, y, 0.9), (1.8, 1.6, 0.6), crate)
        elif kind < 0.7:                     # crates
            for k in range(random.randint(1, 3)):
                add_box(f"crate_{y:.0f}_{k}", (x, y+k*0.6, 0.3+k*0.55), (0.55, 0.55, 0.55), crate)
        else:                                # small ground lantern / bollard
            add_lantern(x, y, random.uniform(0.8, 1.4), lantern_mat)


# ---------------- figures (bronze statues, mocap) ----------------
def statue_mat():
    return principled("Bronze", (0.28, 0.18, 0.08), rough=0.35, metal=0.85)

def clothe(arm, mat):
    for bone in arm.data.bones:
        if bone.length < 0.12:
            continue
        me = bpy.data.meshes.new("limb"); bm = bmesh.new()
        bmesh.ops.create_cone(bm, segments=8, radius1=0.055, radius2=0.055, depth=bone.length, cap_ends=True)
        bmesh.ops.bevel(bm, geom=bm.edges[:], offset=0.02, segments=2, affect='EDGES')
        bm.to_mesh(me); bm.free()
        c = bpy.data.objects.new("limb", me); col().objects.link(c)
        c.data.materials.append(mat); c.parent = arm; c.parent_type = 'BONE'; c.parent_bone = bone.name
        c.location = (0, -bone.length/2, 0); c.rotation_euler = (math.radians(90), 0, 0)
    # head sphere on the highest bone
    head_bone = max(arm.data.bones, key=lambda b: b.head_local.z)
    me = bpy.data.meshes.new("head"); bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=10, radius=0.11); bm.to_mesh(me); bm.free()
    hd = bpy.data.objects.new("head", me); col().objects.link(hd); hd.data.materials.append(mat)
    hd.parent = arm; hd.parent_type = 'BONE'; hd.parent_bone = head_bone.name

def spawn_figures(mat, n=7):
    bvhs = sorted(os.path.join(BVH_DIR, f) for f in os.listdir(BVH_DIR) if f.endswith(".bvh")) if os.path.isdir(BVH_DIR) else []
    if not bvhs:
        print("[WARN] no mocap BVH — plate rendered without figures"); return
    random.seed(SEED + 3)
    for i in range(n):
        bvh = random.choice([b for b in bvhs if "02_01" not in b] or bvhs)
        # subject-02 skeleton: 0.0564 -> ~1.42 m (brief); 0.0675 -> ~1.7 m eye height
        bpy.ops.import_anim.bvh(filepath=bvh, global_scale=0.0675, use_fps_scale=True,
                                axis_forward='-Z', axis_up='Y')
        arm = bpy.context.object
        if i == 0:
            print(f"[figure height] armature dims.z = {arm.dimensions.z:.2f} m")
        arm.location = (random.uniform(-4.2, 4.2), random.uniform(-30, 42), 0)
        arm.rotation_euler = (0, 0, 0.0 if random.random() < 0.6 else math.pi)
        # (frame-offset de-sync is irrelevant for a single still; add per-frame offset before the anim render)
        clothe(arm, mat)


def main():
    bpy.ops.wm.read_homefile(use_empty=True)   # headless-safe (no MCP addon to unregister)
    setup_render(); setup_world(); setup_camera(); setup_sun()
    add_ground(); add_haze()
    facades = facade_pool()
    roof_mat = principled("Roof", (0.15, 0.16, 0.18), rough=0.6, metal=0.1)
    awning_mat = principled("Awning", (0.55, 0.12, 0.08), rough=0.7)
    lantern_mat = principled("Lantern", (0.9, 0.1, 0.05), rough=0.5, emit=(1.0, 0.15, 0.04), emit_str=7.0)
    timber = principled("Timber", (0.18, 0.12, 0.08), rough=0.7)
    build_backdrop()
    build_paifang(24.0)
    build_street(facades, roof_mat, awning_mat, lantern_mat, timber)
    add_clutter(lantern_mat)
    spawn_figures(statue_mat(), n=7)

    SCENE.frame_set(60)   # mid-walk — frame 1 is the BVH calibration T-pose
    os.makedirs(os.path.dirname(OUT_BLEND), exist_ok=True)
    os.makedirs(os.path.dirname(STILL), exist_ok=True)
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
    SCENE.render.filepath = STILL
    print(f"[OK] built scene: {len(bpy.data.objects)} objects. Rendering still...")
    bpy.ops.render.render(write_still=True)
    print(f"[OK] still -> {STILL}")


if __name__ == "__main__":
    main()
