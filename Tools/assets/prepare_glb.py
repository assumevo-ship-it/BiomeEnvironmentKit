"""Shrink the island kit's .glb files for release: downscale and re-encode their embedded textures (plain Python:
Pillow + numpy). Geometry is copied untouched (Nanite handles the density).

    python Tools/assets/prepare_glb.py [--kit <dir with kit_manifest.json>] [--scale 1.0]

Reads the kept assets from Tools/assets/catalog.py (the licence audit), writes Build/Assets/<Category>/<Name>.glb and
Build/Assets/prepared.json (sizes before/after). Texture size limit per asset, by its real size:
    over 8 m (buildings, castle, cliffs, big trees)  2048 px
    0.6 - 8 m                                        1024 px
    under 0.6 m (small props)                        512 px
"""
import argparse
import io
import json
import os
import struct
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import catalog  # noqa: E402

DEFAULT_KIT = os.path.normpath(os.path.join(ROOT, "..", "..", "WorldData", "PirateKit"))


def read_glb(path):
    data = open(path, "rb").read()
    if data[:4] != b"glTF":
        raise ValueError(f"{path}: not a binary glTF")
    length = struct.unpack("<I", data[8:12])[0]
    pos, js, binary = 12, None, b""
    while pos < length:
        clen, ctype = struct.unpack("<II", data[pos:pos + 8])
        chunk = data[pos + 8:pos + 8 + clen]
        if ctype == 0x4E4F534A:
            js = json.loads(chunk)
        elif ctype == 0x004E4942:
            binary = chunk
        pos += 8 + clen
    return js, binary


def write_glb(path, js, binary):
    jb = json.dumps(js, separators=(",", ":")).encode("utf8")
    jb += b" " * ((4 - len(jb) % 4) % 4)
    binary += b"\0" * ((4 - len(binary) % 4) % 4)
    total = 12 + 8 + len(jb) + 8 + len(binary)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, total))
        f.write(struct.pack("<II", len(jb), 0x4E4F534A))
        f.write(jb)
        f.write(struct.pack("<II", len(binary), 0x004E4942))
        f.write(binary)


def limit_for(entry, scale):
    size = max(entry.get("size_cm", [100]))
    px = 2048 if size > 800 else (1024 if size > 60 else 512)
    return max(256, int(px * scale))


def normal_like(name):
    n = (name or "").lower()
    return "nor" in n or "normal" in n


def shrink_image(raw, mime, limit, name):
    im = Image.open(io.BytesIO(raw))
    im.load()
    has_alpha = im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info)
    if has_alpha:
        alpha = im.convert("RGBA").getchannel("A")
        has_alpha = alpha.getextrema()[0] < 250
    w, h = im.size
    k = min(1.0, limit / max(w, h))
    if k < 1.0:
        im = im.resize((max(1, int(round(w * k))), max(1, int(round(h * k)))), Image.LANCZOS)
    out = io.BytesIO()
    if has_alpha:
        im.convert("RGBA").save(out, "PNG", optimize=True)
        return out.getvalue(), "image/png"
    if k >= 1.0 and mime == "image/jpeg":
        return raw, mime   # already small enough: keep the original bytes (no second JPEG loss)
    im.convert("RGB").save(out, "JPEG", quality=94 if normal_like(name) else 88, subsampling=0 if normal_like(name) else 2)
    return out.getvalue(), "image/jpeg"


def prepare(src, dst, limit):
    js, binary = read_glb(src)
    views = js.get("bufferViews", [])
    image_views = {img["bufferView"]: i for i, img in enumerate(js.get("images", [])) if "bufferView" in img}
    new_bin = bytearray()
    for vi, view in enumerate(views):
        start = view.get("byteOffset", 0)
        blob = binary[start:start + view["byteLength"]]
        if vi in image_views:
            img = js["images"][image_views[vi]]
            blob, mime = shrink_image(blob, img.get("mimeType", "image/png"), limit, img.get("name"))
            img["mimeType"] = mime
        while len(new_bin) % 4:
            new_bin.append(0)
        view["byteOffset"] = len(new_bin)
        view["byteLength"] = len(blob)
        view.pop("byteStride", None) if vi in image_views else None
        new_bin.extend(blob)
    if js.get("buffers"):
        js["buffers"][0]["byteLength"] = len(new_bin)
        js["buffers"] = js["buffers"][:1]
    write_glb(dst, js, bytes(new_bin))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kit", default=DEFAULT_KIT)
    ap.add_argument("--scale", type=float, default=1.0, help="multiply every texture limit (0.5: half size)")
    ap.add_argument("--only", default="", help="comma separated asset names")
    args = ap.parse_args()
    manifest = json.load(open(os.path.join(args.kit, "kit_manifest.json"), encoding="utf8"))
    kept, _ = catalog.audit(manifest)
    only = [x for x in args.only.split(",") if x]
    out_root = os.path.join(ROOT, "Build", "Assets")
    report = {}
    before = after = 0
    for e in kept:
        if only and e["name"] not in only:
            continue
        src = os.path.join(args.kit, *e["file"].split("/"))
        dst = os.path.join(out_root, *e["cat"].replace("\\", "/").split("/"), e["name"] + ".glb")
        limit = limit_for(e, args.scale)
        if not (os.path.exists(dst) and os.path.getmtime(dst) > os.path.getmtime(src)):
            prepare(src, dst, limit)
        b, a = os.path.getsize(src), os.path.getsize(dst)
        before += b
        after += a
        report[e["name"]] = {"cat": e["cat"], "file": os.path.relpath(dst, out_root).replace("\\", "/"), "limit": limit,
                             "mb_before": round(b / 1e6, 2), "mb_after": round(a / 1e6, 2), "tris": e["tris"]}
    json.dump(report, open(os.path.join(out_root, "prepared.json"), "w"), indent=1)
    print(f"{len(report)} assets: {before / 1e6:.0f} MB -> {after / 1e6:.0f} MB")


if __name__ == "__main__":
    main()
