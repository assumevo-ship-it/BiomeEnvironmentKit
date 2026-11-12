"""Scatter a biome's island assets over the landscape in the open level (UE Python, editor).

    set BAM_BIOME=TemperateForest   (any name in Tools/assets/catalog.py)
    Tools > Execute Python Script... > Tools/assets/scatter_biome.py

Options (environment): BAM_SEA_LEVEL (m, default 0), BAM_SCATTER_SEED (default 1), BAM_SCATTER_DENSITY (multiplier,
default 1), BAM_SCATTER_ROLES (default trees,shrubs,rocks,coast,ground,reef,seabed,fish), BAM_SCATTER_CLEAR=1 removes an
earlier scatter.

Places static mesh actors (one folder per role in the Outliner, tagged BiomeScatter) on the landscape by slope and
height above sea level, following ROLE_RULES in catalog.py: trees on gentle ground above the beach, rocks on steeper
slopes, coastal rocks only near the water line, small ground cover sparsely (paint dense grass with the Foliage tool or
the landscape's grass output instead). Each mesh gets a random yaw, scale and a little sink into the ground.
Under the sea (Tools/marine): reef and seabed life by depth, and shoals of fish. A shoal is one actor holding an
instanced mesh: each fish carries the shoal's ellipse in its per-instance custom data, and M_SeaCreature swims it round
(and out of a swimmer's way), so the reef is alive in the editor without any Blueprint.
It only adds actors: nothing existing is changed, and BAM_SCATTER_CLEAR=1 only removes actors it tagged itself.
"""
import json
import math
import os
import random
import sys

import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import importlib  # noqa: E402

import catalog  # noqa: E402

importlib.reload(catalog)

ACT = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
TAG = "BiomeScatter"
GROUND_SHARE = 0.08   # ground cover as actors is heavy: a sparse accent only


def log(m):
    unreal.log(f"[BAM] {m}")


def mesh_paths():
    rec = os.path.join(ROOT, "Build", "Assets", "imported.json")
    out = {}
    if os.path.exists(rec):
        for name, info in json.load(open(rec)).items():
            short = name[3:] if name.startswith("SM_") else name
            if info["meshes"]:
                out[short] = info["meshes"][0]
    else:
        for a in unreal.EditorAssetLibrary.list_assets("/BiomeAutoMaterials/Assets", recursive=True):
            n = a.split(".")[-1]
            if n.startswith("SM_") and "/StaticMeshes/" in a:
                out.setdefault(n[3:], a.split(".")[0])
    for a in unreal.EditorAssetLibrary.list_assets("/BiomeAutoMaterials/Marine", recursive=False):
        n = a.split(".")[-1]
        if n.startswith("SM_Sea_"):
            out.setdefault(n[7:], a.split(".")[0])
    return out


def add_shoal(world, rng, mesh, centre, biome, scale):
    """One actor with an instanced mesh: 8-40 fish swimming round the same ellipse (custom data D0-D4)."""
    a = ACT.spawn_actor_from_class(unreal.Actor, centre, unreal.Rotator())
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    handles = sds.k2_gather_subobject_data_for_instance(a)
    if not handles:
        root = unreal.AddNewSubobjectParams(parent_handle=unreal.SubobjectDataHandle(), new_class=unreal.SceneComponent)
        handles = [sds.add_new_subobject(root)[0]]
    params = unreal.AddNewSubobjectParams(parent_handle=handles[0], new_class=unreal.InstancedStaticMeshComponent, blueprint_context=None)
    handle, fail = sds.add_new_subobject(params)
    ism = unreal.SubobjectDataBlueprintFunctionLibrary.get_object(unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle))
    if not ism:
        ACT.destroy_actor(a)
        return 0
    ism.set_static_mesh(mesh)
    ism.set_editor_property("num_custom_data_floats", 5)
    ism.set_cast_shadow(False)
    ism.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    size = max(mesh.get_bounding_box().max.x - mesh.get_bounding_box().min.x, 5.0)   # body length, cm
    count = rng.randint(8, 40) if size < 40 else rng.randint(3, 10)
    ra = rng.uniform(250.0, 900.0)
    rb = ra * rng.uniform(0.35, 0.8)
    speed = size * rng.uniform(1.0, 2.0)                    # cruising at one to two body lengths a second
    om = speed / ra * rng.choice((-1.0, 1.0))
    phase, heading = rng.uniform(0, 6.283), rng.uniform(0, 6.283)
    spread = 40.0 + size * 3.0
    for i in range(count):
        off = unreal.Vector(rng.gauss(0, spread), rng.gauss(0, spread), rng.gauss(0, spread * 0.35))
        s = scale * rng.uniform(0.85, 1.15)
        idx = ism.add_instance(unreal.Transform(off, unreal.Rotator(), unreal.Vector(s, s, s)), False)
        for k, v in enumerate((ra, rb, om, phase, heading)):
            ism.set_custom_data_value(idx, k, v, True)
    a.tags = [TAG]
    a.set_folder_path(f"BiomeScatter/{biome}/fish")
    a.set_actor_label(f"Shoal_{mesh.get_name()[7:]}")
    return count


def landscape_bounds():
    for a in ACT.get_all_level_actors():
        if isinstance(a, unreal.LandscapeProxy):
            origin, extent = a.get_actor_bounds(False)
            return origin, extent
    return None


def ground_at(world, x, y, top, bottom):
    hit = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(x, y, top), unreal.Vector(x, y, bottom),
                                                 unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [],
                                                 unreal.DrawDebugTrace.NONE, True)
    if not hit:
        return None
    t = hit.to_tuple()
    blocking, loc, normal, actor = t[0], t[4], t[6], t[9]
    if not blocking or not isinstance(actor, unreal.LandscapeProxy):
        return None
    return loc, normal


def main():
    biome = os.environ.get("BAM_BIOME", "TemperateMeadow")
    sets = catalog.sets_for(biome)
    if not sets:
        raise RuntimeError(f"unknown biome {biome}; see BIOME_SETS in Tools/assets/catalog.py")
    if os.environ.get("BAM_SCATTER_CLEAR") == "1":
        gone = [a for a in ACT.get_all_level_actors() if TAG in [str(t) for t in a.tags]]
        for a in gone:
            ACT.destroy_actor(a)
        log(f"removed {len(gone)} scattered actors")
    bounds = landscape_bounds()
    if not bounds:
        raise RuntimeError("no landscape in the level")
    origin, extent = bounds
    world = unreal.UnrealEditorSubsystem().get_editor_world()
    sea = float(os.environ.get("BAM_SEA_LEVEL", "0")) * 100.0
    rng = random.Random(int(os.environ.get("BAM_SCATTER_SEED", "1")))
    density = float(os.environ.get("BAM_SCATTER_DENSITY", "1"))
    roles = [r for r in os.environ.get("BAM_SCATTER_ROLES", "trees,shrubs,rocks,coast,ground,reef,seabed,fish").split(",") if r]
    paths = mesh_paths()
    area_ha = (2 * extent.x / 100.0) * (2 * extent.y / 100.0) / 10000.0
    placed = 0
    for role in roles:
        names = [n for n in sets.get(role, []) if n in paths]
        rule = catalog.ROLE_RULES[role]
        if not names:
            continue
        meshes = [unreal.load_asset(paths[n]) for n in names]
        count = int(rule["per_ha"] * area_ha * density * (GROUND_SHARE if role == "ground" else 1.0))
        tries = count * 4
        made = 0
        while made < count and tries > 0:
            tries -= 1
            x = origin.x + rng.uniform(-extent.x, extent.x)
            y = origin.y + rng.uniform(-extent.y, extent.y)
            g = ground_at(world, x, y, origin.z + extent.z + 10000.0, origin.z - extent.z - 10000.0)
            if not g:
                continue
            loc, n = g
            h = (loc.z - sea) / 100.0
            slope = math.degrees(math.acos(max(-1.0, min(1.0, n.z))))
            if slope > rule["max_slope"] or h < rule["min_h"] or h > rule["max_h"]:
                continue
            mesh = rng.choice(meshes)
            s = rng.uniform(*rule["scale"])
            if role == "fish":   # mid-water, at least 1.5 m off the bottom and 2 m under the surface
                z = rng.uniform(loc.z + 150.0, min(sea - 200.0, loc.z + 1200.0))
                if z <= loc.z + 150.0:
                    continue
                made += 1 if add_shoal(world, rng, mesh, unreal.Vector(loc.x, loc.y, z), biome, s) else 0
                continue
            rot = unreal.Rotator(roll=0.0, pitch=0.0, yaw=rng.uniform(0, 360))
            pos = unreal.Vector(loc.x, loc.y, loc.z - rule["sink"] * s)
            a = ACT.spawn_actor_from_object(mesh, pos, rot)
            if not a:
                continue
            a.set_actor_scale3d(unreal.Vector(s, s, s))
            a.tags = [TAG]
            a.set_folder_path(f"BiomeScatter/{biome}/{role}")
            made += 1
        placed += made
        log(f"{biome} {role}: {made} placed")
    log(f"BAM SCATTER DONE {placed} actors")


try:
    main()
except Exception:  # noqa
    import traceback
    unreal.log_error("[BAM] " + traceback.format_exc())
