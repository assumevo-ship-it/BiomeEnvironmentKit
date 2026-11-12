"""Biome Auto-Materials: the texture library and the biome presets (plain data, no dependencies).

Every texture set is CC0 (Poly Haven "ph:<id>" or ambientCG "acg:<id>"), so the built plugin can be redistributed.

TEXTURES  key -> (source, target albedo, real-world size in metres or None, porosity)
    target albedo   mean linear (visible band) albedo the set is calibrated to; the build sets the layer's Brightness
                    to target / measured mean, so every biome sits at physically plausible brightness under the same sun
                    (literature values, e.g. fresh snow ~0.85, desert sand ~0.4, green grass ~0.09, basalt ~0.06).
                    None keeps the photo as it is.
    size            metres the photo covers; None uses Poly Haven's published dimensions, else the slot default.
    porosity        how much the surface darkens when wet (soil/sand ~1, rock ~0.35, snow 0).

BIOMES  name -> dict(desc, layers={slot: texture key}, params={parameter: value}, tints={slot: (r, g, b)})
    slots (bottom to top of the stack): Ground, GroundB, Soil, Shore, Scree, Rock, RockB, Snow.
    A slot that a biome leaves out is filled with another layer's texture and its coverage is turned off.
    params override PARAM_DEFAULTS (see Docs/Parameters.md); per-layer parameters are "<Slot> <Name>".
"""

# Roughness calibration: scanned roughness maps are often authored, not measured, and some (ambientCG's Grass004 averages
# 0.26) would make turf shine like wet plastic under an overcast sky. Natural dry ground is matte: the build raises a set
# whose mean roughness is below its floor (keeping the map's own variation). None leaves a set as it is.
ROUGHNESS_FLOOR_DEFAULT = 0.72
ROUGHNESS_FLOOR = {"ice_glacier": None, "snow_fresh": 0.62, "snow_clean": 0.62, "snow_wind": 0.62, "snow_frozen": 0.55,
                   "snow_dirty": 0.66, "gravel_black": 0.62, "low_tide_rocks": 0.6}


# ---------------------------------------------------------------------------------------------------------------------
# texture library
# ---------------------------------------------------------------------------------------------------------------------
TEXTURES = {
    # --- grass / vegetation cover
    "grass_dense":       ("acg:Grass004", 0.085, 2.0, 0.8),
    "grass_meadow":      ("acg:Grass001", 0.080, 2.0, 0.8),
    "grass_sparse":      ("ph:sparse_grass", 0.10, None, 0.9),
    "grass_dry":         ("ph:withered_grass", 0.20, None, 0.9),
    "grass_dirt":        ("ph:grass_ground", 0.14, None, 0.9),
    "moss_green":        ("acg:Moss002", 0.065, 1.5, 0.7),
    "moss_ground":       ("acg:Moss001", 0.12, 1.5, 0.7),
    "litter_mossy":      ("ph:forest_leaves_02", 0.09, None, 0.9),
    "litter_green":      ("ph:leaves_forest_ground", 0.085, None, 0.9),
    "litter_twigs":      ("ph:forrest_ground_01", 0.12, None, 0.9),
    "litter_autumn":     ("ph:forest_leaves_03", 0.1, None, 0.9),
    "litter_autumn2":    ("ph:forest_leaves_04", 0.12, None, 0.9),
    "litter_dry":        ("ph:dry_decay_leaves", 0.14, None, 0.9),
    "needles":           ("ph:forrest_ground_03", 0.11, None, 0.9),
    "needles_sand":      ("ph:forrest_sand_01", 0.13, None, 0.9),
    "mud_leaves":        ("ph:brown_mud_leaves_01", 0.08, None, 1.0),
    "burned":            ("ph:burned_ground_01", 0.05, None, 1.0),
    # --- soils
    "soil_compact":      ("ph:forest_ground_05", 0.13, None, 1.0),
    "soil_forest":       ("ph:forest_ground_04", 0.11, None, 1.0),
    "soil_leafy":        ("ph:forest_ground_06", 0.11, None, 1.0),
    "soil_laterite":     ("ph:red_laterite_soil_stones", 0.15, None, 1.0),
    "soil_redmud":       ("ph:red_mud_stones", 0.14, None, 1.0),
    "soil_terrarossa":   ("ph:red_dirt_mud_01", 0.15, None, 1.0),
    "soil_rocky":        ("ph:rocks_ground_05", 0.15, None, 0.8),
    "mud_mossy":         ("ph:brown_mud_rocks_01", 0.08, None, 1.0),
    "mud_forest":        ("acg:Ground024", 0.07, 2.0, 1.0),
    "mud_beach":         ("acg:Ground054", 0.15, 2.0, 1.0),
    "dry_cracked":       ("ph:dry_ground_01", 0.28, None, 1.0),
    "dry_cracked_mud":   ("ph:mud_cracked_dry_03", 0.25, None, 1.0),
    "riverbed_cracked":  ("ph:mud_cracked_dry_riverbed_002", 0.27, None, 1.0),
    "dry_rocky":         ("ph:dry_ground_rocks", 0.22, None, 0.9),
    "dry_field":         ("ph:dry_mud_field_001", 0.20, None, 1.0),
    "red_cracked":       ("ph:cracked_red_ground", 0.2, None, 1.0),
    # --- sand / beach / gravel
    "sand_beach":        ("ph:coast_sand_01", 0.33, None, 1.0),
    "sand_beach_white":  ("acg:Ground033", 0.55, 2.0, 1.0),
    "sand_damp":         ("ph:damp_beach_sand_02", 0.20, None, 1.0),
    "sand_fine":         ("ph:sand_01", 0.36, None, 1.0),
    "sand_dune":         ("acg:Ground093C", 0.40, 2.0, 1.0),
    "sand_red":          ("ph:red_sand", 0.30, None, 1.0),
    "sand_gravelly":     ("ph:gravelly_sand", 0.27, None, 1.0),
    "sand_gravel_dusty": ("ph:sandy_gravel_02", 0.26, None, 0.9),
    "coral_gravel":      ("ph:coral_gravel", 0.45, None, 0.8),
    "shells":            ("ph:shell_floor_01", 0.40, None, 0.8),
    "pebbles_river":     ("ph:ganges_river_pebbles", 0.22, None, 0.5),
    "pebbles_dry":       ("ph:dry_river_pebbles", 0.24, None, 0.5),
    "pebbles_clean":     ("ph:clean_pebbles", 0.30, None, 0.5),
    "low_tide_rocks":    ("ph:low_tide_rocks", 0.12, None, 0.5),
    "gravel_black":      ("acg:Gravel024", 0.055, 1.5, 0.6),
    "gravel_grey":       ("ph:ground_grey", 0.18, None, 0.7),
    # --- scree / rubble
    "scree_broken":      ("ph:rocks_ground_06", 0.18, None, 0.6),
    "scree_grey":        ("ph:rock_ground", 0.17, None, 0.6),
    "scree_pebbly":      ("ph:rocks_ground_03", 0.18, None, 0.6),
    "scree_stony":       ("ph:rocks_ground_09", 0.19, None, 0.6),
    "scree_trail":       ("ph:rocky_trail", 0.17, None, 0.6),
    "scree_red":         ("ph:terrain_red_01", 0.15, None, 0.6),
    "scree_leafy":       ("ph:leaf_scattered_gravel", 0.12, None, 0.7),
    "river_stones":      ("ph:river_small_rocks", 0.17, None, 0.5),
    # --- rock (cliffs: triplanar)
    "rock_face":         ("ph:rock_face", 0.2, None, 0.35),
    "rock_cliff":        ("ph:cliff_side", 0.22, None, 0.35),
    "rock_mossy":        ("ph:mossy_rock", 0.12, None, 0.4),
    "rock_lichen":       ("ph:lichen_rock", 0.15, None, 0.4),
    "rock_dark":         ("ph:dark_rock", 0.05, None, 0.35),
    "rock_slate":        ("ph:dark_rock_02", 0.08, None, 0.35),
    "rock_seaside":      ("ph:seaside_rock", 0.12, None, 0.4),
    "rock_grey":         ("ph:gray_rocks", 0.20, None, 0.35),
    "rock_limestone":    ("ph:marble_rock_02", 0.40, None, 0.35),
    "rock_limestone2":   ("ph:marble_cliff_02", 0.38, None, 0.35),
    "rock_sandstone":    ("ph:worn_rock_natural_01", 0.33, None, 0.45),
    "rock_yellow":       ("ph:rock_06", 0.30, None, 0.45),
    "rock_orange":       ("ph:rock_boulder_cracked", 0.24, None, 0.45),
    "rock_redsand":      ("ph:rock_pitted_mossy", 0.22, None, 0.45),
    "rock_tiger":        ("ph:tiger_rock", 0.22, None, 0.35),
    "rock_boulder":      ("ph:rock_boulder_dry", 0.24, None, 0.35),
    "rock_rough":        ("ph:rock_04", 0.20, None, 0.35),
    "rock_coarse":       ("ph:rock_08", 0.21, None, 0.35),
    "rock_mountain":     ("acg:Rock051", 0.22, 4.0, 0.35),
    "rock_alpine":       ("acg:Rock028", 0.16, 4.0, 0.35),
    "rock_basalt":       ("acg:Rock031", 0.06, 4.0, 0.3),
    "rock_basalt_cave":  ("acg:Rock035", 0.05, 4.0, 0.3),
    "rock_desert_red":   ("acg:Rock029", 0.24, 4.0, 0.45),
    # --- snow / ice
    "snow_fresh":        ("ph:snow_02", 0.85, None, 0.0),
    "snow_clean":        ("acg:Snow010A", 0.82, 2.0, 0.0),
    "snow_wind":         ("acg:Snow008A", 0.80, 3.0, 0.0),
    "snow_dirty":        ("ph:snow_04", 0.50, None, 0.2),
    "snow_frozen":       ("acg:Snow014", 0.60, 2.0, 0.0),
    "ice_glacier":       ("acg:Ice002", 0.35, 3.0, 0.0),
    # --- otherworldly
    "regolith":          ("ph:moon_dusted_01", 0.12, None, 0.0),
    "regolith_rough":    ("ph:moon_02", 0.12, None, 0.0),
    "regolith_rocks":    ("ph:moon_04", 0.12, None, 0.0),
}

SLOTS = ["Ground", "GroundB", "Soil", "Shore", "Scree", "Rock", "RockB", "Snow"]
SLOT_DEFAULT_SIZE = {"Ground": 2.5, "GroundB": 2.5, "Soil": 2.5, "Shore": 2.5, "Scree": 2.5, "Rock": 6.0, "RockB": 6.0, "Snow": 3.0}
# which coverage parameter turns a slot off when a biome leaves it out
SLOT_OFF = {"GroundB": {"GroundB Amount": 0.0}, "Soil": {"Soil Angle": 90.0, "Soil Patches": 0.0}, "Shore": {"Shore Height": -1000.0},
            "Scree": {"Scree Amount": 0.0}, "RockB": {"RockB Amount": 0.0}, "Snow": {"Snow Amount": 0.0}}

# ---------------------------------------------------------------------------------------------------------------------
# master material parameters (name: default). Lengths in metres, angles in degrees.
# ---------------------------------------------------------------------------------------------------------------------
LAYER_PARAMS = {  # per slot: "<Slot> <Name>"
    "Tile": None,             # metres the texture covers (filled from TEXTURES / Poly Haven dimensions)
    "Aspect": 1.0,            # height / width of the photo
    "Brightness": 1.0,        # set by albedo calibration
    "Saturation": 1.0,
    "Normal": 1.0,
    "Roughness": 1.0,         # multiplier on the measured roughness
    "Height Bias": 0.0,       # pushes the layer up/down in the height blend
    "Porosity": 1.0,          # darkening when wet
}
PARAM_DEFAULTS = {
    # world
    "Sea Level": 0.0,              # metres (world Z) of the water line
    "Landscape Quad Size": 1.0,    # metres per landscape quad (landscape X/Y scale / 100)
    # ground variation
    "GroundB Amount": 0.35, "GroundB Scale": 1.0, "GroundB Altitude Bias": 0.0, "GroundB Slope Bias": 0.0,
    # soil
    "Soil Angle": 24.0, "Soil Fade": 8.0, "Soil Patches": 0.15,
    # shore
    "Shore Height": 1.6, "Shore Fade": 0.9, "Shore Noise": 1.4, "Shore Max Angle": 16.0,
    # scree: talus collects at its angle of repose (30-37 deg)
    "Scree Amount": 0.6, "Scree Angle": 33.0, "Scree Width": 9.0,
    # rock
    "Rock Angle": 40.0, "Rock Fade": 7.0, "Rock Noise": 10.0, "RockB Amount": 0.4,
    "Strata Amount": 0.0, "Strata Scale": 2.5, "Strata Warp": 3.0, "Strata Tint Amount": 0.0,
    "Rock Moss": 0.0,
    # snow
    "Snow Amount": 1.0, "Snow Line": 100000.0, "Snow Fade": 12.0, "Snow Line Noise": 25.0, "Snow Max Angle": 48.0,
    "Snow Cover": 0.0, "Snow Smoothing": 0.6,
    # water
    "Wet Band": 0.6, "Wetness": 0.0, "Puddles": 0.0,
    # blending / anti-tiling
    "Height Blend": 1.0, "Blend Softness": 0.12, "Hex Tiling": 1.0, "Hex Contrast": 0.6, "Hex Rotation": 1.0,
    "Far Scale": 0.27, "Fade Start": 1500.0, "Fade Length": 6000.0,   # cm
    "Macro Scale": 60.0, "Macro Strength": 0.18, "Macro Saturation": 0.15,
    "Debug View": 0.0,
}
VECTOR_DEFAULTS = {
    "Strata Tint": (0.78, 0.62, 0.50),
    "Moss Color": (0.045, 0.06, 0.025),
}
# parameter -> group (UI order in the material instance editor)
def group_of(name):
    for slot_i, slot in enumerate(SLOTS):
        if name.startswith(slot + " "):
            return f"{slot_i + 2:02d} {slot}"
    table = [("Sea", "00 World"), ("Landscape", "00 World"), ("Height Blend", "01 Blending"), ("Blend", "01 Blending"),
             ("Hex", "01 Blending"), ("Far", "01 Blending"), ("Fade", "01 Blending"), ("Macro", "01 Blending"),
             ("Debug", "00 World"), ("Wet", "10 Water"), ("Puddle", "10 Water"), ("Strata", "07 Rock"), ("Moss", "07 Rock")]
    for pre, g in table:
        if name.startswith(pre):
            return g
    for slot_i, slot in enumerate(SLOTS):
        if name.split(" ")[0] == slot:
            return f"{slot_i + 2:02d} {slot}"
    return "00 World"


# ---------------------------------------------------------------------------------------------------------------------
# biomes
# ---------------------------------------------------------------------------------------------------------------------
SNOWLINE = 140.0  # showcase snowline (metres above sea); real ones are far higher, set "Snow Line" to suit your world

BIOMES = {
    "TropicalIsland": dict(
        desc="Volcanic tropical island: coral-white beaches, lush grass and leaf litter over red laterite, dark wet rock.",
        layers=dict(Ground="grass_dense", GroundB="litter_green", Soil="soil_laterite", Shore="sand_beach_white",
                    Scree="coral_gravel", Rock="rock_dark", RockB="rock_mossy"),
        params={"GroundB Amount": 0.4, "Rock Moss": 0.35, "Shore Height": 2.2, "Scree Amount": 0.25, "Wet Band": 0.8,
                "Soil Angle": 32.0, "Soil Patches": 0.06, "Moss Color": (0.04, 0.065, 0.02)},
        albedo={"Soil": 0.11},
    ),
    "Rainforest": dict(
        desc="Equatorial rainforest floor: wet leaf litter, moss, red clay, mossy boulders; always damp.",
        layers=dict(Ground="litter_mossy", GroundB="mud_leaves", Soil="soil_redmud", Shore="mud_beach",
                    Scree="mud_mossy", Rock="rock_mossy", RockB="rock_lichen"),
        params={"GroundB Amount": 0.45, "Rock Moss": 0.7, "Wetness": 0.35, "Puddles": 0.25, "Soil Patches": 0.25,
                "Rock Angle": 46.0, "Moss Color": (0.03, 0.06, 0.02)},
    ),
    "Swamp": dict(
        desc="Bayou / bog: carpets of moss and mud, standing water in the hollows, algae-stained rock.",
        layers=dict(Ground="moss_green", GroundB="mud_mossy", Soil="mud_forest", Shore="mud_beach",
                    Scree="river_stones", Rock="rock_mossy", RockB="rock_grey"),
        params={"GroundB Amount": 0.5, "Wetness": 0.55, "Puddles": 0.7, "Wet Band": 1.5, "Shore Height": 1.0,
                "Rock Moss": 0.8, "Soil Patches": 0.3},
        tints={"Ground": (0.92, 1.0, 0.82)},
    ),
    "TemperateMeadow": dict(
        desc="Rolling European grassland with wild patches, bare soil on banks, grey lichen rock and snowy peaks.",
        layers=dict(Ground="grass_meadow", GroundB="grass_sparse", Soil="soil_compact", Shore="sand_beach",
                    Scree="scree_broken", Rock="rock_grey", RockB="rock_lichen", Snow="snow_fresh"),
        params={"GroundB Amount": 0.35, "Snow Line": SNOWLINE + 40, "Rock Moss": 0.25},
    ),
    "TemperateForest": dict(
        desc="Deciduous woodland: green leaf litter, twigs, dark forest soil, mossy outcrops.",
        layers=dict(Ground="litter_green", GroundB="litter_twigs", Soil="soil_forest", Shore="pebbles_river",
                    Scree="mud_mossy", Rock="rock_mossy", RockB="rock_face"),
        params={"GroundB Amount": 0.45, "Rock Moss": 0.55, "Wetness": 0.1, "Puddles": 0.1},
    ),
    "AutumnForest": dict(
        desc="Beech/maple forest in October: orange leaf fall, leafy gravel, lichen-grey rock.",
        layers=dict(Ground="litter_autumn", GroundB="litter_autumn2", Soil="soil_leafy", Shore="pebbles_river",
                    Scree="scree_leafy", Rock="rock_lichen", RockB="rock_mossy"),
        params={"GroundB Amount": 0.45, "Rock Moss": 0.3},
    ),
    "BorealTaiga": dict(
        desc="Northern conifer forest: pine needles and feather moss on sandy podzol, lichen granite, early snow.",
        layers=dict(Ground="needles", GroundB="moss_ground", Soil="needles_sand", Shore="pebbles_river",
                    Scree="scree_trail", Rock="rock_lichen", RockB="rock_face", Snow="snow_fresh"),
        params={"GroundB Amount": 0.4, "Snow Line": SNOWLINE - 30, "Snow Cover": 0.15, "Rock Moss": 0.2},
    ),
    "Alpine": dict(
        desc="High mountains: short alpine turf, rocky soil, layered limestone/slate faces, talus and permanent snow.",
        layers=dict(Ground="grass_sparse", GroundB="grass_dirt", Soil="soil_rocky", Shore="river_stones",
                    Scree="scree_grey", Rock="rock_mountain", RockB="rock_slate", Snow="snow_fresh"),
        params={"GroundB Amount": 0.4, "GroundB Altitude Bias": 0.004, "Snow Line": SNOWLINE - 20, "Scree Amount": 0.9,
                "Rock Angle": 36.0, "Strata Amount": 0.5, "Strata Scale": 4.0, "Soil Angle": 20.0},
    ),
    "ArcticTundra": dict(
        desc="Polar tundra: dead sedge, cushion moss and gravel, frost-shattered rock, lingering snow patches.",
        layers=dict(Ground="litter_dry", GroundB="moss_ground", Soil="scree_trail", Shore="pebbles_river",
                    Scree="scree_pebbly", Rock="rock_lichen", RockB="rock_dark", Snow="snow_dirty"),
        params={"GroundB Amount": 0.45, "Snow Line": 40.0, "Snow Cover": 0.35, "Snow Line Noise": 40.0, "Scree Amount": 0.8,
                "Soil Patches": 0.3},
        tints={"Ground": (0.92, 0.85, 0.75)},
    ),
    "Glacier": dict(
        desc="Ice sheet and glacier: wind-packed snow, sastrugi, blue ice on slopes, moraine and dark nunataks.",
        layers=dict(Ground="snow_clean", GroundB="snow_wind", Soil="ice_glacier", Shore="ice_glacier",
                    Scree="scree_grey", Rock="rock_alpine", RockB="rock_slate", Snow="snow_fresh"),
        params={"GroundB Amount": 0.5, "Soil Angle": 18.0, "Soil Patches": 0.1, "Snow Line": -50.0, "Snow Cover": 1.0,
                "Snow Max Angle": 42.0, "Shore Height": 1.0, "Scree Amount": 0.5},
        tints={"Soil": (0.80, 0.93, 1.0), "Shore": (0.80, 0.93, 1.0)},
    ),
    "DesertDunes": dict(
        desc="Erg sand sea: ripple-marked dune sand, cracked interdune pans, honey sandstone outcrops.",
        layers=dict(Ground="sand_dune", GroundB="sand_fine", Soil="dry_cracked", Shore="sand_fine",
                    Scree="sand_gravel_dusty", Rock="rock_sandstone", RockB="rock_yellow"),
        params={"GroundB Amount": 0.3, "Soil Angle": 90.0, "Soil Patches": 0.12, "Rock Angle": 44.0, "Strata Amount": 0.6,
                "Strata Scale": 1.8, "Strata Tint Amount": 0.25, "Scree Amount": 0.4, "Wet Band": 0.2},
    ),
    "RockyDesert": dict(
        desc="Hamada / reg stone desert: desert pavement gravel, baked crust, banded granite kopjes.",
        layers=dict(Ground="sand_gravel_dusty", GroundB="sand_gravelly", Soil="dry_rocky", Shore="sand_fine",
                    Scree="scree_stony", Rock="rock_tiger", RockB="rock_cliff"),
        params={"GroundB Amount": 0.4, "Soil Patches": 0.25, "Scree Amount": 0.8, "Wet Band": 0.2},
    ),
    "RedCanyon": dict(
        desc="Colorado-plateau canyon country: red sand, layered red/orange sandstone cliffs with banded strata.",
        layers=dict(Ground="sand_red", GroundB="red_cracked", Soil="soil_redmud", Shore="sand_red",
                    Scree="scree_red", Rock="rock_orange", RockB="rock_redsand"),
        params={"GroundB Amount": 0.35, "Rock Angle": 34.0, "Strata Amount": 0.9, "Strata Scale": 3.0, "Strata Warp": 2.0,
                "Strata Tint Amount": 0.55, "Strata Tint": (0.95, 0.62, 0.45), "Scree Amount": 0.9, "Wet Band": 0.2},
    ),
    "Savanna": dict(
        desc="East-African savanna: straw-dry grass, red laterite paths, weathered granite boulders.",
        layers=dict(Ground="grass_dry", GroundB="grass_dirt", Soil="soil_laterite", Shore="sand_gravelly",
                    Scree="dry_rocky", Rock="rock_boulder", RockB="rock_tiger"),
        params={"GroundB Amount": 0.4, "Soil Patches": 0.22, "Scree Amount": 0.4},
    ),
    "Steppe": dict(
        desc="Continental steppe / prairie: tussock grass, dry ploughed loess, rough grey outcrops.",
        layers=dict(Ground="grass_dirt", GroundB="grass_dry", Soil="dry_field", Shore="sand_gravelly",
                    Scree="soil_rocky", Rock="rock_rough", RockB="rock_coarse"),
        params={"GroundB Amount": 0.45, "Soil Patches": 0.12},
    ),
    "Mediterranean": dict(
        desc="Garrigue coast: sun-dried grass, terra rossa, white limestone crags and pebble beaches.",
        layers=dict(Ground="grass_dry", GroundB="grass_sparse", Soil="soil_terrarossa", Shore="pebbles_clean",
                    Scree="scree_stony", Rock="rock_limestone", RockB="rock_limestone2"),
        params={"GroundB Amount": 0.4, "Soil Patches": 0.25, "Scree Amount": 0.7, "Shore Height": 1.2},
    ),
    "Volcanic": dict(
        desc="Young volcanic field: black tephra, grey ash, scorched soil, basalt cliffs, black-sand beach.",
        layers=dict(Ground="gravel_black", GroundB="regolith_rough", Soil="burned", Shore="gravel_black",
                    Scree="gravel_grey", Rock="rock_basalt", RockB="rock_basalt_cave", Snow="snow_dirty"),
        params={"GroundB Amount": 0.4, "Snow Line": SNOWLINE + 30, "Scree Amount": 0.7, "Strata Amount": 0.35,
                "Strata Scale": 2.0},
        tints={"GroundB": (0.55, 0.55, 0.55)},
    ),
    "RockyCoast": dict(
        desc="North-Atlantic coast: salt-sprayed turf, shingle beaches, seaweed-dark low-tide rock, slate cliffs.",
        layers=dict(Ground="grass_meadow", GroundB="grass_sparse", Soil="soil_rocky", Shore="pebbles_dry",
                    Scree="low_tide_rocks", Rock="rock_seaside", RockB="rock_slate"),
        params={"GroundB Amount": 0.4, "Shore Height": 2.0, "Wet Band": 1.4, "Rock Angle": 34.0, "Scree Amount": 0.5,
                "Strata Amount": 0.3},
    ),
    "Moorland": dict(
        desc="Upland heath and bog: tawny moor grass, sphagnum moss, black peat, grey gritstone.",
        layers=dict(Ground="grass_dirt", GroundB="moss_ground", Soil="mud_forest", Shore="mud_mossy",
                    Scree="scree_pebbly", Rock="rock_grey", RockB="rock_lichen"),
        params={"GroundB Amount": 0.4, "Wetness": 0.2, "Puddles": 0.35, "Soil Patches": 0.2},
        tints={"Ground": (0.98, 0.84, 0.72)},
    ),
    "SaltFlat": dict(
        desc="Playa / salt pan: blinding white polygonal crust, damp margins, bare ochre hills.",
        layers=dict(Ground="riverbed_cracked", GroundB="snow_frozen", Soil="dry_cracked", Shore="sand_damp",
                    Scree="sand_gravel_dusty", Rock="rock_sandstone", RockB="rock_yellow"),
        params={"GroundB Amount": 0.3, "Soil Angle": 8.0, "Shore Height": 0.4, "Wet Band": 0.3},
        tints={"Ground": (1.0, 0.99, 0.96)},
        albedo={"Ground": 0.70, "GroundB": 0.72},
    ),
    "BurnedForest": dict(
        desc="After the wildfire: ash and charcoal, scorched litter, sooty rock.",
        layers=dict(Ground="burned", GroundB="litter_dry", Soil="soil_forest", Shore="pebbles_river",
                    Scree="scree_broken", Rock="rock_dark", RockB="rock_face"),
        params={"GroundB Amount": 0.3},
        tints={"GroundB": (0.55, 0.5, 0.45), "Soil": (0.6, 0.58, 0.55), "RockB": (0.5, 0.5, 0.5)},
    ),
    "Lunar": dict(
        desc="Airless regolith (not an Earth biome): fine dust, impact-churned soil, dark basaltic rock.",
        layers=dict(Ground="regolith", GroundB="regolith_rough", Soil="regolith_rocks", Scree="regolith_rocks",
                    Rock="rock_dark", RockB="rock_basalt"),
        params={"GroundB Amount": 0.4, "Soil Patches": 0.2, "Sea Level": -10000.0, "Wet Band": -1000.0, "Rock Angle": 45.0},
        tints={"Rock": (0.75, 0.75, 0.75)},
    ),
    "Martian": dict(
        desc="Iron-oxide desert of Mars (not an Earth biome): rust dust, cracked duricrust, red layered rock.",
        layers=dict(Ground="sand_red", GroundB="red_cracked", Soil="scree_red", Scree="scree_red",
                    Rock="rock_desert_red", RockB="rock_orange"),
        params={"GroundB Amount": 0.4, "Sea Level": -10000.0, "Wet Band": -1000.0, "Strata Amount": 0.6, "Strata Tint Amount": 0.3,
                "Strata Tint": (0.9, 0.6, 0.45)},
        tints={"Ground": (1.0, 0.82, 0.68), "GroundB": (1.0, 0.85, 0.72)},
        albedo={"Ground": 0.25, "GroundB": 0.24},
    ),
}


def texture_keys():
    keys = []
    for b in BIOMES.values():
        for k in b["layers"].values():
            if k not in keys:
                keys.append(k)
    return keys


def resolved_layers(biome):
    """slot -> texture key for every slot (missing ones borrow a neighbour's texture), plus the params that turn them off."""
    lay = dict(biome["layers"])
    off = {}
    borrow = {"GroundB": "Ground", "Soil": "Ground", "Shore": "Soil", "Scree": "Soil", "RockB": "Rock", "Snow": "Ground"}
    for slot in SLOTS:
        if slot not in lay:
            lay[slot] = lay.get(borrow.get(slot, "Ground")) or lay["Ground"]
            off.update(SLOT_OFF.get(slot, {}))
    return lay, off
