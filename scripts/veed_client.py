#!/usr/bin/env python3
"""
VEED Editing API + fal.ai (Fabric, Lipsync) client.

VEED editing: https://www.veed.io/api
fal.ai endpoints: veed/fabric-1.0, veed/lipsync
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import requests

from utils import ensure_project_dirs, load_env, load_shot_list, project_dir, save_json, utc_now_iso

VEED_API_BASE = "https://api.veed.io"
FAL_QUEUE_BASE = "https://queue.fal.run"


class VeedClient:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
        )

    def submit_render(self, payload: dict) -> dict:
        resp = self.session.post(f"{VEED_API_BASE}/renders", json=payload, timeout=60)
        resp.raise_for_status()
        return resp.json()

    def get_render(self, job_id: str) -> dict:
        resp = self.session.get(f"{VEED_API_BASE}/renders/{job_id}", timeout=30)
        resp.raise_for_status()
        return resp.json()


class FalClient:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Key {api_key}",
                "Content-Type": "application/json",
            }
        )

    def submit(self, endpoint: str, input_data: dict) -> dict:
        resp = self.session.post(
            f"{FAL_QUEUE_BASE}/{endpoint}",
            json={"input": input_data},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()

    def status(self, endpoint: str, request_id: str) -> dict:
        resp = self.session.get(
            f"{FAL_QUEUE_BASE}/{endpoint}/requests/{request_id}/status",
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def result(self, endpoint: str, request_id: str) -> dict:
        resp = self.session.get(
            f"{FAL_QUEUE_BASE}/{endpoint}/requests/{request_id}",
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()


def jobs_path(slug: str) -> Path:
    return project_dir(slug) / "renders" / "jobs.json"


def load_jobs(slug: str) -> dict:
    path = jobs_path(slug)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"jobs": []}


def save_job(slug: str, job: dict) -> None:
    data = load_jobs(slug)
    data["jobs"].append(job)
    data["updated_at"] = utc_now_iso()
    save_json(jobs_path(slug), data)


def poll_fal(
    fal: FalClient,
    endpoint: str,
    request_id: str,
    timeout_sec: int = 600,
    interval_sec: int = 10,
) -> dict:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        status = fal.status(endpoint, request_id)
        state = status.get("status", "")
        print(f"  status: {state}")
        if state == "COMPLETED":
            return fal.result(endpoint, request_id)
        if state in ("FAILED", "CANCELLED"):
            raise RuntimeError(f"fal job failed: {status}")
        time.sleep(interval_sec)
    raise TimeoutError(f"fal job {request_id} timed out")


def cmd_fabric(args: argparse.Namespace) -> None:
    load_env()
    fal_key = os.environ.get("FAL_KEY", "")
    if not fal_key:
        print("ERROR: FAL_KEY not set", file=sys.stderr)
        sys.exit(1)

    fal = FalClient(fal_key)
    input_data = {
        "image_url": args.image,
        "audio_url": args.audio,
    }
    if args.resolution:
        input_data["resolution"] = args.resolution

    print("Submitting Fabric job...")
    submitted = fal.submit("veed/fabric-1.0", input_data)
    request_id = submitted.get("request_id")
    if not request_id:
        print(json.dumps(submitted, indent=2))
        sys.exit(1)

    print(f"request_id: {request_id}")
    if args.project:
        save_job(
            args.project,
            {
                "type": "fabric",
                "request_id": request_id,
                "endpoint": "veed/fabric-1.0",
                "submitted_at": utc_now_iso(),
            },
        )

    if args.wait:
        result = poll_fal(fal, "veed/fabric-1.0", request_id)
        print(json.dumps(result, indent=2))
        video_url = _extract_video_url(result)
        if video_url and args.output:
            _download(video_url, Path(args.output))


def cmd_lipsync(args: argparse.Namespace) -> None:
    load_env()
    fal_key = os.environ.get("FAL_KEY", "")
    if not fal_key:
        print("ERROR: FAL_KEY not set", file=sys.stderr)
        sys.exit(1)

    fal = FalClient(fal_key)
    submitted = fal.submit(
        "veed/lipsync",
        {"video_url": args.video, "audio_url": args.audio},
    )
    request_id = submitted.get("request_id")
    print(f"request_id: {request_id}")

    if args.project:
        save_job(
            args.project,
            {
                "type": "lipsync",
                "request_id": request_id,
                "endpoint": "veed/lipsync",
                "submitted_at": utc_now_iso(),
            },
        )

    if args.wait and request_id:
        result = poll_fal(fal, "veed/lipsync", request_id)
        print(json.dumps(result, indent=2))


def cmd_poll(args: argparse.Namespace) -> None:
    load_env()
    fal_key = os.environ.get("FAL_KEY", "")
    veed_key = os.environ.get("VEED_API_KEY", "")

    if args.endpoint and fal_key:
        fal = FalClient(fal_key)
        result = poll_fal(fal, args.endpoint, args.job_id)
        print(json.dumps(result, indent=2))
        return

    if veed_key:
        client = VeedClient(veed_key)
        status = client.get_render(args.job_id)
        print(json.dumps(status, indent=2))
        return

    print("ERROR: set FAL_KEY or VEED_API_KEY", file=sys.stderr)
    sys.exit(1)


def _extract_video_url(result: dict) -> str | None:
    for key in ("video", "video_url", "output"):
        val = result.get(key)
        if isinstance(val, str) and val.startswith("http"):
            return val
        if isinstance(val, dict) and val.get("url"):
            return val["url"]
    data = result.get("data") or result.get("output") or {}
    if isinstance(data, dict):
        for key in ("video", "video_url", "url"):
            if isinstance(data.get(key), str):
                return data[key]
    return None


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    resp = requests.get(url, timeout=300)
    resp.raise_for_status()
    dest.write_bytes(resp.content)
    print(f"Downloaded: {dest}")


def build_assemble_payload(slug: str) -> dict:
    """Build a VEED render payload from project manifest and shot list."""
    shot_list = load_shot_list(slug)
    base = project_dir(slug)
    manifest_path = base / "assets" / "manifest.json"
    manifest = (
        json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest_path.exists()
        else {"scenes": {}}
    )

    clips = []
    for scene in shot_list.get("scenes", []):
        sid = scene["id"]
        scene_assets = manifest.get("scenes", {}).get(sid, {})
        video = scene_assets.get("selected") or scene_assets.get("voiceover")
        if not video:
            visual = scene.get("visual", {})
            if visual.get("source_path"):
                video = visual["source_path"]
        if video:
            clips.append(
                {
                    "scene_id": sid,
                    "path": str(base / video) if not str(video).startswith("http") else video,
                    "duration_sec": scene.get("duration_sec"),
                    "on_screen_text": scene.get("on_screen_text", ""),
                }
            )

    webhook = os.environ.get("VEED_WEBHOOK_URL", "")
    payload: dict[str, Any] = {
        "project": slug,
        "title": shot_list.get("title", slug),
        "aspect_ratio": shot_list.get("aspect_ratio", "16:9"),
        "clips": clips,
        "subtitles": True,
    }
    if webhook:
        payload["webhook_url"] = webhook
    return payload


def cmd_assemble(args: argparse.Namespace) -> None:
    load_env()
    ensure_project_dirs(args.project)
    veed_key = os.environ.get("VEED_API_KEY", "")

    payload = build_assemble_payload(args.project)
    payload_path = project_dir(args.project) / "renders" / "assemble-payload.json"
    save_json(payload_path, payload)
    print(f"Wrote assemble payload: {payload_path}")
    print(f"Clips: {len(payload.get('clips', []))}")

    if not veed_key:
        print("VEED_API_KEY not set — payload only (agent can submit manually)")
        return

    client = VeedClient(veed_key)
    try:
        result = client.submit_render(payload)
        job_id = result.get("id") or result.get("job_id")
        print(json.dumps(result, indent=2))
        if job_id:
            save_job(
                args.project,
                {
                    "type": "veed_render",
                    "job_id": job_id,
                    "submitted_at": utc_now_iso(),
                },
            )
    except requests.HTTPError as exc:
        print(f"VEED API error (payload saved for manual retry): {exc}", file=sys.stderr)
        if exc.response is not None:
            print(exc.response.text, file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description="VEED + fal.ai video client")
    sub = parser.add_subparsers(dest="command", required=True)

    p_fabric = sub.add_parser("fabric", help="VEED Fabric 1.0 image+audio → video")
    p_fabric.add_argument("--image", required=True, help="Image URL or path")
    p_fabric.add_argument("--audio", required=True, help="Audio URL or path")
    p_fabric.add_argument("--resolution", default="480p")
    p_fabric.add_argument("--project")
    p_fabric.add_argument("--output")
    p_fabric.add_argument("--wait", action="store_true")
    p_fabric.set_defaults(func=cmd_fabric)

    p_lip = sub.add_parser("lipsync", help="VEED Lipsync video+audio")
    p_lip.add_argument("--video", required=True)
    p_lip.add_argument("--audio", required=True)
    p_lip.add_argument("--project")
    p_lip.add_argument("--wait", action="store_true")
    p_lip.set_defaults(func=cmd_lipsync)

    p_poll = sub.add_parser("poll", help="Poll job status")
    p_poll.add_argument("--job-id", required=True)
    p_poll.add_argument("--endpoint", help="fal endpoint e.g. veed/fabric-1.0")
    p_poll.set_defaults(func=cmd_poll)

    p_asm = sub.add_parser("assemble", help="Build/submit VEED assemble job")
    p_asm.add_argument("--project", required=True)
    p_asm.set_defaults(func=cmd_assemble)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
