// Biome Auto-Materials - main evaluation (body of the "BiomeAutoMaterial" Custom node).
// Inputs: P (xy metres in landscape space, z metres world), N (vertex normal, world), Dist (pixel depth, cm), NoiseTex,
// per slot <S>_CH, <S>_NRA, <S>_P0, <S>_P1, <S>_Tint for S in G GB SO SH SC R RB SN, and the global scalars.
// Returns float4(base colour, roughness); extra outputs NormalWS (float3) and AO (float).
// Order of the stack, bottom to top: Ground -> GroundB -> Soil -> Shore -> Scree -> Rock(A/B) -> Snow, then water.

float3 Ng = normalize(N);
float nz = saturate(Ng.z);
float slope = degrees(acos(nz));
float alt = P.z - SeaLevel;
float3 dPx = ddx(P), dPy = ddy(P);
float f = saturate((Dist - FadeStart) / max(FadeLength, 1.0));

// ---- noise (equalised 0..1): A ~ MacroScale, B ~ 4.4x larger, C ~ 6 m detail
float ms = max(MacroScale, 1.0);
float4 nA = BAM_Noise(NoiseTex, P.xy / ms);
float4 nB = BAM_Noise(NoiseTex, P.xy / (ms * 4.37) + float2(0.37, 0.71));
float4 nC = BAM_Noise(NoiseTex, P.xy / 6.1 + float2(0.13, 0.57));
float4 nD = BAM_Noise(NoiseTex, P.xy / (ms * 0.31 * max(GroundBScale, 0.05)) + float2(0.61, 0.29));

// ---- coverage (no texture reads yet)
float tGB = saturate((nD.x * 0.6 + nA.y * 0.4 - (1.0 - GroundBAmount)) * 5.0 + alt * GroundBAltitudeBias + slope * GroundBSlopeBias)
          * step(1e-3, GroundBAmount);
float tSO = max(BAM_Ramp(slope + (nC.y - 0.5) * 6.0, SoilAngle, SoilFade),
                saturate((nB.z * 0.65 + nA.z * 0.35 + (nC.w - 0.5) * 0.12 - (1.0 - SoilPatches)) * 7.0) * step(1e-3, SoilPatches));
float tSH = saturate((ShoreHeight + (nA.z - 0.5) * ShoreNoise - alt) / max(ShoreFade, 0.01)) * (1.0 - BAM_Ramp(slope, ShoreMaxAngle, 8.0));
float tSC = ScreeAmount * saturate(1.0 - abs(slope - ScreeAngle) / max(ScreeWidth, 1.0)) * saturate((nA.w * 0.6 + nC.x * 0.4) * 2.2 - 0.35);
float tR  = BAM_Ramp(slope + (nA.y - 0.5) * RockNoise + (nC.x - 0.5) * RockNoise * 0.5, RockAngle, RockFade);
// rock B: noise patches, or sedimentary strata bands (warped horizontal layers) when Strata Amount > 0
float zs = P.z + (nB.x - 0.5) * StrataWarp + (nC.z - 0.5) * StrataWarp * 0.15;
float band = floor(zs / max(StrataScale, 0.05));
float tRB = lerp(saturate((nB.y - (1.0 - RockBAmount)) * 5.0), step(BAM_Hash11(band), RockBAmount), StrataAmount) * step(1e-3, RockBAmount);
float strataT = BAM_Hash11(band + 17.31) * StrataTintAmount;
// snow: altitude with a ragged line, plus winter cover below it; slope limit applied with the detailed normal later
float tSNh = saturate((alt - (SnowLine + (nB.w - 0.5) * SnowLineNoise)) / max(SnowFade, 0.01));
float tSN0 = saturate(max(tSNh, SnowCover * saturate((nA.x - 0.25) * 2.0 + (nC.y - 0.5) * 0.6))) * SnowAmount;

// ---- which layers can show (a layer fully covered by one above is not sampled)
bool snowFull = tSN0 >= 0.999 && slope < SnowMaxAngle - 25.0;
bool rockFull = tR >= 0.999 || snowFull;
bool screeFull = (tSC >= 0.999) || rockFull;
bool shoreFull = (tSH >= 0.999) || screeFull;
bool soilFull = (tSO >= 0.999) || shoreFull;
bool gbFull = (tGB >= 0.999) || soilFull;

float hex = HexTiling, hc = HexContrast, hr = HexRotation, fs = FarScale;
BAMSurf s = BAM_Zero();
s.n = Ng;
float aGB = 0, aSO = 0, aSH = 0, aSC = 0, aR = 0, aSN = 0;
[branch] if (!gbFull)
    s = BAM_Planar(G_CH, G_NRA, P.xy, dPx.xy, dPy.xy, Ng, G_P0, G_P1, G_Tint, f, hex, hc, hr, fs);
[branch] if (tGB > 1e-3 && !soilFull)
{
    BAMSurf l = BAM_Planar(GB_CH, GB_NRA, P.xy, dPx.xy, dPy.xy, Ng, GB_P0, GB_P1, GB_Tint, f, hex, hc, hr, fs);
    if (gbFull) { s = l; aGB = 1.0; } else s = BAM_Over(s, l, tGB, HeightBlend, BlendSoftness, aGB);
}
[branch] if (tSO > 1e-3 && !shoreFull)
{
    BAMSurf l = BAM_Planar(SO_CH, SO_NRA, P.xy, dPx.xy, dPy.xy, Ng, SO_P0, SO_P1, SO_Tint, f, hex, hc, hr, fs);
    if (soilFull) { s = l; aSO = 1.0; } else s = BAM_Over(s, l, tSO, HeightBlend, BlendSoftness, aSO);
}
[branch] if (tSH > 1e-3 && !screeFull)
{
    BAMSurf l = BAM_Planar(SH_CH, SH_NRA, P.xy, dPx.xy, dPy.xy, Ng, SH_P0, SH_P1, SH_Tint, f, hex, hc, hr, fs);
    if (shoreFull) { s = l; aSH = 1.0; } else s = BAM_Over(s, l, tSH, HeightBlend, BlendSoftness, aSH);
}
[branch] if (tSC > 1e-3 && !rockFull)
{
    BAMSurf l = BAM_Planar(SC_CH, SC_NRA, P.xy, dPx.xy, dPy.xy, Ng, SC_P0, SC_P1, SC_Tint, f, hex, hc, hr, fs);
    if (screeFull) { s = l; aSC = 1.0; } else s = BAM_Over(s, l, tSC, HeightBlend, BlendSoftness, aSC);
}
[branch] if (tR > 1e-3 && !snowFull)
{
    // near: the photo at its real size; far: the same rock 1/FarScale larger, cross-faded with distance
    BAMSurf ra = BAM_Zero(), rb = BAM_Zero();
    [branch] if (tRB < 0.999)
    {
        ra = BAM_Triplanar(R_CH, R_NRA, P, dPx, dPy, Ng, R_P0, R_P1, R_Tint, 1.0);
        [branch] if (f > 0.001) ra = BAM_Lerp(ra, BAM_Triplanar(R_CH, R_NRA, P, dPx, dPy, Ng, R_P0, R_P1, R_Tint, 1.0 / max(fs, 0.05)), f);
    }
    [branch] if (tRB > 0.001)
    {
        rb = BAM_Triplanar(RB_CH, RB_NRA, P, dPx, dPy, Ng, RB_P0, RB_P1, RB_Tint, 1.0);
        [branch] if (f > 0.001) rb = BAM_Lerp(rb, BAM_Triplanar(RB_CH, RB_NRA, P, dPx, dPy, Ng, RB_P0, RB_P1, RB_Tint, 1.0 / max(fs, 0.05)), f);
    }
    float aRB = (tRB <= 0.001) ? 0.0 : (tRB >= 0.999 ? 1.0 : BAM_HeightAlpha(tRB, ra.h, rb.h, HeightBlend, BlendSoftness));
    BAMSurf r = BAM_Lerp(ra, rb, aRB);
    r.col *= lerp(1.0.xxx, StrataTint, strataT);
    // moss / lichen on the upward-facing parts of the rock relief
    float moss = RockMoss * saturate((r.n.z - 0.55) / 0.3) * saturate(nA.x * 1.8 - 0.35 + (nC.w - 0.5) * 0.6);
    r.col = lerp(r.col, MossColor * (0.75 + 0.5 * nC.z), moss);
    r.rough = lerp(r.rough, 0.92, moss);
    r.h += moss * 0.15;
    if (rockFull) { s = r; aR = 1.0; } else s = BAM_Over(s, r, tR, HeightBlend, BlendSoftness, aR);
}
// snow settles on the detailed surface: ledges and the tops of stones keep it, steep faces shed it
[branch] if (tSN0 > 1e-3)
{
    float detailSlope = degrees(acos(saturate(normalize(s.n).z)));
    float tSN = tSN0 * (1.0 - BAM_Ramp(detailSlope + (nC.x - 0.5) * 8.0, SnowMaxAngle, 12.0));
    [branch] if (tSN > 1e-3)
    {
        BAMSurf l = BAM_Planar(SN_CH, SN_NRA, P.xy, dPx.xy, dPy.xy, Ng, SN_P0, SN_P1, SN_Tint, f, hex, hc, hr, fs);
        // a blanket of snow softens the relief underneath and fills its hollows first
        l.n = normalize(lerp(s.n, l.n, SnowSmoothing + (1.0 - SnowSmoothing) * 0.5));
        BAMSurf under = s;
        under.h = 1.0 - s.h;     // hollows (low) are "high" for the snow
        if (snowFull) { s = l; aSN = 1.0; } else s = BAM_Over(under, l, tSN, HeightBlend, BlendSoftness, aSN);
        s.h = lerp(under.h, l.h, aSN);
    }
}

// ---- water: wet band above the sea line, rain wetness, puddles in flat hollows (Lagarde, "Water drop" 2013)
float wet = saturate(max(Wetness, saturate((WetBand - alt) / max(WetBand * 0.6, 0.05)))) * saturate(s.por);
float puddle = Puddles * saturate(Wetness * 1.5 + saturate((WetBand - alt) / max(WetBand, 0.05)))
             * saturate((0.42 - s.h + (nC.z - 0.5) * 0.5) / 0.07) * saturate((nz - 0.985) / 0.01) * saturate(s.por * 2.0);
float wetAll = saturate(wet + puddle);
s.col *= lerp(1.0, lerp(1.0, 0.18, wetAll), s.col);              // porous surfaces darken, darker ones less
s.col *= lerp(1.0, 0.82, wetAll);
s.rough = lerp(s.rough, lerp(0.45, 0.08, puddle), wetAll * 0.85);   // wet soil is satin, only puddles mirror
s.n = normalize(lerp(s.n, Ng, puddle));
s.ao = lerp(s.ao, 1.0, puddle);

// ---- macro variation: soft brightness and saturation drift over tens of metres (kills large-scale repetition)
float3 c = s.col;
c *= lerp(1.0 - MacroStrength, 1.0 + MacroStrength * 0.6, nA.w * 0.6 + nB.x * 0.4);
float lum = dot(c, BAM_LUM);
c = lerp(lum.xxx, c, saturate(1.0 + (nB.z - 0.5) * 2.0 * MacroSaturation));

// ---- debug: layer coverage colours
[branch] if (DebugView > 0.5)
{
    float3 dc = float3(0.1, 0.6, 0.1);
    dc = lerp(dc, float3(0.8, 0.8, 0.1), aGB);
    dc = lerp(dc, float3(0.45, 0.25, 0.1), aSO);
    dc = lerp(dc, float3(0.95, 0.85, 0.6), aSH);
    dc = lerp(dc, float3(0.5, 0.5, 0.5), aSC);
    dc = lerp(dc, lerp(float3(0.2, 0.2, 0.25), float3(0.7, 0.15, 0.1), tRB), aR);
    dc = lerp(dc, float3(1, 1, 1), aSN);
    dc = lerp(dc, float3(0.1, 0.3, 0.9), puddle);
    c = dc * 0.5;
}

NormalWS = normalize(s.n);
AO = saturate(s.ao);
return float4(max(c, 0.0), saturate(s.rough));
