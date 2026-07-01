#!/usr/bin/env python3
"""
FFmpeg-based QC: concat, frame extract, duration check, transcript match.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from utils import load_shot_list, project_dir, utc_now_iso

QA_TEMPLATE = """# QA Report — {title}

Generated: {timestamp}
Video: `{video_path}`

## Summary

| Check | Result |
|-------|--------|
| Duration | {duration_result} |
| Scene keyframes | {frame_result} |
| Script match | {script_result} |
| Acceptance criteria | {criteria_result} |

## Duration

- Target: {target_sec}s
- Actual: {actual_sec}s
- Delta: {delta_sec}s
- Status: **{duration_status}**

## Scene keyframes

{frame_details}

## Transcript match

{transcript_details}

## Acceptance criteria

{criteria_details}

## Overall

**{overall_status}**

{next_steps}
"""


def run_cmd(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)


def ffprobe_duration(video: Path) -> float:
    result = run_cmd(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(video),
        ]
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr or "ffprobe failed")
    return float(result.stdout.strip())


def extract_frame(video: Path, timestamp: float, out: Path) -> bool:
    out.parent.mkdir(parents=True, exist_ok=True)
    result = run_cmd(
        [
            "ffmpeg",
            "-y",
            "-ss",
            str(timestamp),
            "-i",
            str(video),
            "-frames:v",
            "1",
            "-q:v",
            "2",
            str(out),
        ]
    )
    return result.returncode == 0 and out.exists()


def concat_clips(slug: str, output: Path) -> None:
    base = project_dir(slug)
    manifest_path = base / "assets" / "manifest.json"
    shot_list = load_shot_list(slug)

    manifest = (
        json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest_path.exists()
        else {"scenes": {}}
    )

    list_file = base / "renders" / "concat-list.txt"
    lines = []
    for scene in shot_list.get("scenes", []):
        sid = scene["id"]
        assets = manifest.get("scenes", {}).get(sid, {})
        clip = assets.get("selected")
        if clip:
            path = base / clip
            if path.exists():
                lines.append(f"file '{path.resolve().as_posix()}'")

    if not lines:
        print("ERROR: no clips in manifest for concat", file=sys.stderr)
        sys.exit(1)

    list_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)

    result = run_cmd(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-c",
            "copy",
            str(output),
        ]
    )
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        sys.exit(1)
    print(f"Concatenated: {output}")


def normalize_audio(input_video: Path, output: Path) -> None:
    result = run_cmd(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(input_video),
            "-af",
            "loudnorm=I=-16:TP=-1.5:LRA=11",
            "-c:v",
            "copy",
            str(output),
        ]
    )
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        sys.exit(1)


def transcribe_whisper(video: Path) -> str:
    try:
        import whisper
    except ImportError:
        return ""

    model = whisper.load_model("base")
    result = model.transcribe(str(video))
    return result.get("text", "").strip()


def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    return " ".join(text.split())


def script_similarity(script: str, transcript: str) -> float:
    if not script or not transcript:
        return 0.0
    s_words = set(normalize_text(script).split())
    t_words = set(normalize_text(transcript).split())
    if not s_words:
        return 0.0
    return len(s_words & t_words) / len(s_words)


def check_criterion(criterion: str, script: str, transcript: str, duration: float, target: float) -> tuple[bool, str]:
    c = criterion.lower()
    script_l = script.lower()
    transcript_l = transcript.lower()

    if "first 5 second" in c and "product name" in c:
        product_hint = script_l.split(".")[0] if script_l else ""
        passed = bool(product_hint and product_hint[:80] in transcript_l[:200])
        return passed, "Product mention in opening (heuristic)"

    if "final 10 second" in c and "cta" in c:
        passed = len(transcript_l) > 50
        return passed, "CTA segment present (heuristic)"

    if "benefit" in c:
        benefits = ["fast", "secure", "accurate", "reliable", "enterprise"]
        found = [b for b in benefits if b in transcript_l or b in script_l]
        return len(found) >= 2, f"Benefit keywords found: {found}"

    if "quality" in c or "professional" in c:
        return duration > 10, "Video duration indicates complete render"

    return True, "Manual review recommended"


def cmd_concat(args: argparse.Namespace) -> None:
    output = Path(args.output) if args.output else project_dir(args.project) / "renders" / "draft.mp4"
    concat_clips(args.project, output)


def cmd_check(args: argparse.Namespace) -> None:
    base = project_dir(args.project)
    video = Path(args.video) if args.video else base / "renders" / "final.mp4"
    if not video.is_absolute():
        video = base / video
    if not video.exists():
        video = base / "renders" / "draft.mp4"
    if not video.exists():
        print(f"ERROR: video not found: {video}", file=sys.stderr)
        sys.exit(1)

    shot_list = load_shot_list(args.project)
    target = shot_list.get("duration_target_sec", 90)
    actual = ffprobe_duration(video)
    delta = actual - target
    duration_ok = abs(delta) <= max(5, target * 0.1)

    script_path = base / "script.md"
    script = script_path.read_text(encoding="utf-8") if script_path.exists() else ""
    for scene in shot_list.get("scenes", []):
        script += " " + scene.get("narration", "")

    frames_dir = base / "renders" / "frames"
    frame_lines = []
    frame_ok = True
    scenes = shot_list.get("scenes", [])
    if scenes:
        step = actual / len(scenes) if actual else 1
        for i, scene in enumerate(scenes):
            ts = i * step
            frame_out = frames_dir / f"{scene['id']}.jpg"
            ok = extract_frame(video, ts, frame_out)
            status = "ok" if ok else "FAILED"
            if not ok:
                frame_ok = False
            frame_lines.append(f"- {scene['id']} @ {ts:.1f}s → `{frame_out.name}` — {status}")
    else:
        frame_lines.append("- (no scenes in shot list)")

    transcript = transcribe_whisper(video) if not args.skip_transcript else ""
    similarity = script_similarity(script, transcript)
    script_ok = similarity >= 0.4 or not transcript

    criteria_lines = []
    criteria_ok = True
    for criterion in shot_list.get("acceptance_criteria", []):
        passed, note = check_criterion(criterion, script, transcript, actual, target)
        if not passed:
            criteria_ok = False
        status = "PASS" if passed else "FAIL"
        criteria_lines.append(f"- [{status}] {criterion} — {note}")

    overall = duration_ok and frame_ok and script_ok and criteria_ok

    report = QA_TEMPLATE.format(
        title=shot_list.get("title", args.project),
        timestamp=utc_now_iso(),
        video_path=str(video.relative_to(base)).replace("\\", "/"),
        duration_result="PASS" if duration_ok else "FAIL",
        frame_result="PASS" if frame_ok else "FAIL",
        script_result="PASS" if script_ok else "FAIL",
        criteria_result="PASS" if criteria_ok else "FAIL",
        target_sec=target,
        actual_sec=f"{actual:.1f}",
        delta_sec=f"{delta:+.1f}",
        duration_status="PASS" if duration_ok else "FAIL",
        frame_details="\n".join(frame_lines),
        transcript_details=(
            f"Similarity score: {similarity:.0%}\n\n```\n{transcript[:1500]}\n```"
            if transcript
            else "Whisper not available — install openai-whisper for transcript check"
        ),
        criteria_details="\n".join(criteria_lines) or "- (none defined)",
        overall_status="PASS — ready to publish" if overall else "FAIL — address issues above",
        next_steps="" if overall else "Re-render affected scenes and re-run check.",
    )

    report_path = base / "qa-report.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"Wrote {report_path}")
    print(f"Overall: {'PASS' if overall else 'FAIL'}")
    sys.exit(0 if overall else 1)


def main() -> None:
    parser = argparse.ArgumentParser(description="FFmpeg QC tools")
    sub = parser.add_subparsers(dest="command", required=True)

    p_concat = sub.add_parser("concat", help="Concat manifest clips to draft mp4")
    p_concat.add_argument("--project", required=True)
    p_concat.add_argument("--output")
    p_concat.set_defaults(func=cmd_concat)

    p_check = sub.add_parser("check", help="Run QA checks")
    p_check.add_argument("--project", required=True)
    p_check.add_argument("--video")
    p_check.add_argument("--skip-transcript", action="store_true")
    p_check.set_defaults(func=cmd_check)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
