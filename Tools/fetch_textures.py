"""Download the CC0 texture sets used by the biomes and pack them for the material.

    python Tools/fetch_textures.py [--res 1k|2k|4k] [--only key,key] [--force]

Needs Python 3.9+ with numpy and Pillow (pip install numpy pillow). Network: api.polyhaven.com, dl.polyhaven.org,
ambientcg.com. Everything downloaded is CC0 (https://polyhaven.com/license, https://docs.ambientcg.com/license/).

Output (git-ignored):
    .cache/<source>/<id>/...                       raw downloads
    Build/Textures/<key>/T_<key>_CH.png            base colour (sRGB) + height in alpha (normalised 0..1)
    Build/Textures/<key>/T_<key>_NRA.png           normal X, normal Y (DirectX), roughness, ambient occlusion
    Build/Textures/T_BiomeNoise.png                tileable noise: R/G two fBm fields, B Worley cells, A fine fBm
    Build/textures.json                            measured stats per set (mean albedo, size in metres, authors)
    CREDITS.md                                     list of every set with its author and link
"""
import argparse
import io
import json
import os
import sys
import time
import urllib.request
import zipfile

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import biomes  # noqa: E402

CACHE = os.path.join(ROOT, ".cache")
OUT = os.path.join(ROOT, "Build", "Textures")
UA = {"User-Agent": "BiomeAutoMaterials-fetch/1.0"}
Image.MAX_IMAGE_PIXELS = None


def http(url, tries=3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300) as r:
                return r.read()
        except Exception as e:  # noqa
            if i == tries - 1:
                raise
            print(f"  retry {url}: {e}")
            time.sleep(3 + 5 * i)


def cached(path, url):
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        data = http(url)
        with open(path + ".part", "wb") as f:
            f.write(data)
        os.replace(path + ".part", path)
    return path


# ---------------------------------------------------------------------------------------------------------------------
# sources
# ---------------------------------------------------------------------------------------------------------------------
def fetch_polyhaven(pid, res):
    d = os.path.join(CACHE, "polyhaven", pid)
    os.makedirs(d, exist_ok=True)
    files_p = os.path.join(d, "files.json")
    info_p = os.path.join(d, "info.json")
    if not os.path.exists(files_p):
        open(files_p, "wb").write(http(f"https://api.polyhaven.com/files/{pid}"))
    if not os.path.exists(info_p):
        open(info_p, "wb").write(http(f"https://api.polyhaven.com/info/{pid}"))
    files = json.load(open(files_p, encoding="utf8"))
    info = json.load(open(info_p, encoding="utf8"))
    maps = {}
    for role, key, fmt in (("color", "Diffuse", "jpg"), ("normal", "nor_dx", "jpg"), ("rough", "Rough", "jpg"),
                           ("ao", "AO", "jpg"), ("height", "Displacement", "png")):
        entry = files.get(key, {}).get(res) or {}
        e = entry.get(fmt) or entry.get("jpg") or entry.get("png")
        if not e:
            continue
        url = e["url"]
        maps[role] = cached(os.path.join(d, f"{pid}_{key}_{res}.{url.rsplit('.', 1)[-1]}"), url)
    dims = info.get("dimensions")  # millimetres [w, h]
    size = (dims[0] / 1000.0, dims[1] / 1000.0) if dims and dims[0] else None
    return maps, {"authors": list((info.get("authors") or {}).keys()), "url": f"https://polyhaven.com/a/{pid}",
                  "size": size, "name": info.get("name", pid), "site": "Poly Haven"}


def fetch_ambientcg(aid, res):
    d = os.path.join(CACHE, "ambientcg", aid)
    os.makedirs(d, exist_ok=True)
    tag = f"{res.upper()}-JPG"
    zp = cached(os.path.join(d, f"{aid}_{tag}.zip"), f"https://ambientcg.com/get?file={aid}_{tag}.zip")
    maps = {}
    with zipfile.ZipFile(zp) as z:
        for n in z.namelist():
            low = n.lower()
            role = None
            if low.endswith("_color.jpg"):
                role = "color"
            elif low.endswith("_normaldx.jpg"):
                role = "normal"
            elif low.endswith("_roughness.jpg"):
                role = "rough"
            elif low.endswith("_ambientocclusion.jpg"):
                role = "ao"
            elif "_displacement." in low and (low.endswith(".jpg") or low.endswith(".png")):
                role = "height"
            if role:
                dest = os.path.join(d, os.path.basename(n))
                if not os.path.exists(dest):
                    with z.open(n) as src, open(dest, "wb") as f:
                        f.write(src.read())
                maps[role] = dest
    return maps, {"authors": ["ambientCG (Lennart Demes)"], "url": f"https://ambientcg.com/view?id={aid}", "size": None,
                  "name": aid, "site": "ambientCG"}


# ---------------------------------------------------------------------------------------------------------------------
# packing
# ---------------------------------------------------------------------------------------------------------------------
def load_gray(path, size):
    im = Image.open(path)
    if im.mode in ("I;16", "I;16B", "I;16L", "I", "F"):
        a = np.asarray(im).astype(np.float32)
        a = a / (65535.0 if a.max() > 255 else 255.0)
    else:
        a = np.asarray(im.convert("L")).astype(np.float32) / 255.0
    if a.shape != (size[1], size[0]):
        a = np.asarray(Image.fromarray(a).resize(size, Image.LANCZOS))
    return a.astype(np.float64)


def load_rgb(path, size):
    im = Image.open(path).convert("RGB")
    if im.size != size:
        im = im.resize(size, Image.LANCZOS)
    return np.asarray(im, dtype=np.float64) / 255.0


def box_blur_wrap(a, r):
    """Separable box blur with wrap-around (keeps the texture tileable)."""
    k = 2 * r + 1
    for axis in (0, 1):
        c = np.cumsum(np.concatenate([a.take(range(-r - 1, 0), axis=axis), a, a.take(range(0, r), axis=axis)], axis=axis), axis=axis)
        n = a.shape[axis]
        a = (c.take(range(k, k + n), axis=axis) - c.take(range(0, n), axis=axis)) / k
    return a


def srgb_to_linear(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def pack(key, maps, res_px, out_dir):
    color = maps.get("color")
    if not color:
        raise RuntimeError("no colour map")
    im = Image.open(color)
    w, h = im.size
    scale = res_px / max(w, h)
    size = (max(4, int(round(w * scale / 4)) * 4), max(4, int(round(h * scale / 4)) * 4))
    rgb = load_rgb(color, size)
    # height: displacement if present, else from luminance; normalised by percentiles so every set blends alike
    if "height" in maps:
        hgt = load_gray(maps["height"], size)
    else:
        hgt = rgb @ np.array([0.2126, 0.7152, 0.0722])
        hgt = hgt - box_blur_wrap(hgt, max(2, size[0] // 64)) + 0.5
    lo, hi = np.percentile(hgt, 1.0), np.percentile(hgt, 99.0)
    hgt = np.clip((hgt - lo) / max(hi - lo, 1e-6), 0.0, 1.0)
    rough = load_gray(maps["rough"], size) if "rough" in maps else np.full(rgb.shape[:2], 0.85)
    if "ao" in maps:
        ao = load_gray(maps["ao"], size)
    else:
        cav = box_blur_wrap(hgt, max(2, size[0] // 128)) - hgt
        ao = np.clip(1.0 - np.maximum(cav, 0.0) * 2.2, 0.35, 1.0)
    if "normal" in maps:
        nrm = load_rgb(maps["normal"], size)[..., :2]
    else:  # from height (DirectX convention: green = -dV)
        s = 2.0
        gx = (np.roll(hgt, -1, 1) - np.roll(hgt, 1, 1)) * s
        gy = (np.roll(hgt, -1, 0) - np.roll(hgt, 1, 0)) * s
        n = np.stack([-gx, gy, np.ones_like(gx)], -1)
        n /= np.linalg.norm(n, axis=-1, keepdims=True)
        nrm = n[..., :2] * 0.5 + 0.5
    os.makedirs(out_dir, exist_ok=True)
    ch = np.dstack([rgb, hgt])
    nra = np.dstack([nrm, rough, ao])
    Image.fromarray(np.clip(ch * 255 + 0.5, 0, 255).astype(np.uint8)).save(os.path.join(out_dir, f"T_{key}_CH.png"), optimize=False)
    Image.fromarray(np.clip(nra * 255 + 0.5, 0, 255).astype(np.uint8)).save(os.path.join(out_dir, f"T_{key}_NRA.png"), optimize=False)
    lin = srgb_to_linear(rgb)
    lum = lin @ np.array([0.2126, 0.7152, 0.0722])
    return {"px": list(size), "mean_albedo": float(lum.mean()), "mean_rgb": [float(x) for x in lin.reshape(-1, 3).mean(0)],
            "mean_rough": float(rough.mean()), "had": sorted(maps.keys())}


# ---------------------------------------------------------------------------------------------------------------------
# tileable noise (own work, CC0)
# ---------------------------------------------------------------------------------------------------------------------
def spectral_noise(n, beta, rng, lowcut=1.0):
    """Perfectly tileable fBm via a power-law spectrum."""
    fx = np.fft.fftfreq(n)[None, :] * n
    fy = np.fft.fftfreq(n)[:, None] * n
    f = np.sqrt(fx * fx + fy * fy)
    f[0, 0] = 1.0
    amp = f ** (-beta / 2.0)
    amp[f < lowcut] = 0.0
    phase = rng.uniform(0, 2 * np.pi, (n, n))
    field = np.real(np.fft.ifft2(amp * np.exp(1j * phase)))
    field -= field.min()
    field /= field.max()
    # equalise to a uniform distribution so thresholds in the material mean coverage fractions
    order = field.ravel().argsort()
    eq = np.empty(n * n)
    eq[order] = np.linspace(0, 1, n * n)
    return eq.reshape(n, n)


def worley(n, cells, rng):
    pts = rng.uniform(0, 1, (cells, cells, 2))
    yy, xx = np.mgrid[0:n, 0:n] / n * cells
    ci, cj = np.floor(yy).astype(int), np.floor(xx).astype(int)
    best = np.full((n, n), 9.0)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            a, b = (ci + dy) % cells, (cj + dx) % cells
            py = ci + dy + pts[a, b, 0]
            px = cj + dx + pts[a, b, 1]
            best = np.minimum(best, np.hypot(yy - py, xx - px))
    best /= best.max()
    return best


def make_noise(path, n=1024, seed=7):
    rng = np.random.default_rng(seed)
    r = spectral_noise(n, 3.2, rng, 1.0)
    g = spectral_noise(n, 3.0, rng, 1.0)
    b = worley(n, 12, rng)
    a = spectral_noise(n, 2.2, rng, 4.0)
    img = np.dstack([r, g, b, a])
    Image.fromarray(np.clip(img * 255 + 0.5, 0, 255).astype(np.uint8)).save(path)


# ---------------------------------------------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--res", default=os.environ.get("BAM_RES", "2k"), choices=["1k", "2k", "4k"])
    ap.add_argument("--only", default="")
    ap.add_argument("--force", action="store_true", help="re-pack even if the packed files exist")
    args = ap.parse_args()
    res_px = {"1k": 1024, "2k": 2048, "4k": 4096}[args.res]
    os.makedirs(OUT, exist_ok=True)
    stats_path = os.path.join(ROOT, "Build", "textures.json")
    stats = json.load(open(stats_path)) if os.path.exists(stats_path) else {}
    keys = biomes.texture_keys()
    if args.only:
        keys = [k for k in keys if k in args.only.split(",")]
    bad = []
    for i, key in enumerate(keys):
        src, target, size_m, porosity = biomes.TEXTURES[key]
        out_dir = os.path.join(OUT, key)
        done = os.path.exists(os.path.join(out_dir, f"T_{key}_NRA.png")) and key in stats and stats[key].get("res") == args.res
        if done and not args.force:
            print(f"[{i + 1}/{len(keys)}] {key}: packed")
            continue
        print(f"[{i + 1}/{len(keys)}] {key} <- {src}")
        try:
            site, sid = src.split(":", 1)
            maps, meta = fetch_polyhaven(sid, args.res) if site == "ph" else fetch_ambientcg(sid, args.res)
            st = pack(key, maps, res_px, out_dir)
            st.update(meta)
            st.update({"source": src, "res": args.res, "target_albedo": target, "porosity": porosity})
            if size_m:
                st["size"] = (size_m, size_m * st["px"][1] / st["px"][0])
            stats[key] = st
            json.dump(stats, open(stats_path, "w"), indent=1)
            print(f"    {st['px']} albedo {st['mean_albedo']:.3f} -> {target}  maps {st['had']}")
        except Exception as e:  # noqa
            print(f"    FAILED {key}: {e}")
            bad.append(key)
    noise = os.path.join(OUT, "T_BiomeNoise.png")
    if not os.path.exists(noise) or args.force:
        print("noise texture")
        make_noise(noise)
    write_credits(stats)
    print(f"done: {len(keys) - len(bad)} sets, failed: {bad}")
    return 1 if bad else 0


OTHER_CREDITS = [
    "", "# Other credits", "",
    "- **Moon map**: NASA's Scientific Visualization Studio, *CGI Moon Kit* (LRO/LROC colour mosaic), "
    "https://svs.gsfc.nasa.gov/4720. Public domain (NASA imagery is not copyrighted).",
    "- **Milky Way map**: NASA/Goddard Space Flight Center Scientific Visualization Studio, *Deep Star Maps 2020*, with data "
    "from ESA/Gaia/DPAC, https://svs.gsfc.nasa.gov/4851. Public domain.",
    "- **Star catalogue**: positions, magnitudes and colour indices of the bright stars are public astronomical data "
    "(Yale Bright Star Catalogue / Hipparcos).",
    "- **Cloud shapes**: Unreal Engine's own volume noise textures, referenced from `/Engine/EngineSky`, not redistributed.",
    "- **Island assets**: the Polyester Pirates kit (generated assets, CC0) and CC0 scans from Poly Haven; see "
    "[Docs/AssetCredits.md](Docs/AssetCredits.md).",
]


def write_credits(stats):
    lines = ["# Texture credits", "",
             "Every texture set used by the biome materials is **CC0 / public domain**. No attribution is required, but these",
             "artists deserve it. `T_BiomeNoise` is generated by `Tools/fetch_textures.py` (CC0).", "",
             "| Set | Source | Author(s) | Used as |", "|---|---|---|---|"]
    use = {}
    for bname, b in biomes.BIOMES.items():
        for slot, k in b["layers"].items():
            use.setdefault(k, []).append(f"{bname}.{slot}")
    for key in sorted(stats):
        s = stats[key]
        lines.append(f"| `{key}` | [{s.get('name', key)}]({s['url']}) ({s.get('site', '')}) | {', '.join(s.get('authors', []))} | "
                     f"{', '.join(use.get(key, []))} |")
    open(os.path.join(ROOT, "CREDITS.md"), "w", encoding="utf8").write("\n".join(lines + OTHER_CREDITS) + "\n")


if __name__ == "__main__":
    sys.exit(main())
