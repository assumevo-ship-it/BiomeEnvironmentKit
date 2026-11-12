// Biome Auto-Materials - shared helpers.
// Injected into the material through a Custom node (the "closing brace" technique): build_materials.py wraps this file as
//     return 0; }  <this file>  float BAM_HelpersEnd() { return 0;
// so everything here becomes a global function in the generated shader. Everything is prefixed BAM_.
// All textures are read with the view's shared wrap sampler (world texture group anisotropy + TSR mip bias), so the
// material can use 17 textures without hitting the 16-sampler limit.

#define BAM_SS View.MaterialTextureBilinearWrapedSampler
#define BAM_LUM float3(0.2126, 0.7152, 0.0722)

struct BAMSurf
{
    float3 col;    // linear albedo
    float  h;      // height for blending (0..1 + bias)
    float3 n;      // world-space normal
    float  rough;
    float  ao;
    float  por;    // porosity (wet darkening)
};

BAMSurf BAM_Zero()
{
    BAMSurf s;
    s.col = 0; s.h = 0; s.n = float3(0, 0, 1); s.rough = 1; s.ao = 1; s.por = 0;
    return s;
}

float  BAM_Hash11(float p) { p = frac(p * 0.1031); p *= p + 33.33; p *= p + p; return frac(p); }
float2 BAM_Hash22(float2 p)
{
    float3 p3 = frac(float3(p.xyx) * float3(0.1031, 0.1030, 0.0973));
    p3 += dot(p3, p3.yzx + 33.33);
    return frac((p3.xx + p3.yz) * p3.zy);
}

// 0 below (a - w/2), 1 above (a + w/2)
float BAM_Ramp(float x, float a, float w) { return saturate((x - (a - 0.5 * w)) / max(w, 1e-3)); }

// Non-periodic noise. One tiling texture read at a single scale repeats on a grid that is plain to see from the air
// (the patches of an 18 m period, the brightness drift of a 60 m one). A second read, turned 53 degrees and scaled by
// 1/sqrt(2), shares no period with the first, so their sum never repeats. The mean of two uniform values has a
// triangular distribution; its CDF (2m^2 below 0.5, 1 - 2(1-m)^2 above) maps it back to uniform, so coverage
// thresholds and patch sizes keep their meaning.
float4 BAM_Noise(Texture2D T, float2 uv)
{
    float4 a = T.SampleLevel(BAM_SS, uv, 0);
    float2 r = float2(uv.x * 0.6018 - uv.y * 0.7986, uv.x * 0.7986 + uv.y * 0.6018) * 0.70710678 + float2(0.271, 0.413);
    float4 m = (a + T.SampleLevel(BAM_SS, r, 0)) * 0.5;
    float4 below = step(m, 0.5);
    return lerp(1.0 - 2.0 * (1.0 - m) * (1.0 - m), 2.0 * m * m, below);
}

// ---------------------------------------------------------------------------------------------------------------------
// Hex-tiling (Mikkelsen 2022, "Practical Real-Time Hex-Tiling", after Heitz & Neyret 2018): three randomly rotated and
// offset copies on a triangle grid, blended by barycentric weight sharpened with the texture's own height so the seams
// follow the content instead of crossfading.
// ---------------------------------------------------------------------------------------------------------------------
void BAM_TriGrid(float2 st, out float w1, out float w2, out float w3, out float2 v1, out float2 v2, out float2 v3)
{
    st *= 3.46410162;  // 2 sqrt(3)
    float2 sk = float2(st.x - 0.57735027 * st.y, 1.15470054 * st.y);
    float2 base = floor(sk);
    float3 t = float3(frac(sk), 0);
    t.z = 1.0 - t.x - t.y;
    float s = step(0.0, -t.z);
    float s2 = 2.0 * s - 1.0;
    w1 = -t.z * s2;
    w2 = s - t.y * s2;
    w3 = s - t.x * s2;
    v1 = base + float2(s, s);
    v2 = base + float2(s, 1.0 - s);
    v3 = base + float2(1.0 - s, s);
}

float2 BAM_HexCentre(float2 v) { return float2(v.x + 0.5 * v.y, 0.8660254 * v.y) / 3.46410162; }

float2x2 BAM_HexRot(float2 v, float strength)
{
    float a = (BAM_Hash22(v + 17.0).x * 2.0 - 1.0) * 3.14159265 * strength;
    float c = cos(a), s = sin(a);
    return float2x2(c, -s, s, c);
}

// one tap of colour+height and normal+rough+ao, with explicit gradients (safe inside dynamic branches)
void BAM_Tap(Texture2D CH, Texture2D NRA, float2 uv, float2 gx, float2 gy, out float4 ch, out float4 nra)
{
    ch = CH.SampleGrad(BAM_SS, uv, gx, gy);
    nra = NRA.SampleGrad(BAM_SS, uv, gx, gy);
}

void BAM_HexTap(Texture2D CH, Texture2D NRA, float2 uv, float2 gx, float2 gy, float contrast, float rotStrength,
                out float4 ch, out float4 nra)
{
    float w1, w2, w3; float2 v1, v2, v3;
    BAM_TriGrid(uv, w1, w2, w3, v1, v2, v3);
    float2x2 r1 = BAM_HexRot(v1, rotStrength), r2 = BAM_HexRot(v2, rotStrength), r3 = BAM_HexRot(v3, rotStrength);
    float2 c1 = BAM_HexCentre(v1), c2 = BAM_HexCentre(v2), c3 = BAM_HexCentre(v3);
    float2 u1 = mul(uv - c1, r1) + c1 + BAM_Hash22(v1);
    float2 u2 = mul(uv - c2, r2) + c2 + BAM_Hash22(v2);
    float2 u3 = mul(uv - c3, r3) + c3 + BAM_Hash22(v3);
    float4 ch1, ch2, ch3, n1, n2, n3;
    BAM_Tap(CH, NRA, u1, mul(gx, r1), mul(gy, r1), ch1, n1);
    BAM_Tap(CH, NRA, u2, mul(gx, r2), mul(gy, r2), ch2, n2);
    BAM_Tap(CH, NRA, u3, mul(gx, r3), mul(gy, r3), ch3, n3);
    // normals back into the unrotated frame
    n1.rg = mul(r1, n1.rg * 2.0 - 1.0) * 0.5 + 0.5;
    n2.rg = mul(r2, n2.rg * 2.0 - 1.0) * 0.5 + 0.5;
    n3.rg = mul(r3, n3.rg * 2.0 - 1.0) * 0.5 + 0.5;
    float3 W = float3(w1, w2, w3);
    float3 D = lerp(1.0, float3(ch1.a, ch2.a, ch3.a) * 1.6 + 0.2, contrast);
    W = D * pow(max(W, 0.0), 7.0);
    W /= max(W.x + W.y + W.z, 1e-5);
    ch = ch1 * W.x + ch2 * W.y + ch3 * W.z;
    nra = n1 * W.x + n2 * W.y + n3 * W.z;
}

// colour grading + unpacking. P0 = (tile, aspect, brightness, saturation), P1 = (normal, roughness, height bias, porosity)
BAMSurf BAM_Grade(float4 ch, float4 nra, float4 P0, float4 P1, float3 tint)
{
    BAMSurf s;
    float3 c = ch.rgb * P0.z;
    float l = dot(c, BAM_LUM);
    s.col = clamp(lerp(l.xxx, c, P0.w) * tint, 0.0, 0.95);   // no real surface reflects more than ~95%
    s.h = ch.a + P1.z;
    float2 t = nra.rg * 2.0 - 1.0;
    float tz = sqrt(saturate(1.0 - dot(t, t)));
    s.n = float3(t * P1.x, tz);          // tangent space here; callers turn it into world space
    s.rough = saturate(nra.b * P1.y);
    s.ao = lerp(1.0, nra.a, saturate(P1.x));
    s.por = P1.w;
    return s;
}

float2 BAM_InvTile(float4 P0, float scale) { float t = max(P0.x * scale, 0.01); return float2(1.0 / t, 1.0 / (t * max(P0.y, 0.05))); }

// planar (top-down) layer: hex-tiled near, a larger rotated copy far away, cross-faded by distance f
BAMSurf BAM_Planar(Texture2D CH, Texture2D NRA, float2 xy, float2 dx, float2 dy, float3 N, float4 P0, float4 P1, float3 tint,
                   float f, float hex, float hexC, float hexR, float farScale)
{
    float2 inv = BAM_InvTile(P0, 1.0);
    float4 ch = 0, nra = float4(0.5, 0.5, 1, 1);
    [branch] if (f < 0.999)
    {
        float2 uv = xy * inv, gx = dx * inv, gy = dy * inv;
        [branch] if (hex > 0.5) BAM_HexTap(CH, NRA, uv, gx, gy, hexC, hexR, ch, nra);
        else BAM_Tap(CH, NRA, uv, gx, gy, ch, nra);
    }
    [branch] if (f > 0.001)
    {
        const float2x2 R = float2x2(0.8253, -0.5646, 0.5646, 0.8253);
        float2 inv2 = inv * farScale;
        float4 ch2, nra2;
        BAM_Tap(CH, NRA, mul(xy * inv2, R) + 0.37, mul(dx * inv2, R), mul(dy * inv2, R), ch2, nra2);
        nra2.rg = mul(R, nra2.rg * 2.0 - 1.0) * 0.5 + 0.5;
        ch = lerp(ch, ch2, f);
        nra = lerp(nra, nra2, f);
    }
    BAMSurf s = BAM_Grade(ch, nra, P0, P1, tint);
    // whiteout blend onto the terrain normal (landscape tangent frame = world X/Y)
    s.n = normalize(float3(s.n.xy + N.xy, s.n.z * N.z));
    return s;
}

// triplanar layer for cliffs: X/Y side projections (orientation-corrected) plus a top projection, sharp blend
BAMSurf BAM_Triplanar(Texture2D CH, Texture2D NRA, float3 P, float3 dPx, float3 dPy, float3 N, float4 P0, float4 P1, float3 tint,
                      float scale)
{
    float2 inv = BAM_InvTile(P0, scale);
    float3 bw = pow(abs(N), 6.0);
    bw /= (bw.x + bw.y + bw.z + 1e-5);
    float sx = N.x >= 0 ? 1.0 : -1.0;
    float sy = N.y >= 0 ? 1.0 : -1.0;
    float4 ch = 0, nra = 0;
    float3 nw = 0;
    [branch] if (bw.x > 0.01)
    {
        float4 c, n;
        BAM_Tap(CH, NRA, float2(P.y * sx, -P.z) * inv, float2(dPx.y * sx, -dPx.z) * inv, float2(dPy.y * sx, -dPy.z) * inv, c, n);
        float2 t = (n.rg * 2.0 - 1.0) * P1.x;
        nw += normalize(float3(0, sx, 0) * t.x + float3(0, 0, -1) * t.y + N * sqrt(saturate(1.0 - dot(t, t)) + 0.05)) * bw.x;
        ch += c * bw.x; nra += n * bw.x;
    }
    [branch] if (bw.y > 0.01)
    {
        float4 c, n;
        BAM_Tap(CH, NRA, float2(-P.x * sy, -P.z) * inv, float2(-dPx.x * sy, -dPx.z) * inv, float2(-dPy.x * sy, -dPy.z) * inv, c, n);
        float2 t = (n.rg * 2.0 - 1.0) * P1.x;
        nw += normalize(float3(-sy, 0, 0) * t.x + float3(0, 0, -1) * t.y + N * sqrt(saturate(1.0 - dot(t, t)) + 0.05)) * bw.y;
        ch += c * bw.y; nra += n * bw.y;
    }
    [branch] if (bw.z > 0.01)
    {
        float4 c, n;
        BAM_Tap(CH, NRA, P.xy * inv, dPx.xy * inv, dPy.xy * inv, c, n);
        float2 t = (n.rg * 2.0 - 1.0) * P1.x;
        nw += normalize(float3(t + N.xy, sqrt(saturate(1.0 - dot(t, t))) * N.z)) * bw.z;
        ch += c * bw.z; nra += n * bw.z;
    }
    BAMSurf s = BAM_Grade(ch, nra, P0, P1, tint);
    s.n = normalize(nw + N * 1e-3);
    return s;
}

BAMSurf BAM_Lerp(BAMSurf a, BAMSurf b, float t)
{
    BAMSurf s;
    s.col = lerp(a.col, b.col, t); s.h = lerp(a.h, b.h, t); s.n = lerp(a.n, b.n, t);
    s.rough = lerp(a.rough, b.rough, t); s.ao = lerp(a.ao, b.ao, t); s.por = lerp(a.por, b.por, t);
    return s;
}

// height-aware blend: t = coverage (0 never, 1 always); in between the higher texture wins (stones poke through sand,
// sand fills the gaps between stones). Softness = width of the transition in height units.
float BAM_HeightAlpha(float t, float hBase, float hLayer, float heightBlend, float soft)
{
    soft = max(soft, 0.01);
    float d = clamp(hLayer - hBase, -1.0, 1.0) * saturate(heightBlend);
    float x = (2.0 * t - 1.0) * (1.0 + soft) + d;
    return saturate(x / (2.0 * soft) + 0.5) * step(1e-4, t);
}

BAMSurf BAM_Over(BAMSurf base, BAMSurf layer, float t, float heightBlend, float soft, out float a)
{
    a = BAM_HeightAlpha(t, base.h, layer.h, heightBlend, soft);
    return BAM_Lerp(base, layer, a);
}
