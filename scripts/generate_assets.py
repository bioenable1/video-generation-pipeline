#!/usr/bin/env python3
"""Download stock, extract sources, and prepare asset manifest for any project."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils import ROOT, load_shot_list, project_dir, save_json, utc_now_iso


def collect_ai_prompts(slug: str) -> dict[str, dict]:
    """Scenes needing AI-generated images — agent uses these prompts."""
    prompts = {}
    for scene in load_shot_list(slug)["scenes"]:
        visual = scene.get("visual", {})
        if visual.get("type") not in ("ai_image", "ai_video"):
            continue
        prompt = visual.get("prompt") or visual.get("query") or scene.get("on_screen_text", "")
        if not prompt:
            continue
        prompts[scene["id"]] = {
            "type": visual["type"],
            "prompt": prompt,
            "output": f"assets/images/{scene['id']}.png",
            "status": "pending",
            "note": "Generate via Cursor imagegen / ai-studio-image skill, then re-run generate-assets",
        }
    return prompts


def check_scene_assets(slug: str) -> dict[str, dict]:
    base = project_dir(slug)
    status = {}
    for scene in load_shot_list(slug)["scenes"]:
        sid = scene["id"]
        visual = scene.get("visual", {})
        vtype = visual.get("type", "stock_video")
        entry = {"type": vtype, "ready": False, "path": None}

        stock = base / "assets" / "stock" / f"{sid}.mp4"
        if stock.exists() and stock.stat().st_size > 50000:
            entry["ready"] = True
            entry["path"] = f"assets/stock/{sid}.mp4"

        src = visual.get("source_path", "")
        if src:
            src_path = base / src
            entry["source_path"] = src
            entry["source_exists"] = src_path.exists()
            if vtype in ("product_image", "screen_recording") and src_path.exists():
                entry["ready"] = True
                entry["path"] = src

        ai_img = base / "assets" / "images" / f"{sid}.png"
        if vtype == "ai_image" and ai_img.exists():
            entry["ready"] = True
            entry["path"] = f"assets/images/{sid}.png"

        status[sid] = entry
    return status


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch stock and prepare assets for render")
    parser.add_argument("--project", required=True)
    parser.add_argument("--skip-extract", action="store_true")
    parser.add_argument("--skip-stock", action="store_true")
    args = parser.parse_args()

    slug = args.project
    scripts = ROOT / "scripts"
    py = sys.executable

    print(f"=== Generate assets: {slug} ===")

    if not args.skip_extract:
        print("1. Extract source materials (PDF, website URLs from brief)")
        subprocess.run([py, str(scripts / "extract_assets.py"), "--project", slug], check=False)

    if not args.skip_stock:
        print("2. Fetch stock B-roll + background music")
        subprocess.run([py, str(scripts / "fetch_free_stock.py"), "--project", slug], check=False)

    print("3. AI asset prompts + readiness check")
    ai_prompts = collect_ai_prompts(slug)
    scene_status = check_scene_assets(slug)
    pending_ai = [sid for sid, p in ai_prompts.items() if p["status"] == "pending"
                  and not (project_dir(slug) / p["output"]).exists()]

    prompts_path = project_dir(slug) / "assets" / "ai-prompts.json"
    if ai_prompts:
        save_json(prompts_path, {"updated_at": utc_now_iso(), "prompts": ai_prompts})
        print(f"   AI prompts: {prompts_path}")
        if pending_ai:
            print(f"   Pending AI generation: {', '.join(pending_ai)}")
            print("   → Use Cursor imagegen to create assets/images/<scene>.png")

    ready = sum(1 for s in scene_status.values() if s["ready"])
    total = len(scene_status)
    manifest = {
        "updated_at": utc_now_iso(),
        "scenes": scene_status,
        "ai_prompts_file": str(prompts_path.relative_to(project_dir(slug))) if ai_prompts else None,
        "ready_count": ready,
        "total_scenes": total,
    }
    save_json(project_dir(slug) / "assets" / "manifest.json", manifest)
    print(f"\nAsset readiness: {ready}/{total} scenes")
    if pending_ai:
        print("Some AI images still pending — render may fall back to stock for those scenes.")


if __name__ == "__main__":
    main()
