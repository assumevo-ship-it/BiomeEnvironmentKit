"""Small helpers for building material graphs from Python (shared by the sky and ocean builders)."""
import os

import unreal

EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
C = unreal.CustomMaterialOutputType
ERRORS = []


def log(msg):
    unreal.log(f"[BAM] {msg}")


def warn(msg):
    ERRORS.append(msg)
    unreal.log_warning(f"[BAM] {msg}")


def ensure_dir(path):
    if not EAL.does_directory_exist(path):
        EAL.make_directory(path)


def fresh_material(folder, name):
    ensure_dir(folder)
    path = f"{folder}/{name}"
    if EAL.does_asset_exist(path):
        # Clearing an existing graph (delete_all_material_expressions) leaves stale nodes behind in UE 5.x and can
        # assert on rooted objects, so the material is deleted and made again. The actors reference it by soft path.
        EAL.delete_asset(path)
        unreal.SystemLibrary.collect_garbage()
    if EAL.does_asset_exist(path):
        m = unreal.load_asset(path)
        MEL.delete_all_material_expressions(m)
        return m
    m = TOOLS.create_asset(name, folder, unreal.Material, unreal.MaterialFactoryNew())
    if not m:
        raise RuntimeError(f"could not create {path}")
    return m


def read(path):
    return open(path, encoding="utf8").read()


class Graph:
    def __init__(self, mat):
        self.m = mat
        self.n = 0
        self.params = {}

    def node(self, cls, **props):
        e = MEL.create_material_expression(self.m, cls, -2400 + (self.n // 30) * 340, -1500 + (self.n % 30) * 110)
        self.n += 1
        for k, v in props.items():
            e.set_editor_property(k, v)
        return e

    def link(self, a, b, pin_b="", pin_a=""):
        if isinstance(a, tuple):
            a, pin_a = a
        if not MEL.connect_material_expressions(a, pin_a, b, pin_b):
            warn(f"{self.m.get_name()}: link failed {a.get_name()}.{pin_a} -> {b.get_name()}.{pin_b}")

    def out(self, a, prop, pin_a=""):
        if isinstance(a, tuple):
            a, pin_a = a
        if not MEL.connect_material_property(a, pin_a, prop):
            warn(f"{self.m.get_name()}: output link failed {a.get_name()}.{pin_a} -> {prop}")

    def scalar(self, name, default=0.0, group="Parameters"):
        if name not in self.params:
            self.params[name] = self.node(unreal.MaterialExpressionScalarParameter, parameter_name=name,
                                          default_value=float(default), group=group)
        return self.params[name]

    def vector(self, name, default=(0.0, 0.0, 0.0, 0.0), group="Parameters"):
        if name not in self.params:
            d = list(default) + [0.0] * (4 - len(default))
            self.params[name] = self.node(unreal.MaterialExpressionVectorParameter, parameter_name=name,
                                          default_value=unreal.LinearColor(*d), group=group)
        return self.params[name]

    def texture(self, name, tex, linear=True, group="Textures"):
        if name not in self.params:
            st = unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR if linear else unreal.MaterialSamplerType.SAMPLERTYPE_COLOR
            self.params[name] = self.node(unreal.MaterialExpressionTextureObjectParameter, parameter_name=name, texture=tex,
                                          sampler_type=st, group=group)
        return self.params[name]

    def const(self, v):
        return self.node(unreal.MaterialExpressionConstant, r=float(v))

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
            # A vector parameter's default pin is RGB; custom HLSL reads all four components.
            if isinstance(src, unreal.MaterialExpressionVectorParameter):
                src = (src, "RGBA")
            self.link(src, e, iname)
        return e


def finish(m, path):
    MEL.recompile_material(m)
    EAL.save_asset(path, only_if_is_dirty=False)
    try:
        st = MEL.get_statistics(m)
        log(f"{m.get_name()}: vs={st.num_vertex_shader_instructions} ps={st.num_pixel_shader_instructions} samplers={st.num_samplers}")
        if st.num_pixel_shader_instructions <= 0 and st.num_vertex_shader_instructions <= 0:
            warn(f"{m.get_name()} did not compile (see LogShaderCompilers errors)")
    except Exception as e:  # noqa
        warn(f"stats {m.get_name()}: {e}")


def import_texture(png, dest_dir, name, srgb, compression=None, address_y_clamp=False):
    ensure_dir(dest_dir)
    path = f"{dest_dir}/{name}"
    if not os.path.exists(png):
        if EAL.does_asset_exist(path):
            return unreal.load_asset(path)
        warn(f"missing source image {png}")
        return None
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
    if compression is not None:
        tex.set_editor_property("compression_settings", compression)
    tex.set_editor_property("mip_gen_settings", unreal.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE)
    tex.set_editor_property("filter", unreal.TextureFilter.TF_TRILINEAR)
    if address_y_clamp:
        tex.set_editor_property("address_y", unreal.TextureAddress.TA_CLAMP)
    tex.set_editor_property("never_stream", True)
    EAL.save_asset(path, only_if_is_dirty=False)
    return tex
