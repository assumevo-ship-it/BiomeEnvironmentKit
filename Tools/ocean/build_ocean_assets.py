"""Build the BiomeOcean content inside the Unreal Editor.

    Editor:       Tools > Execute Python Script... > Tools/ocean/build_ocean_assets.py
    Command line: UnrealEditor-Cmd.exe <Project>.uproject -ExecutePythonScript="<path>/Tools/ocean/build_ocean_assets.py" -unattended

Creates /BiomeAutoMaterials/Ocean/M_BiomeOcean: a Single Layer Water material. The vertex shader displaces the
camera-following grid of ABiomeOcean with the shared wave model (Tools/ocean/hlsl/BiomeOceanCommon.hlsl, the twin of
Source/BiomeOcean/Private/BiomeOceanModel.cpp); the pixel shader takes its normal from the FFT slope textures, adds the
slopes too small to resolve as roughness (Cox & Munk), lays whitecaps where the crests are squeezed, breaker and swash
foam on the shore field, and colours the water by depth (sapphire offshore, turquoise over sand).
Environment: BAM_QUIT=1 closes the editor when done.
"""
import os
import sys

import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS_DIR = os.path.dirname(HERE)
sys.path.insert(0, TOOLS_DIR)
import importlib  # noqa: E402

import matgraph as mg  # noqa: E402

importlib.reload(mg)

OCEAN = "/BiomeAutoMaterials/Ocean"
HLSL = os.path.join(HERE, "hlsl")
C = mg.C
MEL = mg.MEL

# The helper node closes its own function, defines the shared functions at file scope and opens a dummy function for
# the generated closing brace. The material compiler emits the node once per shader stage and property chunk, so the
# definitions are guarded and each dummy function takes its name from __LINE__.
HELPERS_HEAD = "return 0;\n}\n#ifndef BIOME_OCEAN_COMMON\n#define BIOME_OCEAN_COMMON 1\n"
HELPERS_TAIL = ("\n#define BO_CAT2(a, b) a##b\n#define BO_CAT(a, b) BO_CAT2(a, b)\n#endif\n"
                "float BO_CAT(BO_HelpersEnd, __LINE__)()\n{\n")

SEA_SETUP = r"""
BOSea sea;
sea.W[0] = W0; sea.W[1] = W1; sea.W[2] = W2; sea.W[3] = W3; sea.W[4] = W4;
sea.Phase[0] = PhA.x; sea.Phase[1] = PhA.y; sea.Phase[2] = PhA.z; sea.Phase[3] = PhA.w; sea.Phase[4] = PhB.x;
sea.Q = PhB.y; sea.RunUp = PhB.w; sea.WindVar = SeaInfo.y; sea.Seed = uint(SeaInfo.x + 0.5); sea.Time = Time;
"""

VERTEX = SEA_SETUP + r"""
float2 xy = Pos.xy;
float4 shore = BO_Shore(xy, ShoreTex, ShoreTexSampler, ShoreBounds, HasShore);
float3 d = BO_Swells(sea, shore, xy);
// The wind sea, filtered to the grid's spacing so far vertices do not alias the short waves.
float dist = length(Pos.xy - Cam.xy);
float spacing = GridShape.y + dist * max(GridShape.x - 1.0, 0.0);
float amp = BO_WindSeaAmp(sea, shore);
if (amp > 0.0)
{
    float3 w = BO_Cascade(xy, A0, A0Sampler, Info0, max(0.0, log2(spacing / max(Info0.z, 1.0))));
    w += BO_Cascade(xy, A1, A1Sampler, Info1, max(0.0, log2(spacing / max(Info1.z, 1.0))));
    w += BO_Cascade(xy, A2, A2Sampler, Info2, max(0.0, log2(spacing / max(Info2.z, 1.0))));
    d += w * amp;
}
float2 foamCue;
d += BO_CoastalSurf(sea, shore, xy, foamCue);
return d;
"""

PIXEL = SEA_SETUP + r"""
float2 xy = Pos.xy;
float4 shore = BO_Shore(xy, ShoreTex, ShoreTexSampler, ShoreBounds, HasShore);
float amp = BO_WindSeaAmp(sea, shore);
// Height gradient of the swells (Gerstner normal) and of the wind sea (FFT slopes, squeezed by the horizontal displacement).
float2 grad = 0; float squeeze = 0;
float openAtt = BO_Smooth(0.15, 1.2, shore.y) * BO_Smooth(0.0, 5.0, shore.x);
[unroll] for (int i = 0; i < 5; i++)
{
    float4 w = sea.W[i];
    float th = w.z * dot(w.xy, xy) - sqrt(BO_G * w.z) * sea.Time + sea.Phase[i];
    float a = w.w * openAtt * (i < 3 ? 1.0 - BO_SurfBlend(shore) : 1.0);
    grad += w.xy * w.z * a * cos(th);
    squeeze += sea.Q * w.z * a * sin(th);
}
float3 s0 = BO_CascadeSlope(xy, B0, B0Sampler, C0, C0Sampler, Info0);
float3 s1 = BO_CascadeSlope(xy, B1, B1Sampler, C1, C1Sampler, Info1);
float3 s2 = BO_CascadeSlope(xy, B2, B2Sampler, C2, C2Sampler, Info2);
// Far off, the per-pixel short waves average out into roughness: fade their normals with distance.
float dist = length(Pos.xyz - Cam.xyz);
float near2 = 1.0 - BO_Smooth(4000.0, 20000.0, dist);
float near1 = 1.0 - BO_Smooth(30000.0, 160000.0, dist);
float2 fftGrad = (s0.xy + s1.xy * near1 + s2.xy * near2) * amp;
float jac = 1.0 - saturate(max(s0.z + s1.z, 0.0) * amp * 0.5);
grad += fftGrad / max(jac, 0.4);
float3 n = normalize(float3(-grad.x, -grad.y, max(1.0 - squeeze, 0.25)));

// Roughness: the slopes no texel resolves (Cox & Munk mean square slope for this wind, minus what is drawn).
float U = SeaWind.z;
float totalMSS = 0.003 + 0.00512 * U;
float drawn = ResolvedVar * (0.35 + 0.65 * near2);
float unresolved = max(totalMSS - drawn, 0.0) + (1.0 - near1) * ResolvedVar * 0.5;
Rough = clamp(sqrt(Rough0 * Rough0 + unresolved * 4.0), 0.02, 0.32);

// Whitecaps: the foam the CPU laid on the cascades' most squeezed crests (A.w), torn into lace by a value noise.
float fA0 = Texture2DSample(A0, A0Sampler, float2(cos(Info0.y) * xy.x + sin(Info0.y) * xy.y, -sin(Info0.y) * xy.x + cos(Info0.y) * xy.y) / Info0.x).w * Info0.w;
float fA1 = Texture2DSample(A1, A1Sampler, float2(cos(Info1.y) * xy.x + sin(Info1.y) * xy.y, -sin(Info1.y) * xy.x + cos(Info1.y) * xy.y) / Info1.x).w * Info1.w;
float cap = saturate(fA0 + fA1) * amp * saturate(WhiteScale);
float lace = BO_ValueNoise(xy / 90.0, 11u) * 0.55 + BO_ValueNoise(xy / 31.0, 23u) * 0.3 + BO_ValueNoise(xy / 11.0, 37u) * 0.15;
float caps = BO_Smooth(1.0 - cap, 1.0 - cap + 0.22, lace) * BO_Smooth(0.02, 0.15, cap);
// Surf: broken crests rolling in and the swash on the sand.
float2 cue;
BO_CoastalSurf(sea, shore, xy, cue);
float surf = saturate(cue.x * (0.6 + 0.6 * lace) + cue.y * BO_Smooth(0.35, 0.75, lace)) * ShoreFoam;
Foam = saturate(max(caps, surf));
// Shallow water over sand (from the shore field) turns turquoise; the deep sea stays sapphire.
Shallow = HasShore > 0.5 ? (1.0 - BO_Smooth(4.0, 22.0, shore.y)) * BO_Smooth(-1.0, 2.0, shore.x) : 0.0;
return n;
"""


def build():
    path = f"{OCEAN}/M_BiomeOcean"
    m = mg.fresh_material(OCEAN, "M_BiomeOcean")
    m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_SINGLE_LAYER_WATER)
    m.set_editor_property("tangent_space_normal", False)
    m.set_editor_property("two_sided", False)
    try:
        m.set_editor_property("used_with_static_lighting", False)
    except Exception:  # noqa
        pass
    g = mg.Graph(m)
    black = unreal.load_asset("/Engine/EngineResources/Black")
    helpers = g.custom("BiomeOcean shared wave model (global functions)",
                       HELPERS_HEAD + mg.read(os.path.join(HLSL, "BiomeOceanCommon.hlsl")) + HELPERS_TAIL,
                       C.CMOT_FLOAT1, [])
    rest = g.node(unreal.MaterialExpressionWorldPosition,
                  world_position_shader_offset=unreal.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
    cam = g.node(unreal.MaterialExpressionCameraPositionWS)
    common = [("H", helpers), ("Pos", rest), ("Cam", cam)]
    for i in range(5):
        common.append((f"W{i}", g.vector(f"Wave{i}", (1, 0, 0, 0), "Waves")))
    common += [("PhA", g.vector("WavePhaseA", (0, 0, 0, 0), "Waves")), ("PhB", g.vector("WavePhaseB", (0, 0.6, 0.6, 35), "Waves")),
               ("Time", g.scalar("WaveTime", 0.0, "Waves")), ("SeaInfo", g.vector("SeaInfo", (0, 0, 1, 0), "Waves")),
               ("ShoreTex", g.texture("ShoreField", black, True, "Shore")),
               ("ShoreBounds", g.vector("ShoreBounds", (0, 0, 1, 0), "Shore")), ("HasShore", g.scalar("HasShore", 0.0, "Shore"))]
    infos = [(f"Info{i}", g.vector(f"WindInfo{i}", (1, 0, 1, 0), "Wind sea")) for i in range(3)]
    tex_a = [(f"A{i}", g.texture(f"WindA{i}", black, True, "Wind sea")) for i in range(3)]
    tex_b = [(f"B{i}", g.texture(f"WindB{i}", black, True, "Wind sea")) for i in range(3)]
    tex_c = [(f"C{i}", g.texture(f"WindC{i}", black, True, "Wind sea")) for i in range(3)]

    vertex = g.custom("Ocean displacement", VERTEX, C.CMOT_FLOAT3,
                      common + [("GridShape", g.vector("GridShape", (1.03, 30, 256, 0), "Waves"))] + tex_a + infos)
    g.out(vertex, unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)

    pixel = g.custom("Ocean shading", PIXEL, C.CMOT_FLOAT3,
                     common + tex_a[:2] + tex_b + tex_c + infos +
                     [("SeaWind", g.vector("SeaWind", (1, 0, 8, 0.02), "Waves")),
                      ("ResolvedVar", g.scalar("ResolvedSlopeVar", 0.0, "Wind sea")),
                      ("Rough0", g.scalar("WaterRoughness", 0.06, "Look")),
                      ("WhiteScale", g.scalar("WhitecapVisibility", 1.0, "Look")),
                      ("ShoreFoam", g.scalar("ShoreFoam", 1.0, "Shore"))],
                     outputs=[("Rough", C.CMOT_FLOAT1), ("Foam", C.CMOT_FLOAT1), ("Shallow", C.CMOT_FLOAT1)])
    g.out(pixel, unreal.MaterialProperty.MP_NORMAL)

    foam_color = g.mask(g.vector("FoamColor", (0.85, 0.88, 0.87, 0), "Look"), r=True, g=True, b=True)
    base = g.node(unreal.MaterialExpressionMultiply)
    g.link(foam_color, base, "A")
    g.link((pixel, "Foam"), base, "B")
    g.out(base, unreal.MaterialProperty.MP_BASE_COLOR)
    rough = g.node(unreal.MaterialExpressionLinearInterpolate)
    g.link((pixel, "Rough"), rough, "A")
    g.link(g.const(0.7), rough, "B")
    g.link((pixel, "Foam"), rough, "Alpha")
    g.out(rough, unreal.MaterialProperty.MP_ROUGHNESS)
    g.out(g.const(0.255), unreal.MaterialProperty.MP_SPECULAR)
    # Single Layer Water: Opacity blends towards an opaque surface lit by the base colour (the foam).
    g.out((pixel, "Foam"), unreal.MaterialProperty.MP_OPACITY)

    def mix(a, b):
        e = g.node(unreal.MaterialExpressionLinearInterpolate)
        g.link(g.mask(g.vector(a[0], a[1], "Look"), r=True, g=True, b=True), e, "A")
        g.link(g.mask(g.vector(b[0], b[1], "Look"), r=True, g=True, b=True), e, "B")
        g.link((pixel, "Shallow"), e, "Alpha")
        return e

    absorb = mix(("DeepAbsorption", (0.45, 0.065, 0.022, 0)), ("ShallowAbsorption", (0.30, 0.045, 0.028, 0)))
    scatter = mix(("DeepScattering", (0.0006, 0.0014, 0.0025, 0)), ("ShallowScattering", (0.005, 0.026, 0.022, 0)))
    slw = g.node(unreal.MaterialExpressionSingleLayerWaterMaterialOutput)
    g.link(scatter, slw, "ScatteringCoefficients")
    g.link(absorb, slw, "AbsorptionCoefficients")
    g.link(g.const(0.1), slw, "PhaseG")
    mg.finish(m, path)


def underwater():
    """M_BiomeUnderwater: the view from below the waves. Every pixel loses its light to the water between it and the eye
    (per channel, so red goes in a few metres and blue lasts) and gains the water's own glow in its place. ABiomeOcean
    blends it in when the camera dips under the surface and sets the glow from the sun's height and the camera's depth."""
    m = mg.fresh_material(OCEAN, "M_BiomeUnderwater")
    m.set_editor_property("material_domain", unreal.MaterialDomain.MD_POST_PROCESS)
    m.set_editor_property("blendable_location", unreal.BlendableLocation.BL_SCENE_COLOR_BEFORE_DOF)
    g = mg.Graph(m)
    scene = g.node(unreal.MaterialExpressionSceneTexture, scene_texture_id=unreal.SceneTextureId.PPI_POST_PROCESS_INPUT0)
    depth = g.node(unreal.MaterialExpressionSceneTexture, scene_texture_id=unreal.SceneTextureId.PPI_SCENE_DEPTH)
    fog = g.custom("Underwater extinction", "float metres = min(max(Depth.r, 0.0) * 0.01, 300.0); "
                   "float3 t = exp(-Extinction.rgb * metres); "
                   "return Scene.rgb * t + WaterLight.rgb * (1.0 - t);", C.CMOT_FLOAT3,
                   [("Scene", scene), ("Depth", depth), ("Extinction", g.vector("Extinction", (0.40, 0.075, 0.045, 0))),
                    ("WaterLight", g.vector("WaterLight", (0.10, 0.42, 0.52, 0)))])
    g.out(fog, unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mg.finish(m, f"{OCEAN}/M_BiomeUnderwater")


def main():
    mg.ERRORS.clear()
    mg.ensure_dir(OCEAN)
    build()
    underwater()
    mg.log(f"BAM OCEAN DONE errors={len(mg.ERRORS)}")
    for e in mg.ERRORS:
        mg.log(f"  error: {e}")


try:
    main()
except Exception:  # noqa
    import traceback
    unreal.log_error("[BAM] " + traceback.format_exc())
    mg.log("BAM OCEAN FAILED")
if os.environ.get("BAM_QUIT") == "1":
    unreal.SystemLibrary.quit_editor()
