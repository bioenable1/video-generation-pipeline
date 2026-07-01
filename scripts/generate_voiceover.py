#!/usr/bin/env python3
"""Generate per-scene voiceover via ElevenLabs API."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import requests

from utils import ensure_project_dirs, load_env, load_shot_list, project_dir, save_json, utc_now_iso


def synthesize(api_key: str, voice_id: str, text: str, out_path: Path) -> None:
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.0,
            "use_speaker_boost": True,
        },
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=120)
    resp.raise_for_status()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(resp.content)


def build_segments_from_shot_list(shot_list: dict) -> list[dict]:
    return [
        {
            "scene_id": s["id"],
            "text": s.get("narration", ""),
            "target_duration_sec": s.get("duration_sec", 8),
        }
        for s in shot_list.get("scenes", [])
        if s.get("narration")
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate ElevenLabs voiceover")
    parser.add_argument("--project", required=True)
    parser.add_argument("--scene", help="Single scene id")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    load_env()
    api_key = os.environ.get("ELEVENLABS_API_KEY", "")
    voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")

    if not api_key and not args.dry_run:
        print("ERROR: ELEVENLABS_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    ensure_project_dirs(args.project)
    shot_list = load_shot_list(args.project)

    if not shot_list.get("approved"):
        print("ERROR: shot list not approved", file=sys.stderr)
        sys.exit(1)

    segments_path = project_dir(args.project) / "vo-segments.json"
    if segments_path.exists():
        segments_data = json.loads(segments_path.read_text(encoding="utf-8"))
        segments = segments_data.get("segments", [])
    else:
        segments = build_segments_from_shot_list(shot_list)
        save_json(segments_path, {"segments": segments})

    vo_dir = project_dir(args.project) / "assets" / "vo"
    manifest_path = project_dir(args.project) / "assets" / "manifest.json"
    manifest = (
        json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest_path.exists()
        else {"updated_at": utc_now_iso(), "scenes": {}}
    )

    for seg in segments:
        scene_id = seg["scene_id"]
        if args.scene and scene_id != args.scene:
            continue
        text = seg.get("text", "").strip()
        if not text:
            continue

        out = vo_dir / f"{scene_id}.mp3"
        rel = str(out.relative_to(project_dir(args.project))).replace("\\", "/")

        if args.dry_run:
            print(f"DRY RUN: would synthesize {scene_id} -> {rel} ({len(text)} chars)")
            continue

        print(f"Synthesizing {scene_id}...")
        synthesize(api_key, voice_id, text, out)

        entry = manifest["scenes"].get(scene_id, {})
        entry["voiceover"] = rel
        entry["voice_provider"] = "elevenlabs"
        manifest["scenes"][scene_id] = entry

    if not args.dry_run:
        manifest["updated_at"] = utc_now_iso()
        save_json(manifest_path, manifest)
        print(f"Updated {manifest_path}")


if __name__ == "__main__":
    main()
