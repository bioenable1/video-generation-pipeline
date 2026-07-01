#!/usr/bin/env python3
"""Generate script.md and vo-segments.json from approved shot list."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils import load_shot_list, project_dir, save_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate script from shot list")
    parser.add_argument("--project", required=True)
    args = parser.parse_args()

    data = load_shot_list(args.project)
    if not data.get("approved"):
        print("ERROR: shot list not approved", file=sys.stderr)
        sys.exit(1)

    product = data.get("product", args.project)
    lines = [
        f"# {data.get('title', product)} — Narration Script",
        "",
        f"**Product:** {product}  ",
        f"**Target duration:** {data.get('duration_target_sec', 90)}s  ",
        f"**Pacing:** ~140 WPM",
        "",
        "## Pronunciation notes",
        "- Iriuniverse: eye-ri-YOU-nih-verse",
        "- BioEnable: BY-oh-en-AY-bul",
        "",
        "---",
        "",
    ]

    segments = []
    for scene in data.get("scenes", []):
        sid = scene["id"]
        narration = scene.get("narration", "")
        lines.extend([f"## {sid}", "", narration, ""])
        segments.append(
            {
                "scene_id": sid,
                "text": narration,
                "target_duration_sec": scene.get("duration_sec", 8),
            }
        )

    base = project_dir(args.project)
    script_path = base / "script.md"
    script_path.write_text("\n".join(lines), encoding="utf-8")
    save_json(base / "vo-segments.json", {"segments": segments})

    print(f"Wrote {script_path}")
    print(f"Wrote {base / 'vo-segments.json'}")


if __name__ == "__main__":
    main()
