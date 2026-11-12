# Parameters

All lengths are metres and all angles degrees unless noted. Defaults are the master's; each biome instance overrides some (see `Tools/biomes.py`).

## Global

| Parameter | Default | Meaning |
|---|---|---|
| Sea Level | 0.0 | World Z (metres) of the water line. Shore, wet band and puddles are measured from it. |
| Landscape Quad Size | 1.0 | Metres per landscape quad (landscape X/Y scale / 100). Keeps texture sizes real-world. |
| Debug View | 0.0 | 1 = paint layer coverage: green ground, yellow GroundB, brown soil, beige shore, grey scree, slate/red rock A/B, white snow, blue puddles. |
| Use World Coordinates | False | Static switch: use world X/Y instead of landscape coordinates (for meshes, not landscapes). |
| Height Blend | 1.0 | How much texture heights decide the transitions (0 = plain crossfade). |
| Blend Softness | 0.12 | Width of a height transition (small = crisp stones in sand). |
| Hex Tiling | 1.0 | 1 = hex-tiling anti-repetition on ground layers (3 taps), 0 = plain tiling. Low material quality forces 0. |
| Hex Contrast | 0.6 | How much the texture's height steers the hex-tile seams. |
| Hex Rotation | 1.0 | Random rotation of the hex tiles (0 = none, 1 = full). |
| Far Scale | 0.27 | Far textures are 1/Far Scale larger (breaks repetition seen from afar). |
| Fade Start | 1500.0 | Distance (cm) where the far textures start. |
| Fade Length | 6000.0 | Distance (cm) over which near fades into far. |
| Macro Scale | 60.0 | Size (m) of the large-scale brightness variation. |
| Macro Strength | 0.18 | Strength of that brightness variation. |
| Macro Saturation | 0.15 | Strength of the large-scale saturation variation. |
| GroundB Amount | 0.35 | Share of flat ground covered by the second ground layer (0..1). |
| GroundB Scale | 1.0 | Size of the GroundB patches (1 = ~20 m patches). |
| GroundB Altitude Bias | 0.0 | GroundB coverage change per metre of altitude (e.g. 0.004: more dry grass higher up). |
| GroundB Slope Bias | 0.0 | GroundB coverage change per degree of slope. |
| Soil Angle | 24.0 | Slope (deg) from which bare soil takes over from the ground cover. |
| Soil Fade | 8.0 | Width (deg) of that transition. |
| Soil Patches | 0.15 | Bare-soil patches on flat ground (0..1). |
| Shore Height | 1.6 | Metres above Sea Level the shore layer (beach) reaches. |
| Shore Fade | 0.9 | Metres over which the beach fades into the land above. |
| Shore Noise | 1.4 | Metres of raggedness added to the beach line. |
| Shore Max Angle | 16.0 | Steeper than this (deg) the shore layer is not used (cliffs stay rock). |
| Scree Amount | 0.6 | Strength of loose rubble on talus slopes (0..1). |
| Scree Angle | 33.0 | Slope (deg) where scree collects: the angle of repose of loose rock is 30-37 deg. |
| Scree Width | 9.0 | Range (deg) around Scree Angle that holds scree. |
| Rock Angle | 40.0 | Slope (deg) from which bare rock shows. |
| Rock Fade | 7.0 | Width (deg) of the rock transition. |
| Rock Noise | 10.0 | Degrees of noise on the rock line so it follows no contour. |
| Strata Amount | 0.0 | 0 = RockB in noise patches, 1 = RockB in horizontal sedimentary bands. |
| Strata Scale | 2.5 | Thickness (m) of a stratum. |
| Strata Warp | 3.0 | Metres the bands wander up and down (folding). |
| Strata Tint Amount | 0.0 | Colour difference between bands (0..1), towards Strata Tint. |
| Rock Moss | 0.0 | Moss / lichen on upward-facing rock (0..1). |
| Strata Tint | (0.78, 0.62, 0.5) | Colour the strata bands are tinted towards. |
| Moss Color | (0.045, 0.06, 0.025) | Linear albedo of that moss. |
| RockB Amount | 0.4 | Share of the second rock (patches, or strata bands with Strata Amount). |
| Snow Amount | 1.0 | Master switch for snow (0 = no snow). |
| Snow Line | 100000.0 | Metres above Sea Level where snow starts. Real snowlines are 0-5000 m; set it to suit your world. |
| Snow Fade | 12.0 | Metres over which snow thickens above the snow line. |
| Snow Line Noise | 25.0 | Metres of raggedness on the snow line. |
| Snow Max Angle | 48.0 | Snow does not stay on surfaces steeper than this (deg), judged on the detailed normal so ledges keep it. |
| Snow Cover | 0.0 | Snow below the snow line (0..1): winter cover, patches in hollows. |
| Snow Smoothing | 0.6 | How much a snow blanket smooths the relief beneath it. |
| Wet Band | 0.6 | Metres above Sea Level that are wet (tide zone, splash). |
| Wetness | 0.0 | Rain wetness everywhere (0..1): porous layers darken and turn glossy. |
| Puddles | 0.0 | Standing water in flat hollows when wet (0..1). |

## Per layer

Every slot (`Ground`, `GroundB`, `Soil`, `Shore`, `Scree`, `Rock`, `RockB`, `Snow`) has these, named `<Slot> <Parameter>`.

| Parameter | Meaning |
|---|---|
| Color+Height | Packed texture: base colour (sRGB) + height in alpha. |
| Normal+Rough+AO | Packed texture: normal X/Y (DirectX), roughness, ambient occlusion. |
| Tile | Metres one repeat of the texture covers (real-world size of the photographed patch). |
| Aspect | Height/width of the photo. |
| Brightness | Albedo multiplier; the build calibrates it to the set's real-world albedo. |
| Saturation | Colour saturation multiplier. |
| Tint | Colour multiplier. |
| Normal | Normal-map strength. |
| Roughness | Roughness multiplier. |
| Height Bias | Raises (+) or lowers (-) the layer in height blends. |
| Porosity | How much the layer darkens when wet (soil 1, rock ~0.35, snow 0). |

## Layer stack

Bottom to top: **Ground** (flat cover) -> **GroundB** (patches) -> **Soil** (banks, patches) -> **Shore** (near Sea Level) -> **Scree** (talus slopes) -> **Rock** / **RockB** (steep, triplanar) -> **Snow** -> water (wet band, rain, puddles). Each layer is blended over the result with a height-aware blend, and a layer that is completely hidden by one above is never sampled.
