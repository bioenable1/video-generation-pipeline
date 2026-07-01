#!/usr/bin/env python3
"""Approve shot list (sets approved: true with timestamp)."""

from __future__ import annotations

import argparse
import sys

from utils import load_shot_list, project_dir, save_json, utc_now_iso


def main() -> None:
    parser = argparse.ArgumentParser(description="Approve shot list for production")
    parser.add_argument("--project", required=True)
    args = parser.parse_args()

    path = project_dir(args.project) / "plan" / "shot-list.json"
    data = load_shot_list(args.project)

    if not data.get("scenes"):
        print("ERROR: shot list has no scenes", file=sys.stderr)
        sys.exit(1)

    data["approved"] = True
    data["approved_at"] = utc_now_iso()
    save_json(path, data)
    print(f"Approved: {path}")
    print("Asset generation may proceed.")


if __name__ == "__main__":
    main()
