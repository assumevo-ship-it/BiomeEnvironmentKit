# Biome Ocean

`ABiomeOcean` (module `BiomeOcean`) is an open ocean in one actor: long swells from distant storms, a wind sea grown
from the wind's speed, fetch and duration, whitecaps where the crests are squeezed, surf that shoals, breaks and washes
up the beach wherever your terrain rises, and water height, normal and velocity queries for buoyancy and swimming that
come from the same model the GPU draws.

![Moderate sea](Images/Ocean_Moderate.jpg)

| | |
|---|---|
| ![Calm](Images/Ocean_Calm.jpg) | ![Gale](Images/Ocean_Gale.jpg) |
| ![Aerial](Images/Ocean_Aerial.jpg) | ![Shore](Images/Ocean_Shore.jpg) |

## Setup

1. Place **Biome Ocean**. Its Z is sea level. Remove any other water plane.
2. Set **Wind Speed** (m/s) and **Wind Direction** (the yaw the wind blows towards), or place a **Biome Sky
   Environment**: the ocean finds it and follows its wind (see *Wind sources*).
3. With land in the level, select the ocean and press **Bake Shore Field** (Details panel). It traces the ground round
   the actor (landscapes and meshes with collision) and stores depth, distance to the waterline and direction to the
   shore. Re-bake after editing the coast. Without a shore field the sea is open water everywhere.

The ocean uses the replicated server clock (`AGameStateBase::GetServerWorldTimeSeconds`) when there is a game state,
so every machine sees the same crest and boats float on it; the actor itself does not replicate.

## How it works

### Wave model (shared by CPU and GPU)
Everything is a pure function of time, the sea condition and the shore field, written twice: in C++
(`Source/BiomeOcean/Private/BiomeOceanModel.cpp`) and in HLSL (`Tools/ocean/hlsl/BiomeOceanCommon.hlsl`). Keep them in
step if you change either.

- **Five Gerstner swells** (150, 104, 78, 128 and 61 m, one of them a cross swell 52 deg off), each in energy-preserving
  wave groups, so crests grow and fade in sets. Their amplitude is `SwellAmount` x the sea condition's swell, which
  follows the wind from calm (0.45) to storm (1.8) when `bSwellFollowsWind` is on.
- **The wind sea** is Tessendorf FFT cascades (`UBiomeWindSea`): tiles of 1543 m, 251 m and 41 m, 256 x 256 each, turned
  against each other so their repeats never line up. Each holds the **JONSWAP** spectrum (peak enhancement 3.3 for a
  young sea, easing to Pierson-Moskowitz when fully developed) with **Mitsuyasu** directional spreading (narrowest at
  the peak). Neighbouring cascades share the waves near their split, so no band is missing or doubled. The spectrum is
  rescaled to exactly its expected variance, not the luck of the random draw. The FFTs run on worker threads every
  frame on every machine (the server included); only machines that draw it upload textures.
- **Sea growth** (`FBiomeSeaCondition`): the fetch is kept as the dimensionless g X / U^2 (about 20000 is fully
  developed). The sea is fetch-limited by `FetchKm` and duration-limited by `WindDurationHours` (Shore Protection Manual
  growth: g t / U = 68.8 X^(2/3)). With `bGrowSeaOverTime`, a rising wind builds the sea over minutes
  (`SeaGrowthTimeScale`), and a falling wind, or one that swings by more than 50 deg, leaves its old sea running as swell
  in its own direction while a new wind sea starts under it: the crossed sea after a front. `CrossSeaHeight` adds such
  an old sea by hand.
- **Shallows**: swells shoal with real finite-depth dispersion (k h tanh k h = k0 h, amplitude ~ sqrt(cg0 / cg)), are
  capped so no crest is higher than 0.39 x depth, and the wind sea calms over the shelf.
- **Surf**: on the shore field the three longest swells continue as individual breakers. Each breaker has its own height
  from sets and lulls, wave-to-wave scatter and short crests along the beach (an integer hash, identical on CPU and
  GPU). Zero-mean harmonics give them a narrow peaked crest and a steep shoreward face that pitches forward as the
  depth runs out. A swash then runs up and back down the sand (fast uprush, slower retreat).

### Queries
`GetWaterHeightAt` finds the water particle whose displaced position lands on the point (the surface is displaced
horizontally too, so the height under a point is not the displacement at that point) by a damped fixed-point
inversion, then returns its height. `GetWaterSurfaceAt` adds the normal and the water's velocity there (cm/s) by finite
differences, for buoyancy, swimming and spray. The FFT field is sampled bilinearly with the texture's own texel
convention and extrapolated a frame forward, so the CPU height matches the drawn crest.

### Drawing
- **Grid**: a radial-growth grid of (2N+1)^2 vertices that follows the camera, from 20-60 cm cells under it to 20 km at
  the horizon, snapped so it never swims. The vertex shader displaces it with the same model; the wind sea's texture
  level follows the local cell size, so far vertices don't alias short waves.
- **Normals**: per pixel, from the swells' analytic gradient and the FFT slope textures (squeezed by the horizontal
  displacement's Jacobian), fading the short cascades with distance.
- **Roughness**: the slopes no texel resolves become roughness. The total mean square slope for the wind comes from
  Cox & Munk's sun-glitter measurements (0.003 + 0.00512 U), minus what the textures already draw. A gale's sea glitters
  wide and soft, a calm one sharp. Specular F0 is water's 0.02.
- **Colour**: Single Layer Water with absorption and scattering per metre. Red is absorbed first, so deep water is
  sapphire. Over shallow sand (from the shore field) the scattering rises and it turns turquoise. The seabed shows
  through by its real depth.
- **Whitecaps**: on the CPU, every update finds the level of crest compression (1 - Jacobian) that leaves the wanted
  share of the sea breaking (Monahan's whitecap cover: none below ~4.5 m/s, ~2% in a fresh breeze, a quarter in a gale),
  measured on the field itself. Foam laid there stays with the water and fades over `FoamLifetime` (longer in strong
  winds). The pixel shader tears it into lace with noise, so there are no blobs and no streaks.
- **Surf foam**: broken crests roll in as a roller of foam, and the swash leaves a lace that sinks into the sand.

## Wind sources

The ocean takes its wind, in this order, from:
1. `WindSource`, if set: an actor implementing `IBiomeWindSource` (C++ or Blueprint: return the wind velocity in m/s),
   or any actor with an `FVector WindVelocity` property.
2. With `bFindWindSourceAutomatically`: the first actor in the level implementing the interface or tagged `BiomeSky`
   (the `BiomeSky` environment).
3. Its own `WindSpeed` and `WindDirection`.

## Properties

**Wind**: `WindSpeed` (m/s at 10 m: 3 light air, 8 fresh breeze, 14 near gale, 20 gale, 28 storm), `WindDirection` (yaw),
`FetchKm`, `WindDurationHours` (0 = fully grown), `bGrowSeaOverTime`, `SeaGrowthTimeScale`, `WindSource`,
`bFindWindSourceAutomatically`.

**Swell**: `SwellAmount`, `SwellDirection` (yaw), `bSwellFollowsWind`, `CrossSeaHeight` (m), `CrossSeaPeriod` (s),
`CrossSeaDirection`, `Seed`.

**Foam**: `WhitecapAmount` (1 = calibrated), `FoamLifetime` (s), `ShoreFoam`.

**Look**: `OceanMaterial`, `DeepAbsorption`, `DeepScattering`, `ShallowAbsorption`, `ShallowScattering` (per metre),
`WaterRoughness`, `FoamColor`.

**Quality**: `Quality` (Auto follows `sg.EffectsQuality`), `bPreviewInEditor`, `bUseServerTime`.

**Shore**: `ShoreBakeHalfSize` (cm), `ShoreBakeResolution`, `ShoreMaxDepth` (m), `ShoreTraceChannel`, and the buttons
`BakeShoreField` / `ClearShoreField`.

**Blueprint**: `GetWaterHeightAt`, `GetWaterSurfaceAt` (height, normal, velocity), `IsUnderwater`,
`GetSignificantWaveHeight` (Hs, m), `GetWaveDisplacementAt`, `GetWindVelocity`, `SetSeaCondition`, `FindOcean`.
C++: `GetWaterHeights` (many points at once), `GetSeaState`, `SampleShore`.

## Quality tiers and performance

| Tier | Grid | First cell | FFT cascades |
|---|---|---|---|
| Low | 257^2 | 60 cm | 1 (1.5 km tile) |
| Medium | 385^2 | 40 cm | 2 |
| High | 513^2 | 30 cm | 3 |
| Epic | 769^2 | 20 cm | 3 |

CPU: each cascade is four 256^2 inverse FFTs on the task graph (about 1-2 ms of worker time per cascade). The game
thread never waits: if an update isn't finished, it skips a frame. GPU: the vertex shader evaluates five swells, three
texture reads and the surf; the pixel shader nine texture reads plus the surf foam. Only the Shore half of that runs
near a coast.

## Building the material

Run `Tools/ocean/build_ocean_assets.py` in the editor. It creates `/BiomeAutoMaterials/Ocean/M_BiomeOcean`.
