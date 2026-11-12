import unreal
LVL = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
ACT = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LVL.load_level("/BiomeAutoMaterials/Showcase/L_BiomeShowcase")
oc = [a for a in ACT.get_all_level_actors() if isinstance(a, unreal.BiomeOcean)]
land = [a for a in ACT.get_all_level_actors() if isinstance(a, unreal.LandscapeProxy)]
def L(m): unreal.log("[DIAG] " + str(m))
L(f"oceans {len(oc)} land {len(land)}")
o = oc[0]
L(f"ocean loc {o.get_actor_location()} bounds {o.get_editor_property('shore_bounds')}")
for a in ACT.get_all_level_actors():
    l = a.get_actor_label()
    if l.startswith("Cam_"): L(f"{l} {a.get_actor_location()}")
w = unreal.EditorLevelLibrary.get_editor_world()
for wind in (7.0, 10.0, 20.0):
    o.set_editor_property("wind_speed", wind)
    o.set_editor_property("find_wind_source_automatically", False)
    o.set_sea_condition(o.get_editor_property("sea_condition"))
    L(f"wind {wind} Hs {o.get_significant_wave_height()}")
    for (x, y) in [(0, -48384), (0, -40000), (0, -30000), (-20160, -33264), (0, -20000), (5040, -14112), (0, -60000), (0, -90000)]:
        hit = unreal.SystemLibrary.line_trace_single(w, unreal.Vector(x, y, 50000), unreal.Vector(x, y, -50000), unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [o], unreal.DrawDebugTrace.NONE, True)
        gz = hit.to_tuple()[4].z if hit and hit.to_tuple()[0] else None
        L(f"  ({x},{y}) ground {gz} water {o.get_water_height_at(unreal.Vector(x, y, 0))} disp {o.get_wave_displacement_at(unreal.Vector(x, y, 0))}")
mid = o.get_material_instance()
if mid:
    for p in ("HasShore",):
        L(f"MID {p} {mid.get_scalar_parameter_value(p)}")
    for p in ("ShoreBounds", "WavePhaseB", "Wave0", "Wave1", "SeaInfo", "WindInfo0", "WindInfo1", "WindInfo2"):
        L(f"MID {p} {mid.get_vector_parameter_value(p)}")
unreal.SystemLibrary.quit_editor()
