"""Zip the built plugin for a GitHub release.

    python Tools/package_release.py [--engine 5.8]

Writes seven release assets (GitHub allows 2 GB per file; keep the repository itself to the sources):
  Release/BiomeEnvironmentKit-<version>-UE<engine>.zip          the plugin: .uplugin, Source/, prebuilt Win64 Binaries
                                                                (so Blueprint-only projects work), Content/ without
                                                                the island assets or large textures, Docs/, Tools/,
                                                                Showcase/, README, LICENSE, CREDITS
  Release/BiomeEnvironmentKit-IslandAssets-01-Buildings-Docks-Props-<version>-UE<engine>.zip
  Release/BiomeEnvironmentKit-IslandAssets-02-Nature-<version>-UE<engine>.zip
  Release/BiomeEnvironmentKit-IslandAssets-03-Town-<version>-UE<engine>.zip
                                                                Content/Assets split below GitHub's 2 GB per-file
                                                                limit; unzip all three over the plugin
  Release/BiomeEnvironmentKit-Textures-01/02/03-<version>-UE<engine>.zip
                                                                Content/Textures split into three installable bundles
Raw downloads (.cache/), packed sources (Build/), debug symbols and the full-size review shots stay out.
"""
import argparse
import json
import os
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {".cache", "Build", "Release", ".git", "__pycache__", "raw", "Intermediate", "Saved"}
SKIP_EXT = {".pyc", ".pdb", ".exp", ".lib"}
ASSET_BUNDLES = {
    "01-Buildings-Docks-Props": {"Buildings", "Docks", "Props"},
    "02-Nature": {"Nature"},
    "03-Town": {"Town"},
}
TEXTURE_BUNDLES = ("01", "02", "03")
MAX_RELEASE_BYTES = 2_000_000_000


def files(only_assets=False, asset_categories=None, texture_categories=None):
    for base, dirs, names in os.walk(ROOT):
        rel_base = os.path.relpath(base, ROOT).replace("\\", "/")
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        in_assets = rel_base == "Content/Assets" or rel_base.startswith("Content/Assets/")
        in_textures = rel_base == "Content/Textures" or rel_base.startswith("Content/Textures/")
        if only_assets and not in_assets:
            continue
        if texture_categories is not None and not in_textures:
            continue
        if not only_assets and in_assets:
            continue
        if not only_assets and texture_categories is None and in_textures:
            continue
        if not only_assets and rel_base == "Content":
            dirs[:] = [d for d in dirs if d != "Assets"]
        if only_assets and rel_base == "Content/Assets" and asset_categories:
            dirs[:] = [d for d in dirs if d in asset_categories]
        if texture_categories is not None and rel_base == "Content/Textures":
            dirs[:] = [d for d in dirs if d in texture_categories]
        for f in names:
            if f == "BiomeAutoMaterials.uplugin" or f.startswith("dev_") or os.path.splitext(f)[1] in SKIP_EXT:
                continue
            yield os.path.join(base, f)


def write(out, paths, meta=None):
    n = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        if meta:
            z.writestr("BiomeAutoMaterials/BiomeAutoMaterials.uplugin", json.dumps(meta, indent="\t"))
            n += 1
        for p in paths:
            z.write(p, os.path.join("BiomeAutoMaterials", os.path.relpath(p, ROOT)))
            n += 1
    size_bytes = os.path.getsize(out)
    print(f"{out}: {n} files, {size_bytes / 1e6:.0f} MB")
    if size_bytes >= MAX_RELEASE_BYTES:
        raise SystemExit(f"{out} is {size_bytes / 1e9:.2f} GB; split the bundle below GitHub's 2 GB per-file limit")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", default="5.8")
    a = ap.parse_args()
    meta = json.load(open(os.path.join(ROOT, "BiomeAutoMaterials.uplugin")))
    if not os.path.isdir(os.path.join(ROOT, "Content")):
        raise SystemExit("Content/ is missing: run the builders in the editor first (see README)")
    meta = dict(meta, EngineVersion=f"{a.engine}.0")
    os.makedirs(os.path.join(ROOT, "Release"), exist_ok=True)
    v = meta["VersionName"]
    write(os.path.join(ROOT, "Release", f"BiomeEnvironmentKit-{v}-UE{a.engine}.zip"), files(False), meta)
    if os.path.isdir(os.path.join(ROOT, "Content", "Assets")):
        for bundle, categories in ASSET_BUNDLES.items():
            name = f"BiomeEnvironmentKit-IslandAssets-{bundle}-{v}-UE{a.engine}.zip"
            write(os.path.join(ROOT, "Release", name), files(True, categories))
    texture_root = os.path.join(ROOT, "Content", "Textures")
    if os.path.isdir(texture_root):
        folders = []
        for folder in sorted(os.listdir(texture_root)):
            full = os.path.join(texture_root, folder)
            if os.path.isdir(full):
                size = sum(os.path.getsize(os.path.join(base, f))
                           for base, _, names in os.walk(full) for f in names)
                folders.append((folder, size))
        buckets = [[] for _ in TEXTURE_BUNDLES]
        totals = [0] * len(buckets)
        for folder, size in sorted(folders, key=lambda item: item[1], reverse=True):
            idx = min(range(len(buckets)), key=lambda i: totals[i])
            buckets[idx].append(folder)
            totals[idx] += size
        for bundle, categories in zip(TEXTURE_BUNDLES, buckets):
            name = f"BiomeEnvironmentKit-Textures-{bundle}-{v}-UE{a.engine}.zip"
            write(os.path.join(ROOT, "Release", name), files(texture_categories=set(categories)))


if __name__ == "__main__":
    main()
