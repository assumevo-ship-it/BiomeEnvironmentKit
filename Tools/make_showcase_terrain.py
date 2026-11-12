"""Generate the showcase terrain: a 1 km test landscape that exercises every layer of the material.

    python Tools/make_showcase_terrain.py

Writes Showcase/ShowcaseTerrain.r16 (raw 16-bit, 1009 x 1009, 1 m per sample, import with Z scale 100: height in metres =
(value - 32768) / 128), Showcase/ShowcaseTerrain.png (the same as a 16-bit PNG for the Landscape import dialog) and
Showcase/cameras.json (review cameras placed on the generated ground). Features: a sea with a sandy bay and a rocky
headland, rolling meadows, a terraced mesa with vertical walls (strata), talus fans, and a 230 m peak for snow.
"""
import json
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from fetch_textures import spectral_noise  # noqa: E402

N = 1009
OUT = os.path.join(ROOT, "Showcase")


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def main():
    rng = np.random.default_rng(11)
    n2 = 1024
    f1 = spectral_noise(n2, 3.8, rng, 1.0)[:N, :N]
    f2 = spectral_noise(n2, 3.5, rng, 2.0)[:N, :N]
    f3 = spectral_noise(n2, 3.0, rng, 4.0)[:N, :N]
    f4 = spectral_noise(n2, 2.4, rng, 16.0)[:N, :N]
    y, x = np.mgrid[0:N, 0:N] / (N - 1.0)   # x east, y north (row 0 = south edge after the flip below)

    # land rises from the south coast
    coast = 0.16 + 0.05 * np.sin(x * 9.0) + (f1 - 0.5) * 0.06
    bay = np.exp(-((x - 0.42) ** 2) / 0.012) * 0.07             # a sandy bay
    head = np.exp(-((x - 0.82) ** 2) / 0.004) * -0.09           # rocky headland pushing south
    coast = coast + bay + head
    d = y - coast                                                 # >0 inland
    # The sea bed shelves like a real coast: a gentle sandy beach (about 1:12 for the first tens of metres), then the
    # shoreface steepens down to ~45 m at the landscape's edge, so waves shoal and break on the beach instead of
    # flattening over an endless shallow flat.
    off = np.clip(-d / 0.16, 0.0, 1.0)
    seabed = -(1.2 + 46.0 * off ** 0.85) * smoothstep(0.0, 0.004, -d) + (f3 - 0.5) * 2.0 * off
    land = np.where(d > 0, 4.0 + d * 60.0 + (f2 - 0.5) * 10.0 * smoothstep(0.0, 0.15, d), seabed)
    land = np.maximum(land, -50.0)
    # gentle beach in the bay, cliffs on the headland
    bayw = np.exp(-((x - 0.42) ** 2) / 0.008) * (1.0 - smoothstep(0.04, 0.12, d))
    land = np.where(d > 0, land * (1.0 - 0.55 * bayw), land)
    hd = np.exp(-((x - 0.82) ** 2) / 0.006) * smoothstep(-0.01, 0.02, d) * 26.0
    land = land + hd

    # rolling meadows
    land += (f1 - 0.5) * 18.0 * smoothstep(0.05, 0.3, d)
    # mountain with ridges in the north-east
    r = np.hypot((x - 0.72) / 0.22, (y - 0.74) / 0.2)
    ridged = 1.0 - np.abs(f2 * 2 - 1)
    mount = np.exp(-r ** 2 * 1.4) * (128.0 + ridged * 40.0) + np.exp(-r ** 2 * 0.5) * ridged * 22.0
    land = land + mount * smoothstep(0.02, 0.2, d)
    # terraced mesa in the north-west: flat top, stepped walls (one step per ~7 m)
    rm = np.hypot((x - 0.24) / 0.13, (y - 0.68) / 0.11) + (f3 - 0.5) * 0.18
    mesa_h = 62.0 * smoothstep(1.05, 0.78, rm)
    steps = 7.0
    q = mesa_h / steps
    terr = (np.floor(q) + smoothstep(0.78, 1.0, q - np.floor(q))) * steps
    land = np.where(land > 0, np.maximum(land, land * 0.3 + terr), land)   # (land * 0.3 would raise the sea bed)
    # light thermal relaxation: talus slopes below the walls
    h = land.astype(np.float64)
    talus = np.tan(np.radians(34.0))
    for _ in range(25):
        for dy, dx in ((0, 1), (1, 0), (0, -1), (-1, 0)):
            nb = np.roll(np.roll(h, dy, 0), dx, 1)
            diff = h - nb - talus
            move = np.where((diff > 0) & (diff < 6.0), diff * 0.12, 0.0)   # big walls stay walls
            h -= move
            h += np.roll(np.roll(move, -dy, 0), -dx, 1)
    h += (f4 - 0.5) * 0.8
    h = np.clip(h, -50.0, 250.0)

    os.makedirs(OUT, exist_ok=True)
    raw = np.clip(32768 + h * 128.0, 0, 65535).astype("<u2")
    raw.tofile(os.path.join(OUT, "ShowcaseTerrain.r16"))  # row = landscape Y index, column = X index
    Image.fromarray(raw.astype(np.uint16)).save(os.path.join(OUT, "ShowcaseTerrain.png"))

    def H(px, py):
        return float(h[int(np.clip(py, 0, N - 1)), int(np.clip(px, 0, N - 1))])

    # cameras in landscape metres (origin at the landscape centre; X = column, Y = row) -> written in cm for Unreal
    c = (N - 1) / 2.0

    def cam(name, px, py, above, tx, ty, tabove, fov=60.0):
        loc = (px - c, py - c, max(H(px, py), 0.0) + above)     # heights above the ground, or above the sea
        tgt = (tx - c, ty - c, max(H(tx, ty), 0.0) + tabove)
        return {"name": name, "loc": [v * 100 for v in loc], "target": [v * 100 for v in tgt], "fov": fov}

    # (row index = y*1008 from the south edge, column = x*1008)
    cams = [
        cam("Overview", 0.50 * 1008, 0.02 * 1008, 150.0, 0.50 * 1008, 0.62 * 1008, 0.0, 70.0),
        cam("Coast", 0.30 * 1008, 0.17 * 1008, 9.0, 0.62 * 1008, 0.16 * 1008, 0.0, 65.0),
        cam("Mesa", 0.47 * 1008, 0.42 * 1008, 30.0, 0.24 * 1008, 0.68 * 1008, 25.0, 55.0),
        cam("Mountain", 0.47 * 1008, 0.40 * 1008, 25.0, 0.70 * 1008, 0.70 * 1008, 10.0, 55.0),
        cam("Ground", 0.55 * 1008, 0.36 * 1008, 1.7, 0.57 * 1008, 0.40 * 1008, 0.0, 70.0),
    ]
    json.dump({"size": N, "cameras": cams}, open(os.path.join(OUT, "cameras.json"), "w"), indent=1)
    print("terrain", h.min(), h.max(), "cameras", [cc["name"] for cc in cams])
    prev = np.clip((h + 50) / 300.0, 0, 1)
    Image.fromarray((prev[::-1] * 255).astype(np.uint8)).resize((504, 504)).save(os.path.join(OUT, "ShowcaseTerrain_preview.png"))


if __name__ == "__main__":
    main()
