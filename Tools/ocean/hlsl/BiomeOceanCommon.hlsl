// The GPU half of the ocean's wave model. Keep in step with Source/BiomeOcean/Private/BiomeOceanModel.cpp: the CPU
// floats boats on exactly this surface. Units: centimetres and seconds. Injected as global functions by
// Tools/ocean/build_ocean_assets.py.

#define BO_G 981.0
#define BO_PI 3.14159265

float BO_Smooth(float a, float b, float x)
{
    float t = saturate((x - a) / (b - a));
    return t * t * (3.0 - 2.0 * t);
}

float BO_Hash01(int a, int b, uint seed)
{
    uint h = uint(a) * 374761393u + uint(b) * 668265263u + seed * 2246822519u;
    h = (h ^ (h >> 13)) * 1274126177u;
    return float((h ^ (h >> 16)) & 0x00ffffffu) / 16777215.0;
}

float BO_ValueNoise(float2 p, uint seed)
{
    float2 c = floor(p);
    int ix = int(c.x), iy = int(c.y);
    float2 f = p - c;
    f = f * f * (3.0 - 2.0 * f);
    return lerp(lerp(BO_Hash01(ix, iy, seed), BO_Hash01(ix + 1, iy, seed), f.x),
                lerp(BO_Hash01(ix, iy + 1, seed), BO_Hash01(ix + 1, iy + 1, seed), f.x), f.y);
}

// The sea bed from the baked shore field: x signed distance to the waterline (m), y depth (m), zw direction to shore.
float4 BO_Shore(float2 xy, Texture2D ShoreTex, SamplerState ShoreSampler, float4 Bounds, float HasShore)
{
    float4 open = float4(300.0, 40.0, 1.0, 0.0);
    if (HasShore < 0.5 || Bounds.w < 2.0) return open;
    float2 uv = (xy - Bounds.xy) / Bounds.z;
    float2 t = uv * Bounds.w - 0.5;
    if (any(t < -0.5) || any(t > Bounds.w - 0.5)) return open;
    float4 s = Texture2DSampleLevel(ShoreTex, ShoreSampler, uv, 0);
    float edge = BO_Smooth(0.0, 8.0, min(min(t.x, t.y), min(Bounds.w - 1.0 - t.x, Bounds.w - 1.0 - t.y)));
    float2 d = s.zw;
    d = dot(d, d) > 1e-6 ? normalize(d) : float2(1.0, 0.0);
    return float4(lerp(300.0, s.x, edge), lerp(40.0, s.y, edge), d);
}

float BO_SurfBlend(float4 shore)
{
    return (1.0 - BO_Smooth(3.5, 7.0, shore.y)) * (1.0 - BO_Smooth(65.0, 120.0, shore.x));
}

float BO_Shoaling(float deepK, float depthM)
{
    if (deepK <= 0.0 || depthM >= 40.0) return 1.0;
    float kh0 = deepK * max(30.0, depthM * 100.0);
    float kh = max(kh0, sqrt(kh0));
    [unroll] for (int i = 0; i < 3; i++)
    {
        float t = tanh(kh);
        kh -= (kh * t - kh0) / max(t + kh * (1.0 - t * t), 1e-5);
    }
    float t = tanh(kh);
    float ratio = kh0 / max(kh, 1e-5) * (1.0 + kh * (1.0 - t * t) / max(t, 1e-5));
    float s = clamp(1.0 / sqrt(max(ratio, 0.01)), 0.7, 1.65);
    return lerp(s, 1.0, BO_Smooth(15.0, 40.0, depthM));
}

float BO_SwellGroup(float k, float spacePhase, float time, int index)
{
    float beat = 0.16 * spacePhase - 0.080259 * sqrt(BO_G * k) * time + index * 1.713;
    return (1.0 + 0.28 * cos(beat)) * 0.980959;
}

float BO_BreakerHeight(int n, int train, float2 xy, uint envSeed)
{
    uint seed = uint(train) * 7919u + 17u + envSeed;
    float s = float(n) / 5.5;
    float sc = floor(s);
    float sf = s - sc;
    sf = sf * sf * (3.0 - 2.0 * sf);
    float mood = lerp(BO_Hash01(int(sc), 0, seed), BO_Hash01(int(sc) + 1, 0, seed), sf);
    float setH = 0.35 + 1.3 * BO_Smooth(0.2, 0.8, mood);
    float wave = 0.7 + 0.6 * BO_Hash01(n, 1, seed);
    float2 off = float2(BO_Hash01(n, 2, seed) * 97.0, BO_Hash01(n, 3, seed) * 97.0);
    float crest = 0.45 + 1.1 * BO_ValueNoise(xy / 4500.0 + off, seed + 5u);
    return setH * wave * crest;
}

struct BOSea
{
    float4 W[5];        // dir.x, dir.y, k (rad/cm), amplitude (cm)
    float Phase[5];
    float Q;            // Gerstner choppiness
    float RunUp;        // cm
    float WindVar;      // wind-sea variance, cm^2
    uint Seed;
    float Time;
};

// Coastal surf: breakers and swash (CoastalSurf). Also returns foam cues: x breaking crest, y swash.
float3 BO_CoastalSurf(BOSea sea, float4 shore, float2 xy, out float2 foam)
{
    float3 o = 0;
    foam = 0;
    float d = shore.x;
    float blend = BO_SurfBlend(shore);
    if (blend <= 0.0 || d < -10.0) return o;
    float theta[3], incoming[3];
    float sumIn = 0.0;
    [unroll] for (int t = 0; t < 3; t++)
    {
        float4 w = sea.W[t];
        float sp = w.z * dot(w.xy, xy);
        theta[t] = sp - sqrt(BO_G * w.z) * sea.Time + sea.Phase[t];
        float u = (theta[t] - BO_PI * 0.5) / (2.0 * BO_PI);
        float n = floor(u);
        float mood = lerp(BO_BreakerHeight(int(n), t, xy, sea.Seed), BO_BreakerHeight(int(n) + 1, t, xy, sea.Seed), BO_Smooth(0.35, 0.65, u - n));
        incoming[t] = 2.0 * w.w * BO_Shoaling(w.z, shore.y) * mood * BO_SwellGroup(w.z, sp, sea.Time, t);
        sumIn += incoming[t];
    }
    float scale = min(1.0, 0.78 * max(0.0, shore.y) * 100.0 / max(1.0, sumIn));
    float breaking = BO_Smooth(0.42, 0.9, sumIn / max(35.0, shore.y * 100.0));
    float water = BO_Smooth(-0.5, 1.5, d);
    float washZone = 1.0 - BO_Smooth(1.0, 5.0, d);
    float wetness = 0.0;
    [unroll] for (int t2 = 0; t2 < 3; t2++)
    {
        float th = theta[t2];
        float h = incoming[t2] * scale * blend * water;
        float steep = 0.35 + 0.65 * breaking;
        float profile = 0.5 * sin(th) - 0.16 * steep * cos(2.0 * th) + 0.10 * breaking * sin(2.0 * th);
        float peak = 0.5 + 0.5 * sin(th);
        float lk = sea.W[t2].z;
        float surge = min(0.22 * h, 0.07 / max(lk, 1e-7));
        float ratio = (incoming[t2] + 0.35 * max(0.0, sumIn - incoming[t2])) / max(35.0, shore.y * 100.0);
        float pitch = BO_Smooth(0.32, 0.5, ratio) * (1.0 - BO_Smooth(0.75, 1.1, ratio));
        float lean = min(0.3 * h, 0.08 / max(lk, 1e-7)) * pitch * pow(peak, 6.0);
        o.z += h * profile;
        o.xy += shore.zw * (surge * peak * peak + lean);
        float age = (BO_PI * 0.5 - th) / (2.0 * BO_PI);
        float cyc = age - floor(age);
        float pulse = BO_Smooth(0.02, 0.20, cyc) * (1.0 - BO_Smooth(0.32, 0.90, cyc));
        float front = clamp(1.5 + incoming[t2] * 0.045, 1.5, 9.0) * pulse;
        float wet = (1.0 - BO_Smooth(front - 0.7, front + 0.3, max(0.0, -d))) * BO_Smooth(0.0, 0.07, pulse) * blend * washZone;
        wetness = max(wetness, wet * BO_Smooth(5.0, 55.0, incoming[t2]));
        // Foam: the broken crest runs shoreward as a roller after the lip falls (just past the peak), then leaves lace.
        float broken = BO_Smooth(0.5, 0.95, ratio) * blend * water;
        float roller = BO_Smooth(0.55, 0.95, peak) * (cos(th) < 0.0 ? 1.0 : 0.35);
        foam.x = max(foam.x, broken * roller * BO_Smooth(8.0, 40.0, incoming[t2]));
        foam.y = max(foam.y, wet * (1.0 - BO_Smooth(0.15, 0.9, cyc)));
    }
    o.z += sea.RunUp * wetness * 0.55;
    return o;
}

// The wind sea's displacement from the FFT cascade textures: A = (Dx, Dy, H cm, foam) in each tile's turned frame.
float3 BO_Cascade(float2 xy, Texture2D A, SamplerState S, float4 info, float lod)
{
    if (info.w < 0.5) return 0;
    float c = cos(info.y), s = sin(info.y);
    float2 uv = float2(c * xy.x + s * xy.y, -s * xy.x + c * xy.y) / info.x;
    float3 d = Texture2DSampleLevel(A, S, uv, lod).xyz;
    return float3(c * d.x - s * d.y, s * d.x + c * d.y, d.z);
}

float BO_CrestBound(BOSea sea)
{
    float v = sea.WindVar;
    [unroll] for (int i = 0; i < 5; i++) v += 0.5 * sea.W[i].w * sea.W[i].w;
    return 5.2 * sqrt(v);
}

// Swell part of Displacement(): everything but the wind sea.
float3 BO_Swells(BOSea sea, float4 shore, float2 xy)
{
    float d = shore.x;
    float openAtt = BO_Smooth(0.15, 1.2, shore.y) * BO_Smooth(0.0, 5.0, d);
    float depthLimit = min(1.0, 0.39 * max(0.0, shore.y) * 100.0 / max(1.0, BO_CrestBound(sea)));
    float blend = BO_SurfBlend(shore);
    float3 o = 0;
    [unroll] for (int i = 0; i < 5; i++)
    {
        float4 w = sea.W[i];
        if (w.w <= 0.01) continue;
        float sp = w.z * dot(w.xy, xy);
        float th = sp - sqrt(BO_G * w.z) * sea.Time + sea.Phase[i];
        float waterType = i < 3 ? 1.0 - blend : 1.0;
        float baseA = w.w * openAtt * depthLimit * waterType;
        float a = baseA * BO_Shoaling(w.z, shore.y) * BO_SwellGroup(w.z, sp, sea.Time, i);
        float ha = sea.Q * min(a, baseA / 1.07);
        float c = cos(th);
        o.xy += w.xy * ha * c;
        o.z += a * sin(th);
    }
    return o;
}

float BO_WindSeaAmp(BOSea sea, float4 shore)
{
    float openAtt = BO_Smooth(0.15, 1.2, shore.y) * BO_Smooth(0.0, 5.0, shore.x);
    float depthLimit = min(1.0, 0.39 * max(0.0, shore.y) * 100.0 / max(1.0, BO_CrestBound(sea)));
    return openAtt * depthLimit * lerp(0.12, 1.0, BO_Smooth(1.5, 14.0, shore.y));
}

// Slope and squeeze of one cascade at a rest point, turned into the world frame: xy height gradient, z 1 - Jacobian.
float3 BO_CascadeSlope(float2 xy, Texture2D B, SamplerState SB, Texture2D Cc, SamplerState SC, float4 info)
{
    if (info.w < 0.5) return 0;
    float c = cos(info.y), s = sin(info.y);
    float2 uv = float2(c * xy.x + s * xy.y, -s * xy.x + c * xy.y) / info.x;
    float2 g = Texture2DSample(B, SB, uv).xy;
    float3 j = Texture2DSample(Cc, SC, uv).xyz;   // Dxx, Dyy, Dxy
    float comp = 1.0 - ((1.0 + j.x) * (1.0 + j.y) - j.z * j.z);
    return float3(c * g.x - s * g.y, s * g.x + c * g.y, comp);
}
