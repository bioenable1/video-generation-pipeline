#!/usr/bin/env python3
"""Download Pexels CDN stock or generate Ken Burns clips from scene-configured sources."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import (
    load_env,
    load_shot_list,
    load_stock_catalog,
    project_dir,
    save_json,
    utc_now_iso,
)

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def download_file(url: str, dest: Path) -> bool:
    try:
        r = requests.get(url, headers=HEADERS, timeout=180, stream=True)
        if r.status_code != 200:
            return False
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as f:
            for chunk in r.iter_content(65536):
                f.write(chunk)
        return dest.stat().st_size > 100000
    except Exception as exc:
        print(f"    download error: {exc}")
        return False


def image_to_stock(image: Path, dest: Path, duration: float = 12.0) -> bool:
    import subprocess

    if not image.exists():
        return False
    frames = int(duration * 30)
    cmd = [
        "ffmpeg", "-y", "-loop", "1", "-i", str(image),
        "-vf",
        (
            "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,"
            f"zoompan=z='min(zoom+0.0012,1.2)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d={frames}:s=1920x1080:fps=30"
        ),
        "-t", str(duration), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", str(dest),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-500:])
        return False
    return dest.stat().st_size > 50000


def fetch_pexels_api(query: str, dest: Path, orientation: str = "landscape") -> bool:
    api_key = os.environ.get("PEXELS_API_KEY", "")
    if not api_key or not query:
        return False
    try:
        resp = requests.get(
            "https://api.pexels.com/v1/videos/search",
            headers={"Authorization": api_key},
            params={"query": query, "per_page": 5, "orientation": orientation},
            timeout=30,
        )
        resp.raise_for_status()
        for v in resp.json().get("videos", []):
            files = [f for f in v.get("video_files", []) if "mp4" in f.get("file_type", "")]
            if files and download_file(
                max(files, key=lambda f: f.get("width", 0))["link"], dest
            ):
                return True
    except Exception as exc:
        print(f"    Pexels API: {exc}")
    return False


def resolve_catalog_key(scene: dict, catalog: dict) -> str:
    visual = scene.get("visual", {})
    key = visual.get("catalog_key", "")
    if key and key in catalog.get("videos", {}):
        return key
    return catalog.get("query_fallback", "technology_data")


def find_fallback_image(base: Path, scene: dict) -> Path | None:
    visual = scene.get("visual", {})
    src = visual.get("source_path", "")
    if src:
        p = base / src
        if p.exists():
            return p
    sid = scene["id"]
    for pattern in (
        base / "assets" / "images" / f"{sid}.png",
        base / "assets" / "images" / "hero.png",
        base / "assets" / "images" / "website" / "web-01.png",
        base / "assets" / "images" / "brochure" / "brochure-page1.png",
    ):
        if pattern.exists():
            return pattern
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    args = parser.parse_args()

    load_env()
    base = project_dir(args.project)
    stock_dir = base / "assets" / "stock"
    shot_list = load_shot_list(args.project)
    catalog = load_stock_catalog()
    videos = catalog.get("videos", {})
    orientation = "portrait" if shot_list.get("aspect_ratio") == "9:16" else "landscape"
    manifest_scenes = {}

    for scene in shot_list["scenes"]:
        sid = scene["id"]
        dest = stock_dir / f"{sid}.mp4"
        query = scene.get("visual", {}).get("query", "")
        key = resolve_catalog_key(scene, catalog)

        print(f"  {sid}:")
        ok = False
        source = None

        if query:
            ok = fetch_pexels_api(query, dest, orientation=orientation)
            if ok:
                source = "pexels_api"

        if not ok:
            url = videos.get(key)
            if url:
                print(f"    Pexels CDN ({key})...")
                ok = download_file(url, dest)
                if ok:
                    source = "pexels_cdn"

        if not ok:
            img = find_fallback_image(base, scene)
            if img:
                print(f"    Image Ken Burns: {img.name}")
                ok = image_to_stock(img, dest)
                if ok:
                    source = "product_image"

        if ok:
            manifest_scenes[sid] = {
                "selected": f"assets/stock/{sid}.mp4",
                "catalog_key": key,
                "source": source,
            }
        else:
            print(f"    FAILED — no stock for {sid}")

    music_dir = base / "assets" / "music"
    music_dir.mkdir(parents=True, exist_ok=True)
    music_path = music_dir / "background.mp3"
    if not music_path.exists():
        music_urls = list(catalog.get("music", {}).values())
        for mu in music_urls:
            if download_file(mu, music_path):
                print("  Background music downloaded")
                break

    manifest_path = base / "assets" / "manifest.json"
    existing = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    if "scenes" not in existing:
        existing["scenes"] = {}
    existing["scenes"].update(manifest_scenes)
    existing["updated_at"] = utc_now_iso()
    existing["stock_fetched"] = True
    save_json(manifest_path, existing)
    print(f"Stock ready: {len(manifest_scenes)}/{len(shot_list['scenes'])} clips")


if __name__ == "__main__":
    main()
