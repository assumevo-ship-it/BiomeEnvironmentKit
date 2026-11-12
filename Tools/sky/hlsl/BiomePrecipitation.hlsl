// Rain streaks or snowflakes in a box that follows the camera (ABiomeSkyEnvironment::Precipitation). Every particle is a
// quad of the plane mesh; this vertex code places it from its per-instance random number, so nothing is simulated on the
// CPU. Inputs: UV, Pos (world position, no offsets), Cam, Rand (per instance), Time, Density (0-1 share shown), Snow
// (0 rain .. 1 snow), Wind (cm/s), Box (half extents cm), Streak (seconds of travel drawn as the streak).
float r1 = frac(Rand * 1.0);
float r2 = frac(sin(Rand * 12.9898 + 0.31) * 43758.5453);
float r3 = frac(sin(Rand * 78.2330 + 0.77) * 24634.6345);
float r4 = frac(sin(Rand * 39.4250 + 0.11) * 56445.2357);
float shown = r4 < Density ? 1.0 : 0.0;
float3 B = Box.xyz;
// Raindrops fall at their terminal speed (6-9 m/s for 1-3 mm drops); flakes at about 1 m/s and drift with the air.
float fall = lerp(850.0 * (0.75 + 0.35 * r1), 95.0 * (0.7 + 0.6 * r1), Snow);
// The wind carries all of them, each a little more or less in the gusts; snow flutters as it falls.
float gustSpread = lerp(0.12, 0.3, Snow) * length(Wind.xy);
float3 vel = float3(Wind.xy * lerp(1.0, 0.8, Snow) + (float2(r2, r3) - 0.5) * 2.0 * gustSpread, -fall);
float3 p = (float3(r1, r2, r3) - 0.5) * 2.0 * B + vel * Time;
float swayT = Time * (0.6 + r2 * 0.9) + r3 * 6.2831;
p.xy += Snow * float2(sin(swayT), cos(swayT * 1.3)) * (25.0 + 30.0 * r4);
float3 rel = (frac((p - Cam) / (2.0 * B) + 0.5) - 0.5) * 2.0 * B;
p = Cam + rel;
float3 toCam = Cam - p;
float dist = max(length(toCam), 1.0);
toCam /= dist;
float3 up = vel - toCam * dot(vel, toCam);
float sl = length(up);
up = sl > 1.0 ? up / sl : float3(0.0, 0.0, 1.0);
float3 right = normalize(cross(up, toCam));
// A drop is drawn as its travel during the frame (the eye and a camera blur it so); a flake is a small soft disc.
float len = lerp(min(length(vel) * Streak, 90.0), max(0.6, dist * 0.0012), Snow);
float wide = lerp(max(0.12, dist * 0.0008), max(0.6, dist * 0.0012), Snow);
float thin = lerp(saturate(0.12 / wide * 2.5), saturate(0.6 / wide * 2.0), Snow);
float2 corner = UV * 2.0 - 1.0;
float3 world = p + right * (corner.x * wide * 0.5) + up * (corner.y * len * 0.5);
// Fade near the eye and at the box's edges, so the wrapping never shows.
float edge = 1.0 - smoothstep(0.72, 1.0, max(max(abs(rel.x) / B.x, abs(rel.y) / B.y), abs(rel.z) / B.z));
Alpha = shown * edge * smoothstep(lerp(150.0, 60.0, Snow), lerp(450.0, 200.0, Snow), dist) * thin * (0.6 + 0.4 * r2);
world = shown > 0.5 ? world : p;
return world - Pos;
