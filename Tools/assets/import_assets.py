"""Import the island assets into /BiomeAutoMaterials/Assets (UE Python, rerunnable). Run Tools/assets/prepare_glb.py
first: it writes the size-reduced .glb files to Build/Assets.

    Editor:       Tools > Execute Python Script... > Tools/assets/import_assets.py
    Command line: UnrealEditor-Cmd.exe <Project>.uproject -ExecutePythonScript="<path>/Tools/assets/import_assets.py" -unattended

Per asset (glTF through Interchange, real-world scale, 1 unit = 1 cm):
  * Nanite on every opaque mesh; glass and other translucent meshes stay off Nanite.
  * Collision: buildings, docks, castle, town buildings and streets, cliffs and coastal rocks use their own triangles
    (complex as simple, so you can walk in doors and on stairs); props and loose rocks get a simple convex hull;
    grass, flowers, ferns, moss, shrubs and debris have none (they would only snag the player).
  * No lightmap UVs and no distance fields (the pack is for Lumen; distance fields can be enabled per mesh).
Environment: BAM_ASSETS_FORCE=1 re-imports existing assets; BAM_ASSETS_ONLY=Name,Cat/Sub filters; BAM_QUIT=1 quits.
Writes Build/Assets/imported.json (asset paths, triangle counts, collision kind) for the docs and the scatter tool.
"""
import json
import os
import sys
import time

import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import importlib  # noqa: E402

import catalog  # noqa: E402

importlib.reload(catalog)

DEST = "/BiomeAutoMaterials/Assets"
BUILD = os.path.join(ROOT, "Build", "Assets")
EAL = unreal.EditorAssetLibrary

COMPLEX = ("Buildings", "Docks", "Town/Buildings", "Town/Castle", "Town/Streets", "Town/Square", "Town/Bazaar")
NO_COLLISION_WORDS = ("Grass", "Flower", "Fern", "Moss", "Weed", "Nettle", "Dandelion", "Celandine", "Periwinkle", "DryLeaves",
                      "BarkDebris", "Sorrel", "Anthurium", "Calathea", "Succulent", "Shrub", "Sapling", "Bush", "DryBranches",
                      "Pachira", "Bamboo", "Banana", "Root", "PineRoots", "RooibosBush", "DeadBranch", "Wheat")
SOLID_WORDS = ("Log", "Stump", "Trunk", "Boulder", "Boulders", "Cliff", "Rock", "Rocks", "Stones", "Stone", "QuiverTree", "Tree")
COMPLEX_NATURE = ("CoastalCliff", "CoastRocks", "Mountainside", "RockFace", "DesertCliff", "SandRocks")


def log(m):
    unreal.log(f"[BAM] {m}")


def under(cat, roots):
    return any(cat == r or cat.startswith(r + "/") for r in roots)


def collision_kind(name, cat):
    short = name[3:] if name.startswith("SM_") else name
    if under(cat, COMPLEX) or any(short.startswith(w) for w in COMPLEX_NATURE):
        return "complex"
    if any(w in short for w in NO_COLLISION_WORDS) and not any(short.startswith(w) for w in SOLID_WORDS):
        return "none"
    if cat.startswith("Nature/Plants") or cat.startswith("Nature/Tropical"):
        return "none"
    if cat.startswith("Nature/Trees"):
        return "simple"   # the trunk's convex hull is close enough to block a walker; leaves stay passable
    return "simple"


def is_translucent(mesh):
    for sm in mesh.get_editor_property("static_materials"):
        mi = sm.get_editor_property("material_interface")
        if not mi:
            continue
        base = mi.get_base_material()
        if base and base.get_editor_property("blend_mode") in (unreal.BlendMode.BLEND_TRANSLUCENT, unreal.BlendMode.BLEND_ADDITIVE):
            return True
        if isinstance(mi, unreal.MaterialInstance):
            ov = mi.get_editor_property("base_property_overrides")
            if ov and ov.get_editor_property("override_blend_mode") and ov.get_editor_property("blend_mode") == unreal.BlendMode.BLEND_TRANSLUCENT:
                return True
    return False


def pipelines():
    p1 = EAL.load_asset("/Interchange/Pipelines/DefaultAssetsPipeline")
    p2 = EAL.load_asset("/Interchange/Pipelines/DefaultGLTFPipeline")
    p1.set_editor_property("scene_name_sub_folder", False)
    p1.set_editor_property("asset_type_sub_folders", True)
    p1.set_editor_property("use_source_name_for_asset", False)
    p1.common_meshes_properties.set_editor_property("recompute_normals", False)
    p1.common_meshes_properties.set_editor_property("use_mikk_t_space", False)
    p1.mesh_pipeline.set_editor_property("generate_lightmap_u_vs", False)
    p1.mesh_pipeline.set_editor_property("distance_field_resolution_scale", 0.0)
    params = unreal.ImportAssetParameters()
    params.is_automated = True
    params.replace_existing = True
    params.override_pipelines = [unreal.SoftObjectPath(p1.get_path_name()), unreal.SoftObjectPath(p2.get_path_name())]
    return p1, params


def finish_mesh(mesh, kind, nanite_wanted):
    changed = False
    if nanite_wanted and is_translucent(mesh):
        ns = mesh.get_editor_property("nanite_settings")
        if ns.get_editor_property("enabled"):
            ns.set_editor_property("enabled", False)
            mesh.set_editor_property("nanite_settings", ns)
            changed = True
    body = mesh.get_editor_property("body_setup")
    if body:
        if kind == "complex":
            body.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        elif kind == "none":
            body.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_SIMPLE_AS_COMPLEX)
            try:
                unreal.EditorStaticMeshLibrary.remove_collisions(mesh)
            except Exception:  # noqa
                pass
        changed = True
    if kind == "simple":
        try:
            if unreal.EditorStaticMeshLibrary.get_simple_collision_count(mesh) == 0:
                # A 26-sided hull around the mesh (cheap to build even on dense Nanite meshes).
                unreal.EditorStaticMeshLibrary.add_simple_collisions(mesh, unreal.ScriptCollisionShapeType.NDOP26)
                changed = True
        except Exception as e:  # noqa
            unreal.log_warning(f"[BAM] collision {mesh.get_name()}: {e}")
    return changed


def main():
    prepared_path = os.path.join(BUILD, "prepared.json")
    if not os.path.exists(prepared_path):
        raise RuntimeError("run Tools/assets/prepare_glb.py first (Build/Assets/prepared.json is missing)")
    prepared = json.load(open(prepared_path))
    only = [x for x in os.environ.get("BAM_ASSETS_ONLY", "").split(",") if x]
    force = os.environ.get("BAM_ASSETS_FORCE") == "1"
    im = unreal.InterchangeManager.get_interchange_manager_scripted()
    p1, params = pipelines()
    out_path = os.path.join(BUILD, "imported.json")
    record = json.load(open(out_path)) if os.path.exists(out_path) else {}
    t0 = time.time()
    done = 0
    for i, (name, info) in enumerate(sorted(prepared.items(), key=lambda kv: kv[1]["cat"])):
        cat = info["cat"].replace("\\", "/")
        if only and name not in only and not any(cat.startswith(o) for o in only):
            continue
        folder = f"{DEST}/{cat}"
        first = f"{folder}/StaticMeshes/{name}"
        if not force and EAL.does_asset_exist(first) and name in record:
            continue
        kind = collision_kind(name, cat)
        p1.mesh_pipeline.set_editor_property("build_nanite", True)
        p1.mesh_pipeline.set_editor_property("collision", kind == "simple")
        src = unreal.InterchangeManager.create_source_data(os.path.join(BUILD, *info["file"].split("/")))
        objs = list(im.import_asset(folder, src, params) or [])
        meshes = [o for o in objs if isinstance(o, unreal.StaticMesh)]
        for m in meshes:
            finish_mesh(m, kind, True)
        EAL.save_loaded_assets(objs, only_if_is_dirty=False)
        record[name] = {"cat": cat, "meshes": [m.get_path_name().split(".")[0] for m in meshes], "collision": kind,
                        "tris": info["tris"], "nanite": [bool(m.get_editor_property("nanite_settings").get_editor_property("enabled")) for m in meshes]}
        done += 1
        log(f"[{i + 1}/{len(prepared)}] {cat}/{name}: {len(meshes)} meshes, collision {kind}")
        if done % 10 == 0:
            json.dump(record, open(out_path, "w"), indent=1)
            unreal.SystemLibrary.collect_garbage()
    json.dump(record, open(out_path, "w"), indent=1)
    log(f"BAM ASSETS DONE imported={done} total={len(record)} in {time.time() - t0:.0f}s")


try:
    main()
except Exception:  # noqa
    import traceback
    unreal.log_error("[BAM] " + traceback.format_exc())
    log("BAM ASSETS FAILED")
if os.environ.get("BAM_QUIT") == "1":
    unreal.SystemLibrary.quit_editor()
