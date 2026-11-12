"""Write Docs/Biomes.md, Docs/Parameters.md and the gallery images from the data and the showcase shots.

    python Tools/make_docs.py

Shots: Docs/Images/raw/<Biome>_<Camera>.png (from build_showcase.py) -> Docs/Images/<Biome>_<Camera>.jpg, plus
Docs/Images/gallery.jpg (one tile per biome) for the README.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import biomes  # noqa: E402

DESC = {
    "Sea Level": "World Z (metres) of the water line. Shore, wet band and puddles are measured from it.",
    "Landscape Quad Size": "Metres per landscape quad (landscape X/Y scale / 100). Keeps texture sizes real-world.",
    "Use World Coordinates": "Static switch: use world X/Y instead of landscape coordinates (for meshes, not landscapes).",
    "GroundB Amount": "Share of flat ground covered by the second ground layer (0..1).",
    "GroundB Scale": "Size of the GroundB patches (1 = ~20 m patches).",
    "GroundB Altitude Bias": "GroundB coverage change per metre of altitude (e.g. 0.004: more dry grass higher up).",
    "GroundB Slope Bias": "GroundB coverage change per degree of slope.",
    "Soil Angle": "Slope (deg) from which bare soil takes over from the ground cover.",
    "Soil Fade": "Width (deg) of that transition.",
    "Soil Patches": "Bare-soil patches on flat ground (0..1).",
    "Shore Height": "Metres above Sea Level the shore layer (beach) reaches.",
    "Shore Fade": "Metres over which the beach fades into the land above.",
    "Shore Noise": "Metres of raggedness added to the beach line.",
    "Shore Max Angle": "Steeper than this (deg) the shore layer is not used (cliffs stay rock).",
    "Scree Amount": "Strength of loose rubble on talus slopes (0..1).",
    "Scree Angle": "Slope (deg) where scree collects: the angle of repose of loose rock is 30-37 deg.",
    "Scree Width": "Range (deg) around Scree Angle that holds scree.",
    "Rock Angle": "Slope (deg) from which bare rock shows.",
    "Rock Fade": "Width (deg) of the rock transition.",
    "Rock Noise": "Degrees of noise on the rock line so it follows no contour.",
    "RockB Amount": "Share of the second rock (patches, or strata bands with Strata Amount).",
    "Strata Amount": "0 = RockB in noise patches, 1 = RockB in horizontal sedimentary bands.",
    "Strata Scale": "Thickness (m) of a stratum.",
    "Strata Warp": "Metres the bands wander up and down (folding).",
    "Strata Tint Amount": "Colour difference between bands (0..1), towards Strata Tint.",
    "Strata Tint": "Colour the strata bands are tinted towards.",
    "Rock Moss": "Moss / lichen on upward-facing rock (0..1).",
    "Moss Color": "Linear albedo of that moss.",
    "Snow Amount": "Master switch for snow (0 = no snow).",
    "Snow Line": "Metres above Sea Level where snow starts. Real snowlines are 0-5000 m; set it to suit your world.",
    "Snow Fade": "Metres over which snow thickens above the snow line.",
    "Snow Line Noise": "Metres of raggedness on the snow line.",
    "Snow Max Angle": "Snow does not stay on surfaces steeper than this (deg), judged on the detailed normal so ledges keep it.",
    "Snow Cover": "Snow below the snow line (0..1): winter cover, patches in hollows.",
    "Snow Smoothing": "How much a snow blanket smooths the relief beneath it.",
    "Wet Band": "Metres above Sea Level that are wet (tide zone, splash).",
    "Wetness": "Rain wetness everywhere (0..1): porous layers darken and turn glossy.",
    "Puddles": "Standing water in flat hollows when wet (0..1).",
    "Height Blend": "How much texture heights decide the transitions (0 = plain crossfade).",
    "Blend Softness": "Width of a height transition (small = crisp stones in sand).",
    "Hex Tiling": "1 = hex-tiling anti-repetition on ground layers (3 taps), 0 = plain tiling. Low material quality forces 0.",
    "Hex Contrast": "How much the texture's height steers the hex-tile seams.",
    "Hex Rotation": "Random rotation of the hex tiles (0 = none, 1 = full).",
    "Far Scale": "Far textures are 1/Far Scale larger (breaks repetition seen from afar).",
    "Fade Start": "Distance (cm) where the far textures start.",
    "Fade Length": "Distance (cm) over which near fades into far.",
    "Macro Scale": "Size (m) of the large-scale brightness variation.",
    "Macro Strength": "Strength of that brightness variation.",
    "Macro Saturation": "Strength of the large-scale saturation variation.",
    "Debug View": "1 = paint layer coverage: green ground, yellow GroundB, brown soil, beige shore, grey scree, "
                  "slate/red rock A/B, white snow, blue puddles.",
}
LAYER_DESC = {
    "Color+Height": "Packed texture: base colour (sRGB) + height in alpha.",
    "Normal+Rough+AO": "Packed texture: normal X/Y (DirectX), roughness, ambient occlusion.",
    "Tile": "Metres one repeat of the texture covers (real-world size of the photographed patch).",
    "Aspect": "Height/width of the photo.",
    "Brightness": "Albedo multiplier; the build calibrates it to the set's real-world albedo.",
    "Saturation": "Colour saturation multiplier.",
    "Tint": "Colour multiplier.",
    "Normal": "Normal-map strength.",
    "Roughness": "Roughness multiplier.",
    "Height Bias": "Raises (+) or lowers (-) the layer in height blends.",
    "Porosity": "How much the layer darkens when wet (soil 1, rock ~0.35, snow 0).",
}


def params_md():
    L = ["# Parameters", "", "All lengths are metres and all angles degrees unless noted. Defaults are the master's; each biome "
         "instance overrides some (see `Tools/biomes.py`).", "", "## Global", "", "| Parameter | Default | Meaning |", "|---|---|---|"]
    rows = list(biomes.PARAM_DEFAULTS.items()) + [(k, v) for k, v in biomes.VECTOR_DEFAULTS.items()] + [("Use World Coordinates", False)]
    for k, v in sorted(rows, key=lambda kv: biomes.group_of(kv[0])):
        L.append(f"| {k} | {v} | {DESC.get(k, '')} |")
    L += ["", "## Per layer", "", "Every slot (`" + "`, `".join(biomes.SLOTS) + "`) has these, named `<Slot> <Parameter>`.", "",
          "| Parameter | Meaning |", "|---|---|"]
    for k, v in LAYER_DESC.items():
        L.append(f"| {k} | {v} |")
    L += ["", "## Layer stack", "", "Bottom to top: **Ground** (flat cover) -> **GroundB** (patches) -> **Soil** (banks, patches) -> "
          "**Shore** (near Sea Level) -> **Scree** (talus slopes) -> **Rock** / **RockB** (steep, triplanar) -> **Snow** -> water "
          "(wet band, rain, puddles). Each layer is blended over the result with a height-aware blend, and a layer that is "
          "completely hidden by one above is never sampled."]
    return "\n".join(L) + "\n"


def biomes_md(stats, images):
    L = ["# Biomes", "", f"{len(biomes.BIOMES)} presets, all on the same master material (`M_BiomeAuto`), so switching biome is "
         "just switching the landscape material instance (no shader recompile).", ""]
    for name, b in biomes.BIOMES.items():
        L += [f"## {name}", "", b["desc"], ""]
        imgs = [i for i in images if i.startswith(name + "_")]
        if imgs:
            L.append(" ".join(f"<img src=\"Images/{i}\" width=\"32%\">" for i in imgs[:3]))
            L.append("")
        L += ["| Slot | Texture set | Source |", "|---|---|---|"]
        for slot in biomes.SLOTS:
            k = b["layers"].get(slot)
            if not k:
                continue
            s = stats.get(k, {})
            L.append(f"| {slot} | `{k}` | [{s.get('name', biomes.TEXTURES[k][0])}]({s.get('url', '')}) |")
        if b.get("params"):
            L += ["", "Overrides: " + ", ".join(f"`{k}` = {v}" for k, v in b["params"].items())]
        L.append("")
    return "\n".join(L) + "\n"


def convert_images():
    raw = os.path.join(ROOT, "Docs", "Images", "raw")
    out = os.path.join(ROOT, "Docs", "Images")
    done = []
    if not os.path.isdir(raw):
        return done
    from PIL import Image
    order = ["Overview", "Mountain", "Mesa", "Coast", "Ground"]
    files = [f for f in os.listdir(raw) if f.lower().endswith(".png") and ".blank." not in f.lower() and os.path.isfile(os.path.join(raw, f))]
    files.sort(key=lambda f: (f.split("_")[0], order.index(f.rsplit("_", 1)[1][:-4]) if "_" in f and f.rsplit("_", 1)[1][:-4] in order else 9))
    for f in files:
        im = Image.open(os.path.join(raw, f)).convert("RGB")
        if im.width > 1600:
            im = im.resize((1600, int(im.height * 1600 / im.width)), Image.LANCZOS)
        name = f[:-4] + ".jpg"
        im.save(os.path.join(out, name), quality=86, optimize=True)
        done.append(name)
    # gallery: Overview of every biome, 4 per row
    tiles = [(b, os.path.join(out, f"{b}_Overview.jpg")) for b in biomes.BIOMES]
    tiles = [(b, p) for b, p in tiles if os.path.exists(p)]
    if tiles:
        from PIL import ImageDraw
        tw, th, cols = 480, 270, 4
        rows = (len(tiles) + cols - 1) // cols
        g = Image.new("RGB", (tw * cols, th * rows), (20, 20, 20))
        for i, (b, p) in enumerate(tiles):
            im = Image.open(p).resize((tw, th), Image.LANCZOS)
            d = ImageDraw.Draw(im)
            d.rectangle((0, th - 26, tw, th), fill=(0, 0, 0))
            d.text((8, th - 21), b, fill=(240, 240, 240))
            g.paste(im, ((i % cols) * tw, (i // cols) * th))
        g.save(os.path.join(out, "gallery.jpg"), quality=85, optimize=True)
    # the sky and the sea: a 2 x 2 hero image for the README
    env = [os.path.join(out, f"{n}.jpg") for n in ("Sky_Sunset", "Ocean_Gale", "Sky_Night", "Sky_Storm")]
    if all(os.path.exists(p) for p in env):
        tw, th = 800, 450
        g = Image.new("RGB", (tw * 2, th * 2))
        for i, p in enumerate(env):
            g.paste(Image.open(p).resize((tw, th), Image.LANCZOS), ((i % 2) * tw, (i // 2) * th))
        g.save(os.path.join(out, "environment.jpg"), quality=85, optimize=True)
    return done


def main():
    stats_p = os.path.join(ROOT, "Build", "textures.json")
    stats = json.load(open(stats_p)) if os.path.exists(stats_p) else {}
    images = convert_images()
    os.makedirs(os.path.join(ROOT, "Docs"), exist_ok=True)
    open(os.path.join(ROOT, "Docs", "Parameters.md"), "w", encoding="utf8").write(params_md())
    open(os.path.join(ROOT, "Docs", "Biomes.md"), "w", encoding="utf8").write(biomes_md(stats, images))
    print(f"docs written, {len(images)} images")


if __name__ == "__main__":
    main()
