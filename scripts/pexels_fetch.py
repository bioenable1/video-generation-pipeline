#!/usr/bin/env python3
"""Fetch stock videos from Pexels API and score candidates for scenes."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

import requests

from utils import ensure_project_dirs, load_env, load_shot_list, project_dir, save_json, utc_now_iso


def score_relevance(query: str, video: dict) -> float:
    """Simple keyword overlap score between query and Pexels video metadata."""
    query_words = set(re.findall(r"\w+", query.lower()))
    if not query_words:
        return 0.5

    text_parts = [
        str(video.get("url", "")),
        str(video.get("id", "")),
    ]
    for user in video.get("video_files", []):
        text_parts.append(str(user.get("quality", "")))

    blob = " ".join(text_parts).lower()
    matches = sum(1 for w in query_words if w in blob)
    base = matches / len(query_words)

    # Prefer HD landscape
    width = video.get("width", 0)
    height = video.get("height", 0)
    if width >= 1920:
        base += 0.1
    if height and width / height >= 1.5:
        base += 0.05

    return min(base, 1.0)


def pick_best_file(video: dict) -> dict | None:
    files = video.get("video_files", [])
    if not files:
        return None
    hd = [f for f in files if f.get("quality") == "hd" and f.get("file_type") == "video/mp4"]
    if hd:
        return max(hd, key=lambda f: f.get("width", 0))
    mp4 = [f for f in files if f.get("file_type") == "video/mp4"]
    return max(mp4, key=lambda f: f.get("width", 0)) if mp4 else files[0]


def search_videos(api_key: str, query: str, per_page: int = 5) -> list[dict]:
    resp = requests.get(
        "https://api.pexels.com/v1/videos/search",
        headers={"Authorization": api_key},
        params={"query": query, "per_page": per_page, "orientation": "landscape"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("videos", [])


def download_file(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)


def update_manifest(slug: str, scene_id: str, entry: dict) -> None:
    manifest_path = project_dir(slug) / "assets" / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        manifest = {"updated_at": utc_now_iso(), "scenes": {}}

    manifest["scenes"][scene_id] = entry
    manifest["updated_at"] = utc_now_iso()
    save_json(manifest_path, manifest)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch Pexels stock video for a scene")
    parser.add_argument("--project", required=True)
    parser.add_argument("--scene", help="Scene id (e.g. s01)")
    parser.add_argument("--query", help="Search query (defaults to scene visual.query)")
    parser.add_argument("--all", action="store_true", help="Fetch for all stock_video scenes")
    args = parser.parse_args()

    load_env()
    api_key = os.environ.get("PEXELS_API_KEY", "")
    if not api_key:
        print("ERROR: PEXELS_API_KEY not set in .env", file=sys.stderr)
        sys.exit(1)

    ensure_project_dirs(args.project)
    shot_list = load_shot_list(args.project)

    if not shot_list.get("approved"):
        print("ERROR: shot list not approved. Run approve_plan.py first.", file=sys.stderr)
        sys.exit(1)

    scenes_to_process = []
    for scene in shot_list.get("scenes", []):
        if scene.get("visual", {}).get("type") != "stock_video":
            continue
        if args.all or scene.get("id") == args.scene:
            scenes_to_process.append(scene)

    if not scenes_to_process:
        print("No matching stock_video scenes found.")
        sys.exit(0)

    for scene in scenes_to_process:
        scene_id = scene["id"]
        query = args.query or scene.get("visual", {}).get("query", "")
        if not query:
            print(f"SKIP {scene_id}: no query")
            continue

        print(f"Searching Pexels: {query!r} for {scene_id}")
        videos = search_videos(api_key, query)
        if not videos:
            print(f"  No results for {scene_id}")
            continue

        scored = [(score_relevance(query, v), v) for v in videos]
        scored.sort(key=lambda x: x[0], reverse=True)

        candidates = []
        best_path = None
        best_score = 0.0
        best_id = None

        stock_dir = project_dir(args.project) / "assets" / "stock"
        for rank, (score, video) in enumerate(scored[:3]):
            vf = pick_best_file(video)
            if not vf:
                continue
            url = vf.get("link")
            if not url:
                continue
            ext = Path(urlparse(url).path).suffix or ".mp4"
            dest = stock_dir / f"{scene_id}_c{rank}{ext}"
            try:
                download_file(url, dest)
                rel = str(dest.relative_to(project_dir(args.project))).replace("\\", "/")
                candidates.append(rel)
                if score > best_score:
                    best_score = score
                    best_path = rel
                    best_id = video.get("id")
            except requests.RequestException as exc:
                print(f"  Download failed: {exc}")

        if best_path:
            final = stock_dir / f"{scene_id}.mp4"
            src = project_dir(args.project) / best_path
            if src.exists():
                final.write_bytes(src.read_bytes())
                rel_final = str(final.relative_to(project_dir(args.project))).replace("\\", "/")
                update_manifest(
                    args.project,
                    scene_id,
                    {
                        "selected": rel_final,
                        "candidates": candidates,
                        "score": round(best_score, 3),
                        "source": "pexels",
                        "pexels_id": best_id,
                        "query": query,
                    },
                )
                print(f"  Selected: {rel_final} (score={best_score:.2f})")
        else:
            print(f"  No downloadable candidates for {scene_id}")


if __name__ == "__main__":
    main()
