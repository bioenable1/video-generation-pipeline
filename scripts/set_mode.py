#!/usr/bin/env python3
"""Switch production mode between free and paid."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils import load_production_config, project_dir, save_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Set production mode: free or paid")
    parser.add_argument("--project", required=True)
    parser.add_argument("--mode", choices=["free", "paid"], required=True)
    args = parser.parse_args()

    path = project_dir(args.project) / "production.json"
    data = load_production_config(args.project) if path.exists() else {"mode": "free", "free": {}, "paid": {}}
    data["mode"] = args.mode
    save_json(path, data)

    if args.mode == "free":
        print(f"Mode: FREE — edge-tts + FFmpeg (no API keys required)")
        print(f"  python run.py render --project {args.project}")
    else:
        print(f"Mode: PAID — ElevenLabs + VEED + fal.ai")
        print(f"  Set API keys in .env, then:")
        print(f"  python run.py voiceover --project {args.project}")
        print(f"  python run.py veed assemble --project {args.project}")


if __name__ == "__main__":
    main()
