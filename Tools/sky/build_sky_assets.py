"""Build the BiomeSky content inside the Unreal Editor (run after Tools/sky/fetch_sky_textures.py).

    Editor:       Tools > Execute Python Script... > Tools/sky/build_sky_assets.py
    Command line: UnrealEditor-Cmd.exe <Project>.uproject -ExecutePythonScript="<path>/Tools/sky/build_sky_assets.py" -unattended

Creates under /BiomeAutoMaterials/Sky:
    T_MoonColor, T_MilkyWay        NASA's moon and Milky Way maps (public domain, see Docs/Sky.md)
    MPC_BiomeSky                   sun, moon, wind and weather for any other material to read
    M_BiomeSky                     the sky dome: atmosphere, real stars, Milky Way, moon with phases, meteors, aurora
    M_BiomeClouds                  volumetric clouds: cumulus, stratiform rain decks, cumulonimbus, anvils, cirrus
    M_BiomePrecipitation           GPU rain streaks and snowflakes round the camera
The cloud shapes come from the engine's own volume noise (/Engine/EngineSky/VolumetricClouds), referenced, not copied.
Environment: BAM_QUIT=1 closes the editor when done.
"""
import os
import sys

import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS_DIR = os.path.dirname(HERE)
ROOT = os.path.dirname(TOOLS_DIR)
sys.path.insert(0, HERE)
sys.path.insert(0, TOOLS_DIR)
import importlib  # noqa: E402

import matgraph as mg  # noqa: E402
import star_catalog  # noqa: E402

importlib.reload(mg)
importlib.reload(star_catalog)

SKY = "/BiomeAutoMaterials/Sky"
BUILD = os.path.join(ROOT, "Build", "Sky")
HLSL = os.path.join(HERE, "hlsl")
EAL = mg.EAL
MEL = mg.MEL
C = mg.C


def textures():
    moon = mg.import_texture(os.path.join(BUILD, "T_MoonColor.png"), SKY, "T_MoonColor", True,
                             unreal.TextureCompressionSettings.TC_DEFAULT, True)
    milky = mg.import_texture(os.path.join(BUILD, "T_MilkyWay.png"), SKY, "T_MilkyWay", False,
                              unreal.TextureCompressionSettings.TC_DEFAULT, True)
    return moon, milky


def collection():
    path = f"{SKY}/MPC_BiomeSky"
    if EAL.does_asset_exist(path):
        mpc = unreal.load_asset(path)
    else:
        mpc = mg.TOOLS.create_asset("MPC_BiomeSky", SKY, unreal.MaterialParameterCollection, unreal.MaterialParameterCollectionFactoryNew())
    vectors = []
    for name, d in (("SunDirection", (0, 0, 1, 45)), ("MoonDirection", (0, 0, -1, 0.5)), ("Wind", (0, 0, 0, 0)),
                    ("SkyState", (1, 0.36, 0, 0)), ("Moonlight", (0, 1, 0, 0))):
        v = unreal.CollectionVectorParameter()
        v.set_editor_property("parameter_name", name)
        v.set_editor_property("default_value", unreal.LinearColor(*d))
        vectors.append(v)
    s = unreal.CollectionScalarParameter()
    s.set_editor_property("parameter_name", "SkyTime")
    s.set_editor_property("default_value", 0.0)
    mpc.set_editor_property("vector_parameters", vectors)
    mpc.set_editor_property("scalar_parameters", [s])
    EAL.save_asset(path, only_if_is_dirty=False)
    mg.log("MPC_BiomeSky saved")


def sky_material(moon, milky):
    path = f"{SKY}/M_BiomeSky"
    m = mg.fresh_material(SKY, "M_BiomeSky")
    m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    m.set_editor_property("two_sided", True)
    m.set_editor_property("is_sky", True)
    g = mg.Graph(m)
    view = g.node(unreal.MaterialExpressionSkyAtmosphereViewLuminance)
    sun = g.node(unreal.MaterialExpressionSkyAtmosphereLightDiskLuminance, light_index=0)
    cam = g.node(unreal.MaterialExpressionCameraVectorWS)
    code = star_catalog.hlsl_table() + mg.read(os.path.join(HLSL, "BiomeSkyStars.hlsl"))
    stars = g.custom("Stars, Milky Way, moon, meteors, aurora", code, C.CMOT_FLOAT3, [
        ("CamVec", cam),
        ("SkyNorth", g.vector("SkyNorth", (1, 0, 0, 0))),
        ("SkyEast", g.vector("SkyEast", (0, 1, 0, 0))),
        ("Frame", g.vector("SkyFrame", (0.292, 0.956, 0, 1))),
        ("Intensity", g.scalar("StarIntensity", 0.0)),
        ("Brightness", g.scalar("StarBrightness", 1.2)),
        ("Time", g.scalar("SkyTime", 0.0)),
        ("MoonDir", g.vector("MoonDir", (0, 0, -1, 0))),
        ("SunDir", g.vector("SunDir", (0, 0, 1, 0))),
        ("MoonDisk", g.scalar("MoonDisk", 0.0)),
        ("MoonScale", g.scalar("MoonScale", 5.0)),
        ("MoonTex", g.texture("MoonTex", moon, linear=False)),
        ("MilkyWay", g.texture("MilkyWayMap", milky, linear=True)),
        ("MilkyWayGain", g.scalar("MilkyWayGain", 0.3)),
        ("Aurora", g.scalar("Aurora", 0.0)),
        ("AuroraGain", g.scalar("AuroraGain", 2.0)),
        ("SkyGlow", g.scalar("SkyGlow", 0.0)),
        ("Meteors", g.scalar("Meteors", 1.0)),
    ])
    add = g.node(unreal.MaterialExpressionAdd)
    g.link(view, add, "A")
    g.link(sun, add, "B")
    # Under an overcast the light reaching the horizon has come through cloud: a neutral grey, not the clear air's tint.
    grey = g.custom("Overcast greys the sky", "float l = dot(Col, float3(0.2126, 0.7152, 0.0722)); "
                    "return lerp(Col, l * float3(0.96, 0.99, 1.04), saturate(Grey));", C.CMOT_FLOAT3,
                    [("Col", add), ("Grey", g.scalar("SkyGrey", 0.0))])
    total = g.node(unreal.MaterialExpressionAdd)
    g.link(grey, total, "A")
    g.link(stars, total, "B")
    g.out(total, unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mg.finish(m, path)


def cloud_material():
    path = f"{SKY}/M_BiomeClouds"
    shape = unreal.load_asset("/Engine/EngineSky/VolumetricClouds/VT_PerlinWorley_Balanced") or \
        unreal.load_asset("/Engine/EngineSky/VolumetricClouds/T_VolumeNoiseShape128")
    erosion = unreal.load_asset("/Engine/EngineSky/VolumetricClouds/T_VolumeNoiseErosion32")
    if not shape or not erosion:
        mg.warn("engine cloud volume textures not found (/Engine/EngineSky/VolumetricClouds)")
        return
    m = mg.fresh_material(SKY, "M_BiomeClouds")
    m.set_editor_property("material_domain", unreal.MaterialDomain.MD_VOLUME)
    m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_ADDITIVE)
    MEL.set_material_usage(m, unreal.MaterialUsage.MATUSAGE_VOLUMETRIC_CLOUD)
    g = mg.Graph(m)

    def volume(tex):
        st = unreal.MaterialSamplerType.SAMPLERTYPE_COLOR if tex.get_editor_property("srgb") else unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR
        return g.node(unreal.MaterialExpressionTextureObject, texture=tex, sampler_type=st)

    attr = g.node(unreal.MaterialExpressionCloudSampleAttribute)
    climate = g.vector("CloudClimate", (0.36, 0.12, 0.0, 0.22))
    dens = g.custom("Cloud density, occlusion and lightning", mg.read(os.path.join(HLSL, "BiomeClouds.hlsl")), C.CMOT_FLOAT3, [
        ("Pos", g.node(unreal.MaterialExpressionWorldPosition)),
        ("CameraWorld", g.node(unreal.MaterialExpressionCameraPositionWS)),
        ("Alt", (attr, "NormAltitudeInLayer")),
        ("Coverage", g.scalar("Coverage", 0.36)),
        ("Wind", g.vector("WindOffset", (0, 0, 1, 0))),
        ("Time", g.scalar("SkyTime", 0.0)),
        ("Shape", volume(shape)),
        ("Detail", volume(erosion)),
        ("State", g.vector("WeatherState", (7.0, 104729.0, 0.0, 1.0))),
        ("Climate", climate),
        ("Lightning", g.vector("CloudLightning", (0, 0, 0, 0))),
    ], outputs=[("Albedo", C.CMOT_FLOAT3)])
    ext = g.node(unreal.MaterialExpressionMultiply)
    g.link(g.mask(dens, r=True), ext, "A")
    g.link(g.scalar("Density", 0.018), ext, "B")
    g.out(ext, unreal.MaterialProperty.MP_SUBSURFACE_COLOR)   # Volume domain: extinction
    g.out((dens, "Albedo"), unreal.MaterialProperty.MP_BASE_COLOR)   # Volume domain: albedo
    g.out(g.mask(dens, g=True), unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
    flash = g.node(unreal.MaterialExpressionMultiply)
    g.link(g.mask(dens, b=True), flash, "A")
    g.link(g.node(unreal.MaterialExpressionConstant3Vector, constant=unreal.LinearColor(0.67, 0.79, 1.0, 1.0)), flash, "B")
    g.out(flash, unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    adv = g.node(unreal.MaterialExpressionVolumetricAdvancedMaterialOutput,
                 multi_scattering_approximation_octave_count=3, const_multi_scattering_contribution=0.55,
                 const_multi_scattering_occlusion=0.55, const_multi_scattering_eccentricity=0.5,
                 const_phase_g=0.80, const_phase_g2=-0.20, const_phase_blend=0.85,
                 ground_contribution=True, gray_scale_material=True, ray_march_volume_shadow=True)
    conservative = g.custom("Conservative cloud altitude bounds",
                            "float z = saturate(Alt) * 11200.0; float upper = min(11200.0, 4000.0 + Climate.y * 11000.0); "
                            "return (z <= upper || z >= 8800.0) ? 1.0 : 0.0;", C.CMOT_FLOAT1,
                            [("Alt", (attr, "NormAltitudeInLayer")), ("Climate", climate)])
    g.link(conservative, adv, "ConservativeDensity")
    mg.finish(m, path)


def precipitation_material():
    path = f"{SKY}/M_BiomePrecipitation"
    m = mg.fresh_material(SKY, "M_BiomePrecipitation")
    m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    m.set_editor_property("two_sided", True)
    m.set_editor_property("used_with_instanced_static_meshes", True)
    g = mg.Graph(m)
    uv = g.node(unreal.MaterialExpressionTextureCoordinate)
    pos = g.node(unreal.MaterialExpressionWorldPosition,
                 world_position_shader_offset=unreal.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
    snow = g.scalar("PrecipSnow", 0.0)
    fall = g.custom("Rain and snow placement", mg.read(os.path.join(HLSL, "BiomePrecipitation.hlsl")), C.CMOT_FLOAT3, [
        ("UV", uv), ("Pos", pos), ("Cam", g.node(unreal.MaterialExpressionCameraPositionWS)),
        ("Rand", g.node(unreal.MaterialExpressionPerInstanceRandom)),
        ("Time", g.scalar("PrecipTime", 0.0)), ("Density", g.scalar("PrecipDensity", 0.0)), ("Snow", snow),
        ("Wind", g.vector("PrecipWind", (0, 0, 0, 0))), ("Box", g.vector("PrecipBox", (1500, 1500, 900, 0))),
        ("Streak", g.scalar("PrecipStreak", 0.02)),
    ], outputs=[("Alpha", C.CMOT_FLOAT1)])
    g.out(fall, unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    interp = g.node(unreal.MaterialExpressionVertexInterpolator)
    if not MEL.connect_material_expressions(fall, "Alpha", interp, "VS"):
        g.link((fall, "Alpha"), interp, "")
    shape = g.custom("Streak or flake profile",
                     "float2 c = UV * 2.0 - 1.0; float rain = (1.0 - c.x * c.x) * (1.0 - c.y * c.y * c.y * c.y); "
                     "float flake = saturate(1.0 - dot(c, c)); return saturate(A) * lerp(rain, flake * flake, saturate(Snow));",
                     C.CMOT_FLOAT1, [("UV", uv), ("A", interp), ("Snow", snow)])
    g.out(shape, unreal.MaterialProperty.MP_OPACITY)
    g.out(g.vector("PrecipLight", (0.5, 0.55, 0.6, 0)), unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mg.finish(m, path)


def main():
    mg.ERRORS.clear()
    mg.ensure_dir(SKY)
    moon, milky = textures()
    collection()
    if moon and milky:
        sky_material(moon, milky)
    else:
        mg.warn("sky textures missing: run Tools/sky/fetch_sky_textures.py first")
    cloud_material()
    precipitation_material()
    mg.log(f"BAM SKY DONE errors={len(mg.ERRORS)}")
    for e in mg.ERRORS:
        mg.log(f"  error: {e}")


try:
    main()
except Exception:  # noqa
    import traceback
    unreal.log_error("[BAM] " + traceback.format_exc())
    mg.log("BAM SKY FAILED")
if os.environ.get("BAM_QUIT") == "1":
    unreal.SystemLibrary.quit_editor()
