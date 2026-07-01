#!/usr/bin/env python3
"""CLI entry point — run from repo root: python run.py <script> [args]"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent / "scripts"

USAGE = """Usage: python run.py <command> [args]

Commands:
  new-project       Create a new video project (any type)
  research          YouTube transcript research
  validate          Validate shot-list.json
  plan              Generate content-plan.html
  approve           Approve shot list
  script            Generate script.md + vo-segments.json
  generate-assets   Fetch stock, extract sources, AI prompt manifest
  voiceover         ElevenLabs voiceover (--dry-run supported)
  pexels            Fetch Pexels stock video
  veed              VEED/fal.ai client (assemble, fabric, lipsync, poll)
  qc                FFmpeg QC (concat, check)
  thumbnail         Generate thumbnail
  render            Free/local full render (edge-tts + FFmpeg)
  set-mode          Switch free/paid production mode

Example:
  python run.py new-project --subject "My App" --type explainer --slug my-app-explainer
  python run.py generate-assets --project my-app-explainer
  python run.py render --project my-app-explainer --force
"""

MAP = {
    "new-project": "new_project.py",
    "research": "research.py",
    "validate": "validate_shot_list.py",
    "plan": "plan_generator.py",
    "approve": "approve_plan.py",
    "script": "generate_script.py",
    "voiceover": "generate_voiceover.py",
    "pexels": "pexels_fetch.py",
    "veed": "veed_client.py",
    "qc": "ffmpeg_qc.py",
    "thumbnail": "generate_thumbnail.py",
    "render": "render_free.py",
    "fetch-stock": "fetch_free_stock.py",
    "generate-assets": "generate_assets.py",
    "extract-assets": "extract_assets.py",
    "set-mode": "set_mode.py",
}


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(USAGE)
        sys.exit(0 if len(sys.argv) > 1 else 1)

    cmd = sys.argv[1]
    if cmd not in MAP:
        print(f"Unknown command: {cmd}\n")
        print(USAGE)
        sys.exit(1)

    script = SCRIPTS / MAP[cmd]
    sys.argv = [str(script), *sys.argv[2:]]
    sys.path.insert(0, str(SCRIPTS))
    runpy.run_path(str(script), run_name="__main__")


if __name__ == "__main__":
    main()
