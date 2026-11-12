# Biomes

23 presets, all on the same master material (`M_BiomeAuto`), so switching biome is just switching the landscape material instance (no shader recompile).

## TropicalIsland

Volcanic tropical island: coral-white beaches, lush grass and leaf litter over red laterite, dark wet rock.

<img src="Images/TropicalIsland_Overview.jpg" width="32%"> <img src="Images/TropicalIsland_Mountain.jpg" width="32%"> <img src="Images/TropicalIsland_Mesa.jpg" width="32%">

| Slot | Texture set | Source |
|---|---|---|
| Ground | `grass_dense` | [Grass004](https://ambientcg.com/view?id=Grass004) |
| GroundB | `litter_green` | [Leaves Forest Ground](https://polyhaven.com/a/leaves_forest_ground) |
| Soil | `soil_laterite` | [Red Laterite Soil Stones](https://polyhaven.com/a/red_laterite_soil_stones) |
| Shore | `sand_beach_white` | [Ground033](https://ambientcg.com/view?id=Ground033) |
| Scree | `coral_gravel` | [Coral Gravel](https://polyhaven.com/a/coral_gravel) |
| Rock | `rock_dark` | [Dark Rock](https://polyhaven.com/a/dark_rock) |
| RockB | `rock_mossy` | [Mossy Rock](https://polyhaven.com/a/mossy_rock) |

Overrides: `GroundB Amount` = 0.4, `Rock Moss` = 0.35, `Shore Height` = 2.2, `Scree Amount` = 0.25, `Wet Band` = 0.8, `Soil Angle` = 32.0, `Soil Patches` = 0.06, `Moss Color` = (0.04, 0.065, 0.02)

## Rainforest

Equatorial rainforest floor: wet leaf litter, moss, red clay, mossy boulders; always damp.

<img src="Images/Rainforest_Overview.jpg" width="32%"> <img src="Images/Rainforest_Mountain.jpg" width="32%"> <img src="Images/Rainforest_Mesa.jpg" width="32%">

| Slot | Texture set | Source |
|---|---|---|
| Ground | `litter_mossy` | [Forest Leaves 02](https://polyhaven.com/a/forest_leaves_02) |
| GroundB | `mud_leaves` | [Brown Mud Leaves 01](https://polyhaven.com/a/brown_mud_leaves_01) |
| Soil | `soil_redmud` | [Red Mud Stones](https://polyhaven.com/a/red_mud_stones) |
| Shore | `mud_beach` | [Ground054](https://ambientcg.com/view?id=Ground054) |
| Scree | `mud_mossy` | [Brown Mud Rocks 01](https://polyhaven.com/a/brown_mud_rocks_01) |
| Rock | `rock_mossy` | [Mossy Rock](https://polyhaven.com/a/mossy_rock) |
| RockB | `rock_lichen` | [Lichen Rock](https://polyhaven.com/a/lichen_rock) |

Overrides: `GroundB Amount` = 0.45, `Rock Moss` = 0.7, `Wetness` = 0.35, `Puddles` = 0.25, `Soil Patches` = 0.25, `Rock Angle` = 46.0, `Moss Color` = (0.03, 0.06, 0.02)

## Swamp

Bayou / bog: carpets of moss and mud, standing water in the hollows, algae-stained rock.

| Slot | Texture set | Source |
|---|---|---|
| Ground | `moss_green` | [Moss002](https://ambientcg.com/view?id=Moss002) |
| GroundB | `mud_mossy` | [Brown Mud Rocks 01](https://polyhaven.com/a/brown_mud_rocks_01) |
| Soil | `mud_forest` | [Ground024](https://ambientcg.com/view?id=Ground024) |
| Shore | `mud_beach` | [Ground054](https://ambientcg.com/view?id=Ground054) |
| Scree | `river_stones` | [River Small Rocks](https://polyhaven.com/a/river_small_rocks) |
| Rock | `rock_mossy` | [Mossy Rock](https://polyhaven.com/a/mossy_rock) |
| RockB | `rock_grey` | [Gray Rocks](https://polyhaven.com/a/gray_rocks) |

Overrides: `GroundB Amount` = 0.5, `Wetness` = 0.55, `Puddles` = 0.7, `Wet Band` = 1.5, `Shore Height` = 1.0, `Rock Moss` = 0.8, `Soil Patches` = 0.3

## TemperateMeadow

Rolling European grassland with wild patches, bare soil on banks, grey lichen rock and snowy peaks.

| Slot | Texture set | Source |
|---|---|---|
| Ground | `grass_meadow` | [Grass001](https://ambientcg.com/view?id=Grass001) |
| GroundB | `grass_sparse` | [Sparse Grass](https://polyhaven.com/a/sparse_grass) |
| Soil | `soil_compact` | [Forest Ground 05](https://polyhaven.com/a/forest_ground_05) |
| Shore | `sand_beach` | [Coast Sand 01](https://polyhaven.com/a/coast_sand_01) |
| Scree | `scree_broken` | [Rocks Ground 06](https://polyhaven.com/a/rocks_ground_06) |
| Rock | `rock_grey` | [Gray Rocks](https://polyhaven.com/a/gray_rocks) |
| RockB | `rock_lichen` | [Lichen Rock](https://polyhaven.com/a/lichen_rock) |
| Snow | `snow_fresh` | [Snow 02](https://polyhaven.com/a/snow_02) |

Overrides: `GroundB Amount` = 0.35, `Snow Line` = 180.0, `Rock Moss` = 0.25

## TemperateForest

Deciduous woodland: green leaf litter, twigs, dark forest soil, mossy outcrops.

| Slot | Texture set | Source |
|---|---|---|
| Ground | `litter_green` | [Leaves Forest Ground](https://polyhaven.com/a/leaves_forest_ground) |
| GroundB | `litter_twigs` | [Forest Ground 01](https://polyhaven.com/a/forrest_ground_01) |
| Soil | `soil_forest` | [Forest Ground 04](https://polyhaven.com/a/forest_ground_04) |
| Shore | `pebbles_river` | [Ganges River Pebbles](https://polyhaven.com/a/ganges_river_pebbles) |
| Scree | `mud_mossy` | [Brown Mud Rocks 01](https://polyhaven.com/a/brown_mud_rocks_01) |
| Rock | `rock_mossy` | [Mossy Rock](https://polyhaven.com/a/mossy_rock) |
| RockB | `rock_face` | [Rock Face](https://polyhaven.com/a/rock_face) |

Overrides: `GroundB Amount` = 0.45, `Rock Moss` = 0.55, `Wetness` = 0.1, `Puddles` = 0.1

## AutumnForest

Beech/maple forest in October: orange leaf fall, leafy gravel, lichen-grey rock.

| Slot | Texture set | Source |
|---|---|---|
| Ground | `litter_autumn` | [Forest Leaves 03](https://polyhaven.com/a/forest_leaves_03) |
| GroundB | `litter_autumn2` | [Forest Leaves 04](https://polyhaven.com/a/forest_leaves_04) |
| Soil | `soil_leafy` | [Forest Ground 06](https://polyhaven.com/a/forest_ground_06) |
| Shore | `pebbles_river` | [Ganges River Pebbles](https://polyhaven.com/a/ganges_river_pebbles) |
| Scree | `scree_leafy` | [Leaf Scattered Gravel](https://polyhaven.com/a/leaf_scattered_gravel) |
| Rock | `rock_lichen` | [Lichen Rock](https://polyhaven.com/a/lichen_rock) |
| RockB | `rock_mossy` | [Mossy Rock](https://polyhaven.com/a/mossy_rock) |

Overrides: `GroundB Amount` = 0.45, `Rock Moss` = 0.3

## BorealTaiga

Northern conifer forest: pine needles and feather moss on sandy podzol, lichen granite, early snow.

| Slot | Texture set | Source |
|---|---|---|
| Ground | `needles` | [Forest Ground 03](https://polyhaven.com/a/forrest_ground_03) |
| GroundB | `moss_ground` | [Moss001](https://ambientcg.com/view?id=Moss001) |
| Soil | `needles_sand` | [Forest Sand 01](https://polyhaven.com/a/forrest_sand_01) |
| Shore | `pebbles_river` | [Ganges River Pebbles](https://polyhaven.com/a/ganges_river_pebbles) |
| Scree | `scree_trail` | [Rocky Trail](https://polyhaven.com/a/rocky_trail) |
| Rock | `rock_lichen` | [Lichen Rock](https://polyhaven.com/a/lichen_rock) |
| RockB | `rock_face` | [Rock Face](https://polyhaven.com/a/rock_face) |
| Snow | `snow_fresh` | [Snow 02](https://polyhaven.com/a/snow_02) |

Overrides: `GroundB Amount` = 0.4, `Snow Line` = 110.0, `Snow Cover` = 0.15, `Rock Moss` = 0.2

## Alpine

High mountains: short alpine turf, rocky soil, layered limestone/slate faces, talus and permanent snow.

| Slot | Texture set | Source |
|---|---|---|
| Ground | `grass_sparse` | [Sparse Grass](https://polyhaven.com/a/sparse_grass) |
| GroundB | `grass_dirt` | [Grass Ground](https://polyhaven.com/a/grass_ground) |
| Soil | `soil_rocky` | [Rocks Ground 05](https://polyhaven.com/a/rocks_ground_05) |
| Shore | `river_stones` | [River Small Rocks](https://polyhaven.com/a/river_small_rocks) |
| Scree | `scree_grey` | [Rock Ground](https://polyhaven.com/a/rock_ground) |
| Rock | `rock_mountain` | [Rock051](https://ambientcg.com/view?id=Rock051) |
| RockB | `rock_slate` | [Dark Rock 02](https://polyhaven.com/a/dark_rock_02) |
| Snow | `snow_fresh` | [Snow 02](https://polyhaven.com/a/snow_02) |

Overrides: `GroundB Amount` = 0.4, `GroundB Altitude Bias` = 0.004, `Snow Line` = 120.0, `Scree Amount` = 0.9, `Rock Angle` = 36.0, `Strata Amount` = 0.5, `Strata Scale` = 4.0, `Soil Angle` = 20.0

## ArcticTundra

Polar tundra: dead sedge, cushion moss and gravel, frost-shattered rock, lingering snow patches.

| Slot | Texture set | Source |
|---|---|---|
| Ground | `litter_dry` | [Dry Decay Leaves](https://polyhaven.com/a/dry_decay_leaves) |
| GroundB | `moss_ground` | [Moss001](https://ambientcg.com/view?id=Moss001) |
| Soil | `scree_trail` | [Rocky Trail](https://polyhaven.com/a/rocky_trail) |
| Shore | `pebbles_river` | [Ganges River Pebbles](https://polyhaven.com/a/ganges_river_pebbles) |
| Scree | `scree_pebbly` | [Rocks Ground 03](https://polyhaven.com/a/rocks_ground_03) |
| Rock | `rock_lichen` | [Lichen Rock](https://polyhaven.com/a/lichen_rock) |
| RockB | `rock_dark` | [Dark Rock](https://polyhaven.com/a/dark_rock) |
| Snow | `snow_dirty` | [Snow 04](https://polyhaven.com/a/snow_04) |

Overrides: `GroundB Amount` = 0.45, `Snow Line` = 40.0, `Snow Cover` = 0.35, `Snow Line Noise` = 40.0, `Scree Amount` = 0.8, `Soil Patches` = 0.3

## Glacier

Ice sheet and glacier: wind-packed snow, sastrugi, blue ice on slopes, moraine and dark nunataks.

| Slot | Texture set | Source |
|---|---|---|
| Ground | `snow_clean` | [Snow010A](https://ambientcg.com/view?id=Snow010A) |
| GroundB | `snow_wind` | [Snow008A](https://ambientcg.com/view?id=Snow008A) |
| Soil | `ice_glacier` | [Ice002](https://ambientcg.com/view?id=Ice002) |
| Shore | `ice_glacier` | [Ice002](https://ambientcg.com/view?id=Ice002) |
| Scree | `scree_grey` | [Rock Ground](https://polyhaven.com/a/rock_ground) |
| Rock | `rock_alpine` | [Rock028](https://ambientcg.com/view?id=Rock028) |
| RockB | `rock_slate` | [Dark Rock 02](https://polyhaven.com/a/dark_rock_02) |
| Snow | `snow_fresh` | [Snow 02](https://polyhaven.com/a/snow_02) |

Overrides: `GroundB Amount` = 0.5, `Soil Angle` = 18.0, `Soil Patches` = 0.1, `Snow Line` = -50.0, `Snow Cover` = 1.0, `Snow Max Angle` = 42.0, `Shore Height` = 1.0, `Scree Amount` = 0.5

## DesertDunes

Erg sand sea: ripple-marked dune sand, cracked interdune pans, honey sandstone outcrops.

| Slot | Texture set | Source |
|---|---|---|
| Ground | `sand_dune` | [Ground093C](https://ambientcg.com/view?id=Ground093C) |
| GroundB | `sand_fine` | [Sand 01](https://polyhaven.com/a/sand_01) |
| Soil | `dry_cracked` | [Dry Ground 01](https://polyhaven.com/a/dry_ground_01) |
| Shore | `sand_fine` | [Sand 01](https://polyhaven.com/a/sand_01) |
| Scree | `sand_gravel_dusty` | [Sandy Gravel 02](https://polyhaven.com/a/sandy_gravel_02) |
| Rock | `rock_sandstone` | [Worn Rock Natural 01](https://polyhaven.com/a/worn_rock_natural_01) |
| RockB | `rock_yellow` | [Rock 06](https://polyhaven.com/a/rock_06) |

Overrides: `GroundB Amount` = 0.3, `Soil Angle` = 90.0, `Soil Patches` = 0.12, `Rock Angle` = 44.0, `Strata Amount` = 0.6, `Strata Scale` = 1.8, `Strata Tint Amount` = 0.25, `Scree Amount` = 0.4, `Wet Band` = 0.2

## RockyDesert

Hamada / reg stone desert: desert pavement gravel, baked crust, banded granite kopjes.

| Slot | Texture set | Source |
|---|---|---|
| Ground | `sand_gravel_dusty` | [Sandy Gravel 02](https://polyhaven.com/a/sandy_gravel_02) |
| GroundB | `sand_gravelly` | [Gravelly Sand](https://polyhaven.com/a/gravelly_sand) |
| Soil | `dry_rocky` | [Dry Ground Rocks](https://polyhaven.com/a/dry_ground_rocks) |
| Shore | `sand_fine` | [Sand 01](https://polyhaven.com/a/sand_01) |
| Scree | `scree_stony` | [Rocks Ground 09](https://polyhaven.com/a/rocks_ground_09) |
| Rock | `rock_tiger` | [Tiger Rock](https://polyhaven.com/a/tiger_rock) |
| RockB | `rock_cliff` | [Cliff Side](https://polyhaven.com/a/cliff_side) |

Overrides: `GroundB Amount` = 0.4, `Soil Patches` = 0.25, `Scree Amount` = 0.8, `Wet Band` = 0.2

## RedCanyon

Colorado-plateau canyon country: red sand, layered red/orange sandstone cliffs with banded strata.

| Slot | Texture set | Source |
|---|---|---|
| Ground | `sand_red` | [Red Sand](https://polyhaven.com/a/red_sand) |
| GroundB | `red_cracked` | [Cracked Red Ground](https://polyhaven.com/a/cracked_red_ground) |
| Soil | `soil_redmud` | [Red Mud Stones](https://polyhaven.com/a/red_mud_stones) |
| Shore | `sand_red` | [Red Sand](https://polyhaven.com/a/red_sand) |
| Scree | `scree_red` | [Terrain Red 01](https://polyhaven.com/a/terrain_red_01) |
| Rock | `rock_orange` | [Rock Boulder Cracked](https://polyhaven.com/a/rock_boulder_cracked) |
| RockB | `rock_redsand` | [Rock Pitted Mossy](https://polyhaven.com/a/rock_pitted_mossy) |

Overrides: `GroundB Amount` = 0.35, `Rock Angle` = 34.0, `Strata Amount` = 0.9, `Strata Scale` = 3.0, `Strata Warp` = 2.0, `Strata Tint Amount` = 0.55, `Strata Tint` = (0.95, 0.62, 0.45), `Scree Amount` = 0.9, `Wet Band` = 0.2

## Savanna

East-African savanna: straw-dry grass, red laterite paths, weathered granite boulders.

| Slot | Texture set | Source |
|---|---|---|
| Ground | `grass_dry` | [Withered Grass](https://polyhaven.com/a/withered_grass) |
| GroundB | `grass_dirt` | [Grass Ground](https://polyhaven.com/a/grass_ground) |
| Soil | `soil_laterite` | [Red Laterite Soil Stones](https://polyhaven.com/a/red_laterite_soil_stones) |
| Shore | `sand_gravelly` | [Gravelly Sand](https://polyhaven.com/a/gravelly_sand) |
| Scree | `dry_rocky` | [Dry Ground Rocks](https://polyhaven.com/a/dry_ground_rocks) |
| Rock | `rock_boulder` | [Rock Boulder Dry](https://polyhaven.com/a/rock_boulder_dry) |
| RockB | `rock_tiger` | [Tiger Rock](https://polyhaven.com/a/tiger_rock) |

Overrides: `GroundB Amount` = 0.4, `Soil Patches` = 0.22, `Scree Amount` = 0.4

## Steppe

Continental steppe / prairie: tussock grass, dry ploughed loess, rough grey outcrops.

| Slot | Texture set | Source |
|---|---|---|
| Ground | `grass_dirt` | [Grass Ground](https://polyhaven.com/a/grass_ground) |
| GroundB | `grass_dry` | [Withered Grass](https://polyhaven.com/a/withered_grass) |
| Soil | `dry_field` | [Dry Mud Field 001](https://polyhaven.com/a/dry_mud_field_001) |
| Shore | `sand_gravelly` | [Gravelly Sand](https://polyhaven.com/a/gravelly_sand) |
| Scree | `soil_rocky` | [Rocks Ground 05](https://polyhaven.com/a/rocks_ground_05) |
| Rock | `rock_rough` | [Rock 04](https://polyhaven.com/a/rock_04) |
| RockB | `rock_coarse` | [Rock 08](https://polyhaven.com/a/rock_08) |

Overrides: `GroundB Amount` = 0.45, `Soil Patches` = 0.12

## Mediterranean

Garrigue coast: sun-dried grass, terra rossa, white limestone crags and pebble beaches.

| Slot | Texture set | Source |
|---|---|---|
| Ground | `grass_dry` | [Withered Grass](https://polyhaven.com/a/withered_grass) |
| GroundB | `grass_sparse` | [Sparse Grass](https://polyhaven.com/a/sparse_grass) |
| Soil | `soil_terrarossa` | [Red Dirt Mud 01](https://polyhaven.com/a/red_dirt_mud_01) |
| Shore | `pebbles_clean` | [Clean Pebbles](https://polyhaven.com/a/clean_pebbles) |
| Scree | `scree_stony` | [Rocks Ground 09](https://polyhaven.com/a/rocks_ground_09) |
| Rock | `rock_limestone` | [Marble Rock 02](https://polyhaven.com/a/marble_rock_02) |
| RockB | `rock_limestone2` | [Marble Cliff 02](https://polyhaven.com/a/marble_cliff_02) |

Overrides: `GroundB Amount` = 0.4, `Soil Patches` = 0.25, `Scree Amount` = 0.7, `Shore Height` = 1.2

## Volcanic

Young volcanic field: black tephra, grey ash, scorched soil, basalt cliffs, black-sand beach.

| Slot | Texture set | Source |
|---|---|---|
| Ground | `gravel_black` | [Gravel024](https://ambientcg.com/view?id=Gravel024) |
| GroundB | `regolith_rough` | [Moon 02](https://polyhaven.com/a/moon_02) |
| Soil | `burned` | [Burned Ground 01](https://polyhaven.com/a/burned_ground_01) |
| Shore | `gravel_black` | [Gravel024](https://ambientcg.com/view?id=Gravel024) |
| Scree | `gravel_grey` | [Ground Grey](https://polyhaven.com/a/ground_grey) |
| Rock | `rock_basalt` | [Rock031](https://ambientcg.com/view?id=Rock031) |
| RockB | `rock_basalt_cave` | [Rock035](https://ambientcg.com/view?id=Rock035) |
| Snow | `snow_dirty` | [Snow 04](https://polyhaven.com/a/snow_04) |

Overrides: `GroundB Amount` = 0.4, `Snow Line` = 170.0, `Scree Amount` = 0.7, `Strata Amount` = 0.35, `Strata Scale` = 2.0

## RockyCoast

North-Atlantic coast: salt-sprayed turf, shingle beaches, seaweed-dark low-tide rock, slate cliffs.

| Slot | Texture set | Source |
|---|---|---|
| Ground | `grass_meadow` | [Grass001](https://ambientcg.com/view?id=Grass001) |
| GroundB | `grass_sparse` | [Sparse Grass](https://polyhaven.com/a/sparse_grass) |
| Soil | `soil_rocky` | [Rocks Ground 05](https://polyhaven.com/a/rocks_ground_05) |
| Shore | `pebbles_dry` | [Dry River Pebbles](https://polyhaven.com/a/dry_river_pebbles) |
| Scree | `low_tide_rocks` | [Low Tide Rocks](https://polyhaven.com/a/low_tide_rocks) |
| Rock | `rock_seaside` | [Seaside Rock](https://polyhaven.com/a/seaside_rock) |
| RockB | `rock_slate` | [Dark Rock 02](https://polyhaven.com/a/dark_rock_02) |

Overrides: `GroundB Amount` = 0.4, `Shore Height` = 2.0, `Wet Band` = 1.4, `Rock Angle` = 34.0, `Scree Amount` = 0.5, `Strata Amount` = 0.3

## Moorland

Upland heath and bog: tawny moor grass, sphagnum moss, black peat, grey gritstone.

| Slot | Texture set | Source |
|---|---|---|
| Ground | `grass_dirt` | [Grass Ground](https://polyhaven.com/a/grass_ground) |
| GroundB | `moss_ground` | [Moss001](https://ambientcg.com/view?id=Moss001) |
| Soil | `mud_forest` | [Ground024](https://ambientcg.com/view?id=Ground024) |
| Shore | `mud_mossy` | [Brown Mud Rocks 01](https://polyhaven.com/a/brown_mud_rocks_01) |
| Scree | `scree_pebbly` | [Rocks Ground 03](https://polyhaven.com/a/rocks_ground_03) |
| Rock | `rock_grey` | [Gray Rocks](https://polyhaven.com/a/gray_rocks) |
| RockB | `rock_lichen` | [Lichen Rock](https://polyhaven.com/a/lichen_rock) |

Overrides: `GroundB Amount` = 0.4, `Wetness` = 0.2, `Puddles` = 0.35, `Soil Patches` = 0.2

## SaltFlat

Playa / salt pan: blinding white polygonal crust, damp margins, bare ochre hills.

| Slot | Texture set | Source |
|---|---|---|
| Ground | `riverbed_cracked` | [Mud Cracked Dry Riverbed 002](https://polyhaven.com/a/mud_cracked_dry_riverbed_002) |
| GroundB | `snow_frozen` | [Snow014](https://ambientcg.com/view?id=Snow014) |
| Soil | `dry_cracked` | [Dry Ground 01](https://polyhaven.com/a/dry_ground_01) |
| Shore | `sand_damp` | [Damp Beach Sand 02](https://polyhaven.com/a/damp_beach_sand_02) |
| Scree | `sand_gravel_dusty` | [Sandy Gravel 02](https://polyhaven.com/a/sandy_gravel_02) |
| Rock | `rock_sandstone` | [Worn Rock Natural 01](https://polyhaven.com/a/worn_rock_natural_01) |
| RockB | `rock_yellow` | [Rock 06](https://polyhaven.com/a/rock_06) |

Overrides: `GroundB Amount` = 0.3, `Soil Angle` = 8.0, `Shore Height` = 0.4, `Wet Band` = 0.3

## BurnedForest

After the wildfire: ash and charcoal, scorched litter, sooty rock.

| Slot | Texture set | Source |
|---|---|---|
| Ground | `burned` | [Burned Ground 01](https://polyhaven.com/a/burned_ground_01) |
| GroundB | `litter_dry` | [Dry Decay Leaves](https://polyhaven.com/a/dry_decay_leaves) |
| Soil | `soil_forest` | [Forest Ground 04](https://polyhaven.com/a/forest_ground_04) |
| Shore | `pebbles_river` | [Ganges River Pebbles](https://polyhaven.com/a/ganges_river_pebbles) |
| Scree | `scree_broken` | [Rocks Ground 06](https://polyhaven.com/a/rocks_ground_06) |
| Rock | `rock_dark` | [Dark Rock](https://polyhaven.com/a/dark_rock) |
| RockB | `rock_face` | [Rock Face](https://polyhaven.com/a/rock_face) |

Overrides: `GroundB Amount` = 0.3

## Lunar

Airless regolith (not an Earth biome): fine dust, impact-churned soil, dark basaltic rock.

| Slot | Texture set | Source |
|---|---|---|
| Ground | `regolith` | [Moon Dusted 01](https://polyhaven.com/a/moon_dusted_01) |
| GroundB | `regolith_rough` | [Moon 02](https://polyhaven.com/a/moon_02) |
| Soil | `regolith_rocks` | [Moon 04](https://polyhaven.com/a/moon_04) |
| Scree | `regolith_rocks` | [Moon 04](https://polyhaven.com/a/moon_04) |
| Rock | `rock_dark` | [Dark Rock](https://polyhaven.com/a/dark_rock) |
| RockB | `rock_basalt` | [Rock031](https://ambientcg.com/view?id=Rock031) |

Overrides: `GroundB Amount` = 0.4, `Soil Patches` = 0.2, `Sea Level` = -10000.0, `Wet Band` = -1000.0, `Rock Angle` = 45.0

## Martian

Iron-oxide desert of Mars (not an Earth biome): rust dust, cracked duricrust, red layered rock.

| Slot | Texture set | Source |
|---|---|---|
| Ground | `sand_red` | [Red Sand](https://polyhaven.com/a/red_sand) |
| GroundB | `red_cracked` | [Cracked Red Ground](https://polyhaven.com/a/cracked_red_ground) |
| Soil | `scree_red` | [Terrain Red 01](https://polyhaven.com/a/terrain_red_01) |
| Scree | `scree_red` | [Terrain Red 01](https://polyhaven.com/a/terrain_red_01) |
| Rock | `rock_desert_red` | [Rock029](https://ambientcg.com/view?id=Rock029) |
| RockB | `rock_orange` | [Rock Boulder Cracked](https://polyhaven.com/a/rock_boulder_cracked) |

Overrides: `GroundB Amount` = 0.4, `Sea Level` = -10000.0, `Wet Band` = -1000.0, `Strata Amount` = 0.6, `Strata Tint Amount` = 0.3, `Strata Tint` = (0.9, 0.6, 0.45)

