#!/usr/bin/env python3
"""Download Pexels CDN stock OR generate Ken Burns clips from product images."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import ROOT, load_env, load_shot_list, project_dir, save_json, utc_now_iso

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# Verified working Pexels CDN URLs (no API key)
PEXELS_VIDEOS = {
    "crowd_people": "https://videos.pexels.com/video-files/3195394/3195394-uhd_2560_1440_25fps.mp4",
    "technology_data": "https://videos.pexels.com/video-files/3129957/3129957-uhd_2560_1440_25fps.mp4",
    "eye_closeup": "https://videos.pexels.com/video-files/3255275/3255275-uhd_2560_1440_25fps.mp4",
    "server_room": "https://videos.pexels.com/video-files/856973/856973-uhd_2560_1440_25fps.mp4",
    "government_building": "https://videos.pexels.com/video-files/3045163/3045163-hd_1920_1080_25fps.mp4",
    "fingerprint_tech": "https://videos.pexels.com/video-files/2098989/2098989-hd_1920_1080_30fps.mp4",
    "business_office": "https://videos.pexels.com/video-files/3129957/3129957-uhd_2560_1440_25fps.mp4",
}

# Product images from BioEnable site/brochure as fallback per scene
IMAGE_FALLBACK = {
    "s01": "assets/images/website/web-04.png",
    "s02": "assets/images/website/web-12.png",
    "s03": "assets/images/brochure/brochure-page1.png",
    "s04": "assets/images/website/web-01.png",
    "s05": "assets/images/brochure/brochure-page3.png",
    "s06": "assets/images/brochure/brochure-page2.png",
    "s07": "assets/images/website/web-02.png",
    "s08": "assets/images/website/web-02.png",
}

SCENE_MAP = {
    "s01": "crowd_people",
    "s02": "government_building",
    "s03": "technology_data",
    "s04": "eye_closeup",
    "s05": "server_room",
    "s06": "fingerprint_tech",
    "s07": "business_office",
    "s08": "technology_data",
}


def download_video(url: str, dest: Path) -> bool:
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
    """Ken Burns motion from product still."""
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


def fetch_pexels_api(query: str, dest: Path) -> bool:
    api_key = os.environ.get("PEXELS_API_KEY", "")
    if not api_key:
        return False
    try:
        resp = requests.get(
            "https://api.pexels.com/v1/videos/search",
            headers={"Authorization": api_key},
            params={"query": query, "per_page": 5, "orientation": "landscape"},
            timeout=30,
        )
        resp.raise_for_status()
        for v in resp.json().get("videos", []):
            files = [f for f in v.get("video_files", []) if "mp4" in f.get("file_type", "")]
            if files and download_video(max(files, key=lambda f: f.get("width", 0))["link"], dest):
                return True
    except Exception as exc:
        print(f"    Pexels API: {exc}")
    return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    args = parser.parse_args()

    load_env()
    base = project_dir(args.project)
    stock_dir = base / "assets" / "stock"
    shot_list = load_shot_list(args.project)
    manifest_scenes = {}

    for scene in shot_list["scenes"]:
        sid = scene["id"]
        dest = stock_dir / f"{sid}.mp4"
        query = scene.get("visual", {}).get("query", "")
        key = SCENE_MAP.get(sid, "technology_data")

        print(f"  {sid}:")
        ok = False
        if query:
            ok = fetch_pexels_api(query, dest)

        if not ok:
            url = PEXELS_VIDEOS.get(key)
            if url:
                print(f"    Pexels CDN ({key})...")
                ok = download_video(url, dest)

        if not ok:
            img_rel = IMAGE_FALLBACK.get(sid, "")
            img = base / img_rel if img_rel else None
            if img and img.exists():
                print(f"    Product image Ken Burns: {img.name}")
                ok = image_to_stock(img, dest)

        if ok:
            manifest_scenes[sid] = {
                "selected": f"assets/stock/{sid}.mp4",
                "source": "pexels_cdn" if key in PEXELS_VIDEOS else "product_image",
            }
        else:
            print(f"    FAILED — no stock for {sid}")

    # Free background music from incompetech or freemusic archive - try pixabay music CDN
    music_dir = base / "assets" / "music"
    music_dir.mkdir(parents=True, exist_ok=True)
    music_path = music_dir / "background.mp3"
    if not music_path.exists():
        # Pixabay free music direct (no key needed for some tracks)
        music_urls = [
            "https://cdn.pixabay.com/download/audio/2022/03/15/audio_8cb7499b14.mp3",
            "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
        ]
        for mu in music_urls:
            if download_video(mu, music_path):
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
