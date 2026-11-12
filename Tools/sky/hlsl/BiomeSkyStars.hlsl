// The night sky for any latitude, date and hour. The view ray is turned into equatorial coordinates (right ascension,
// declination) with the actor's local sidereal time, so the real stars, the Milky Way and the poles stand where they do.
// SkyNorth/SkyEast: world vectors of compass north and east. Frame: (sin lat, cos lat, local sidereal time rad, +-1 hemisphere).
float3 dir = normalize(-CamVec);
float3 nN = normalize(SkyNorth.xyz), nE = normalize(SkyEast.xyz);
float hN = dot(dir, nN), hE = dot(dir, nE), hU = dir.z;
float sinLat = Frame.x, cosLat = Frame.y;
float sinDec = clamp(hU * sinLat + hN * cosLat, -1.0, 1.0);
float cosDecCosH = hU * cosLat - hN * sinLat;
float hourAngle = atan2(-hE, cosDecCosH);
float raView = Frame.z - hourAngle;
float cosDec = sqrt(saturate(1.0 - sinDec * sinDec));
float3 v = float3(cosDec * cos(raView), cosDec * sin(raView), sinDec);   // equatorial direction of the view ray
float3 pole = normalize(nN * cosLat + float3(0.0, 0.0, 1.0) * sinLat);  // the north celestial pole in the world
float horizon = smoothstep(-0.02, 0.12, dir.z);
// Angular size of a pixel, so stars stay one or two pixels wide at any field of view and screen size.
float pix = max(length(ddx(dir)) + length(ddy(dir)), 1e-5);
float3 col = float3(0.0, 0.0, 0.0);
struct FSkyNoise
{
    float Hash(float3 p) { return frac(sin(dot(p, float3(127.1, 311.7, 74.7))) * 43758.5453); }
    float Value(float3 p)
    {
        float3 i = floor(p), f = frac(p);
        f = f * f * (3.0 - 2.0 * f);
        return lerp(lerp(lerp(Hash(i), Hash(i + float3(1, 0, 0)), f.x), lerp(Hash(i + float3(0, 1, 0)), Hash(i + float3(1, 1, 0)), f.x), f.y),
                    lerp(lerp(Hash(i + float3(0, 0, 1)), Hash(i + float3(1, 0, 1)), f.x), lerp(Hash(i + float3(0, 1, 1)), Hash(i + float3(1, 1, 1)), f.x), f.y), f.z);
    }
    float Fbm(float3 p) { return 0.5 * Value(p) + 0.25 * Value(p * 2.03) + 0.125 * Value(p * 4.11) + 0.0625 * Value(p * 8.27); }
};
FSkyNoise MN;

// How faint a star one can still see depends on how bright the sky is (SkyGlow: twilight, moonlight, the aurora, the
// lamps of a town; 1 = a full moon). The naked-eye limit is magnitude ~6.4 under a dark sky, ~4.5 under a full moon and
// ~1.5 in twilight; the Milky Way needs a limit fainter than ~5, so a bright moon or the dusk wash it away. Low down
// the stars dim through the long path of air (extinction, ~0.22 magnitudes per air mass).
float limitMag = 6.4 - 2.2 * log10(1.0 + 6.0 * max(SkyGlow, 0.0));
float limitFlux = pow(10.0, -0.4 * limitMag);
float extinction = exp(-0.2 * (1.0 / max(dir.z, 0.03) - 1.0));

// The constellations: the real bright stars (pirate_star_catalog.py), flux from magnitude, colour from B-V.
float sigma = pix * 0.85;
float near = 1.0 - 12.0 * sigma * sigma;
for (int i = 0; i < STAR_COUNT; i++)
{
    float4 s = STAR_DIR[i];
    float c = dot(v, s.xyz);
    if (c > near)
    {
        float t2 = 2.0 * (1.0 - c);                    // angle squared
        float tw = 0.75 + 0.25 * sin(Time * (2.3 + frac(i * 0.618) * 5.0) + i * 7.1);
        tw = lerp(1.0, tw, 1.0 - smoothstep(0.05, 0.5, dir.z));   // stars twinkle most near the horizon
        float seen = s.w * extinction;
        // Every star is a point: the eye (and a lens) cannot resolve one, so a bright star is not bigger, only brighter.
        // Its brightness is squeezed into what a screen can show, so the brightest stars do not bloom into discs.
        float peak = 0.75 * (1.0 - exp(-sqrt(seen) / 0.75));
        col += STAR_COL[i] * peak * smoothstep(limitFlux * 0.5, limitFlux * 2.0, seen) * tw * exp(-t2 / (2.0 * sigma * sigma));
    }
}

// The fainter naked-eye stars (magnitude 3.8-6.4), a hashed field with the real density: about one per 5 square degrees
// (some 4500 more over the whole sky), each a point one pixel across at any field of view.
for (int l = 0; l < 3; l++)
{
    float scale = (l == 0 ? 45.0 : (l == 1 ? 70.0 : 100.0));          // cells 1.3, 0.8 and 0.6 degrees across
    float prob = (l == 0 ? 0.12 : (l == 1 ? 0.05 : 0.017));          // more of the fainter ones, as in the sky
    float3 q = v * scale;
    float3 id = floor(q);
    float3 f = frac(q) - 0.5;
    float h1 = frac(sin(dot(id, float3(127.1, 311.7, 74.7))) * 43758.5453);
    float h2 = frac(sin(dot(id, float3(269.5, 183.3, 246.1))) * 43758.5453);
    float h3 = frac(h1 * 17.13 + h2 * 3.71);
    if (h2 < prob)
    {
        float3 off = (float3(h1, h3, frac(h1 * 7.77 + h3)) - 0.5) * 0.6;
        float dist = length(f - off);
        float magn = lerp(3.8 + l * 0.9, 4.8 + l * 0.9, h3);
        float flux = pow(10.0, -0.4 * magn) * extinction;
        float sg = min(pix * scale * 0.8, 0.25);
        float peak = 0.75 * (1.0 - exp(-sqrt(flux) / 0.75));
        float tw = 0.7 + 0.3 * sin(Time * (1.5 + h1 * 4.0) + h1 * 40.0);
        col += peak * tw * smoothstep(limitFlux * 0.5, limitFlux * 2.0, flux) * exp(-dist * dist / (2.0 * sg * sg))
             * lerp(float3(1.0, 0.8, 0.62), float3(0.72, 0.84, 1.0), h1);
    }
}
// The Milky Way and the unresolved starlight round it, from NASA's Deep Star Maps 2020 (Gaia DR2; pack_nasa_sky.py):
// a map in J2000 right ascension and declination, so the view ray (as it stood at midnight) is turned back into them.
// Sagittarius' bright core, the Cygnus rift and the Magellanic Clouds all stand where they are in the real sky.
float decl = asin(sinDec);
float ra = raView;
float2 muv = float2(frac(0.5 - ra / 6.2831853), 0.5 - decl / 3.14159265);
float3 mw = Texture2DSampleLevel(MilkyWay, MilkyWaySampler, muv, max(0.0, log2(pix / 0.0030680))).rgb;
col += mw * mw * MilkyWayGain * extinction * smoothstep(4.6, 6.2, limitMag);
col *= Intensity * Brightness;

// Shooting stars (sporadic meteors, grains of dust burning up ~100 km high). Time is cut into 30 s slots and each slot
// holds a meteor with probability 1 - sqrt(0.5) = 29.3 %, so any minute (two slots) has exactly a 50 % chance of one
// somewhere in the sky. What a meteor looks like follows life:
//  - it lasts 0.2-1.5 s and crosses 6-35 degrees (usually 10-15) at 14-46 degrees a second; the rare fireball is bigger,
//    slower, flickers as it breaks up and is several times brighter;
//  - the head flares up fast, then fades slowly along its whole run; behind the head the glowing trail thins out
//    exponentially (a bright point with a comet's tail, not a line of even brightness);
//  - most are white-blue, some yellow (sodium), some green (magnesium and oxygen); the trail is a little redder than
//    the head as the gas cools;
//  - a bright one leaves a faint greenish train along its path that lingers for a few seconds, widens and is blown
//    sideways by the high winds.
// The same seeded slot gives the same meteor on every machine (Time is the server clock).
float3 meteors = float3(0.0, 0.0, 0.0);
{
    const float period = 30.0;
    float slot = floor(Time / period);
    float tin = Time - slot * period;
    float rr[12];
    // An integer hash (PCG), identical on every GPU (sin() of a big argument is not).
    [unroll] for (int q = 0; q < 12; q++)
    {
        uint hh = uint(slot) * 747796405u + uint(q) * 2891336453u + 1u;
        hh = ((hh >> ((hh >> 28u) + 4u)) ^ hh) * 277803737u;
        hh = (hh >> 22u) ^ hh;
        rr[q] = float(hh & 0xFFFFFFu) / 16777216.0;
    }
    if (rr[0] < 0.2929)
    {
        bool fireball = rr[3] > 0.93;
        float span = 0.10 + 0.55 * rr[1] * rr[1] * rr[1];
        float speed = 0.25 + 0.55 * rr[2];
        if (fireball) { span *= 1.5; speed *= 0.6; }
        float life = clamp(span / speed, 0.2, 1.6);
        float bright = (0.9 + 4.1 * rr[4] * rr[4] * rr[4]) * (fireball ? 2.5 : 1.0);
        float trainLife = bright > 1.8 ? 1.5 + 2.5 * rr[10] : 0.0;
        float start = 0.5 + rr[5] * (period - 1.0 - life - trainLife * 2.2);
        float age = tin - start;
        if (age > 0.0 && age < life + trainLife * 2.2)
        {
            float az = rr[6] * 6.2831853;
            float el = 0.35 + 0.95 * rr[7];                          // starts 20-75 degrees up
            float3 A = float3(cos(az) * cos(el), sin(az) * cos(el), sin(el));
            float3 east = normalize(cross(float3(0.0, 0.0, 1.0), A));
            float3 upT = cross(A, east);
            float psi = rr[8] * 6.2831853;
            float3 B = cos(psi) * upT + sin(psi) * east;            // the way it travels
            float3 nrm = cross(A, B);                               // the pole of its great circle
            float off = dot(dir, nrm);                              // angle off the track
            float along = atan2(dot(dir, B), dot(dir, A));          // angle along it from where it began
            float3 tint = rr[9] < 0.15 ? float3(1.0, 0.72, 0.40)
                        : (rr[9] < 0.35 ? float3(0.65, 1.0, 0.80)
                        : (rr[9] < 0.50 ? float3(0.70, 0.85, 1.00) : float3(0.92, 0.95, 1.0)));
            if (age < life)
            {
                float tn = age / life;
                float head = span * tn;
                float d = head - along;                             // distance behind the head
                float hw = pix * (fireball ? 1.6 : 0.85);            // the head is a round point of light
                if (d > -hw * 4.0 && d < span * 0.6 && along > -0.003 && abs(off) < pix * 12.0)
                {
                    // Flares up in a quarter of its life, then dies away; a fireball flickers as it fragments.
                    float curve = tn < 0.25 ? (tn / 0.25) * (tn / 0.25) : exp(-(tn - 0.25) * 2.2);
                    if (fireball) curve *= 0.8 + 0.2 * sin(age * 62.0 + rr[3] * 40.0);
                    // The head: a round blob. The trail behind it: thin, brightest at the head, thinning out
                    // exponentially in brightness and a little in width, redder as the gas cools.
                    float headBlob = exp(-(d * d + off * off) / (2.0 * hw * hw));
                    float dt = max(d, 0.0);
                    float w = pix * (fireball ? 1.1 : 0.8) * lerp(1.0, 0.55, saturate(dt / (span * 0.5)));
                    float trail = exp(-dt / (span * 0.22)) * smoothstep(-hw, hw * 2.0, d) * exp(-off * off / (2.0 * w * w));
                    float3 hue = lerp(float3(0.95, 0.97, 1.0), tint, saturate(dt / (span * 0.3)));
                    meteors += hue * curve * bright * (0.8 * headBlob + 0.6 * trail);
                }
            }
            else
            {
                // The persistent train: the whole path, very faint and patchy, fading, spreading and drifting
                // sideways with the high wind.
                float t = age - life;
                float fade = exp(-t / (trainLife * 0.55));
                float w = pix * (1.0 + 1.2 * t);
                float o = off - t * 0.010;
                if (along > 0.0 && along < span)
                {
                    float ends = smoothstep(0.0, span * 0.12, along) * smoothstep(span, span * 0.8, along);
                    float patchy = 0.55 + 0.45 * sin(along * 230.0 + rr[11] * 6.28 + t * 1.3);
                    float across = exp(-o * o / (2.0 * w * w));
                    meteors += float3(0.50, 0.80, 0.66) * across * fade * ends * patchy * 0.012 * bright / (1.0 + t);
                }
            }
        }
    }
}
col += meteors * Meteors * Intensity * Brightness * 2.0 * extinction * smoothstep(1.5, 4.0, limitMag);

// Aurora (the frozen north): curtains of light 100-300 km up. They hang as folded sheets running east-west along the
// auroral oval, drift and ripple, and are striped by fine vertical rays (the field lines); green from oxygen at their
// sharp lower edge (557.7 nm), fading upwards into the dim red of high oxygen (630 nm), a purple fringe at the foot in
// the brightest. The stronger the storm, the further south (overhead) they reach.
if (Aurora > 0.001 && dir.z > 0.0)
{
    float3 glow = float3(0.0, 0.0, 0.0);
    float reach = lerp(420.0, 60.0, Aurora * Aurora);           // km north of the observer
    // Each pixel starts its 32 altitude slices at its own offset: fixed slices drew the thin sheets as stacked bands.
    float jit = frac(sin(dot(dir.xy * 1000.0, float2(12.9898, 78.233))) * 43758.5453);
    for (int st = 0; st < 32; st++)
    {
        float h = (st + jit) / 32.0;
        float alt = 100.0 + 220.0 * h;
        float2 q = float2(hN * Frame.w, hE) / max(dir.z, 0.05) * alt;   // km: x poleward, y east
        // The folds evolve over minutes and smaller kinks ripple along the sheet in tens of seconds.
        float fold = (MN.Fbm(float3(q.y * 0.0035 + Time * 0.004, Time * 0.03, 1.7)) - 0.5) * 380.0
                   + (MN.Value(float3(q.y * 0.02 - Time * 0.05, Time * 0.12, 4.1)) - 0.5) * 60.0;
        float across = q.x - reach - fold;
        float sheets = exp(-pow(across / 14.0, 2.0)) + 0.6 * exp(-pow((across - 95.0) / 22.0, 2.0)) + 0.35 * exp(-pow((across + 140.0) / 30.0, 2.0));
        // The rays run along the curtain (a few km/s) and flicker; brighter patches pulse and drift.
        float rays = 0.45 + 0.75 * pow(MN.Value(float3(q.y * 0.35 + Time * 0.9, Time * 0.7, 9.3)), 2.0);
        float pulse = 0.55 + 0.45 * MN.Value(float3(q.y * 0.012 - Time * 0.25, Time * 0.35, 2.2));
        float green = smoothstep(0.0, 0.05, h) * exp(-h * 5.0);
        float red = 0.22 * exp(-pow((h - 0.55) / 0.28, 2.0));
        float purple = 0.25 * Aurora * exp(-h * 40.0);
        glow += sheets * rays * pulse * (green * float3(0.18, 1.0, 0.42) + red * float3(1.0, 0.16, 0.3) + purple * float3(0.6, 0.2, 1.0));
    }
    col += glow / 32.0 * Aurora * AuroraGain * smoothstep(0.0, 0.08, dir.z);
}

// The moon. Its near side is NASA's map of the real moon (below), turned as it stands
// in the sky: lunar north towards the celestial pole, Mare Crisium on the west limb. It is lit by the real
// sun with the moon's own reflectance (Lommel-Seeliger: no darkening towards the limb, so the full moon is an evenly
// bright disc; a rough, uneven terminator; brighter still right at full, the opposition surge) and the ash-grey
// earthshine on the night side of a crescent. Low down the air reddens and dims it.
float3 md = normalize(MoonDir.xyz);
float3 sd = normalize(SunDir.xyz);
float moonR = 0.004527 * MoonScale;                     // the real angular radius (0.26 degrees) times MoonScale
float moonAngle = acos(clamp(dot(dir, md), -1.0, 1.0));
float3 up = normalize(pole - md * dot(pole, md));       // lunar north, towards the celestial pole
float3 right = cross(up, md);                           // on screen to the right of north as one faces the moon
float2 p = float2(dot(dir, right), dot(dir, up)) / moonR;
float r2d = dot(p, p);
float disc = 1.0 - smoothstep(1.0 - pix * 1.2 / moonR, 1.0, sqrt(r2d));
float lowSky = smoothstep(-0.01, 0.25, md.z);
float3 airTint = lerp(float3(1.0, 0.58, 0.32), float3(1.0, 0.97, 0.93), lowSky) * lerp(0.35, 1.0, lowSky);
float phaseCos = dot(sd, -md);                          // 1 at full moon
float fullness = 0.5 + 0.5 * phaseCos;
// The aureole: a faint glow round a bright moon from the air's forward scattering.
// (Dithered per pixel: a smooth glow this dark shows as rings in 8 bits.)
col += (1.0 - disc) * MoonDisk * airTint * 0.004 * fullness * fullness * exp(-max(moonAngle - moonR, 0.0) / 0.035)
     * (0.8 + 0.4 * MN.Hash(dir * 2600.0));
if (r2d < 1.3)
{
    col *= 1.0 - disc;                                  // the moon hides the stars behind it
    float pz = sqrt(saturate(1.0 - r2d));
    float3 s = float3(p.x, p.y, pz);                    // the point on the moon: x east, y north, z towards us
    float3 nrm = p.x * right + p.y * up - pz * md;       // the same point's normal in the sky's frame
    // The surface: NASA's LROC colour mosaic (CGI Moon Kit; longitude 0 at its centre, east to the right), the real
    // maria, highlands and ray craters, normalised so the highlands are 1.
    float lunarLat = asin(clamp(s.y, -1.0, 1.0));
    float lunarLon = atan2(s.x, s.z);
    float2 tuv = float2(0.5 + lunarLon / 6.2831853, 0.5 - lunarLat / 3.14159265);
    float3 albedo = Texture2DSampleLevel(MoonTex, MoonTexSampler, tuv, max(0.0, log2(pix / moonR / 0.0030680))).rgb;
    // Lommel-Seeliger reflectance, a rough terminator, and the opposition surge.
    float mu0 = dot(nrm, sd);
    float mu = pz;
    float rough = (MN.Fbm(s * 30.0) - 0.5) * 0.12;
    float lit = 2.0 * saturate(mu0) / (saturate(mu0) + mu + 1e-4) * smoothstep(-0.015, 0.05, mu0 + rough);
    float phaseDeg = degrees(acos(clamp(phaseCos, -1.0, 1.0)));
    float surge = 1.0 + 0.3 * exp(-phaseDeg / 6.0);
    // Earthshine: the night side lit by the nearly full Earth, strongest under a thin crescent.
    float earthshine = 0.012 * saturate(-phaseCos) * saturate(-mu0 * 3.0 + 0.2);
    col += disc * albedo * (lit * surge * 0.5 + earthshine) * MoonDisk * airTint;
}
return col * horizon;
