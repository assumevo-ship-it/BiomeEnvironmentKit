"""Build the marine life inside the Unreal Editor (run Tools/marine/marine_life.py and marine_fauna.py first: they write
the procedural meshes to Build/Marine; and Tools/build_materials.py, whose rock_face texture gives rock and coral grain).

    Editor:       Tools > Execute Python Script... > Tools/marine/build_marine_assets.py
    Command line: UnrealEditor-Cmd.exe <Project>.uproject -ExecutePythonScript="<path>/Tools/marine/build_marine_assets.py" -unattended

Creates under /BiomeAutoMaterials/Marine:
    M_SeaLife + MI_Sea_<Species>      corals, sponges, sea grass, kelp, algae, rock, shells, crabs: colour from the vertex
                                      colours, a triplanar rock grain close to, and the surge's to-and-fro sway (WPO);
                                      rock that reaches the surface gets a dark wet band and weed at sea level (world Z 0)
    M_SeaCreature, M_SeaJelly          everything that swims: fish patterns, eyes, gills and fins drawn from UV0; the
                                      swimming (tail beat, flukes, ray wings, turtle flippers, jellyfish pulse) is vertex
                                      animation, so they move in the editor with no Blueprint and no skeleton
    SM_Sea_<Species>                   104 meshes, real sizes (1 unit = 1 cm); Nanite on the still ones
Fish placed as instanced meshes swim round an ellipse from per-instance custom data (D0 radius A cm, D1 radius B cm,
D2 angular speed rad/s, D3 phase, D4 heading rad) when their material's Travel is 1; Tools/assets/scatter_biome.py fills
it in. Big fish (Travel 0) beat their tails in place: move them yourself (a spline, a Blueprint) if they should cruise.
Environment: BAM_QUIT=1 closes the editor when done.
"""
import glob
import os
import sys

import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS_DIR = os.path.dirname(HERE)
ROOT = os.path.dirname(TOOLS_DIR)
sys.path.insert(0, TOOLS_DIR)
import importlib  # noqa: E402

import matgraph as mg  # noqa: E402

importlib.reload(mg)

MARINE = "/BiomeAutoMaterials/Marine"
SRC = os.path.join(ROOT, "Build", "Marine")
GRAIN_TEX = "/BiomeAutoMaterials/Textures/rock_face/T_rock_face"
EAL = mg.EAL
MEL = mg.MEL
MP = unreal.MaterialProperty
C = mg.C

# ColorA, ColorB (the vertex colour's blue mixes them), sway in cm at a free tip. Linear colours as seen in shallow water:
# reef corals are browns, ochres and olive from their algae; the bright ones are the exceptions.
LOOKS = dict(
    BrainCoral=((.20, .19, .075), (.33, .26, .12), 0),
    BarrelSponge=((.28, .09, .06), (.42, .16, .1), 0),
    TubeSponge=((.5, .38, .04), (.2, .05, .24), 0),
    FireCoral=((.42, .31, .08), (.72, .66, .5), 0),
    FingerCoral=((.36, .3, .18), (.3, .2, .28), 0),
    SeaPlume=((.3, .22, .18), (.38, .16, .3), 10),
    BoulderCoral=((.26, .20, .09), (.17, .20, .085), 0),
    TableCoral=((.30, .22, .13), (.62, .56, .42), 0),
    Staghorn=((.36, .25, .13), (.74, .67, .50), 0),
    SeaFan=((.20, .045, .20), (.36, .09, .28), 7),
    Sponges=((.42, .19, .05), (.19, .055, .21), 0),
    SeaGrass=((.05, .13, .028), (.15, .17, .05), 9),
    WeedBush=((.17, .115, .028), (.27, .19, .04), 14),
    Kelp=((.11, .09, .02), (.21, .16, .03), 55),
    Raft=((.30, .20, .04), (.43, .31, .05), 0),
    ReefRock=((.15, .14, .11), (.23, .19, .13), 0),
    Urchin=((.008, .008, .012), (.012, .01, .016), 0),
    Starfish=((.44, .10, .035), (.50, .14, .05), 0),
    Elkhorn=((.40, .27, .12), (.70, .60, .40), 0),
    PillarCoral=((.42, .36, .2), (.5, .44, .26), 0),
    LettuceCoral=((.24, .16, .07), (.5, .42, .24), 0),
    SeaRods=((.3, .16, .1), (.4, .24, .13), 8),
    SeaWhips=((.42, .1, .22), (.5, .3, .05), 16),
    Anemone=((.5, .42, .32), (.26, .05, .3), 5),
    RopeSponge=((.4, .1, .05), (.22, .05, .22), 0),
    ManateeGrass=((.08, .2, .035), (.2, .24, .06), 9),
    Halimeda=((.14, .28, .08), (.42, .46, .28), 2),
    Padina=((.22, .15, .06), (.6, .58, .5), 2),
    Caulerpa=((.06, .22, .03), (.12, .3, .05), 4),
    Dictyota=((.16, .1, .04), (.08, .2, .22), 4),
    Udotea=((.1, .24, .07), (.32, .38, .24), 2),
    ShavingBrush=((.12, .24, .06), (.46, .48, .34), 2),
    SeaLettuce=((.13, .36, .05), (.22, .46, .06), 7),
    RedAlgae=((.2, .03, .04), (.32, .07, .06), 3),
    BullKelp=((.12, .1, .025), (.22, .17, .035), 70),
    SeaCucumber=((.028, .02, .018), (.1, .07, .05), 0),
    Conch=((.42, .32, .2), (.7, .32, .25), 0),
    Mussels=((.018, .02, .035), (.34, .32, .27), 0),
    FeatherWorms=((.5, .24, .08), (.1, .2, .4), 2),
    SandDollar=((.5, .47, .38), (.6, .57, .47), 0),
    Shells=((.44, .38, .3), (.62, .56, .46), 0),
    Crab=((.24, .07, .03), (.32, .11, .04), 1),
    # Ghost crab: dry-sand ivory with grey-brown speckle; B = 1 the dark eye clubs.
    GhostCrab=((.52, .47, .38), (.03, .025, .02), 0),
    GhostCrabLegL=((.55, .5, .41), (.6, .56, .48), 0),
    GhostCrabLegR=((.55, .5, .41), (.6, .56, .48), 0),
    Lobster=((.22, .11, .05), (.44, .3, .12), 2),
    Boulder=((.11, .105, .09), (.18, .155, .115), 0),
    Cobbles=((.15, .14, .12), (.27, .25, .2), 0),
    Pinnacle=((.13, .12, .095), (.21, .18, .125), 0),
    Skerry=((.1, .095, .085), (.17, .16, .13), 0),
    ManOWar=((.2, .08, .4), (.08, .22, .56), 3),
)
DEAD = ((.36, .35, .31), (.13, .14, .12), 0)
# Stone that can reach the surface: dry above, a black wet band and weed at the tide.
# How much photographed grain (0-1) and its tile in metres: rocks the most, stony corals finer, soft things none.
GRAIN = dict(ReefRock=(1.0, 1.4), Boulder=(1.0, 1.6), Cobbles=(.9, .7), Pinnacle=(1.0, 2.5), Skerry=(1.0, 3.0),
             BrainCoral=(.35, .5), BoulderCoral=(.45, .6), TableCoral=(.35, .5), Elkhorn=(.4, .6), PillarCoral=(.4, .5), LettuceCoral=(.35, .45),
             Staghorn=(.3, .4), FingerCoral=(.35, .35), FireCoral=(.25, .4), BarrelSponge=(.5, .5), Dead=(.6, .8))
TIDAL = ("Skerry", "Boulder", "ReefRock", "Pinnacle", "Mussels")
COLLIDING = ("Pinnacle", "Skerry")
SEE_THROUGH = ("Jellyfish", "BoxJellyfish", "SeaNettle", "LionsMane")

SEA_HLSL = r"""
struct LK {
    float H(float3 p) { p = frac(p*.3183099+.1); p *= 17.0; return frac(p.x*p.y*p.z*(p.x+p.y+p.z)); }
    float N(float3 x) {
        float3 i = floor(x), f = frac(x); f = f*f*(3.0-2.0*f);
        return lerp(lerp(lerp(H(i), H(i+float3(1,0,0)), f.x), lerp(H(i+float3(0,1,0)), H(i+float3(1,1,0)), f.x), f.y),
                    lerp(lerp(H(i+float3(0,0,1)), H(i+float3(1,0,1)), f.x), lerp(H(i+float3(0,1,1)), H(i+float3(1,1,1)), f.x), f.y), f.z);
    }
};
LK k;
float3 p = WP/100.0;
float dist = length(Cam-WP)/100.0;
float3 c = lerp(A.rgb, B.rgb, VC.b);
// Mottling at a hand's breadth; each colony its own shade.
c *= lerp(.72, 1.22, k.N(p/.13))*lerp(.8, 1.18, Rand);
c *= lerp(1.0, lerp(.7, 1.15, k.N(p/.45+4.0)), .7);
// Polyps: a fine dark stipple, gone before it can shimmer.
float polyp = k.N(p/.008)*VCA*smoothstep(4.0, 1.2, dist);
c *= 1.0-.42*polyp;
c *= lerp(.42, 1.0, VC.g);
Rough = lerp(.62, .88, k.N(p/.3));
if (Tidal > .5 && p.z > -1.4) {
    float tide = p.z+.35*(k.N(float3(p.xy/2.2, 0.))-.5);
    float wetBand = 1.0-smoothstep(.1, 1.25, tide);
    c = lerp(c*lerp(1.5, .95, k.N(p/.6)), c*.22+float3(.008,.012,.008), wetBand);
    float weed = (1.0-smoothstep(.0, .45, tide))*smoothstep(.45, .62, k.N(p/.25));
    c = lerp(c, float3(.035, .085, .02), weed);
    Rough = lerp(lerp(.8, .92, k.N(p/.2)), .25, wetBand*(1.0-.6*weed));
}
return c;
"""

# Close to, rock and coral are not smooth paint: a triplanar grain from the CC0 Poly Haven photograph rock_face (the biome
# library's own T_rock_face_CH / _NRA), tinted by the instance's own colour. Grain 0 (plants, soft things) skips it.
GRAIN_HLSL = r"""
float3 n = normalize(N);
float3 w = pow(abs(n), 4.0);
w /= (w.x+w.y+w.z);
float3 p = WP/(100.0*max(Tile, .05));
float3 col = 0, r = 0;
float2 t;
float3 tn;
if (w.x > .02) { col += Texture2DSample(D, DSampler, p.zy).rgb*w.x; t = Texture2DSample(Nm, NmSampler, p.zy).xy*2.0-1.0; tn = float3(t+n.zy, abs(sqrt(saturate(1.0-dot(t, t))))*n.x); r += tn.zyx*w.x; }
if (w.y > .02) { col += Texture2DSample(D, DSampler, p.xz).rgb*w.y; t = Texture2DSample(Nm, NmSampler, p.xz).xy*2.0-1.0; tn = float3(t+n.xz, abs(sqrt(saturate(1.0-dot(t, t))))*n.y); r += tn.xzy*w.y; }
if (w.z > .02) { col += Texture2DSample(D, DSampler, p.xy).rgb*w.z; t = Texture2DSample(Nm, NmSampler, p.xy).xy*2.0-1.0; tn = float3(t+n.xy, abs(sqrt(saturate(1.0-dot(t, t))))*n.z); r += tn*w.z; }
float luma = dot(col, float3(.3, .59, .11));
// Fades with distance: far off the grain would only shimmer.
float near = Grain*smoothstep(28.0, 6.0, length(Cam-WP)/100.0);
Shade = lerp(1.0, clamp(luma*2.4, .45, 1.5), near*.75);
return normalize(lerp(n, normalize(r), near));
"""

SWAY_HLSL = r"""
// The surge goes to and fro, slowly, the same way for neighbours; each plant a little out of step, tips later than roots.
float t = Time;
float ph = dot(WP.xy, float2(.0031, .0043))+Rand*1.4;
float w = VC.r*VC.r;
float lag = VC.r*1.1;
float a = sin(t*.85+ph-lag)+.45*sin(t*1.93+ph*1.7-lag*1.6)+.2*sin(t*3.7+ph*3.0-lag*2.2);
float b = cos(t*.61+ph*.8-lag)+.3*sin(t*1.51+ph*2.1);
return float3(float2(.82, .57)*a+float2(-.57, .82)*b*.55, -.12*abs(a))*Sway*w;
"""

# ---- everything that swims, one master. Fish patterns are drawn from UV0 (U along the body, V from belly -1 to back +1).
CREATURE_BODY_HLSL = r"""
struct LK {
    float H(float3 p) { p = frac(p*.3183099+.1); p *= 17.0; return frac(p.x*p.y*p.z*(p.x+p.y+p.z)); }
    float N(float3 x) {
        float3 i = floor(x), f = frac(x); f = f*f*(3.0-2.0*f);
        return lerp(lerp(lerp(H(i), H(i+float3(1,0,0)), f.x), lerp(H(i+float3(0,1,0)), H(i+float3(1,1,0)), f.x), f.y),
                    lerp(lerp(H(i+float3(0,0,1)), H(i+float3(1,0,1)), f.x), lerp(H(i+float3(0,1,1)), H(i+float3(1,1,1)), f.x), f.y), f.z);
    }
};
LK k;
float U = UV.x, V = UV.y;
float isFin = VC.b;
float3 c = lerp(Belly.rgb, Back.rgb, smoothstep(-.42, .38, V));
// Vertical bands, like a sergeant major's or a grouper's.
float band = smoothstep(-.25, .25, sin(U*BandFreq*6.2832+.8+.5*sin(V*2.0)));
c = lerp(c, Accent.rgb, BandAmt*band*step(U, .94));
// Lengthwise stripes, like a grunt's.
float stripe = smoothstep(-.2, .2, sin((V+.13*sin(U*5.0))*StripeFreq*6.2832));
c = lerp(c, Accent2.rgb, StripeAmt*stripe);
// Spots and blotches, large or small.
float n = k.N(float3(U*SpotFreq, V*SpotFreq*.42, Rand*9.0));
float n2 = k.N(float3(U*SpotFreq*2.3, V*SpotFreq, Rand*5.0+3.0));
float spot = smoothstep(.56, .62, n*.75+n2*.25);
c = lerp(c, Accent.rgb, SpotAmt*spot);
// A turtle's carapace (Scutes 1): five vertebral scutes down the middle, four costal pairs, a ring of small marginals,
// each with pale seams and dark streaks radiating from its growth centre, as on a green turtle. On the carapace only
// (V > .3: the mesh gives V = 1 - .6 |across|).
if (Scutes > .5 && isFin < .5 && V > .3 && U > .06 && U < .98) {
    float a = saturate((1.0-V)/.6);
    float u = saturate((U-.06)/.88);
    float cells = a < .3 ? 5.0 : (a < .84 ? 4.0 : 12.0);
    float row0 = a < .3 ? 0.0 : (a < .84 ? .3 : .84), row1 = a < .3 ? .3 : (a < .84 ? .84 : 1.0);
    float cu = u*cells+(a < .3 ? 0.0 : (a < .84 ? .5 : .25));
    float fu = frac(cu), fa = (a-row0)/(row1-row0);
    float seam = 1.0-smoothstep(.015, .045, min(min(fu, 1.0-fu), min(fa, 1.0-fa)*(row1-row0)*cells*1.1));
    float2 cc = float2(fu-.5, (fa-.5)*.8);
    float ang = atan2(cc.y, cc.x);
    float cid = floor(cu)+row0*31.0;
    float streak = smoothstep(.45, .8, k.N(float3(ang*3.0, length(cc)*2.0, cid*1.7)))*smoothstep(.05, .35, length(cc));
    float3 amber = float3(.32, .2, .06), dark = float3(.06, .045, .025);
    float3 shell = lerp(lerp(Back.rgb, amber, .55*k.N(float3(cid*2.3, 0, 1))), dark, streak*.85);
    c = lerp(shell, float3(.42, .36, .2), seam*.7);
}
// Species markings drawn from U (0 snout .. 1 tail root) and V (-1 belly .. +1 back), from photographs:
// Pattern 1 orca: white chin and belly, the white lobe up the flank behind the dorsal, the white oval eye patch above and
// behind the eye, the grey saddle behind the dorsal fin. Pattern 2 dolphin: a darker cape along the back from the melon
// to past the dorsal. Pattern 3 great white: a sharp, ragged line between grey back and white belly.
if (isFin < .5) {
    if (Pattern > .5 && Pattern < 1.5) {
        float belly = step(V, -.28+.06*sin(U*20.0))*step(.035, U)*step(U, .64);
        float lobe = step(.5, U)*step(U, .83)*step(V, .08-6.0*(U-.665)*(U-.665)-.0);
        float chin = step(U, .07)*step(V, -.02);
        float2 e = float2((U-.15)/.055, (abs(V)-.47)/.13);
        float patch = 1.0-smoothstep(.85, 1.0, length(e));
        float white = saturate(belly+lobe+chin+patch);
        c = lerp(Back.rgb, Belly.rgb, white);
        float saddle = smoothstep(.36, .4, U)*smoothstep(.56, .5, U)*smoothstep(.62, .82, V);
        c = lerp(c, float3(.16, .16, .17), saddle*.85);
    } else if (Pattern > 1.5 && Pattern < 2.5) {
        float cape = smoothstep(.45, .7, V+.12*sin(U*9.0))*smoothstep(.06, .12, U)*smoothstep(.7, .55, U);
        c = lerp(c, Back.rgb*.55, cape);
    } else if (Pattern > 2.5) {
        float edge = -.1+.07*sin(U*31.0)+.05*sin(U*67.0+1.3)+.04*(k.N(float3(U*40.0, V*6.0, 3.0))-.5);
        c = lerp(Belly.rgb, Back.rgb, smoothstep(edge-.015, edge+.015, V));
    }
    // A shark's five gill slits, curved lines in a row on each flank behind the eye.
    if (Gills > .5) {
        float g = 0.0;
        for (int i = 0; i < 5; i++) {
            float u0 = EyeU+.07+.016*i+.012*V;
            g = max(g, smoothstep(.0035, .001, abs(U-u0))*step(-.35, V)*step(V, .42-.04*i));
        }
        c *= 1.0-.55*g;
    }
}
// Scales or scutes: a small net that only shows close to.
float2 sc = float2(U*ScaleFreq, V*ScaleFreq*.34);
sc.y += .5*floor(sc.x);
float scales = smoothstep(.05, .3, abs(frac(sc.x)-.5))*smoothstep(.05, .3, abs(frac(sc.y)-.5));
c *= lerp(1.0, lerp(.62, 1.06, scales), ScaleAmt);
// A coloured head (the yellow of a queen angel, the green of a parrotfish's beak).
c = lerp(c, Accent2.rgb, HeadAmt*smoothstep(HeadU+.025, HeadU-.025, U));
// The gill's edge, a lateral line and the dark of the mouth: what makes a shape read as a fish from a metre off.
if (isFin < .5 && EyeR > 0.0) {
    float gillU = EyeU+.1+.03*V*V;
    c *= 1.0-.42*smoothstep(.012, .002, abs(U-gillU))*step(abs(V), .85);
    c *= 1.0-.16*smoothstep(.022, .006, abs(V-.3-.1*U))*step(gillU, U);
    c *= 1.0-.75*smoothstep(.022, .006, U)*smoothstep(.34, .1, abs(V+.12));
}
// Fins forward of PaleFinU wear the belly's colour: a North Atlantic humpback's long white flippers.
// V on a fin is its distance from the root (0) to the rim (1): fins darken and thin towards the edge, with faint rays
// across the length on bony fish only (ScaleAmt > 0). The old sine of U and V drew concentric squares on a shark's fin.
if (isFin > .5) { c = lerp(c, lerp(Fin.rgb, Belly.rgb, step(U, PaleFinU)), .85); c *= lerp(1.0, .78, smoothstep(.55, 1.0, V)); c *= lerp(1.0, lerp(.86, 1.03, .5+.5*sin(U*110.0)), saturate(ScaleAmt)*smoothstep(.1, .4, V)); }
// Fin tips: black on a blacktip, mottled white on an oceanic whitetip (Accent2), from 70 % out to the rim.
if (isFin > .5 && FinTip > 0.0) {
    float tip = smoothstep(.62, .82, V+.08*(k.N(float3(U*60.0, V*20.0, 7.0))-.5));
    c = lerp(c, Accent2.rgb, FinTip*tip);
}
// The eye: a dark pupil in a ring, on both flanks.
float3 eyeCol = c;
float eye = 0.0;
if (isFin < .5 && EyeR > 0.0) {
    float d = length(float2((U-EyeU)*Aspect, abs(V)-EyeV));
    eyeCol = lerp(lerp(float3(.55, .42, .12), c, smoothstep(EyeR*1.0, EyeR*1.35, d)), float3(.004,.004,.006), smoothstep(EyeR*.72, EyeR*.62, d));
    eye = smoothstep(EyeR*1.35, EyeR*1.0, d);
}
c = lerp(c, eyeCol, eye);
c *= lerp(.55, 1.0, VC.g)*lerp(.9, 1.1, Rand);
Rough = lerp(RoughBase, .08, eye);
OutMetal = MetalBase*(1.0-isFin)*(.6+.4*smoothstep(.2, -.5, V));
return c;
"""

CREATURE_LOCAL_HLSL = r"""
// The swimming, in the mesh's own centimetres: bent, turned along the way it travels, then handed to the local->world
// transform, so that the instance's scale and heading apply. Travel: 1 an ellipse (custom data), 0 C++ moves the instance.
float t = Time+Rand*97.0;
float w = BeatFreq*(.85+.3*frac(Rand*5.13));
float3 q = P;
if (Mode < .5) {           // a fish: the wave runs back along the body, growing to the tail; it bursts and glides
    float glide = .5+.5*sin(t*(.27+.2*frac(Rand*2.9)));
    float phase = t*w-1.4*cos(t*.41)-VC.r*4.2;
    q.y += BeatAmp*lerp(.35, 1.1, glide)*VC.r*VC.r*sin(phase);
    q.y += BeatAmp*.08*sin(t*w*.5);
    // Paired fins row, slower than the tail and most when it is gliding.
    q.z += BeatAmp*lerp(1.5, .55, glide)*VCA*VC.b*sin(t*w*.42+sign(P.y)*.6);
} else if (Mode < 1.5) {   // a whale's or a dolphin's flukes, up and down
    q.z += BeatAmp*VC.r*VC.r*sin(t*w-VC.r*3.4);
} else if (Mode < 2.5) {   // a ray: the wave goes out along the wing; the whip of a tail trails
    float s = VC.r;
    float whip = VC.b > .5 ? .14 : 1.0;
    q.z += whip*BeatAmp*s*s*sin(t*w-s*1.8)+BeatAmp*.06*sin(t*w+P.x*.012);
    // The wing's edge ripples behind the stroke.
    q.z += whip*BeatAmp*.12*s*sin(t*w*2.0-s*3.0+P.x*.02);
} else if (Mode < 3.5) {   // a turtle's flippers: a slow stroke down and back; the shell does not bend
    float s = VC.r;
    q.z += BeatAmp*s*sin(t*w);
    q.x += BeatAmp*.5*s*cos(t*w);
} else if (Mode < 4.5) {   // a jellyfish: the bell closes, then opens slowly; tentacles trail after it
    float pulse = pow(.5+.5*sin(t*w), 3.0);
    if (VC.b < .5) {
        float close = pulse*.3*smoothstep(.2, 1.0, VC.r);
        q.xy *= 1.0-close;
        q.z += pulse*VC.r*BeatAmp;
    } else {
        q.xy *= 1.0-.14*sin(t*w-VC.r*3.0)*(1.0-VC.r);
        q.xy += float2(sin(t*.4+VC.r*5.0+P.x*.1), cos(t*.33+VC.r*4.0+P.y*.1))*VC.r*VC.r*BeatAmp*1.3;
    }
} else {                   // a soft body: a moray breathing, an octopus's arms
    q += float3(sin(t*w+P.y*.03), cos(t*w*.8+P.x*.03), .4*sin(t*w*1.2+P.x*.02+P.y*.02))*BeatAmp*VC.r;
}
if (Puff > .001 && Mode < .5) {
    // A porcupinefish blowing up: the body swells into a ball, shorter, and the spines (B .5, A 1 at the tip) stand out of it.
    float s = pow(saturate(VC.r), .667);
    float k = pow(max(sin(3.14159*saturate((s-.02)/.86)), 0.0), .6);
    float spine = (VC.b > .3 && VC.b < .7) ? 1.0 : 0.0;
    float finv = VC.b > .7 ? .7 : 1.0;
    float grow = Puff*finv*(1.6*k+spine*VCA*.9);
    q.yz *= 1.0+grow;
    q.x *= 1.0-.18*Puff*finv;
}
float3 travel = float3(0, 0, 0);
if (Travel > .5) {
    float Ra = D0, Rb = D1, Om = D2, Rot = D4;
    // A whole shoal keeps one phase; each fish drifts a little ahead or behind it, and in and out.
    float jit = (frac(Rand*7.31)-.5)*.2/max(max(Ra, Rb)*.01, 1.0);
    // Nobody cruises at one speed: the journey hurries and dawdles, the whole shoal together.
    float th = (Time+1.9*sin(Time*.37+D3))*Om+D3+jit;
    float2 e = float2(cos(th)*Ra, sin(th)*Rb);
    float2 de = float2(-sin(th)*Ra, cos(th)*Rb)*sign(Om);
    float cr = cos(Rot), sr = sin(Rot);
    travel.xy = float2(e.x*cr-e.y*sr, e.x*sr+e.y*cr);
    float2 dir = float2(de.x*cr-de.y*sr, de.x*sr+de.y*cr);
    float wander = sin(Time*(.31+.17*frac(Rand*3.7))+Rand*17.0);
    travel += float3(sin(Time*.23+Rand*31.0), cos(Time*.19+Rand*23.0), wander*.6)*(12.0+18.0*frac(Rand*11.3));
    // Heads of neighbours differ a little.
    float head = atan2(dir.y, dir.x)+.16*wander;
    float cs = cos(head), sn = sin(head);
    q = float3(q.x*cs-q.y*sn, q.x*sn+q.y*cs, q.z);
    // Close to a swimmer the whole group gives way.
    float3 away = (WP+travel)-Cam;
    float d = length(away);
    travel += away/max(d, 1.0)*smoothstep(Shy, Shy*.25, d)*Shy*.8;
}
Travelled = travel;
return q-P;
"""


def _f(back, belly, fin, accent=(0, 0, 0), accent2=(0, 0, 0), mode=0, freq=6.0, amp=.1, travel=1, shy=320, rough=.42, metal=0.0, eye=(.13, .3, .05, 4.0),
       band=(0, 1), stripe=(0, 1), spot=(0, 1), scale=(.5, 60), head=(0, 0), pale_fin=-1.0, scutes=0.0, pattern=0, gills=0, fin_tip=0.0):
    return dict(Back=back, Belly=belly, Fin=fin, Accent=accent, Accent2=accent2, Mode=mode, BeatFreq=freq, BeatAmp=amp, Travel=travel, Shy=shy, RoughBase=rough, MetalBase=metal,
                EyeU=eye[0], EyeV=eye[1], EyeR=eye[2], Aspect=eye[3], BandAmt=band[0], BandFreq=band[1], StripeAmt=stripe[0], StripeFreq=stripe[1], SpotAmt=spot[0], SpotFreq=spot[1],
                ScaleAmt=scale[0], ScaleFreq=scale[1], HeadAmt=head[0], HeadU=head[1], PaleFinU=pale_fin, Scutes=scutes, Pattern=pattern, Gills=gills, FinTip=fin_tip)


# Colours are linear as seen in shallow water: a real Caribbean cast, with the cold seas' cod, herring, seals and orcas.
# amp: cm in the mesh's own size; freq: rad/s of the tail.
FAUNA = dict(
    Sardine=_f((.05, .14, .2), (.62, .64, .62), (.4, .42, .4), freq=19, amp=1.0, rough=.2, metal=.8, scale=(.3, 26), eye=(.09, .12, .08, 3.2)),
    Herring=_f((.03, .1, .16), (.55, .58, .58), (.3, .33, .33), freq=13, amp=1.7, rough=.22, metal=.8, scale=(.35, 26), eye=(.09, .12, .08, 3.2)),
    Grunt=_f((.42, .32, .05), (.5, .46, .22), (.5, .36, .04), accent2=(.07, .16, .32), freq=11, amp=1.6, stripe=(.85, 5.0), eye=(.12, .2, .055, 2.6)),
    Snapper=_f((.3, .2, .24), (.6, .55, .52), (.6, .44, .03), freq=10, amp=2.2, rough=.35, metal=.3, eye=(.13, .18, .05, 3.0)),
    Tang=_f((.02, .05, .3), (.03, .08, .36), (.025, .08, .4), accent2=(.008, .02, .14), freq=8, amp=1.1, stripe=(.3, 8.0), eye=(.15, .22, .05, 1.6), scale=(.2, 50)),
    Angelfish=_f((.05, .14, .24), (.42, .36, .03), (.55, .42, .02), accent=(.015, .05, .2), accent2=(.6, .46, .02), freq=4.2, amp=1.3, spot=(.25, 26), head=(.8, .1), eye=(.17, .2, .045, 1.4), scale=(.4, 46)),
    Butterflyfish=_f((.5, .48, .34), (.65, .62, .5), (.55, .4, .03), accent=(.012, .012, .014), freq=6, amp=.7, band=(.24, 1.0), eye=(.17, .2, .06, 1.4)),
    Sergeant=_f((.45, .42, .12), (.62, .62, .5), (.3, .3, .2), accent=(.02, .02, .025), freq=9, amp=.9, band=(.75, 4.2), eye=(.14, .22, .05, 2.0)),
    Parrotfish=_f((.05, .3, .22), (.2, .32, .22), (.09, .22, .3), accent=(.5, .14, .22), accent2=(.04, .35, .3), freq=5, amp=3.0, spot=(.28, 7), head=(.5, .08), scale=(.75, 34), eye=(.13, .3, .04, 2.6)),
    Grouper=_f((.14, .1, .06), (.22, .18, .12), (.1, .08, .06), accent=(.05, .035, .025), freq=2.2, amp=2.5, band=(.45, 3.8), spot=(.2, 15), scale=(.5, 50), eye=(.15, .35, .04, 2.6), shy=180),
    YellowtailSnapper=_f((.16, .2, .3), (.64, .62, .58), (.62, .46, .03), accent2=(.65, .48, .03), freq=10, amp=2.0, rough=.3, metal=.3, stripe=(.55, 1.0), scale=(.3, 40), eye=(.13, .18, .05, 3.0)),
    Hogfish=_f((.5, .24, .17), (.66, .54, .46), (.5, .26, .16), accent=(.15, .05, .04), accent2=(.22, .07, .05), freq=4, amp=2.0, head=(.6, .12), spot=(.2, 10), scale=(.4, 34), eye=(.2, .32, .04, 3.0)),
    Squirrelfish=_f((.45, .05, .035), (.62, .32, .26), (.55, .25, .05), accent2=(.62, .5, .45), freq=6, amp=1.2, stripe=(.45, 4.0), scale=(.6, 30), eye=(.12, .2, .1, 2.0)),
    Spadefish=_f((.38, .4, .4), (.58, .6, .58), (.2, .22, .22), accent=(.02, .02, .025), freq=4, amp=1.6, rough=.3, metal=.3, band=(.85, 3.0), scale=(.2, 40), eye=(.14, .25, .05, 1.6)),
    Porkfish=_f((.52, .44, .1), (.62, .58, .32), (.6, .46, .05), accent=(.015, .015, .02), accent2=(.06, .12, .32), freq=7, amp=1.0, band=(.6, 1.1), stripe=(.55, 4.0), scale=(.3, 36), eye=(.15, .22, .05, 1.8)),
    HorseEyeJack=_f((.12, .18, .22), (.66, .68, .66), (.42, .38, .12), freq=6, amp=3.5, rough=.2, metal=.85, scale=(.15, 30), eye=(.11, .2, .07, 3.0)),
    Goatfish=_f((.46, .42, .24), (.68, .64, .55), (.62, .48, .05), accent2=(.65, .5, .04), freq=6, amp=1.2, stripe=(.55, 1.0), scale=(.4, 36), eye=(.12, .25, .05, 3.0)),
    Cowfish=_f((.34, .3, .12), (.5, .44, .2), (.36, .32, .14), accent=(.08, .16, .32), freq=3, amp=.5, rough=.5, spot=(.65, 26), scale=(.7, 12), eye=(.15, .35, .07, 1.6)),
    Flounder=_f((.42, .38, .28), (.5, .46, .36), (.42, .38, .28), accent=(.12, .22, .38), mode=5, freq=.4, amp=.6, travel=0, rough=.6, spot=(.5, 18), scale=(0, 1), eye=(.12, .3, .05, 2.0)),
    Cod=_f((.13, .13, .07), (.42, .4, .32), (.12, .12, .08), accent=(.05, .05, .03), freq=4, amp=3.0, spot=(.6, 30), scale=(.35, 50), eye=(.14, .3, .05, 2.8)),
    Trumpetfish=_f((.22, .12, .05), (.32, .22, .1), (.2, .13, .06), accent=(.09, .06, .03), freq=3, amp=1.4, band=(.5, 12), eye=(.2, .1, .08, 6.0), shy=160),
    Jellyfish=_f((.42, .42, .5), (.25, .26, .36), (.34, .34, .42), mode=4, freq=1.0, amp=1.8, shy=70, rough=.2, eye=(0, 0, 0, 1), scale=(0, 1)),
    Moray=_f((.08, .1, .025), (.14, .15, .05), (.08, .1, .025), accent=(.03, .04, .012), mode=5, freq=.7, amp=2.0, travel=0, spot=(.45, 22), scale=(0, 1), eye=(.05, .35, .08, 8.0)),
    Octopus=_f((.24, .11, .06), (.42, .27, .17), (.24, .11, .06), accent=(.09, .04, .025), mode=5, freq=.55, amp=4.0, travel=0, spot=(.5, 16), scale=(0, 1), eye=(.085, .95, .05, 3.0)),
    Pufferfish=_f((.32, .27, .14), (.62, .6, .52), (.35, .3, .18), accent=(.04, .035, .02), freq=3.5, amp=.5, travel=0, spot=(.7, 18), scale=(0, 1), eye=(.12, .25, .07, 1.4)),
    Swordfish=_f((.06, .04, .06), (.4, .36, .3), (.05, .04, .05), freq=2.0, amp=12.0, travel=0, rough=.3, metal=.4, scale=(0, 1), eye=(.1, .22, .03, 3.5)),
    BlueMarlin=_f((.008, .02, .07), (.6, .62, .62), (.01, .03, .09), accent=(.25, .45, .7), freq=2.2, amp=14.0, travel=0, rough=.25, metal=.6, band=(.45, 14), scale=(0, 1), eye=(.09, .2, .03, 4.0)),
    MahiMahi=_f((.02, .2, .12), (.6, .5, .06), (.02, .15, .25), accent=(.01, .05, .06), freq=4.0, amp=5.0, travel=0, rough=.25, metal=.5, spot=(.5, 40), scale=(.2, 40), eye=(.07, .2, .04, 3.0)),
    Lionfish=_f((.32, .05, .02), (.75, .66, .6), (.4, .12, .08), accent=(.8, .75, .7), freq=2.0, amp=.5, travel=0, shy=0, band=(.9, 11), scale=(0, 1), eye=(.12, .25, .05, 2.0)),
    QueenTriggerfish=_f((.08, .16, .22), (.5, .44, .18), (.1, .2, .3), accent2=(.05, .25, .6), freq=3.0, amp=1.2, travel=0, stripe=(.7, 4.0), scale=(.3, 40), eye=(.2, .3, .05, 2.0)),
    Tuna=_f((.008, .02, .07), (.62, .64, .62), (.6, .42, .02), freq=9, amp=7.0, travel=0, rough=.2, metal=.8, scale=(.1, 30), eye=(.1, .2, .04, 4.0)),
    Tarpon=_f((.06, .13, .16), (.72, .74, .72), (.2, .22, .24), freq=4.5, amp=7.0, travel=0, rough=.2, metal=.9, scale=(.5, 22), eye=(.08, .22, .05, 5.0)),
    Barracuda=_f((.11, .15, .17), (.62, .64, .62), (.18, .2, .22), accent=(.02, .025, .03), freq=3.0, amp=3.2, travel=0, rough=.24, metal=.7, spot=(.5, 15), scale=(.1, 40), eye=(.13, .18, .06, 7.0)),
    BullShark=_f((.16, .15, .12), (.6, .58, .54), (.13, .12, .1), freq=2.2, amp=12.0, travel=0, rough=.5, scale=(0, 1), eye=(.1, .14, .014, 5.0), gills=1),
    Blacktip=_f((.2, .2, .19), (.62, .62, .6), (.17, .17, .16), accent2=(.012, .012, .014), freq=2.8, amp=9.0, travel=0, rough=.45, scale=(0, 1), eye=(.12, .14, .018, 5.0), gills=1, fin_tip=1.0),
    OceanicWhitetip=_f((.14, .13, .11), (.58, .58, .55), (.13, .12, .1), accent2=(.62, .62, .6), freq=1.8, amp=14.0, travel=0, rough=.5, scale=(0, 1), eye=(.12, .14, .015, 5.0), gills=1, fin_tip=1.0),
    GreatWhite=_f((.1, .11, .12), (.78, .78, .76), (.09, .1, .11), accent2=(.04, .04, .045), freq=1.5, amp=22.0, travel=0, rough=.45, scale=(0, 1), eye=(.1, .12, .014, 5.0), gills=1, pattern=3, fin_tip=.5),
    BoxJellyfish=_f((.55, .6, .65), (.3, .35, .4), (.45, .5, .55), mode=4, freq=1.6, amp=2.0, shy=0, rough=.15, eye=(0, 0, 0, 1), scale=(0, 1)),
    SeaNettle=_f((.55, .42, .25), (.35, .22, .12), (.6, .35, .2), mode=4, freq=1.1, amp=1.6, shy=0, rough=.2, eye=(0, 0, 0, 1), scale=(0, 1)),
    LionsMane=_f((.5, .2, .06), (.32, .12, .04), (.6, .3, .1), mode=4, freq=.6, amp=3.0, shy=0, rough=.2, eye=(0, 0, 0, 1), scale=(0, 1)),
    ReefShark=_f((.11, .12, .13), (.6, .6, .58), (.09, .1, .11), accent2=(.03, .03, .035), freq=2.4, amp=11.0, travel=0, rough=.5, scale=(0, 1), eye=(.12, .14, .018, 5.0), gills=1, fin_tip=.45),
    TigerShark=_f((.12, .13, .12), (.62, .62, .58), (.1, .11, .1), accent=(.04, .045, .045), freq=1.9, amp=18.0, travel=0, rough=.5, band=(.36, 12), scale=(0, 1), eye=(.11, .14, .015, 5.0), gills=1),
    Hammerhead=_f((.15, .15, .14), (.62, .62, .58), (.12, .12, .12), freq=2.2, amp=16.0, travel=0, rough=.5, scale=(0, 1), eye=(.14, .14, .001, 5.0), gills=1),
    NurseShark=_f((.2, .15, .08), (.36, .3, .2), (.17, .13, .07), accent=(.1, .07, .04), mode=5, freq=.3, amp=1.5, travel=0, rough=.65, spot=(.3, 16), scale=(0, 1), eye=(.09, .18, .012, 5.0)),
    EagleRay=_f((.012, .014, .02), (.6, .6, .58), (.012, .014, .02), accent=(.5, .5, .48), mode=2, freq=1.6, amp=26.0, travel=0, rough=.45, spot=(.8, 34), scale=(0, 1), eye=(0, 0, 0, 1)),
    Manta=_f((.018, .022, .03), (.6, .6, .58), (.018, .022, .03), mode=2, freq=.9, amp=68.0, travel=0, rough=.5, scale=(0, 1), eye=(0, 0, 0, 1)),
    Stingray=_f((.2, .17, .11), (.55, .55, .5), (.15, .13, .09), accent=(.1, .09, .06), mode=2, freq=.5, amp=1.5, travel=0, rough=.75, spot=(.25, 12), scale=(0, 1), eye=(0, 0, 0, 1)),
    GreenTurtle=_f((.16, .12, .05), (.62, .56, .36), (.12, .1, .06), accent=(.05, .035, .02), mode=3, freq=.9, amp=20.0, travel=0, rough=.4, spot=(.35, 18), scale=(0, 1), eye=(.03, .25, .035, 3.0), scutes=1.0),
    Seal=_f((.1, .1, .09), (.3, .29, .25), (.08, .08, .07), accent=(.03, .03, .03), mode=1, freq=2.0, amp=12.0, travel=0, rough=.32, spot=(.5, 30), scale=(0, 1), eye=(.08, .35, .045, 4.0)),
    Dolphin=_f((.16, .18, .2), (.66, .66, .64), (.12, .14, .16), mode=1, freq=3.2, amp=13.0, travel=0, rough=.22, scale=(0, 1), eye=(.12, .05, .018, 5.0), pattern=2),
    Orca=_f((.006, .006, .008), (.78, .78, .76), (.006, .006, .008), mode=1, freq=1.6, amp=33.0, travel=0, rough=.25, scale=(0, 1), eye=(.12, .3, .012, 5.0), pattern=1),
    Humpback=_f((.018, .02, .025), (.5, .5, .48), (.03, .032, .035), accent=(.28, .28, .28), mode=1, freq=.75, amp=62.0, travel=0, rough=.55, spot=(0, 1), scale=(0, 1), eye=(.16, .1, .008, 5.0), pale_fin=.6),
)



def sea_life_material():
    m = mg.fresh_material(MARINE, "M_SeaLife")
    m.set_editor_property("two_sided", True)
    m.set_editor_property("used_with_nanite", True)
    m.set_editor_property("used_with_instanced_static_meshes", True)
    g = mg.Graph(m)
    vc = g.node(unreal.MaterialExpressionVertexColor)
    wp = g.node(unreal.MaterialExpressionWorldPosition)
    rand = g.node(unreal.MaterialExpressionPerInstanceRandom)
    cam = g.node(unreal.MaterialExpressionCameraPositionWS)
    body = g.custom("Sea life colour", SEA_HLSL, C.CMOT_FLOAT3, [
        ("VC", vc), ("VCA", (vc, "A")), ("WP", wp), ("Cam", cam), ("Rand", rand),
        ("A", g.vector("ColorA", (.2, .2, .1, 1))), ("B", g.vector("ColorB", (.3, .25, .1, 1))), ("Tidal", g.scalar("Tidal", 0.0)),
    ], outputs=[("Rough", C.CMOT_FLOAT1)])
    ch = unreal.load_asset(GRAIN_TEX + "_CH")
    nra = unreal.load_asset(GRAIN_TEX + "_NRA")
    if not ch or not nra:
        mg.warn("rock_face textures missing: run Tools/build_materials.py first (the grain borrows the biome library's rock_face)")
        ch = nra = unreal.load_asset("/Engine/EngineResources/Black")
    grain = g.custom("Rock grain (triplanar)", GRAIN_HLSL, C.CMOT_FLOAT3, [
        ("N", g.node(unreal.MaterialExpressionVertexNormalWS)), ("WP", wp), ("Cam", cam),
        ("D", g.texture("GrainColor", ch, linear=False)), ("Nm", g.texture("GrainNormal", nra, linear=True)),
        ("Tile", g.scalar("GrainTile", 1.2)), ("Grain", g.scalar("Grain", 0.0)),
    ], outputs=[("Shade", C.CMOT_FLOAT1)])
    shaded = g.node(unreal.MaterialExpressionMultiply)
    g.link(body, shaded, "A")
    g.link((grain, "Shade"), shaded, "B")
    # back to tangent space, so two-sided blades still flip their normal on the far side
    to_tangent = g.node(unreal.MaterialExpressionTransform,
                        transform_source_type=unreal.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD,
                        transform_type=unreal.MaterialVectorCoordTransform.TRANSFORM_TANGENT)
    g.link(grain, to_tangent, "")
    g.out(shaded, MP.MP_BASE_COLOR)
    g.out(to_tangent, MP.MP_NORMAL)
    g.out((body, "Rough"), MP.MP_ROUGHNESS)
    sway = g.custom("Surge sway", SWAY_HLSL, C.CMOT_FLOAT3, [
        ("VC", vc), ("WP", wp), ("Rand", rand), ("Time", g.node(unreal.MaterialExpressionTime)), ("Sway", g.scalar("Sway", 0.0)),
    ])
    g.out(sway, MP.MP_WORLD_POSITION_OFFSET)
    mg.finish(m, f"{MARINE}/M_SeaLife")
    return m


def creature_material(name, see_through):
    m = mg.fresh_material(MARINE, name)
    m.set_editor_property("two_sided", True)
    m.set_editor_property("used_with_instanced_static_meshes", True)
    if see_through:
        m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    g = mg.Graph(m)
    vc = g.node(unreal.MaterialExpressionVertexColor)
    rand = g.node(unreal.MaterialExpressionPerInstanceRandom)
    uv = g.node(unreal.MaterialExpressionTextureCoordinate)
    wp = g.node(unreal.MaterialExpressionWorldPosition)
    cam = g.node(unreal.MaterialExpressionCameraPositionWS)
    time = g.node(unreal.MaterialExpressionTime)
    local = g.node(unreal.MaterialExpressionPreSkinnedPosition)   # the vertex in the mesh's own space (vertex shader)
    body_in = [("VC", vc), ("UV", uv), ("Rand", rand)]
    body_in += [(n, g.vector(n, (.3, .3, .3, 1))) for n in ("Back", "Belly", "Fin", "Accent", "Accent2")]
    body_in += [(n, g.scalar(n, 0.0)) for n in ("BandAmt", "BandFreq", "StripeAmt", "StripeFreq", "SpotAmt", "SpotFreq", "ScaleAmt",
                                                "ScaleFreq", "HeadAmt", "HeadU", "EyeU", "EyeV", "EyeR", "Aspect", "RoughBase",
                                                "MetalBase", "PaleFinU", "Scutes", "Pattern", "Gills", "FinTip")]
    body = g.custom("Creature markings", CREATURE_BODY_HLSL, C.CMOT_FLOAT3, body_in,
                    outputs=[("Rough", C.CMOT_FLOAT1), ("OutMetal", C.CMOT_FLOAT1)])
    g.out(body, MP.MP_BASE_COLOR)
    g.out((body, "Rough"), MP.MP_ROUGHNESS)
    g.out((body, "OutMetal"), MP.MP_METALLIC)
    if see_through:
        # glass seen edge-on is what shows a jellyfish: nearly nothing face-on, milky at the rim, a faint glow by night
        fres = g.node(unreal.MaterialExpressionFresnel, exponent=2.2, base_reflect_fraction=.1)
        g.out(fres, MP.MP_OPACITY)
        glow = g.node(unreal.MaterialExpressionMultiply, const_b=.12)
        g.link(body, glow, "A")
        g.out(glow, MP.MP_EMISSIVE_COLOR)
    swim_in = [("P", local), ("VC", vc), ("VCA", (vc, "A")), ("Rand", rand), ("Time", time), ("WP", wp), ("Cam", cam)]
    swim_in += [(f"D{i}", g.node(unreal.MaterialExpressionPerInstanceCustomData, data_index=i)) for i in range(5)]
    swim_in += [(n, g.scalar(n, 0.0)) for n in ("Mode", "BeatFreq", "BeatAmp", "Travel", "Shy", "Puff")]
    swim = g.custom("Swimming", CREATURE_LOCAL_HLSL, C.CMOT_FLOAT3, swim_in, outputs=[("Travelled", C.CMOT_FLOAT3)])
    # the bending is in the mesh's frame, so it scales and turns with the instance; the journey is in the world's
    to_world = g.node(unreal.MaterialExpressionTransform,
                      transform_source_type=unreal.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_LOCAL,
                      transform_type=unreal.MaterialVectorCoordTransform.TRANSFORM_WORLD)
    g.link(swim, to_world, "")
    add = g.node(unreal.MaterialExpressionAdd)
    g.link(to_world, add, "A")
    g.link((swim, "Travelled"), add, "B")
    g.out(add, MP.MP_WORLD_POSITION_OFFSET)
    mg.finish(m, f"{MARINE}/{name}")
    return m


def instance(name, parent, scalars=None, vectors=None):
    path = f"{MARINE}/{name}"
    if EAL.does_asset_exist(path):
        EAL.delete_asset(path)
    mi = mg.TOOLS.create_asset(name, MARINE, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(mi, parent)
    for k, v in (vectors or {}).items():
        MEL.set_material_instance_vector_parameter_value(mi, k, unreal.LinearColor(v[0], v[1], v[2], 1.0))
    for k, v in (scalars or {}).items():
        MEL.set_material_instance_scalar_parameter_value(mi, k, float(v))
    EAL.save_loaded_asset(mi, only_if_is_dirty=False)
    return mi


def instances(life, creature, jelly):
    for name, (a, b, sway) in list(LOOKS.items()) + [("Dead", DEAD)]:
        grain, tile = GRAIN.get(name, (0.0, 1.0))
        instance(f"MI_Sea_{name}", life, dict(Sway=sway, Tidal=1.0 if name in TIDAL else 0.0, Grain=grain, GrainTile=tile),
                 dict(ColorA=a, ColorB=b))
    for name, values in FAUNA.items():
        instance(f"MI_Sea_{name}", jelly if name in SEE_THROUGH else creature,
                 {k: v for k, v in values.items() if not isinstance(v, tuple)},
                 {k: v for k, v in values.items() if isinstance(v, tuple)})


def import_meshes():
    p1 = EAL.load_asset("/Interchange/Pipelines/DefaultAssetsPipeline")
    p2 = EAL.load_asset("/Interchange/Pipelines/DefaultGLTFPipeline")
    p1.set_editor_property("scene_name_sub_folder", False)
    p1.set_editor_property("asset_type_sub_folders", False)
    p1.common_meshes_properties.set_editor_property("recompute_normals", False)
    p1.mesh_pipeline.set_editor_property("generate_lightmap_u_vs", False)
    params = unreal.ImportAssetParameters()
    params.is_automated = True
    params.replace_existing = True
    params.override_pipelines = [unreal.SoftObjectPath(p1.get_path_name()), unreal.SoftObjectPath(p2.get_path_name())]
    im = unreal.InterchangeManager.get_interchange_manager_scripted()
    sub = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    n = 0
    meshes = []
    for glb in sorted(glob.glob(os.path.join(SRC, "SM_Sea_*.glb"))):
        name = os.path.splitext(os.path.basename(glb))[0]
        species = name[len("SM_Sea_"):]
        # swimming moves every vertex of a light mesh: Nanite would not help and costs a lot with WPO
        p1.mesh_pipeline.set_editor_property("build_nanite", species not in FAUNA)
        p1.mesh_pipeline.set_editor_property("collision", False)
        objs = list(im.import_asset(MARINE, unreal.InterchangeManager.create_source_data(glb), params) or [])
        mesh = next((o for o in objs if isinstance(o, unreal.StaticMesh)), None)
        if mesh is None:
            mg.warn(f"import failed: {name}")
            continue
        for o in objs:
            if isinstance(o, (unreal.Material, unreal.MaterialInstance, unreal.Texture)):
                EAL.delete_asset(o.get_path_name())
        mi = unreal.load_asset(f"{MARINE}/MI_Sea_{species}")
        if not mi and species.startswith("GhostCrabLeg"):
            mi = unreal.load_asset(f"{MARINE}/MI_Sea_GhostCrab")
        if mi:
            mesh.set_material(0, mi)
        else:
            mg.warn(f"no material for {species}")
        if species in COLLIDING:   # sea stacks and skerries stop boats: a few convex hulls of the visible shape
            sub.set_convex_decomposition_collisions(mesh, 6, 32, 200000)
        meshes.append(mesh)
        n += 1
        bb = mesh.get_bounding_box()
        mg.log(f"MARINE {name}: {bb.max.x - bb.min.x:.0f} x {bb.max.y - bb.min.y:.0f} x {bb.max.z - bb.min.z:.0f} cm")
    EAL.save_loaded_assets(meshes, only_if_is_dirty=False)
    return n


def main():
    mg.ERRORS.clear()
    mg.ensure_dir(MARINE)
    if not glob.glob(os.path.join(SRC, "SM_Sea_*.glb")):
        raise RuntimeError("Build/Marine is empty: run Tools/marine/marine_life.py and Tools/marine/marine_fauna.py first")
    life = sea_life_material()
    creature = creature_material("M_SeaCreature", False)
    jelly = creature_material("M_SeaJelly", True)
    instances(life, creature, jelly)
    n = import_meshes()
    mg.log(f"BAM MARINE DONE meshes={n} errors={len(mg.ERRORS)}")
    for e in mg.ERRORS:
        mg.log(f"  error: {e}")


try:
    main()
except Exception:  # noqa
    import traceback
    unreal.log_error("[BAM] " + traceback.format_exc())
    mg.log("BAM MARINE FAILED")
if os.environ.get("BAM_QUIT") == "1":
    unreal.SystemLibrary.quit_editor()
