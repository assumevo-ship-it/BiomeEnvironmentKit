# Island assets

261 static meshes for building islands, from the Polyester Pirates kit: trees and plants for every climate,
rocks and cliffs, coastal pieces, colonial and medieval buildings, a castle kit, docks, streets and props.
Real-world scale (1 unit = 1 cm), Nanite on every opaque mesh, PBR materials. They ship in three separate release zips
(`BiomeEnvironmentKit-IslandAssets-...zip`) to stay below GitHub's per-file limit. Download all three and unzip each over
the plugin; the assets appear under `Assets/`.

- Triangles in total: 24.0 M (Nanite streams them; the full-detail meshes are the source).
- Size: built on import.
- Collision: buildings, docks, castle, streets, cliffs and coastal rocks use their own triangles (you can walk
  in doors and up stairs); props, trees and loose rocks have a 26-sided hull; grass, flowers, ferns and debris none.
- Textures are capped at 2048 px for pieces over 8 m, 1024 px for most and 512 px for small props.

![Assets_Buildings.jpg](Images/Assets_Buildings.jpg)

![Assets_Docks.jpg](Images/Assets_Docks.jpg)

![Assets_Nature.jpg](Images/Assets_Nature.jpg)

![Assets_Nature_1.jpg](Images/Assets_Nature_1.jpg)

![Assets_Nature_2.jpg](Images/Assets_Nature_2.jpg)

![Assets_Nature_3.jpg](Images/Assets_Nature_3.jpg)

![Assets_Nature_4.jpg](Images/Assets_Nature_4.jpg)

![Assets_Nature_5.jpg](Images/Assets_Nature_5.jpg)

![Assets_Props_1.jpg](Images/Assets_Props_1.jpg)

![Assets_Props_2.jpg](Images/Assets_Props_2.jpg)

![Assets_Props_3.jpg](Images/Assets_Props_3.jpg)

![Assets_Props_4.jpg](Images/Assets_Props_4.jpg)

![Assets_Town_1.jpg](Images/Assets_Town_1.jpg)

![Assets_Town_2.jpg](Images/Assets_Town_2.jpg)

![Assets_Town_3.jpg](Images/Assets_Town_3.jpg)

## Scattering per biome

`Tools/assets/catalog.py` lists which assets suit each of the 23 biomes (trees, shrubs, ground cover, rocks,
coast, buildings). `Tools/assets/scatter_biome.py` places a biome's set on the open level's landscape by slope
and height above sea level (set `BAM_BIOME=<Name>` and run it in the editor). For dense grass use the Foliage
tool or a landscape grass type with the same meshes.

| Biome | Trees | Shrubs | Ground | Rocks | Coast | Buildings |
|---|---|---|---|---|---|---|
| TropicalIsland | Tree_Jungle_Kapok, Plant_Banana, Plant_Bamboo_Clump, Tree_Mangrove | Pachira, Bush_Broadleaf, Bush_Flowering | Grass_Bermuda, Sorrel, Anthurium, Calathea, Fern | Rock_Sandstone_Medium, Rock_A, Rock_B | CoastRocks_A, CoastRocks_B, CoastalCliff, SandRocks, Shell_Conch, Rock_River_Flat, Rock_Pebbles_Scatter | DockKit, PierKit_Scanned, Ladder_A, Ladder_B, Bollard_Iron, MooringPost_Rope, Warehouse, Shack_Stilts, Tavern, Hut_Trading, MarketStall, Watchtower, Well, FortKit, PalisadeKit |
| Rainforest | Tree_Jungle_Kapok, Plant_Bamboo_Clump, Plant_Banana | Pachira, Calathea, Anthurium, Bush_Broadleaf | Fern, Moss, Sorrel, Grass_Bermuda, BarkDebris, DryBranches, Root, RootCluster, TreeStump_B, DeadTrunk, PineRoots | Rock_Mossy_Large, Rock_Mossy_Medium, RockMossSet, RockMossSet_B | CoastRocks_A, CoastRocks_B, CoastalCliff, SandRocks, Shell_Conch, Rock_River_Flat, Rock_Pebbles_Scatter | Hut_Trading, Shack_Stilts |
| Swamp | Tree_Mangrove, Tree_Willow_Weeping, Tree_Dead_A, Tree_Dead_B_Snag | Bush_Broadleaf | Grass_Tall_Clump, Fern, Moss, Nettle, Weed, BarkDebris, DryBranches, Root, RootCluster, TreeStump_B, DeadTrunk, PineRoots | Rock_Mossy_Large, Rock_Mossy_Medium, RockMossSet, RockMossSet_B | - | Shack_Stilts, Hut_Trading, DockKit |
| TemperateMeadow | Tree_Oak_A, Tree_Oak_B, Tree_Birch | Shrub_A, Shrub_B, Bush_Flowering, Bush_Broadleaf | Grass_Medium_A, Grass_Medium_B, Dandelion, Celandine, Nettle, Periwinkle, Weed, Fern, Moss, Grass_Wheat_Patch, Grass_Tall_Clump | Rock_Granite_Large, Rock_Granite_Medium, Rock_Granite_Small, Boulder, Rock_A, Rock_B, Stone, Rock_Standing_Stone | CoastRocks_A, CoastRocks_B, CoastalCliff, SandRocks, Shell_Conch, Rock_River_Flat, Rock_Pebbles_Scatter | House_Timber_A, House_Timber_B, House_Timber_C, House_Timber_D_Tall, Cottage_Stone, Blacksmith_Forge, MarketHall, CastleKit, Castle_Gatehouse, Castle_Keep, StreetKit, Fountain_Square |
| TemperateForest | Tree_Oak_A, Tree_Oak_B, Tree_Birch, Tree_Maple_Red, Tree_Dead_A | Shrub_A, Shrub_B, Shrub_C, Shrub_D | Grass_Medium_A, Grass_Medium_B, Dandelion, Celandine, Nettle, Periwinkle, Weed, Fern, Moss, BarkDebris, DryBranches, Root, RootCluster, TreeStump_B, DeadTrunk, PineRoots | Rock_Mossy_Large, Rock_Mossy_Medium, RockMossSet, RockMossSet_B, Rock_Granite_Large, Rock_Granite_Medium, Rock_Granite_Small, Boulder, Rock_A, Rock_B, Stone | CoastRocks_A, CoastRocks_B, CoastalCliff, SandRocks, Shell_Conch, Rock_River_Flat, Rock_Pebbles_Scatter | Cottage_Stone, Watchtower |
| AutumnForest | Tree_Oak_Autumn, Tree_Maple_Red, Tree_Birch, Tree_Dead_A | Shrub_C, Shrub_D | DryBranches, BarkDebris, Fern, Moss, Grass_Medium_B, BarkDebris, DryBranches, Root, RootCluster, TreeStump_B, DeadTrunk, PineRoots | Rock_Mossy_Large, Rock_Mossy_Medium, RockMossSet, RockMossSet_B | CoastRocks_A, CoastRocks_B, CoastalCliff, SandRocks, Shell_Conch, Rock_River_Flat, Rock_Pebbles_Scatter | Cottage_Stone, House_Timber_A, House_Timber_B |
| BorealTaiga | Tree_Fir, Tree_Pine_Scots, Tree_Birch, Fir_Sapling, Pine_Sapling | Shrub_A, Shrub_B | Moss, Fern, PineRoots, BarkDebris, DryBranches, Grass_Medium_A | Rock_Mossy_Large, Rock_Mossy_Medium, RockMossSet, RockMossSet_B, Rock_Granite_Large, Rock_Granite_Medium, Rock_Granite_Small, Boulder, Rock_A, Rock_B, Stone | CoastRocks_A, CoastRocks_B, CoastalCliff, SandRocks, Shell_Conch, Rock_River_Flat, Rock_Pebbles_Scatter | PalisadeKit, Watchtower, Cottage_Stone |
| Alpine | Tree_Fir_Snowy, Tree_Pine_Snowy, Tree_Spruce_Snowy_Small, Tree_Fir | Bush_Snowy | Grass_Medium_A, Moss, Celandine | Rock_Granite_Large, Rock_Granite_Medium, Rock_Granite_Small, Boulder, Rock_A, Rock_B, Stone, RockFace_A, RockFace_B, Rock_Cliff_Chunk, Mountainside | - | Cottage_Stone, Watchtower |
| ArcticTundra | Tree_Spruce_Snowy_Small | Bush_Snowy | Moss, Grass_Medium_A | Rock_Granite_Large, Rock_Granite_Medium, Rock_Granite_Small, Boulder, Rock_A, Rock_B, Stone, Rock_River_Flat | CoastRocks_A, Rock_River_Flat | Shack_Stilts |
| Glacier | - | - | - | Rock_Granite_Large, Rock_Granite_Medium, Rock_Cliff_Chunk, RockFace_A, RockFace_B, Rock_Cliff_Chunk, Mountainside | - | - |
| DesertDunes | Tree_Acacia_Savanna | DeadBranch_A, DeadBranch_B | DryLeaves, Succulent_Othonna | DesertStones, DesertRocks | SandRocks | Bazaar_Stall_A, Bazaar_Stall_B, Well |
| RockyDesert | QuiverTree_A, QuiverTree_B, QuiverTree_Dead | RooibosBush, DeadBranch_A, DeadBranch_B | Succulent_Cheiridopsis, Succulent_Iceplant, Succulent_Leipoldtia, Succulent_Othonna, Flower_Gazania, Flower_Ursinia, Flower_Heliophila, Flower_Empodium, Flower_Stinkkruid, DryLeaves | DesertBoulder_A, DesertBoulder_B, DesertBoulder_C, DesertBoulders, DesertRocks, DesertStones, Rock_Tan_Desert, Rock_Sandstone_Large, Rock_Sandstone_Medium, DesertCliff_A, DesertCliff_B | SandRocks | Bazaar_Stall_A, Bazaar_Stall_C, Well, Watchtower |
| RedCanyon | QuiverTree_Dead | RooibosBush, DeadBranch_A | DryLeaves, Succulent_Othonna | DesertBoulder_A, DesertBoulder_B, DesertBoulder_C, DesertBoulders, DesertRocks, DesertStones, Rock_Tan_Desert, Rock_Sandstone_Large, Rock_Sandstone_Medium, DesertCliff_A, DesertCliff_B | - | Well |
| Savanna | Tree_Acacia_Savanna, QuiverTree_A | RooibosBush, Bush_Broadleaf | Grass_Dry_Savanna, Grass_Tall_Clump, DryLeaves | Rock_Tan_Desert, DesertBoulders, Rock_Sandstone_Medium | - | Hut_Trading, MarketStall, Well |
| Steppe | - | RooibosBush, DeadBranch_B | Grass_Dry_Savanna, Grass_Wheat_Patch, Grass_Medium_B, Weed | Rock_Granite_Small, Rock_Standing_Stone, Stone | - | Hut_Trading, Well |
| Mediterranean | Tree_Olive, Tree_Cypress | Shrub_A, Shrub_C, Bush_Flowering | Grass_Dry_Savanna, Grass_Medium_B, Flower_Gazania, Dandelion, Weed | Rock_Sandstone_Large, Rock_Sandstone_Medium, Rock_A, RockFace_A, RockFace_B, Rock_Cliff_Chunk, Mountainside | CoastRocks_A, CoastRocks_B, CoastalCliff, SandRocks, Shell_Conch, Rock_River_Flat, Rock_Pebbles_Scatter | Cottage_Stone, FortKit, Fountain_Square, MarketHall, DockKit, PierKit_Scanned, Ladder_A, Ladder_B, Bollard_Iron, MooringPost_Rope, Warehouse, Shack_Stilts |
| Volcanic | Tree_Dead_A, Tree_Dead_B_Snag | DeadBranch_B | Moss | Rock_Cliff_Chunk, RockFace_A, RockFace_B, Mountainside | CoastRocks_B, CoastalCliff | - |
| RockyCoast | Tree_Pine_Scots, Tree_Cypress | Shrub_B, Bush_Broadleaf | Grass_Medium_A, Moss, Weed | Rock_Granite_Large, Rock_Granite_Medium, Rock_Granite_Small, Boulder, Rock_A, Rock_B, Stone, RockFace_A, RockFace_B, Rock_Cliff_Chunk, Mountainside | CoastRocks_A, CoastRocks_B, CoastalCliff, SandRocks, Shell_Conch, Rock_River_Flat, Rock_Pebbles_Scatter | DockKit, PierKit_Scanned, Ladder_A, Ladder_B, Bollard_Iron, MooringPost_Rope, Warehouse, Shack_Stilts, Watchtower, FortKit |
| Moorland | Tree_Dead_B_Snag | Shrub_D, Shrub_B | Grass_Tall_Clump, Grass_Medium_A, Moss, Fern | Rock_Mossy_Large, Rock_Mossy_Medium, RockMossSet, RockMossSet_B, Rock_Standing_Stone | CoastRocks_A, CoastRocks_B, CoastalCliff, SandRocks, Shell_Conch, Rock_River_Flat, Rock_Pebbles_Scatter | Cottage_Stone |
| SaltFlat | - | - | - | DesertStones, Rock_Tan_Desert | - | Well |
| BurnedForest | Tree_Dead_A, Tree_Dead_B_Snag, QuiverTree_Dead | DeadBranch_A, DeadBranch_B, DryBranches | BarkDebris, DryLeaves, Root, TreeStump_B, DeadTrunk | Rock_Granite_Large, Rock_Granite_Medium, Rock_Granite_Small, Boulder, Rock_A, Rock_B, Stone | - | - |
| Lunar | - | - | - | Rock_Granite_Large, Rock_Granite_Medium, Rock_Granite_Small, Boulder | - | - |
| Martian | - | - | - | DesertBoulder_A, DesertBoulder_B, DesertBoulder_C, DesertBoulders, DesertRocks, DesertStones, Rock_Tan_Desert, Rock_Sandstone_Large, Rock_Sandstone_Medium, DesertCliff_A, DesertCliff_B | - | - |

## Contents

| Category | Asset | Triangles | Size (cm) | Collision |
|---|---|---|---|---|
| Buildings/Fort | `SM_FortKit` | 28,218 | 4267 x 7138 x 1367 |  |
| Buildings/Fort | `SM_Fort_Door` | 12,640 | 201 x 16 x 296 |  |
| Buildings/Fort | `SM_Fort_IronGate` | 38,140 | 295 x 10 x 293 |  |
| Buildings/Fortifications | `SM_PalisadeKit` | 21,378 | 420 x 151 x 538 |  |
| Buildings/Outpost | `SM_Gallows` | 19,296 | 407 x 260 x 480 |  |
| Buildings/Outpost | `SM_Hut_Trading` | 38,956 | 661 x 608 x 511 |  |
| Buildings/Outpost | `SM_MarketStall` | 35,240 | 436 x 297 x 272 |  |
| Buildings/Outpost | `SM_Shack_Stilts` | 103,544 | 578 x 607 x 653 |  |
| Buildings/Outpost | `SM_Warehouse` | 531,024 | 1380 x 913 x 858 |  |
| Buildings/Outpost | `SM_Watchtower` | 49,028 | 456 x 483 x 1192 |  |
| Buildings/Outpost | `SM_Well` | 21,732 | 260 x 196 x 322 |  |
| Buildings/Tavern | `SM_Tavern` | 1,001,052 | 1349 x 1257 x 1164 |  |
| Docks | `SM_DockKit` | 361,600 | 791 x 420 x 1052 |  |
| Docks | `SM_Ladder_A` | 8,492 | 96 x 50 x 133 |  |
| Docks | `SM_Ladder_B` | 6,126 | 99 x 62 x 172 |  |
| Docks | `SM_PierKit_Scanned` | 84,780 | 310 x 1903 x 752 |  |
| Nature/Arid | `SM_DeadBranch_A` | 14,834 | 25 x 23 x 44 |  |
| Nature/Arid | `SM_DeadBranch_B` | 14,386 | 29 x 20 x 53 |  |
| Nature/Arid | `SM_DesertBoulder_A` | 97,964 | 253 x 123 x 88 |  |
| Nature/Arid | `SM_DesertBoulder_B` | 59,066 | 252 x 250 x 190 |  |
| Nature/Arid | `SM_DesertBoulder_C` | 109,114 | 67 x 121 x 65 |  |
| Nature/Arid | `SM_DesertBoulders` | 40,850 | 106 x 59 x 25 |  |
| Nature/Arid | `SM_DesertCliff_A` | 94,369 | 828 x 439 x 496 |  |
| Nature/Arid | `SM_DesertCliff_B` | 194,080 | 2023 x 659 x 718 |  |
| Nature/Arid | `SM_DesertRocks` | 85,716 | 145 x 22 x 15 |  |
| Nature/Arid | `SM_DesertStones` | 70,124 | 102 x 11 x 8 |  |
| Nature/Arid | `SM_DryLeaves` | 78,720 | 40 x 19 x 42 |  |
| Nature/Arid | `SM_Flower_Empodium` | 3,053 | 132 x 28 x 27 |  |
| Nature/Arid | `SM_Flower_Gazania` | 14,340 | 144 x 71 x 24 |  |
| Nature/Arid | `SM_Flower_Heliophila` | 101,621 | 275 x 142 x 40 |  |
| Nature/Arid | `SM_Flower_Stinkkruid` | 80,716 | 171 x 30 x 18 |  |
| Nature/Arid | `SM_Flower_Ursinia` | 24,933 | 219 x 34 x 17 |  |
| Nature/Arid | `SM_QuiverTree_A` | 150,124 | 118 x 97 x 272 |  |
| Nature/Arid | `SM_QuiverTree_B` | 82,074 | 87 x 88 x 147 |  |
| Nature/Arid | `SM_QuiverTree_Dead` | 17,978 | 31 x 27 x 199 |  |
| Nature/Arid | `SM_RooibosBush` | 27,519 | 228 x 84 x 54 |  |
| Nature/Arid | `SM_Succulent_Cheiridopsis` | 82,438 | 216 x 96 x 27 |  |
| Nature/Arid | `SM_Succulent_Iceplant` | 13,094 | 169 x 74 x 8 |  |
| Nature/Arid | `SM_Succulent_Leipoldtia` | 385,504 | 231 x 81 x 32 |  |
| Nature/Arid | `SM_Succulent_Othonna` | 118,149 | 397 x 180 x 197 |  |
| Nature/Coastal | `SM_CoastRocks_A` | 679,936 | 5951 x 4252 x 329 |  |
| Nature/Coastal | `SM_CoastRocks_B` | 1,260,423 | 4596 x 4946 x 317 |  |
| Nature/Coastal | `SM_CoastalCliff` | 461,824 | 9198 x 1097 x 1033 |  |
| Nature/Coastal | `SM_RockMossSet` | 63,127 | 800 x 695 x 177 |  |
| Nature/Coastal | `SM_SandRocks` | 739,469 | 463 x 388 x 53 |  |
| Nature/Coastal | `SM_Shell_Conch` | 12,498 | 14 x 7 x 5 |  |
| Nature/Coastal | `SM_TreeStump` | 41,046 | 143 x 159 x 57 |  |
| Nature/Plants | `SM_Bush_Broadleaf` | 75,616 | 196 x 173 x 164 |  |
| Nature/Plants | `SM_Bush_Flowering` | 26,568 | 108 x 122 x 131 |  |
| Nature/Plants | `SM_Bush_Snowy` | 58,327 | 129 x 151 x 153 |  |
| Nature/Plants | `SM_Grass_Dry_Savanna` | 1,280 | 137 x 136 x 91 |  |
| Nature/Plants | `SM_Grass_Tall_Clump` | 1,120 | 98 x 99 x 79 |  |
| Nature/Plants | `SM_Grass_Wheat_Patch` | 3,520 | 115 x 116 x 123 |  |
| Nature/Rocks | `SM_Boulder` | 66,122 | 127 x 183 x 100 |  |
| Nature/Rocks | `SM_Mountainside` | 153,472 | 1021 x 525 x 1052 |  |
| Nature/Rocks | `SM_RockFace_A` | 20,174 | 495 x 383 x 356 |  |
| Nature/Rocks | `SM_RockFace_B` | 29,566 | 271 x 213 x 247 |  |
| Nature/Rocks | `SM_RockMossSet_B` | 57,647 | 828 x 341 x 137 |  |
| Nature/Rocks | `SM_Rock_A` | 14,844 | 17 x 32 x 14 |  |
| Nature/Rocks | `SM_Rock_B` | 12,416 | 7 x 14 x 3 |  |
| Nature/Rocks | `SM_Rock_Cliff_Chunk` | 81,920 | 1043 x 741 x 793 |  |
| Nature/Rocks | `SM_Rock_Granite_Large` | 81,920 | 571 x 448 x 243 |  |
| Nature/Rocks | `SM_Rock_Granite_Medium` | 20,480 | 312 x 256 x 134 |  |
| Nature/Rocks | `SM_Rock_Granite_Small` | 5,120 | 132 x 101 x 60 |  |
| Nature/Rocks | `SM_Rock_Mossy_Large` | 81,920 | 569 x 444 x 185 |  |
| Nature/Rocks | `SM_Rock_Mossy_Medium` | 20,480 | 251 x 176 x 111 |  |
| Nature/Rocks | `SM_Rock_Pebbles_Scatter` | 4,800 | 198 x 167 x 13 |  |
| Nature/Rocks | `SM_Rock_River_Flat` | 1,280 | 249 x 183 x 44 |  |
| Nature/Rocks | `SM_Rock_Sandstone_Large` | 81,920 | 744 x 489 x 144 |  |
| Nature/Rocks | `SM_Rock_Sandstone_Medium` | 20,480 | 319 x 232 x 74 |  |
| Nature/Rocks | `SM_Rock_Standing_Stone` | 1,280 | 127 x 96 x 357 |  |
| Nature/Rocks | `SM_Rock_Tan_Desert` | 1,280 | 368 x 334 x 175 |  |
| Nature/Rocks | `SM_Stone` | 53,520 | 15 x 9 x 7 |  |
| Nature/Temperate | `SM_BarkDebris` | 193,406 | 121 x 67 x 11 |  |
| Nature/Temperate | `SM_Celandine` | 8,966 | 224 x 31 x 19 |  |
| Nature/Temperate | `SM_Dandelion` | 54,764 | 421 x 26 x 17 |  |
| Nature/Temperate | `SM_DeadTrunk` | 83,128 | 405 x 106 x 106 |  |
| Nature/Temperate | `SM_DryBranches` | 16,803 | 106 x 130 x 34 |  |
| Nature/Temperate | `SM_Fern` | 6,232 | 197 x 172 x 43 |  |
| Nature/Temperate | `SM_Fir_Sapling` | 433,021 | 274 x 83 x 130 |  |
| Nature/Temperate | `SM_Grass_Medium_A` | 24,730 | 560 x 33 x 34 |  |
| Nature/Temperate | `SM_Grass_Medium_B` | 7,842 | 131 x 43 x 41 |  |
| Nature/Temperate | `SM_Moss` | 204 | 22 x 3 x 4 |  |
| Nature/Temperate | `SM_Nettle` | 31,304 | 108 x 9 x 22 |  |
| Nature/Temperate | `SM_Periwinkle` | 34,350 | 124 x 32 x 41 |  |
| Nature/Temperate | `SM_PineRoots` | 162,693 | 177 x 189 x 15 |  |
| Nature/Temperate | `SM_Pine_Sapling` | 398,144 | 264 x 77 x 130 |  |
| Nature/Temperate | `SM_Root` | 61,027 | 56 x 184 x 18 |  |
| Nature/Temperate | `SM_RootCluster` | 225,261 | 412 x 268 x 151 |  |
| Nature/Temperate | `SM_Shrub_A` | 156,012 | 259 x 22 x 40 |  |
| Nature/Temperate | `SM_Shrub_B` | 27,254 | 598 x 179 x 198 |  |
| Nature/Temperate | `SM_Shrub_C` | 8,287 | 137 x 15 x 40 |  |
| Nature/Temperate | `SM_Shrub_D` | 27,327 | 58 x 15 x 22 |  |
| Nature/Temperate | `SM_TreeStump_B` | 62,345 | 152 x 139 x 52 |  |
| Nature/Temperate | `SM_Weed` | 11,116 | 213 x 29 x 8 |  |
| Nature/Trees/Arid | `SM_Tree_Acacia_Savanna` | 216,062 | 817 x 695 x 976 |  |
| Nature/Trees/Boreal | `SM_Tree_Fir` | 401,142 | 854 x 940 x 1428 |  |
| Nature/Trees/Boreal | `SM_Tree_Fir_Snowy` | 382,140 | 786 x 712 x 1215 |  |
| Nature/Trees/Boreal | `SM_Tree_Pine_Scots` | 819,691 | 873 x 748 x 1931 |  |
| Nature/Trees/Boreal | `SM_Tree_Pine_Snowy` | 734,682 | 726 x 639 x 1570 |  |
| Nature/Trees/Boreal | `SM_Tree_Spruce_Snowy_Small` | 70,780 | 349 x 365 x 620 |  |
| Nature/Trees/Mediterranean | `SM_Tree_Cypress` | 309,303 | 226 x 223 x 1479 |  |
| Nature/Trees/Mediterranean | `SM_Tree_Olive` | 417,949 | 396 x 504 x 781 |  |
| Nature/Trees/Temperate | `SM_Tree_Birch` | 398,861 | 601 x 718 x 1404 |  |
| Nature/Trees/Temperate | `SM_Tree_Dead_A` | 4,134 | 379 x 617 x 1034 |  |
| Nature/Trees/Temperate | `SM_Tree_Dead_B_Snag` | 1,925 | 291 x 308 x 673 |  |
| Nature/Trees/Temperate | `SM_Tree_Maple_Red` | 95,632 | 752 x 723 x 1186 |  |
| Nature/Trees/Temperate | `SM_Tree_Oak_A` | 319,354 | 980 x 1117 x 1307 |  |
| Nature/Trees/Temperate | `SM_Tree_Oak_Autumn` | 202,386 | 1048 x 728 x 1275 |  |
| Nature/Trees/Temperate | `SM_Tree_Oak_B` | 238,652 | 723 x 870 x 1118 |  |
| Nature/Trees/Temperate | `SM_Tree_Willow_Weeping` | 951,836 | 623 x 673 x 1176 |  |
| Nature/Trees/Tropical | `SM_Plant_Bamboo_Clump` | 39,988 | 350 x 351 x 897 |  |
| Nature/Trees/Tropical | `SM_Plant_Banana` | 5,748 | 418 x 372 x 426 |  |
| Nature/Trees/Tropical | `SM_Tree_Jungle_Kapok` | 1,421,526 | 2316 x 1816 x 2883 |  |
| Nature/Trees/Tropical | `SM_Tree_Mangrove` | 213,457 | 502 x 536 x 878 |  |
| Nature/Tropical | `SM_Anthurium` | 67,152 | 280 x 180 x 50 |  |
| Nature/Tropical | `SM_Calathea` | 16,688 | 249 x 119 x 42 |  |
| Nature/Tropical | `SM_Grass_Bermuda` | 941 | 169 x 14 x 16 |  |
| Nature/Tropical | `SM_Pachira` | 76,914 | 687 x 100 x 190 |  |
| Nature/Tropical | `SM_Sorrel` | 3,319 | 35 x 15 x 6 |  |
| Props/Camp | `SM_FirePit` | 3,887 | 145 x 143 x 39 |  |
| Props/Containers | `SM_Barrel_Cask` | 28,324 | 62 x 61 x 93 |  |
| Props/Containers | `SM_Barrel_Gunpowder` | 33,756 | 38 x 38 x 61 |  |
| Props/Containers | `SM_Barrel_Rum` | 26,956 | 54 x 53 x 79 |  |
| Props/Containers | `SM_Basket_A` | 22,276 | 38 x 30 x 12 |  |
| Props/Containers | `SM_Basket_B` | 17,850 | 36 x 25 x 20 |  |
| Props/Containers | `SM_Bucket_A` | 5,116 | 37 x 34 x 55 |  |
| Props/Containers | `SM_Bucket_B` | 7,252 | 62 x 62 x 35 |  |
| Props/Containers | `SM_Chest_Sea` | 11,312 | 108 x 56 x 49 |  |
| Props/Containers | `SM_Crate_Cargo` | 14,820 | 91 x 64 x 60 |  |
| Props/Containers | `SM_Crate_Long` | 13,308 | 161 x 49 x 38 |  |
| Props/Containers | `SM_Crate_Scanned_A` | 6,576 | 83 x 41 x 35 |  |
| Props/Containers | `SM_Crate_Scanned_B` | 5,176 | 53 x 117 x 46 |  |
| Props/Containers | `SM_Sack_Grain` | 11,652 | 40 x 31 x 52 |  |
| Props/Containers | `SM_Sack_Pile` | 15,360 | 126 x 67 x 42 |  |
| Props/Containers | `SM_WineBarrel` | 10,820 | 74 x 76 x 87 |  |
| Props/Decor | `SM_LionHead_Knocker` | 47,214 | 32 x 21 x 44 |  |
| Props/Decor | `SM_WantedPoster` | 2,520 | 30 x 2 x 41 |  |
| Props/Docks | `SM_Bollard_Iron` | 1,904 | 41 x 41 x 55 |  |
| Props/Docks | `SM_MooringPost_Rope` | 15,970 | 175 x 36 x 132 |  |
| Props/Food | `SM_Apple` | 7,012 | 10 x 10 x 9 |  |
| Props/Food | `SM_Bananas` | 46,868 | 60 x 24 x 18 |  |
| Props/Food | `SM_Lemon` | 4,012 | 7 x 7 x 10 |  |
| Props/Food | `SM_Lime` | 8,100 | 6 x 6 x 8 |  |
| Props/Food | `SM_Onion` | 5,444 | 7 x 7 x 9 |  |
| Props/Food | `SM_Pomegranate` | 8,142 | 11 x 12 x 11 |  |
| Props/Furniture | `SM_Bed_Captain` | 18,745 | 149 x 204 x 153 |  |
| Props/Furniture | `SM_Bench_Painted` | 630 | 116 x 50 x 89 |  |
| Props/Furniture | `SM_Cabinet_Carved` | 12,170 | 172 x 102 x 236 |  |
| Props/Furniture | `SM_Chair_Captain` | 19,992 | 69 x 66 x 227 |  |
| Props/Furniture | `SM_Chair_Carved` | 11,560 | 58 x 60 x 103 |  |
| Props/Furniture | `SM_Drawers_Apothecary` | 5,184 | 86 x 46 x 55 |  |
| Props/Furniture | `SM_Mirror_Ornate` | 14,246 | 49 x 3 x 74 |  |
| Props/Furniture | `SM_SpinningWheel` | 52,023 | 49 x 102 x 97 |  |
| Props/Furniture | `SM_Stool_A` | 10,946 | 43 x 44 x 44 |  |
| Props/Furniture | `SM_Stool_B` | 11,146 | 27 x 18 x 18 |  |
| Props/Furniture | `SM_Stool_Folding` | 6,324 | 53 x 55 x 44 |  |
| Props/Furniture | `SM_Table_BenchTable` | 10,210 | 224 x 302 x 75 |  |
| Props/Furniture | `SM_Table_Carved` | 5,528 | 83 x 52 x 49 |  |
| Props/Furniture | `SM_Table_Pedestal` | 1,514 | 30 x 30 x 42 |  |
| Props/Furniture | `SM_Table_Round` | 8,640 | 140 x 140 x 101 |  |
| Props/Furniture | `SM_Table_Rustic` | 196 | 113 x 71 x 80 |  |
| Props/Lighting | `SM_Candelabra_Brass` | 41,936 | 105 x 36 x 84 |  |
| Props/Lighting | `SM_Candles_Cluster` | 4,488 | 25 x 25 x 20 |  |
| Props/Lighting | `SM_Candlestick_Wooden` | 212,992 | 10 x 10 x 22 |  |
| Props/Lighting | `SM_Lantern_Chandelier` | 5,971 | 58 x 57 x 88 |  |
| Props/Lighting | `SM_Lantern_Hurricane` | 33,902 | 12 x 10 x 29 |  |
| Props/Lighting | `SM_Lantern_Wooden` | 8,321 | 22 x 23 x 53 |  |
| Props/Maritime | `SM_Anchor` | 7,604 | 123 x 140 x 191 |  |
| Props/Maritime | `SM_Oar` | 1,372 | 295 x 15 x 6 |  |
| Props/Maritime | `SM_RopeCoil_Flemish` | 68,070 | 69 x 94 x 3 |  |
| Props/Maritime | `SM_RopeCoil_Stacked` | 40,980 | 115 x 47 x 28 |  |
| Props/Maritime | `SM_ShipWheel` | 13,532 | 143 x 28 x 150 |  |
| Props/Navigation | `SM_Book_Logbook` | 1,688 | 22 x 26 x 6 |  |
| Props/Navigation | `SM_Compass_Brass` | 11,645 | 8 x 10 x 2 |  |
| Props/Navigation | `SM_MagnifyingGlass` | 7,240 | 13 x 3 x 27 |  |
| Props/Navigation | `SM_Map_Rolled` | 6,664 | 45 x 6 x 6 |  |
| Props/Navigation | `SM_Map_Treasure` | 11,220 | 62 x 47 x 5 |  |
| Props/Navigation | `SM_PocketWatch` | 16,098 | 6 x 1 x 8 |  |
| Props/Navigation | `SM_Spyglass` | 2,958 | 80 x 6 x 6 |  |
| Props/Tavern | `SM_Bottle_Gin_Case` | 1,314 | 12 x 12 x 26 |  |
| Props/Tavern | `SM_Bottle_Rum_Onion` | 2,826 | 16 x 16 x 23 |  |
| Props/Tavern | `SM_Bottle_Rum_Onion_Dark` | 2,444 | 16 x 16 x 26 |  |
| Props/Tavern | `SM_Bowl_Wooden_A` | 14,122 | 31 x 31 x 9 |  |
| Props/Tavern | `SM_Bowl_Wooden_B` | 4,666 | 13 x 12 x 7 |  |
| Props/Tavern | `SM_ChessSet` | 76,920 | 55 x 55 x 11 |  |
| Props/Tavern | `SM_CuttingBoard` | 3,520 | 45 x 25 x 4 |  |
| Props/Tavern | `SM_Goblets_Brass` | 9,600 | 45 x 30 x 27 |  |
| Props/Tavern | `SM_Pan_Brass` | 4,340 | 19 x 45 x 5 |  |
| Props/Tavern | `SM_Plate_Wooden` | 2,112 | 27 x 27 x 4 |  |
| Props/Tavern | `SM_Pot_Brass_A` | 3,760 | 30 x 30 x 29 |  |
| Props/Tavern | `SM_Pot_Brass_B` | 3,344 | 37 x 30 x 11 |  |
| Props/Tavern | `SM_Pot_Ceramic` | 3,592 | 66 x 50 x 37 |  |
| Props/Tavern | `SM_Spoon_Wooden` | 6,576 | 9 x 28 x 3 |  |
| Props/Tavern | `SM_Tankard_Wooden` | 14,704 | 17 x 11 x 17 |  |
| Props/Tools | `SM_Axe` | 3,348 | 5 x 21 x 63 |  |
| Props/Tools | `SM_Broom` | 14,258 | 49 x 11 x 145 |  |
| Props/Tools | `SM_Handsaw` | 2,548 | 4 x 63 x 17 |  |
| Props/Tools | `SM_Mallet` | 3,617 | 11 x 2 x 28 |  |
| Props/Tools | `SM_Spade` | 11,436 | 17 x 5 x 110 |  |
| Props/Treasure | `SM_Coins_Stacks` | 12,480 | 19 x 19 x 3 |  |
| Props/Treasure | `SM_TreasureChest_Scanned` | 103,330 | 96 x 52 x 62 |  |
| Props/Treasure | `SM_TreasurePile_Gold` | 344,992 | 125 x 126 x 34 |  |
| Props/Weapons | `SM_Cannonball` | 1,280 | 12 x 12 x 12 |  |
| Props/Weapons | `SM_Cannonball_Stack` | 10,608 | 56 x 56 x 36 |  |
| Town/Bazaar | `SM_Bazaar_Stall_A` | 6,052 | 340 x 261 x 260 |  |
| Town/Bazaar | `SM_Bazaar_Stall_B` | 6,052 | 340 x 261 x 260 |  |
| Town/Bazaar | `SM_Bazaar_Stall_C` | 6,052 | 400 x 261 x 260 |  |
| Town/Bazaar | `SM_CarvedElephant` | 2,752 | 11 x 6 x 10 |  |
| Town/Bazaar | `SM_ClayPot` | 3,080 | 27 x 26 x 22 |  |
| Town/Bazaar | `SM_Lamp_Brass_Diya` | 12,742 | 12 x 12 x 38 |  |
| Town/Bazaar | `SM_Mancala_Board` | 7,304 | 14 x 60 x 4 |  |
| Town/Bazaar | `SM_Vase_Brass_A` | 21,440 | 23 x 23 x 69 |  |
| Town/Bazaar | `SM_Vase_Brass_B` | 6,890 | 21 x 21 x 53 |  |
| Town/Bazaar | `SM_Vase_Brass_C` | 2,616 | 8 x 8 x 20 |  |
| Town/Bazaar | `SM_Vase_Brass_D` | 2,760 | 8 x 6 x 17 |  |
| Town/Bazaar | `SM_Vase_Ceramic_A` | 10,296 | 20 x 20 x 40 |  |
| Town/Bazaar | `SM_Vase_Ceramic_Antique` | 9,408 | 26 x 26 x 44 |  |
| Town/Bazaar | `SM_Vase_Ceramic_B` | 11,128 | 22 x 22 x 31 |  |
| Town/Bazaar | `SM_Vase_Ceramic_C` | 11,136 | 11 x 11 x 41 |  |
| Town/Bazaar | `SM_Vase_Ceramic_D` | 9,000 | 18 x 18 x 34 |  |
| Town/Blacksmith | `SM_Axe_B` | 2,218 | 5 x 23 x 70 |  |
| Town/Blacksmith | `SM_Axe_C` | 3,886 | 5 x 16 x 63 |  |
| Town/Blacksmith | `SM_Sledgehammer` | 2,596 | 21 x 9 x 101 |  |
| Town/Blacksmith | `SM_SmithHammer` | 2,124 | 10 x 2 x 30 |  |
| Town/Buildings | `SM_Blacksmith_Forge` | 127,848 | 918 x 733 x 619 |  |
| Town/Buildings | `SM_Cottage_Stone` | 186,396 | 899 x 734 x 735 |  |
| Town/Buildings | `SM_House_Timber_A` | 392,910 | 788 x 1003 x 1401 |  |
| Town/Buildings | `SM_House_Timber_B` | 259,066 | 1474 x 858 x 1142 |  |
| Town/Buildings | `SM_House_Timber_C` | 268,806 | 797 x 908 x 1474 |  |
| Town/Buildings | `SM_House_Timber_D_Tall` | 286,694 | 638 x 1097 x 1660 |  |
| Town/Buildings | `SM_MarketHall` | 322,932 | 1297 x 816 x 1411 |  |
| Town/Castle | `SM_CastleKit` | 649,226 | 1245 x 890 x 2100 |  |
| Town/Castle | `SM_Castle_Gatehouse` | 290,518 | 1796 x 816 x 1410 |  |
| Town/Castle | `SM_Castle_Keep` | 817,304 | 1690 x 1875 x 3301 |  |
| Town/Castle | `SM_KiteShield` | 10,306 | 54 x 13 x 139 |  |
| Town/Castle | `SM_Mace` | 14,762 | 9 x 10 x 63 |  |
| Town/Castle | `SM_WarHammer` | 5,192 | 14 x 3 x 71 |  |
| Town/Furniture | `SM_Bookshelf_Worn` | 10,106 | 137 x 58 x 206 |  |
| Town/Furniture | `SM_Cabinet_Painted` | 2,227 | 119 x 62 x 118 |  |
| Town/Furniture | `SM_Chair_Painted_A` | 724 | 43 x 54 x 96 |  |
| Town/Furniture | `SM_Chair_Painted_B` | 1,246 | 66 x 64 x 126 |  |
| Town/Furniture | `SM_Commode_Gothic` | 3,897 | 120 x 58 x 121 |  |
| Town/Furniture | `SM_Shelves_Painted` | 524 | 51 x 37 x 113 |  |
| Town/Furniture | `SM_Stool_Painted` | 676 | 38 x 41 x 58 |  |
| Town/Furniture | `SM_Table_Painted` | 600 | 241 x 114 x 96 |  |
| Town/Market | `SM_CheeseBox` | 884 | 24 x 11 x 7 |  |
| Town/Market | `SM_Ginger` | 7,205 | 24 x 15 x 57 |  |
| Town/Market | `SM_Pears` | 12,572 | 10 x 13 x 9 |  |
| Town/Market | `SM_SweetPotato` | 2,042 | 6 x 6 x 10 |  |
| Town/Props | `SM_Bench_Wooden` | 1,248 | 180 x 46 x 48 |  |
| Town/Props | `SM_Cart_Hand` | 11,352 | 300 x 160 x 113 |  |
| Town/Props | `SM_LampPost_Iron` | 2,600 | 104 x 44 x 305 |  |
| Town/Props | `SM_Signpost` | 212 | 174 x 176 x 298 |  |
| Town/Props | `SM_Torch_Wall` | 572 | 10 x 33 x 83 |  |
| Town/Props | `SM_Wagon_Hay` | 24,356 | 494 x 190 x 210 |  |
| Town/Props | `SM_Wheelbarrow` | 6,268 | 176 x 78 x 99 |  |
| Town/Square | `SM_Fountain_Square` | 29,736 | 700 x 700 x 303 |  |
| Town/Square | `SM_GothicStatue` | 27,739 | 148 x 156 x 174 |  |
| Town/Square | `SM_HorseStatue` | 22,388 | 16 x 11 x 22 |  |
| Town/Streets | `SM_StreetKit` | 323,172 | 407 x 451 x 121 |  |

## Rebuilding

```bash
python Tools/assets/prepare_glb.py --kit <path to the kit>   # shrink textures into Build/Assets
```
Then run `Tools/assets/import_assets.py` in the editor (rerunnable; `BAM_ASSETS_FORCE=1` re-imports).
