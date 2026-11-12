"""Download NASA's moon and Milky Way maps and pack them for M_BiomeSky (plain Python: numpy + Pillow).

    python Tools/sky/fetch_sky_textures.py

Sources (public domain: NASA imagery is not copyrighted, see https://www.nasa.gov/nasa-brand-center/images-and-media/ ;
credit NASA's Scientific Visualization Studio, and ESA/Gaia/DPAC for the star data):
  CGI Moon Kit colour map, LRO/LROC     https://svs.gsfc.nasa.gov/4720   plate carree, longitude 0 at the centre
  Deep Star Maps 2020 (Milky Way)        https://svs.gsfc.nasa.gov/4851   plate carree in J2000 RA / Dec, half-float EXR
Downloads go to .cache/nasa (git-ignored), outputs to Build/Sky:
  T_MoonColor.png   2048x1024 sRGB albedo, normalised so the highlands average 1
  T_MilkyWay.png    2048x1024 8-bit linear, sqrt-encoded radiance (the shader squares it)
"""
import json
import os
import struct
import sys
import urllib.request
import zlib

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
CACHE = os.path.join(ROOT, ".cache", "nasa")
OUT = os.path.join(ROOT, "Build", "Sky")
SOURCES = {
    "lroc_color_poles_4k.tif": "https://svs.gsfc.nasa.gov/vis/a000000/a004700/a004720/lroc_color_poles_4k.tif",
    "milkyway_2020_4k.exr": "https://svs.gsfc.nasa.gov/vis/a000000/a004800/a004851/milkyway_2020_4k.exr",
}
Image.MAX_IMAGE_PIXELS = None


def fetch(name):
    os.makedirs(CACHE, exist_ok=True)
    dst = os.path.join(CACHE, name)
    if os.path.exists(dst) and os.path.getsize(dst) > 1000000:
        return dst
    print("downloading", SOURCES[name])
    req = urllib.request.Request(SOURCES[name], headers={"User-Agent": "BiomeAutoMaterials-fetch/1.0"})
    with urllib.request.urlopen(req, timeout=300) as r, open(dst + ".part", "wb") as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
    os.replace(dst + ".part", dst)
    return dst


def read_exr_zip(path):
    """A minimal OpenEXR reader for scanline images, ZIP compression, HALF channels (enough for the NASA maps)."""
    data = open(path, "rb").read()
    assert data[:4] == b"\x76\x2f\x31\x01", "not an EXR"
    i, header = 8, {}
    while data[i] != 0:
        name = data[i:data.index(b"\0", i)].decode(); i += len(name) + 1
        kind = data[i:data.index(b"\0", i)].decode(); i += len(kind) + 1
        size = struct.unpack("<i", data[i:i + 4])[0]; i += 4
        header[name] = (kind, data[i:i + size]); i += size
    i += 1
    channels, raw = [], header["channels"][1]
    j = 0
    while raw[j] != 0:
        name = raw[j:raw.index(b"\0", j)].decode(); j += len(name) + 1
        ptype = struct.unpack("<i", raw[j:j + 4])[0]; j += 16
        assert ptype == 1, "only HALF channels"
        channels.append(name)
    assert header["compression"][1] == b"\x03", "only ZIP compression"
    x0, y0, x1, y1 = struct.unpack("<4i", header["dataWindow"][1])
    w, h = x1 - x0 + 1, y1 - y0 + 1
    lines = 16
    chunks = (h + lines - 1) // lines
    offsets = struct.unpack(f"<{chunks}Q", data[i:i + 8 * chunks])
    out = np.zeros((h, len(channels), w), np.float16)
    for off in offsets:
        y, size = struct.unpack("<2i", data[off:off + 8])
        z = np.frombuffer(zlib.decompress(data[off + 8:off + 8 + size]), np.uint8).astype(np.int64)
        # Undo the predictor: each byte was stored as the difference to the one before, plus 128.
        z[1:] -= 128
        t = (np.cumsum(z) & 0xFF).astype(np.uint8)
        half = (len(t) + 1) // 2
        b = np.empty(len(t), np.uint8)
        b[0::2], b[1::2] = t[:half], t[half:]
        n = min(lines, h - (y - y0))
        out[y - y0:y - y0 + n] = np.frombuffer(b.tobytes(), np.float16).reshape(n, len(channels), w)
    img = {c: out[:, k, :].astype(np.float32) for k, c in enumerate(channels)}
    return np.stack([img["R"], img["G"], img["B"]], axis=-1)


def moon():
    im = np.asarray(Image.open(fetch("lroc_color_poles_4k.tif")).convert("RGB").resize((2048, 1024), Image.LANCZOS), np.float32) / 255.0
    # Linear albedo relative to the bright highlands (the 90th percentile), stored back as sRGB.
    lin = np.where(im <= 0.04045, im / 12.92, ((im + 0.055) / 1.055) ** 2.4)
    lin = np.clip(lin / np.percentile(lin.mean(axis=-1), 90), 0, 1)
    srgb = np.where(lin <= 0.0031308, lin * 12.92, 1.055 * lin ** (1 / 2.4) - 0.055)
    os.makedirs(OUT, exist_ok=True)
    dst = os.path.join(OUT, "T_MoonColor.png")
    Image.fromarray((srgb * 255 + 0.5).astype(np.uint8)).save(dst)
    print("moon ->", dst)


def milky_way():
    rgb = np.clip(np.nan_to_num(read_exr_zip(fetch("milkyway_2020_4k.exr"))), 0, None)
    h, w = rgb.shape[:2]
    rgb = rgb.reshape(h // 2, 2, w // 2, 2, 3).mean(axis=(1, 3))
    scale = float(np.percentile(rgb.max(axis=-1), 99.9))
    enc = np.sqrt(np.clip(rgb / scale, 0, 1))
    os.makedirs(OUT, exist_ok=True)
    dst = os.path.join(OUT, "T_MilkyWay.png")
    Image.fromarray((enc * 255 + 0.5).astype(np.uint8)).save(dst)
    json.dump({"scale": scale, "encoding": "sqrt", "mean": float(rgb.mean())}, open(dst.replace(".png", ".json"), "w"), indent=1)
    print("milky way ->", dst)


if __name__ == "__main__":
    which = sys.argv[1:] or ["moon", "milkyway"]
    if "moon" in which:
        moon()
    if "milkyway" in which:
        milky_way()
