#!/usr/bin/env python3
"""Validate shot-list.json against JSON schema and approval gate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from jsonschema import Draft7Validator

from utils import ROOT, SCHEMA_PATH, load_shot_list, project_dir


def validate_schema(data: dict) -> list[str]:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft7Validator(schema)
    errors = []
    for err in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
        path = ".".join(str(p) for p in err.path) or "(root)"
        errors.append(f"{path}: {err.message}")
    return errors


def validate_business_rules(data: dict) -> list[str]:
    errors = []
    scenes = data.get("scenes", [])
    if not scenes:
        errors.append("scenes: at least one scene required before production")

    total = sum(s.get("duration_sec", 0) for s in scenes)
    target = data.get("duration_target_sec", 0)
    if scenes and abs(total - target) > target * 0.15:
        errors.append(
            f"duration: scene total ({total}s) differs from target ({target}s) by >15%"
        )

    ids = [s.get("id") for s in scenes]
    if len(ids) != len(set(ids)):
        errors.append("scenes: duplicate scene ids")

    for scene in scenes:
        visual = scene.get("visual", {})
        vtype = visual.get("type")
        if vtype in ("stock_video", "stock_photo") and not (
            visual.get("query") or visual.get("catalog_key")
        ):
            errors.append(f"{scene.get('id')}: stock visual requires query or catalog_key")
        if vtype == "ai_image" and not (visual.get("prompt") or visual.get("intent")):
            errors.append(f"{scene.get('id')}: ai_image requires prompt or intent")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate shot list")
    parser.add_argument("--project", required=True)
    parser.add_argument("--require-approval", action="store_true", help="Fail if not approved")
    args = parser.parse_args()

    path = project_dir(args.project) / "plan" / "shot-list.json"
    if not path.exists():
        print(f"ERROR: {path} not found", file=sys.stderr)
        sys.exit(1)

    data = load_shot_list(args.project)
    all_errors = validate_schema(data) + validate_business_rules(data)

    if args.require_approval and not data.get("approved"):
        all_errors.append("approval: shot-list.json must have approved: true")

    if all_errors:
        print("VALIDATION FAILED:")
        for err in all_errors:
            print(f"  - {err}")
        sys.exit(1)

    print(f"OK: {path}")
    print(f"  scenes: {len(data.get('scenes', []))}")
    print(f"  approved: {data.get('approved', False)}")
    if data.get("approved_at"):
        print(f"  approved_at: {data['approved_at']}")


if __name__ == "__main__":
    main()
