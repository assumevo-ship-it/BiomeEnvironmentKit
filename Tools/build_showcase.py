"""Build the showcase level and (optionally) photograph it. Runs inside the Unreal Editor.

    UnrealEditor.exe <Project>.uproject -ExecCmds="py <path>/Tools/build_showcase.py"      (needs a ticking editor)

Creates /BiomeAutoMaterials/Showcase/L_BiomeShowcase: the generated test terrain (Showcase/ShowcaseTerrain.r16, 1 km,
1 m quads), the plugin's own environment (ABiomeSkyEnvironment: sun, moon, stars, clouds, fog, weather; ABiomeOcean: the
sea, with its shore field baked from the terrain) and one CineCamera per entry in Showcase/cameras.json plus a few sea
and sky cameras. Without the C++ modules or their materials it falls back to the engine's stock sky and a flat sea.

Creating a landscape from a heightmap is not exposed to stock Python, so the landscape is made with
PirateWorldBuilderLibrary.CreateIslandLandscape when the project has it (the project this pack was developed in).
Elsewhere, create it by hand once: Landscape mode > Import from File > Showcase/ShowcaseTerrain.png, 1009 x 1009,
Scale 100/100/100, centred at the origin, then rerun this script; it reuses an existing landscape.

Environment:
  BAM_SHOTS=biomes|sky|ocean|assets|all (or 1 = biomes)  photograph into Docs/Images/raw
  BAM_SHOT_BIOMES / BAM_SHOT_CAMS                       filter the biome shots by name
  BAM_SHOT_RES=1600x900, BAM_FIRST_WAIT=150 (s), BAM_QUIT=1 closes the editor afterwards
"""
import json
import math
import os
import sys
import time

import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import biomes  # noqa: E402

LEVEL = "/BiomeAutoMaterials/Showcase/L_BiomeShowcase"
SHOW_DIR = "/BiomeAutoMaterials/Showcase"
EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
ACT = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LVL = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
TAG = "BAMShowcase"
SKY_CLASS = getattr(unreal, "BiomeSkyEnvironment", None)
OCEAN_CLASS = getattr(unreal, "BiomeOcean", None)
HAS_SKY = SKY_CLASS is not None and EAL.does_asset_exist("/BiomeAutoMaterials/Sky/M_BiomeSky")
HAS_OCEAN = OCEAN_CLASS is not None and EAL.does_asset_exist("/BiomeAutoMaterials/Ocean/M_BiomeOcean")

# Extra cameras (loc, target, fov): the sea lies to the south-west of the terrain (world -Y).
EXTRA_CAMS = {
    "SeaLow": ((-6000.0, -52000.0, 420.0), (-6000.0, -90000.0, 300.0), 60.0),
    "SeaWest": ((2000.0, -50000.0, 900.0), (2000.0, -120000.0, 2500.0), 70.0),
    "SeaAerial": ((-30000.0, -40000.0, 9000.0), (-2000.0, -80000.0, 0.0), 60.0),
    "SkyUp": ((0.0, -30000.0, 2500.0), (0.0, -60000.0, 22000.0), 80.0),
    # on the headland, ~10 m above its top: high enough that a gale's crests stay below the lens
    "SeaCliff": ((32200.0, -34000.0, 4200.0), (-20000.0, -110000.0, 0.0), 65.0),
    # the bay's reef: under water, and looking down into the shallows
    "Reef": ((-8000.0, -36500.0, -700.0), (-6000.0, -43000.0, -1500.0), 75.0),
    "Shallows": ((-8000.0, -32500.0, 700.0), (-8000.0, -36500.0, -900.0), 70.0),
}


def log(m):
    unreal.log(f"[BAM] {m}")


def spawn(cls, loc=(0, 0, 0), rot=(0, 0, 0), label=None):
    a = ACT.spawn_actor_from_class(cls, unreal.Vector(*loc), unreal.Rotator(roll=rot[0], pitch=rot[1], yaw=rot[2]))
    if label:
        a.set_actor_label(label)
    a.tags = [TAG]
    return a


def water_material():
    path = f"{SHOW_DIR}/M_ShowcaseSea"
    if EAL.does_asset_exist(path):
        return unreal.load_asset(path)
    m = TOOLS.create_asset("M_ShowcaseSea", SHOW_DIR, unreal.Material, unreal.MaterialFactoryNew())
    c = MEL.create_material_expression(m, unreal.MaterialExpressionConstant3Vector, -400, 0)
    c.set_editor_property("constant", unreal.LinearColor(0.006, 0.022, 0.028, 1))
    r = MEL.create_material_expression(m, unreal.MaterialExpressionConstant, -400, 200)
    r.set_editor_property("r", 0.06)
    MEL.connect_material_property(c, "", unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(r, "", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.recompile_material(m)
    EAL.save_asset(path)
    return m


def find_landscape():
    for a in ACT.get_all_level_actors():
        if isinstance(a, unreal.LandscapeProxy):
            return a
    return None


def stock_environment():
    sun = spawn(unreal.DirectionalLight, (0, 0, 50000), (0, -32, 205), "Sun")
    lc = sun.get_component_by_class(unreal.DirectionalLightComponent)
    lc.set_editor_property("atmosphere_sun_light", True)
    lc.set_editor_property("intensity", 9.0)
    lc.set_editor_property("light_source_angle", 0.545)
    spawn(unreal.SkyAtmosphere, label="SkyAtmosphere")
    sky = spawn(unreal.SkyLight, (0, 0, 20000), label="SkyLight")
    sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property("real_time_capture", True)
    fog = spawn(unreal.ExponentialHeightFog, (0, 0, 0), label="Fog")
    fc = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
    fc.set_editor_property("fog_density", 0.0025)
    fc.set_editor_property("fog_height_falloff", 0.15)
    spawn(unreal.VolumetricCloud, label="Clouds")


def build_level():
    if os.environ.get("BAM_REUSE_LEVEL") == "1" and EAL.does_asset_exist(LEVEL):
        LVL.load_level(LEVEL)
        return find_landscape()
    first = unreal.load_asset(f"/BiomeAutoMaterials/Biomes/MI_Biome_{next(iter(biomes.BIOMES))}")
    if EAL.does_asset_exist(LEVEL):
        LVL.load_level(LEVEL)
    else:
        LVL.new_level(LEVEL)
    for a in ACT.get_all_level_actors():
        if TAG in [str(t) for t in a.tags]:
            ACT.destroy_actor(a)
    land = find_landscape()
    if land and os.environ.get("BAM_NEW_TERRAIN") == "1":
        # Showcase/ShowcaseTerrain.r16 was regenerated: replace the showcase's own landscape (this level only).
        ACT.destroy_actor(land)
        land = None
    if not land:
        lib = getattr(unreal, "PirateWorldBuilderLibrary", None)
        if lib is None:
            unreal.log_error("[BAM] no landscape in the level and no landscape builder: import Showcase/ShowcaseTerrain.png "
                             "in Landscape mode (1009 x 1009, scale 100), then run this script again")
            return None
        land = lib.create_island_landscape(os.path.join(ROOT, "Showcase", "ShowcaseTerrain.r16"), 1009,
                                           unreal.Vector(0, 0, 0), unreal.Vector(100, 100, 100), first, "BiomeShowcaseLandscape")
    land.set_editor_property("landscape_material", first)

    if HAS_SKY:
        sky = spawn(SKY_CLASS, (0, 0, 0), label="BiomeSky")
        sky.set_editor_property("time_of_day", 10.5)
        sky.set_editor_property("weather", unreal.BiomeSkyWeather.FAIR)
    else:
        stock_environment()
    pp = spawn(unreal.PostProcessVolume, label="PostProcess")
    pp.set_editor_property("unbound", True)
    s = pp.get_editor_property("settings")
    s.set_editor_property("override_depth_of_field_fstop", True)
    s.set_editor_property("depth_of_field_fstop", 32.0)
    if not HAS_SKY:
        s.set_editor_property("override_auto_exposure_bias", True)
        s.set_editor_property("auto_exposure_bias", 0.3)
    pp.set_editor_property("settings", s)

    if HAS_OCEAN:
        ocean = spawn(OCEAN_CLASS, (0, 0, 0), label="BiomeOcean")
        ocean.set_editor_property("shore_bake_half_size", 120000.0)
        ocean.set_editor_property("shore_bake_resolution", 1024)
        ocean.bake_shore_field()
    else:
        sea = spawn(unreal.StaticMeshActor, (0, 0, 0), label="Sea")
        smc = sea.static_mesh_component
        smc.set_static_mesh(unreal.load_asset("/Engine/BasicShapes/Plane"))
        sea.set_actor_scale3d(unreal.Vector(5000, 5000, 1))
        smc.set_material(0, water_material())

    if EAL.does_directory_exist("/BiomeAutoMaterials/Marine") and os.environ.get("BAM_NO_MARINE") != "1":
        # a tropical reef in the bay (the scatter tool's own sets and rules), thinned out for the showcase
        import runpy
        os.environ.update(BAM_BIOME="TropicalIsland", BAM_SCATTER_ROLES="reef,seabed,fish", BAM_SCATTER_CLEAR="1",
                          BAM_SCATTER_DENSITY=os.environ.get("BAM_SHOWCASE_MARINE_DENSITY", "0.25"), BAM_SCATTER_SEED="3")
        runpy.run_path(os.path.join(HERE, "assets", "scatter_biome.py"), run_name="__main__")

    cams = json.load(open(os.path.join(ROOT, "Showcase", "cameras.json")))["cameras"]
    entries = [(c["name"], c["loc"], c["target"], c["fov"]) for c in cams]
    entries += [(n, l, t, f) for n, (l, t, f) in EXTRA_CAMS.items()]
    for name, l, t, fov in entries:
        loc = unreal.Vector(*l)
        rot = unreal.MathLibrary.find_look_at_rotation(loc, unreal.Vector(*t))
        cam = ACT.spawn_actor_from_class(unreal.CineCameraActor, loc, rot)
        cam.set_actor_label(f"Cam_{name}")
        cam.tags = [TAG]
        cc = cam.get_cine_camera_component()
        fs = cc.get_editor_property("focus_settings")
        fs.set_editor_property("focus_method", unreal.CameraFocusMethod.DISABLE)
        cc.set_editor_property("focus_settings", fs)
        fb = cc.get_editor_property("filmback")
        cc.set_editor_property("current_focal_length", fb.sensor_width * 0.5 / math.tan(math.radians(fov * 0.5)))
    LVL.save_current_level()
    log(f"showcase level saved with {len(entries)} cameras (sky={HAS_SKY}, ocean={HAS_OCEAN})")
    return land


# ---------------------------------------------------------------------------------------------------------------------
# photographs (driven by the editor tick so the renderer can stream textures and compile shaders between shots)
# ---------------------------------------------------------------------------------------------------------------------
def find(label):
    for a in ACT.get_all_level_actors():
        if a.get_actor_label() == label:
            return a
    return None


def set_sky(time_of_day=None, weather=None, lat=None, date=None, auroras=None, cover=None):
    sky = find("BiomeSky")
    if not sky:
        return
    if lat is not None:
        sky.set_location(float(lat), sky.get_editor_property("longitude"))
    if date is not None:
        sky.set_date(date[0], date[1], date[2])
    if time_of_day is not None:
        sky.set_time_of_day(float(time_of_day))
    if weather is not None:
        sky.set_editor_property("weather", getattr(unreal.BiomeSkyWeather, weather))
    if auroras is not None:
        sky.set_editor_property("auroras", auroras)
    sky.set_cloud_cover(-1.0 if cover is None else cover)
    sky.snap_to_target()


def set_sea(wind, direction=200.0, swell=1.0):
    ocean = find("BiomeOcean")
    if ocean:
        ocean.set_editor_property("wind_speed", float(wind))
        ocean.set_editor_property("wind_direction", float(direction))
        ocean.set_editor_property("swell_amount", float(swell))
        ocean.set_editor_property("find_wind_source_automatically", False)
    sky = find("BiomeSky")
    if sky:
        sky.set_wind(float(direction), float(wind))


def aim_at_moon(cam_label):
    sky, cam = find("BiomeSky"), find(cam_label)
    if not sky or not cam:
        return
    d = sky.get_moon_direction()
    loc = cam.get_actor_location()
    tgt = unreal.Vector(loc.x + d.x * 10000.0, loc.y + d.y * 10000.0, loc.z + max(d.z, 0.05) * 10000.0 - 1500.0)
    cam.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(loc, tgt), False)


def night_with_moon():
    """A clear night with a gibbous moon well up in the sky (searched over the dates of 2026)."""
    sky = find("BiomeSky")
    best = (2026, 4, 1)
    if sky:
        for month in range(1, 13):
            for day in (2, 6, 10, 14, 18, 22, 26):
                set_sky(time_of_day=21.5, weather="CLEAR", lat=17.0, date=(2026, month, day))
                ph, z = sky.get_moon_phase(), sky.get_moon_direction().z
                if 0.38 < ph < 0.48 and 0.3 < z < 0.7:
                    best = (2026, month, day)
                    break
            else:
                continue
            break
    set_sky(time_of_day=21.5, weather="CLEAR", lat=17.0, date=best)
    aim_at_moon("Cam_SeaWest")


def shot_quality(high):
    """Screenshots are single frames: without the temporal history the volumetric clouds come out grainy. For stills,
    trace them at full resolution with more samples."""
    for c in (("r.VolumetricRenderTarget", "0" if high else "1"),):
        unreal.SystemLibrary.execute_console_command(None, f"{c[0]} {c[1]}")
    sky = find("BiomeSky")
    if sky:
        cl = sky.get_editor_property("clouds")
        cl.set_editor_property("view_sample_count_scale", 4.0 if high else 1.0)
        cl.set_editor_property("shadow_view_sample_count_scale", 2.0 if high else 1.0)


def jobs_for(sets, land):
    out = os.path.join(ROOT, "Docs", "Images", "raw")
    jobs = []
    if "biomes" in sets:
        bf = [x for x in os.environ.get("BAM_SHOT_BIOMES", "").split(",") if x]
        cf = [x for x in os.environ.get("BAM_SHOT_CAMS", "").split(",") if x] or [c["name"] for c in json.load(open(os.path.join(ROOT, "Showcase", "cameras.json")))["cameras"]]
        for b in biomes.BIOMES:
            if bf and b not in bf:
                continue
            setup = (lambda b=b: (land.set_editor_property("landscape_material", unreal.load_asset(f"/BiomeAutoMaterials/Biomes/MI_Biome_{b}")),
                                  set_sky(10.5, "FAIR", 17.0, (2026, 4, 1), False), set_sea(7.0)))
            for i, c in enumerate(cf):
                jobs.append(dict(file=os.path.join(out, f"{b}_{c}.png"), cam=f"Cam_{c}", setup=setup if i == 0 else None,
                                 wait=float(os.environ.get("BAM_BIOME_WAIT", "25")) if i == 0 else 1.0))
    if "sky" in sets and HAS_SKY:
        grass = lambda: land.set_editor_property("landscape_material", unreal.load_asset("/BiomeAutoMaterials/Biomes/MI_Biome_TropicalIsland"))  # noqa: E731
        jobs += [
            dict(file=os.path.join(out, "Sky_Noon.png"), cam="Cam_Overview", setup=lambda: (grass(), set_sky(12.5, "FAIR", 17.0, (2026, 4, 1), False), set_sea(7.0)), wait=40),
            dict(file=os.path.join(out, "Sky_Sunset.png"), cam="Cam_SeaWest", setup=lambda: (set_sky(18.25, "FAIR", 17.0, (2026, 4, 1)), set_sea(6.0)), wait=30),
            dict(file=os.path.join(out, "Sky_Night.png"), cam="Cam_SeaWest", setup=lambda: (night_with_moon(), set_sea(5.0)), wait=30),
            dict(file=os.path.join(out, "Sky_Stars.png"), cam="Cam_SkyUp", setup=lambda: (set_sky(1.0, "CLEAR", 17.0, (2026, 7, 15)), set_sea(4.0)), wait=25),
            dict(file=os.path.join(out, "Sky_Overcast.png"), cam="Cam_Overview", setup=lambda: (set_sky(11.0, "OVERCAST", 17.0, (2026, 4, 1)), set_sea(10.0)), wait=30),
            dict(file=os.path.join(out, "Sky_Storm.png"), cam="Cam_SeaCliff", setup=lambda: (set_sky(15.0, "STORM", 17.0, (2026, 4, 1)), set_sea(20.0)), wait=40),
            dict(file=os.path.join(out, "Sky_Aurora.png"), cam="Cam_SkyUp", setup=lambda: (set_sky(23.5, "CLEAR", 69.0, (2026, 1, 20), True), set_sea(5.0)), wait=30),
        ]
    if "ocean" in sets and HAS_OCEAN:
        jobs += [
            dict(file=os.path.join(out, "Ocean_Calm.png"), cam="Cam_SeaLow", setup=lambda: (set_sky(9.5, "CLEAR", 17.0, (2026, 4, 1), False), set_sea(2.5, 200.0, 0.6)), wait=30),
            dict(file=os.path.join(out, "Ocean_Moderate.png"), cam="Cam_SeaLow", setup=lambda: (set_sky(9.5, "FAIR"), set_sea(9.0)), wait=30),
            dict(file=os.path.join(out, "Ocean_Gale.png"), cam="Cam_SeaCliff", setup=lambda: (set_sky(13.0, "OVERCAST"), set_sea(19.0, 200.0, 1.4)), wait=30),
            dict(file=os.path.join(out, "Ocean_Aerial.png"), cam="Cam_SeaAerial", setup=lambda: (set_sky(10.0, "FAIR"), set_sea(11.0)), wait=30),
            dict(file=os.path.join(out, "Ocean_Shore.png"), cam="Cam_Coast", setup=lambda: (set_sky(10.0, "FAIR"), set_sea(8.0)), wait=30),
        ]
    if "marine" in sets and HAS_OCEAN:
        jobs += [
            dict(file=os.path.join(out, "Marine_Reef.png"), cam="Cam_Reef", setup=lambda: (set_sky(11.5, "CLEAR", 17.0, (2026, 4, 1), False), set_sea(4.0, 200.0, 0.5)), wait=35),
            dict(file=os.path.join(out, "Marine_Shallows.png"), cam="Cam_Shallows", setup=lambda: set_sea(3.0, 200.0, 0.4), wait=20),
        ]
    if "debug" in sets:
        ocean = lambda show: find("BiomeOcean").set_actor_hidden_in_game(not show) or find("BiomeOcean").set_is_temporarily_hidden_in_editor(not show)  # noqa: E731
        clouds = lambda hq: shot_quality(hq)  # noqa: E731
        jobs += [
            dict(file=os.path.join(out, "Dbg_Overcast_Ocean.png"), cam="Cam_Overview", setup=lambda: (set_sky(11.0, "OVERCAST", 17.0, (2026, 4, 1)), set_sea(10.0)), wait=30),
            dict(file=os.path.join(out, "Dbg_Overcast_NoOcean.png"), cam="Cam_Overview", setup=lambda: ocean(False), wait=10),
            dict(file=os.path.join(out, "Dbg_Fair_LQ.png"), cam="Cam_SeaLow", setup=lambda: (ocean(True), clouds(False), set_sky(9.5, "FAIR", 17.0, (2026, 4, 1)), set_sea(7.0)), wait=25),
            dict(file=os.path.join(out, "Dbg_Fair_HQ.png"), cam="Cam_SeaLow", setup=lambda: clouds(True), wait=15),
        ]
    for j in jobs:
        j.setdefault("wait", 1.0)
    return jobs


class Shooter:
    def __init__(self, jobs):
        self.jobs = jobs
        w, h = os.environ.get("BAM_SHOT_RES", "1600x900").split("x")
        self.res = (int(w), int(h))
        os.makedirs(os.path.join(ROOT, "Docs", "Images", "raw"), exist_ok=True)
        self.i = 0
        self.busy = False
        self.pending = None
        self.prepared = -1
        self.wait_until = time.monotonic() + float(os.environ.get("BAM_FIRST_WAIT", "150"))
        try:
            perf = unreal.get_default_object(unreal.EditorPerformanceSettings)
            perf.set_editor_property("throttle_cpu_when_not_foreground", False)
        except Exception as e:  # noqa
            unreal.log_warning(f"[BAM] throttle setting: {e}")
        unreal.SystemLibrary.execute_console_command(None, "t.IdleWhenNotForeground 0")
        shot_quality(True)
        self.handle = unreal.register_slate_post_tick_callback(self.tick)
        log(f"shooting {len(self.jobs)} images")

    def tick(self, dt):
        # take_high_res_screenshot ticks Slate itself, which calls back in here: ignore nested calls
        if self.busy or time.monotonic() < self.wait_until:
            return
        self.busy = True
        try:
            self.step()
        except Exception:  # noqa
            import traceback
            unreal.log_error("[BAM] " + traceback.format_exc())
            self.pending = None
            self.i += 1
        finally:
            self.busy = False

    def step(self):
        if self.pending:  # wait until the renderer has written the requested file
            fn, t0, tries = self.pending
            if os.path.exists(fn) and os.path.getsize(fn) > 0:
                log(f"shot {os.path.basename(fn)}")
                self.pending = None
                self.i += 1
                self.wait_until = time.monotonic() + 1.0
            elif time.monotonic() - t0 > 90:
                if tries >= 2:
                    unreal.log_warning(f"[BAM] no image for {fn}")
                    self.pending = None
                    self.i += 1
                else:
                    self.request(tries + 1)
            return
        if self.i >= len(self.jobs):
            unreal.unregister_slate_post_tick_callback(self.handle)
            log("BAM SHOTS DONE")
            if os.environ.get("BAM_QUIT") == "1":
                unreal.SystemLibrary.quit_editor()
            return
        job = self.jobs[self.i]
        if self.prepared != self.i:
            self.prepared = self.i
            if job.get("setup"):
                job["setup"]()
            self.wait_until = time.monotonic() + job["wait"]
            return
        if os.path.exists(job["file"]):
            os.remove(job["file"])
        self.request(1)

    def request(self, tries):
        job = self.jobs[self.i]
        self.pending = (job["file"], time.monotonic(), tries)
        cam = find(job["cam"])
        ocean = find("BiomeOcean")
        if ocean:
            log(f"{os.path.basename(job['file'])}: sea Hs {ocean.get_significant_wave_height():.2f} m, wind {ocean.get_wind_velocity().length():.1f} m/s")
        unreal.AutomationLibrary.take_high_res_screenshot(self.res[0], self.res[1], job["file"], cam, False, False,
                                                         unreal.ComparisonTolerance.LOW)


try:
    _land = build_level()
    _sets = os.environ.get("BAM_SHOTS", "")
    _sets = {"1": "biomes", "all": "biomes,sky,ocean,marine"}.get(_sets, _sets)
    if _land and _sets:
        _shooter = Shooter(jobs_for(_sets.split(","), _land))
    elif os.environ.get("BAM_QUIT") == "1":
        unreal.SystemLibrary.quit_editor()
except Exception:  # noqa
    import traceback
    unreal.log_error("[BAM] " + traceback.format_exc())
    if os.environ.get("BAM_QUIT") == "1":
        unreal.SystemLibrary.quit_editor()
