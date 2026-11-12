# Biome Sky

`ABiomeSkyEnvironment` (module `BiomeSky`) is a complete physical sky in one actor: the sun and moon where they really
stand for a latitude, date and time; the real stars and the Milky Way turning about the celestial pole; the moon's
phase lit by the sun; shooting stars and auroras; volumetric clouds and fog that follow the weather; rain and snow round
the camera; lightning; and an exposure floor that keeps nights and storms dark.

![Noon](Images/Sky_Noon.jpg)

| | |
|---|---|
| ![Sunset](Images/Sky_Sunset.jpg) | ![Night](Images/Sky_Night.jpg) |
| ![Overcast](Images/Sky_Overcast.jpg) | ![Storm](Images/Sky_Storm.jpg) |
| ![Stars](Images/Sky_Stars.jpg) | ![Aurora](Images/Sky_Aurora.jpg) |

## Setup

1. Remove any directional light, Sky Atmosphere, Sky Light, Exponential Height Fog and Volumetric Cloud from your level
   (the actor brings its own).
2. Place **Biome Sky Environment** (Place Actors, or drag the class in). Its Z is the ground: the planet's surface is
   put `GroundDepth` (100 m) below it, so seabeds a little lower still get sunlight.
3. Set **Latitude**, the **date**, **Time Of Day** and the **Weather**. Press Play: the clock runs at `SecondsPerGameHour`
   (60 s by default: a 24-minute day). Tick `bRunInEditor` to watch a day pass in the editor.

The actor does not replicate. In a networked game, set the same time, date and weather on every machine (the clouds
are a pure function of the seed, the time and the wind, so every client sees the same sky).

## How it works

### Sun and moon
`BiomeSkyAstronomy` holds a low-precision ephemeris (the Astronomical Almanac's sun, good to ~0.01 deg; Meeus' moon with
the equation of the centre, evection, variation and annual equation, a few tenths of a degree). From the date and time
it computes Julian days since J2000, Greenwich and local sidereal time, and each body's right ascension and
declination, then turns them into the local horizon frame (X north, Y east, Z up; `NorthOffset` rotates that onto your
level). `TimeOfDay` is local mean solar time by default (`bSolarTime`), or a zone time at `UtcOffsetHours`.

The sun is the atmosphere's light 0 with a real 0.545 deg disc, cloud shadows and per-pixel atmospheric transmittance
(red at dawn). It keeps lighting the high air after it sets, which is the twilight glow, and is gone at -18 deg.
The moon is light 1, so its light reddens and dims low down too. Its light follows the lit fraction cubed
(`MoonLightAmount ~ illumination^3`): a half moon gives about a tenth of the full moon's light (the opposition surge,
and a half disc is seen side-on).

### Stars, Milky Way and moon disc (`M_BiomeSky`)
The sky material turns each view ray into right ascension and declination using the actor's latitude and local
sidereal time (`SkyFrame`), so the sky is right at any place and hour:
- **135 real bright stars** (`Tools/sky/star_catalog.py`, J2000 positions, magnitudes and B-V colours) as true points,
  one or two pixels wide at any field of view, coloured by temperature, twinkling more near the horizon.
- **~4500 fainter naked-eye stars** as a hashed field with the real density.
- **A limiting magnitude** from the sky's brightness (twilight, moonlight, aurora): 6.4 under a dark sky, ~4.5 under a
  full moon, ~1.5 in twilight. The Milky Way needs better than ~5, so a bright moon or the dusk washes it away.
  Atmospheric extinction dims stars low down (~0.2 magnitudes per air mass).
- **The Milky Way** from NASA's Deep Star Maps 2020 (Gaia DR2), mapped in RA/Dec, so Sagittarius, the Cygnus rift and
  the Magellanic Clouds stand where they are.
- **The moon** is a sphere drawn in the shader with NASA's LROC colour map, lunar north towards the celestial pole,
  lit by the real sun direction: Lommel-Seeliger reflectance (no limb darkening, so a full moon is evenly bright), a
  rough terminator, the opposition surge, and ash-grey earthshine on a crescent's night side. `MoonDrawScale` enlarges it
  (default x5) because a wide game camera shows it far smaller than the eye perceives it.
- **Shooting stars**: 30 s slots, each with a 29.3% chance of a meteor, so any minute has a 50% chance of one. Real
  durations (0.2-1.5 s), speeds and colours (sodium yellow, magnesium green), a flaring head with a fading tail, rare
  fireballs, and a lingering train after bright ones. Integer-hashed, so every machine sees the same meteors.
- **Auroras** (`bAuroras`): folded curtains 100-320 km up, drifting and rippling, striped by rays, green at the sharp
  lower edge (557.7 nm oxygen) fading into high red (630 nm), with a purple fringe in strong displays. They sit on the
  poleward side of the sky; a stronger aurora reaches further overhead. Real auroras need a high latitude: try 65-70 deg.

### Clouds (`M_BiomeClouds`)
A volumetric cloud material in a 0.8-12 km shell, with separate physical bands that weather changes without rescaling
the sky:
- **Low cloud**: fair-weather cumulus groups with blue sky between them, growing into towering cumulonimbus with
  `Convection`. Bases are flat and firm, towers have lumpy cauliflower rims (three billow octaves, eroded edges).
- **Rain decks**: with `Precipitation` the cumulus merges into a lower stratiform deck. Seen from below it is dark,
  heavy and textured, with rolls lying across the wind and sagging cells, plus ragged scud under it.
- **Anvils**: strong convection spreads ice downwind into a broad frayed anvil at 6.4-9.6 km.
- **Cirrus**: thin fibrous ice at 9-11 km (`HighCloud`), gated into separate banks so it never repeats.
- Everything drifts with the wind (sheared with height), and detail is filtered by the camera's footprint so distant
  clouds don't shimmer. Lightning lights the volume from inside.

The cloud shapes use the engine's own volume noise (`/Engine/EngineSky/VolumetricClouds`), referenced, not copied.

### Weather, fog and exposure
A weather preset is an air mass (`FBiomeSkyWeatherState`: cover, convection, precipitation, high cloud, visibility,
storm, snow). Changing it blends over `WeatherBlendSeconds`: the clouds build ahead of the rain and clear after it, and
visibility blends in log space. Presets can be edited in `WeatherPresets`.

| Preset | Cover | Convection | Rain/snow | Visibility |
|---|---|---|---|---|
| Clear | 0.06 | 0.02 | 0 | 40 km |
| Fair | 0.36 | 0.12 | 0 | 25 km |
| Overcast | 0.74 | 0.26 | 0 | 15 km |
| Rain | 0.88 | 0.40 | 0.62 | 4 km |
| Storm | 0.95 | 0.85 | 0.95 | 1.5 km |
| Snow | 0.86 | 0.15 | 0.55 snow | 2.5 km |
| Fog | 0.55 | 0.05 | 0 | 0.3 km |

- **Fog** density comes from the visibility by Koschmieder's law (extinction = 3.912 / V). Light weather uses half of
  it (more would veil the sky). The haze hugs the ground, turns red-orange at sunset and is cut off short of the star dome.
- **Exposure floor**: auto exposure would brighten a moonless night to noon. The actor limits how far it opens
  (`NightExposureFloor`, `StormExposureFloor`, `DayExposureFloor`, EV100), closing in through twilight, so nights stay
  dark and storms gloomy. A storm by day is also 0.3-0.9 stops darker.
- **Rain and snow** are GPU particles (`M_BiomePrecipitation`): every quad of an instanced plane is placed by the
  vertex shader in a box that wraps round the camera. Rain falls at 6-9 m/s as motion-blurred streaks, snow at ~1 m/s
  as soft flakes that flutter; the wind carries both.
- **Lightning** strikes at random (exponential gaps, `LightningPerMinute`) during play, 8-70 km away, as a few return
  strokes. It lights the cloud volume from inside and the world through one point light.

## Reading the sky from other systems

Without linking the module:
- **Materials**: `MPC_BiomeSky` holds `SunDirection` (xyz, w = elevation deg), `MoonDirection` (xyz, w = phase),
  `Wind` (velocity m/s xy, speed, heading deg), `SkyState` (daylight 0-1, cloud cover, precipitation, storm),
  `Moonlight` (moonlight, illumination, lightning flash, snow) and `SkyTime`.
- **C++/Blueprint by reflection**: the first actor tagged `BiomeSky` has the read-only properties `SunDirection`,
  `MoonDirection`, `MoonPhase`, `WindVelocity`, `CloudCoverNow`, `DayLight`... `ABiomeOcean` reads `WindVelocity` this
  way, so the ocean follows the sky's wind automatically.

With the module: `ABiomeSkyEnvironment::FindSky(World)` and the Blueprint getters below.

## Properties

**Place and time**: `Latitude`, `Longitude`, `NorthOffset` (compass heading of world +X), `Year`/`Month`/`Day`,
`TimeOfDay`, `bSolarTime`, `UtcOffsetHours`, `SecondsPerGameHour`, `bTimeRunning`, `bRunInEditor`.

**Weather**: `Weather`, `CloudCover` (with its override toggle), `WindDirection` (compass, where the wind blows to),
`WindSpeed` (m/s), `WeatherBlendSeconds`, `CloudSeed`, `CloudDensityScale`, `bPrecipitationParticles`,
`MaxPrecipitationParticles`, `bLightning`, `LightningPerMinute`, `WeatherPresets`.

**Night**: `bAuroras`, `AuroraStrength`, `bShootingStars`, `StarBrightness`, `MilkyWayBrightness`, `MoonDrawScale`,
`MoonBrightness`, `MoonPhaseOverride` (with its toggle).

**Exposure**: `SunIntensity` (lux), `MoonIntensity`, `bExposureFloor`, `NightExposureFloor`, `StormExposureFloor`,
`DayExposureFloor`, `ExposureBias`, `VisibilityScale`, `GroundDepth`.

**Assets** (advanced): the sky, cloud and precipitation materials, the parameter collection and the meshes.

**Blueprint functions**: `SetTimeOfDay`, `SetDate`, `SetLocation`, `SetTimeRunning`, `SetWeather(Preset, BlendSeconds)`,
`SetCloudCover`, `SetWind`, `SnapToTarget`; getters `GetSunDirection`, `GetMoonDirection`, `GetSunElevation`,
`GetMoonPhase`, `GetMoonIllumination`, `GetMoonLight`, `GetDayLight`, `IsNight`, `GetWindVelocity`, `GetCloudCover`,
`GetCurrentWeather`, `GetTimeOfDay`, `GetDaysSinceJ2000`, `GetPreset`, `FindSky`.

## Building the assets

```bash
pip install numpy pillow
python Tools/sky/fetch_sky_textures.py      # NASA moon and Milky Way maps -> Build/Sky
```
Then run `Tools/sky/build_sky_assets.py` in the editor. It creates `T_MoonColor`, `T_MilkyWay`, `MPC_BiomeSky`,
`M_BiomeSky`, `M_BiomeClouds` and `M_BiomePrecipitation` under `/BiomeAutoMaterials/Sky`.

## Performance

The volumetric clouds are the main cost (as with the engine's own clouds): `Clouds.ViewSampleCountScale` (2 by
default) and the `r.VolumetricCloud.*` scalability settings trade quality for speed. The star field costs a fixed
loop over 135 stars plus three hash layers per sky pixel; the aurora's 32-step march runs only when it is on and the
sun is down. Directional lights only turn when the sky has moved 0.15 deg, so virtual shadow maps aren't re-rendered
every frame.

## Credits

- Moon: NASA's Scientific Visualization Studio, *CGI Moon Kit* (LRO/LROC colour mosaic), https://svs.gsfc.nasa.gov/4720
- Milky Way: NASA/Goddard Space Flight Center Scientific Visualization Studio, *Deep Star Maps 2020*, with data from
  ESA/Gaia/DPAC, https://svs.gsfc.nasa.gov/4851
- NASA imagery is not protected by copyright in the United States and may be used freely; NASA asks for credit and that
  its insignia are not used to imply endorsement (https://www.nasa.gov/nasa-brand-center/images-and-media/). The maps are
  downloaded by the fetch script and packed into the release; the repository does not contain them.
- Star positions, magnitudes and colour indices are public astronomical data (Yale Bright Star Catalogue / Hipparcos).
