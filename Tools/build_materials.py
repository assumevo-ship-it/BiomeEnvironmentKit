"""Build the Biome Auto-Materials plugin content inside the Unreal Editor.

Run after Tools/fetch_textures.py, with the plugin in <YourProject>/Plugins/BiomeAutoMaterials:
    Editor:      Tools > Execute Python Script... > Tools/build_materials.py
    Command line UnrealEditor.exe <Project>.uproject -ExecutePythonScript="<path>/Tools/build_materials.py" -unattended

Creates (all under /BiomeAutoMaterials):
    Textures/<set>/T_<set>_CH, T_<set>_NRA, Textures/T_BiomeNoise
    Materials/M_BiomeAuto                 the master (one Custom-HLSL evaluator, every feature data driven)
    Biomes/MI_Biome_<Name>                one instance per biome in Tools/biomes.py

Environment: BAM_REIMPORT=1 re-imports textures that already exist; BAM_ONLY=Name,Name builds just those instances;
BAM_QUIT=1 closes the editor when done.
"""
import json
import os
import sys

import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import importlib  # noqa: E402

import biomes  # noqa: E402

importlib.reload(biomes)

MOUNT = "/BiomeAutoMaterials"
TEX_DIR = f"{MOUNT}/Textures"
MAT_DIR = f"{MOUNT}/Materials"
MI_DIR = f"{MOUNT}/Biomes"
MASTER = "M_BiomeAuto"
BUILD = os.path.join(ROOT, "Build")

EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
SHORT = {"Ground": "G", "GroundB": "GB", "Soil": "SO", "Shore": "SH", "Scree": "SC", "Rock": "R", "RockB": "RB", "Snow": "SN"}
SLOT_NORMAL = {"Snow": 0.7, "Rock": 1.1, "RockB": 1.1}
ERRORS = []


def log(msg):
    unreal.log(f"[BAM] {msg}")


def warn(msg):
    ERRORS.append(msg)
    unreal.log_warning(f"[BAM] {msg}")


def ident(name):
    return name.replace(" ", "")


# ---------------------------------------------------------------------------------------------------------------------
# textures
# ---------------------------------------------------------------------------------------------------------------------
def import_texture(png, dest_dir, name, srgb):
    path = f"{dest_dir}/{name}"
    if EAL.does_asset_exist(path) and os.environ.get("BAM_REIMPORT") != "1":
        return unreal.load_asset(path)
    t = unreal.AssetImportTask()
    t.set_editor_property("filename", png)
    t.set_editor_property("destination_path", dest_dir)
    t.set_editor_property("destination_name", name)
    t.set_editor_property("automated", True)
    t.set_editor_property("replace_existing", True)
    t.set_editor_property("save", False)
    TOOLS.import_asset_tasks([t])
    tex = unreal.load_asset(path)
    if not tex:
        warn(f"import failed: {png}")
        return None
    tex.set_editor_property("srgb", srgb)
    tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_BC7)
    tex.set_editor_property("lod_group", unreal.TextureGroup.TEXTUREGROUP_WORLD)
    tex.set_editor_property("virtual_texture_streaming", False)
    EAL.save_asset(path, only_if_is_dirty=False)
    return tex


def import_all(stats):
    out = {}
    for i, key in enumerate(sorted(stats)):
        d = os.path.join(BUILD, "Textures", key)
        ch = import_texture(os.path.join(d, f"T_{key}_CH.png"), f"{TEX_DIR}/{key}", f"T_{key}_CH", True)
        nra = import_texture(os.path.join(d, f"T_{key}_NRA.png"), f"{TEX_DIR}/{key}", f"T_{key}_NRA", False)
        out[key] = (ch, nra)
        if i % 10 == 0:
            log(f"textures {i + 1}/{len(stats)}")
    noise = import_texture(os.path.join(BUILD, "Textures", "T_BiomeNoise.png"), TEX_DIR, "T_BiomeNoise", False)
    return out, noise


# ---------------------------------------------------------------------------------------------------------------------
# master material
# ---------------------------------------------------------------------------------------------------------------------
class Graph:
    def __init__(self, mat):
        self.m = mat
        self.col = 0
        self.row = 0
        self.params = {}

    def node(self, cls, **props):
        e = MEL.create_material_expression(self.m, cls, -3000 + self.col * 320, -2000 + self.row * 110)
        self.row += 1
        if self.row > 40:
            self.row, self.col = 0, self.col + 1
        for k, v in props.items():
            e.set_editor_property(k, v)
        return e

    def link(self, a, b, pin_b="", pin_a=""):
        if isinstance(a, tuple):
            a, pin_a = a
        if not MEL.connect_material_expressions(a, pin_a, b, pin_b):
            warn(f"link failed {a.get_name()}.{pin_a} -> {b.get_name()}.{pin_b}")

    def scalar(self, name, default=None, group=None):
        if name not in self.params:
            v = biomes.PARAM_DEFAULTS.get(name, default) if default is None else default
            self.params[name] = self.node(unreal.MaterialExpressionScalarParameter, parameter_name=name, default_value=float(v),
                                          group=group or biomes.group_of(name))
        return self.params[name]

    def vector(self, name, default, group=None):
        if name not in self.params:
            r, g, b = default
            self.params[name] = self.node(unreal.MaterialExpressionVectorParameter, parameter_name=name,
                                          default_value=unreal.LinearColor(r, g, b, 1.0), group=group or biomes.group_of(name))
        return self.params[name]

    def op(self, cls, a, b=None, **props):
        e = self.node(cls, **props)
        self.link(a, e, "A")
        if b is not None:
            self.link(b, e, "B")
        return e

    def append(self, *xs):
        cur = xs[0]
        for x in xs[1:]:
            cur = self.op(unreal.MaterialExpressionAppendVector, cur, x)
        return cur

    def mask(self, a, r=False, g=False, b=False, al=False):
        e = self.node(unreal.MaterialExpressionComponentMask, r=r, g=g, b=b, a=al)
        self.link(a, e, "")
        return e

    def custom(self, desc, code, out_type, inputs, outputs=()):
        e = self.node(unreal.MaterialExpressionCustom, code=code, description=desc, output_type=out_type)
        cins = []
        for iname, _ in inputs:
            ci = unreal.CustomInput()
            ci.set_editor_property("input_name", iname)
            cins.append(ci)
        e.set_editor_property("inputs", cins)
        if outputs:
            couts = []
            for oname, otype in outputs:
                co = unreal.CustomOutput()
                co.set_editor_property("output_name", oname)
                co.set_editor_property("output_type", otype)
                couts.append(co)
            e.set_editor_property("additional_outputs", couts)
        for iname, src in inputs:
            self.link(src, e, iname)
        return e


def hlsl(name):
    return open(os.path.join(HERE, "hlsl", name), encoding="utf8").read()


def build_master(textures, noise, first_set):
    path = f"{MAT_DIR}/{MASTER}"
    # instances are rebuilt below, so the old master can simply go
    for a in EAL.list_assets(MI_DIR, recursive=False, include_folder=False) if EAL.does_directory_exist(MI_DIR) else []:
        EAL.delete_asset(a.split(".")[0])
    if EAL.does_asset_exist(path):
        EAL.delete_asset(path)
    m = TOOLS.create_asset(MASTER, MAT_DIR, unreal.Material, unreal.MaterialFactoryNew())
    m.set_editor_property("tangent_space_normal", False)
    g = Graph(m)
    C = unreal.CustomMaterialOutputType
    ST = unreal.MaterialSamplerType

    # coordinates: landscape-space metres (precise far from the origin) or world metres for meshes
    lc = g.node(unreal.MaterialExpressionLandscapeLayerCoords, mapping_scale=1.0)
    lxy = g.op(unreal.MaterialExpressionMultiply, lc, g.scalar("Landscape Quad Size"))
    wp = g.node(unreal.MaterialExpressionWorldPosition)
    wxy = g.op(unreal.MaterialExpressionMultiply, g.mask(wp, r=True, g=True), None, const_b=0.01)
    sw = g.node(unreal.MaterialExpressionStaticSwitchParameter, parameter_name="Use World Coordinates", default_value=False,
                group="00 World")
    g.link(wxy, sw, "True")
    g.link(lxy, sw, "False")
    z = g.op(unreal.MaterialExpressionMultiply, g.mask(wp, b=True), None, const_b=0.01)
    P = g.append(sw, z)
    N = g.node(unreal.MaterialExpressionVertexNormalWS)
    dist = g.node(unreal.MaterialExpressionPixelDepth)

    helpers = g.custom("BAM helpers (global functions)", "return 0;\n}\n" + hlsl("BiomeCommon.hlsl") + "\nfloat BAM_HelpersEnd()\n{\n",
                       C.CMOT_FLOAT1, [])
    noise_obj = g.node(unreal.MaterialExpressionTextureObjectParameter, parameter_name="Noise", texture=noise,
                       sampler_type=ST.SAMPLERTYPE_LINEAR_COLOR, group="01 Blending")

    inputs = [("P", P), ("N", N), ("Dist", dist), ("Helpers", helpers), ("NoiseTex", noise_obj)]
    ch0, nra0 = textures[first_set]
    for slot in biomes.SLOTS:
        s = SHORT[slot]
        grp = biomes.group_of(f"{slot} Tile")
        ch = g.node(unreal.MaterialExpressionTextureObjectParameter, parameter_name=f"{slot} Color+Height", texture=ch0,
                    sampler_type=ST.SAMPLERTYPE_COLOR, group=grp)
        nra = g.node(unreal.MaterialExpressionTextureObjectParameter, parameter_name=f"{slot} Normal+Rough+AO", texture=nra0,
                     sampler_type=ST.SAMPLERTYPE_LINEAR_COLOR, group=grp)

        def sp(n):
            d = biomes.LAYER_PARAMS[n]
            if n == "Tile":
                d = biomes.SLOT_DEFAULT_SIZE[slot]
            if n == "Normal":
                d = SLOT_NORMAL.get(slot, 1.0)
            return g.scalar(f"{slot} {n}", d, grp)

        p0 = g.append(sp("Tile"), sp("Aspect"), sp("Brightness"), sp("Saturation"))
        p1 = g.append(sp("Normal"), sp("Roughness"), sp("Height Bias"), sp("Porosity"))
        tint = g.mask(g.vector(f"{slot} Tint", (1.0, 1.0, 1.0), grp), r=True, g=True, b=True)
        inputs += [(f"{s}_CH", ch), (f"{s}_NRA", nra), (f"{s}_P0", p0), (f"{s}_P1", p1), (f"{s}_Tint", tint)]

    for name in biomes.PARAM_DEFAULTS:
        if name in ("Landscape Quad Size",):
            continue
        src = g.scalar(name)
        if name == "Hex Tiling":  # Low material quality: plain tiling (a third of the texture reads)
            q = g.node(unreal.MaterialExpressionQualitySwitch)
            g.link(src, q, "Default")
            g.link(g.node(unreal.MaterialExpressionConstant, r=0.0), q, "Low")
            src = q
        inputs.append((ident(name), src))
    for name, d in biomes.VECTOR_DEFAULTS.items():
        inputs.append((ident(name), g.mask(g.vector(name, d), r=True, g=True, b=True)))

    main = g.custom("BiomeAutoMaterial", hlsl("BiomeMain.hlsl"), C.CMOT_FLOAT4, inputs,
                    outputs=[("NormalWS", C.CMOT_FLOAT3), ("AO", C.CMOT_FLOAT1)])
    MEL.connect_material_property(g.mask(main, r=True, g=True, b=True), "", unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(g.mask(main, al=True), "", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.connect_material_property(main, "NormalWS", unreal.MaterialProperty.MP_NORMAL)
    MEL.connect_material_property(main, "AO", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
    MEL.recompile_material(m)
    EAL.save_asset(path, only_if_is_dirty=False)
    try:
        st = MEL.get_statistics(m)
        log(f"{MASTER}: ps={st.num_pixel_shader_instructions} samplers={st.num_samplers} tex_samples={st.num_pixel_texture_samples}")
        if st.num_pixel_shader_instructions <= 0:
            warn(f"{MASTER} did not compile (see LogMaterial / LogShaderCompilers errors in the log)")
    except Exception as e:  # noqa
        warn(f"stats: {e}")
    return m


# ---------------------------------------------------------------------------------------------------------------------
# instances
# ---------------------------------------------------------------------------------------------------------------------
def layer_values(slot, key, stats, biome):
    st = stats[key]
    _, target, size_m, porosity = biomes.TEXTURES[key]
    target = biome.get("albedo", {}).get(slot, target)
    size = st.get("size")
    if size_m:
        size = (size_m, size_m * st["px"][1] / st["px"][0])
    if not size or not size[0]:
        d = biomes.SLOT_DEFAULT_SIZE[slot]
        size = (d, d * st["px"][1] / st["px"][0])
    bright = 1.0
    if target and st.get("mean_albedo"):
        bright = max(0.35, min(3.0, target / st["mean_albedo"]))
    rough = 1.0
    floor = biomes.ROUGHNESS_FLOOR.get(key, biomes.ROUGHNESS_FLOOR_DEFAULT)
    if floor and st.get("mean_rough"):
        rough = max(1.0, min(3.5, floor / max(st["mean_rough"], 0.05)))
    return {f"{slot} Tile": size[0], f"{slot} Aspect": size[1] / size[0], f"{slot} Brightness": bright,
            f"{slot} Roughness": rough, f"{slot} Porosity": porosity}


def build_instances(master, textures, stats):
    only = [x for x in os.environ.get("BAM_ONLY", "").split(",") if x]
    made = []
    for name, b in biomes.BIOMES.items():
        if only and name not in only:
            continue
        lay, off = biomes.resolved_layers(b)
        missing = [k for k in lay.values() if k not in textures or not textures[k][0]]
        if missing:
            warn(f"{name}: textures missing {missing}")
            continue
        path = f"{MI_DIR}/MI_Biome_{name}"
        if EAL.does_asset_exist(path):
            EAL.delete_asset(path)
        mi = TOOLS.create_asset(f"MI_Biome_{name}", MI_DIR, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        MEL.set_material_instance_parent(mi, master)
        scal, vec = {}, {}
        for slot, key in lay.items():
            ch, nra = textures[key]
            MEL.set_material_instance_texture_parameter_value(mi, f"{slot} Color+Height", ch)
            MEL.set_material_instance_texture_parameter_value(mi, f"{slot} Normal+Rough+AO", nra)
            scal.update(layer_values(slot, key, stats, b))
        for slot, t in b.get("tints", {}).items():
            vec[f"{slot} Tint"] = t
        for k, v in list(b.get("params", {}).items()) + list(off.items()):
            if isinstance(v, (tuple, list)):
                vec[k] = v
            else:
                scal[k] = v
        for k, v in scal.items():
            MEL.set_material_instance_scalar_parameter_value(mi, k, float(v))
        for k, v in vec.items():
            MEL.set_material_instance_vector_parameter_value(mi, k, unreal.LinearColor(v[0], v[1], v[2], 1.0))
        MEL.update_material_instance(mi)
        EAL.save_asset(path, only_if_is_dirty=False)
        made.append(name)
    log(f"instances: {len(made)} {made}")
    return made


def main():
    stats_path = os.path.join(BUILD, "textures.json")
    if not os.path.exists(stats_path):
        raise RuntimeError("run Tools/fetch_textures.py first (Build/textures.json is missing)")
    stats = json.load(open(stats_path))
    textures, noise = import_all(stats)
    first = biomes.BIOMES[next(iter(biomes.BIOMES))]["layers"]["Ground"]
    master = build_master(textures, noise, first)
    build_instances(master, textures, stats)
    log(f"BAM BUILD DONE errors={len(ERRORS)}")
    for e in ERRORS:
        log(f"  error: {e}")


try:
    main()
except Exception as ex:  # noqa
    import traceback
    unreal.log_error("[BAM] " + traceback.format_exc())
    log("BAM BUILD FAILED")
if os.environ.get("BAM_QUIT") == "1":
    unreal.SystemLibrary.quit_editor()
