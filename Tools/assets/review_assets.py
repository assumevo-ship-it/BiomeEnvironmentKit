"""Photograph every imported island asset and sea creature, 12 to a frame, for review (UE Python, needs a ticking editor).

    UnrealEditor.exe <Project>.uproject -ExecCmds="py <path>/Tools/assets/review_assets.py"

Builds /BiomeAutoMaterials/Showcase/L_AssetReview (a grey floor under the plugin's sky at 10:30), lays the meshes out on a
4 x 3 grid, each scaled so its bounding sphere is the same size (the frame is for judging shading, not size), and
writes Docs/Images/raw/review/Review_<Group>_<n>.png plus review.json (which mesh is in which cell, its real size and
triangle count). Tools/assets/make_asset_docs.py --review turns them into labelled sheets.
Environment: BAM_REVIEW_ONLY=Nature,Marine (path filters), BAM_SHOT_RES=1920x1080, BAM_QUIT=1.
"""
import json
import math
import os
import time

import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
LEVEL = "/BiomeAutoMaterials/Showcase/L_AssetReview"
OUT = os.path.join(ROOT, "Docs", "Images", "raw", "review")
EAL = unreal.EditorAssetLibrary
ACT = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LVL = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
COLS, ROWS = 4, 3
CELL = 700.0          # cm between cell centres
FIT = 260.0           # every mesh scaled to this bounding-sphere radius (cm)


def log(m):
    unreal.log(f"[BAM] {m}")


def meshes():
    only = [x for x in os.environ.get("BAM_REVIEW_ONLY", "").split(",") if x]
    out = []
    for root in ("/BiomeAutoMaterials/Assets", "/BiomeAutoMaterials/Marine"):
        for a in EAL.list_assets(root, recursive=True):
            p = a.split(".")[0]
            n = p.rsplit("/", 1)[-1]
            if not n.startswith("SM_") or (only and not any(o in p for o in only)):
                continue
            if EAL.find_asset_data(p).asset_class_path.asset_name != "StaticMesh":
                continue
            group = "Marine" if "/Marine" in p else p.split("/Assets/")[1].split("/")[0]
            out.append((group, p))
    out.sort()
    return out


def build_level():
    if EAL.does_asset_exist(LEVEL):
        EAL.delete_asset(LEVEL)
    LVL.new_level(LEVEL)
    sky_cls = getattr(unreal, "BiomeSkyEnvironment", None)
    if sky_cls:
        sky = ACT.spawn_actor_from_class(sky_cls, unreal.Vector(0, 0, 0))
        sky.set_editor_property("time_of_day", 10.5)
        sky.set_editor_property("weather", unreal.BiomeSkyWeather.CLEAR)
        sky.snap_to_target()
    floor = ACT.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(COLS * CELL / 2, ROWS * CELL / 2, 0))
    floor.static_mesh_component.set_static_mesh(unreal.load_asset("/Engine/BasicShapes/Plane"))
    floor.set_actor_scale3d(unreal.Vector(400, 400, 1))
    grey = unreal.load_asset("/Engine/EngineMaterials/DefaultMaterial")
    floor.static_mesh_component.set_material(0, grey)
    cam = ACT.spawn_actor_from_class(unreal.CineCameraActor, unreal.Vector(0, 0, 0))
    cam.set_actor_label("ReviewCam")
    cc = cam.get_cine_camera_component()
    fs = cc.get_editor_property("focus_settings")
    fs.set_editor_property("focus_method", unreal.CameraFocusMethod.DISABLE)
    cc.set_editor_property("focus_settings", fs)
    fb = cc.get_editor_property("filmback")
    cc.set_editor_property("current_focal_length", fb.sensor_width * 0.5 / math.tan(math.radians(25.0)))
    # the grid is seen from the front, slightly above, so trees and buildings show their faces
    centre = unreal.Vector((COLS - 1) * CELL / 2, (ROWS - 1) * CELL / 2, FIT * 0.9)
    loc = unreal.Vector(centre.x - 3600.0, centre.y, 1500.0)
    cam.set_actor_location(loc, False, False)
    cam.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(loc, centre), False)
    return cam


class Shooter:
    def __init__(self, cam, items):
        self.cam = cam
        self.pages = []
        groups = {}
        for g, p in items:
            groups.setdefault(g, []).append(p)
        for g, ps in groups.items():
            for i in range(0, len(ps), COLS * ROWS):
                self.pages.append((g, i // (COLS * ROWS) + 1, ps[i:i + COLS * ROWS]))
        w, h = os.environ.get("BAM_SHOT_RES", "1920x1080").split("x")
        self.res = (int(w), int(h))
        os.makedirs(OUT, exist_ok=True)
        self.i, self.actors, self.pending, self.busy = 0, [], None, False
        self.index = {}
        self.wait = time.monotonic() + 60.0
        unreal.SystemLibrary.execute_console_command(None, "t.IdleWhenNotForeground 0")
        unreal.SystemLibrary.execute_console_command(None, "r.VolumetricRenderTarget 0")
        self.handle = unreal.register_slate_post_tick_callback(self.tick)
        log(f"review: {len(items)} meshes on {len(self.pages)} pages")

    def lay_out(self, paths):
        for a in self.actors:
            ACT.destroy_actor(a)
        self.actors = []
        cells = []
        for k, p in enumerate(paths):
            mesh = unreal.load_asset(p)
            bb = mesh.get_bounding_box()
            ext = unreal.Vector(bb.max.x - bb.min.x, bb.max.y - bb.min.y, bb.max.z - bb.min.z)
            r = max(0.5 * math.sqrt(ext.x ** 2 + ext.y ** 2 + ext.z ** 2), 1.0)
            s = FIT / r
            # row 0 is the far row (+X), so the frame reads left to right, top to bottom
            col, row = k % COLS, k // COLS
            x = (ROWS - 1 - row) * CELL
            y = col * CELL
            cx, cy = (bb.min.x + bb.max.x) * 0.5 * s, (bb.min.y + bb.max.y) * 0.5 * s
            z = -bb.min.z * s
            a = ACT.spawn_actor_from_object(mesh, unreal.Vector(x - cx, y - cy, z), unreal.Rotator(0, 0, 0))
            a.set_actor_scale3d(unreal.Vector(s, s, s))
            self.actors.append(a)
            tris = 0
            try:
                tris = mesh.get_num_triangles(0)
            except Exception:  # noqa
                pass
            cells.append(dict(mesh=p.rsplit("/", 1)[-1], size_m=[round(ext.x / 100, 2), round(ext.y / 100, 2), round(ext.z / 100, 2)],
                              tris=tris, nanite=bool(mesh.get_editor_property("nanite_settings").get_editor_property("enabled"))))
        return cells

    def tick(self, dt):
        if self.busy or time.monotonic() < self.wait:
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
        if self.pending:
            fn, t0 = self.pending
            if os.path.exists(fn) and os.path.getsize(fn) > 0:
                log(f"shot {os.path.basename(fn)}")
                self.pending = None
                self.i += 1
                self.wait = time.monotonic() + 0.5
            elif time.monotonic() - t0 > 90:
                unreal.log_warning(f"[BAM] no image for {fn}")
                self.pending = None
                self.i += 1
            return
        if self.i >= len(self.pages):
            unreal.unregister_slate_post_tick_callback(self.handle)
            json.dump(self.index, open(os.path.join(OUT, "review.json"), "w"), indent=1)
            log("BAM REVIEW DONE")
            if os.environ.get("BAM_QUIT") == "1":
                unreal.SystemLibrary.quit_editor()
            return
        g, n, paths = self.pages[self.i]
        key = f"Review_{g}_{n:02d}"
        if key not in self.index:
            self.index[key] = self.lay_out(paths)
            self.wait = time.monotonic() + 12.0     # stream textures and compile shaders
            return
        fn = os.path.join(OUT, key + ".png")
        if os.path.exists(fn):
            os.remove(fn)
        self.pending = (fn, time.monotonic())
        unreal.AutomationLibrary.take_high_res_screenshot(self.res[0], self.res[1], fn, self.cam, False, False,
                                                         unreal.ComparisonTolerance.LOW)


try:
    _items = meshes()
    if not _items:
        raise RuntimeError("nothing imported under /BiomeAutoMaterials/Assets or /Marine")
    _shooter = Shooter(build_level(), _items)
except Exception:  # noqa
    import traceback
    unreal.log_error("[BAM] " + traceback.format_exc())
    if os.environ.get("BAM_QUIT") == "1":
        unreal.SystemLibrary.quit_editor()
