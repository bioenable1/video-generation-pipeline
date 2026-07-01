#!/usr/bin/env python3
"""
Research phase: fetch YouTube transcripts and produce competitor analysis.

Comment analysis via Rube MCP is documented in output for the agent to complete.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from utils import (
    ensure_project_dirs,
    extract_youtube_id,
    project_dir,
    utc_now_iso,
)

COMPETITOR_TEMPLATE = """# Competitor Analysis — {product}

Generated: {timestamp}

## Videos analyzed

{video_table}

## Common patterns

### Hooks
{hooks}

### Structure
{structure}

### Visual style
{visual_style}

### CTAs
{ctas}

## Opportunities for our video
{opportunities}

## Transcript excerpts

{excerpts}
"""

AUDIENCE_TEMPLATE = """# Audience Insights — {product}

Generated: {timestamp}

## Comment analysis status
{comment_status}

## Themes to address
{themes}

## FAQ items from audience
{faqs}

## Agent instructions (Rube MCP)
If Rube MCP is connected, run:
1. `RUBE_SEARCH_TOOLS` for YouTube toolkit
2. `YOUTUBE_LIST_COMMENT_THREADS` for each reference video
3. Summarize pain points, questions, and sentiment here
4. Re-run: `python scripts/research.py --project {slug} --merge-comments comments.json`
"""


def fetch_transcript(video_id: str) -> tuple[str, str]:
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:
        print("Install: pip install youtube-transcript-api", file=sys.stderr)
        sys.exit(1)

    try:
        api = YouTubeTranscriptApi()
        fetched = api.fetch(video_id)
        transcript_list = fetched.to_raw_data()
    except AttributeError:
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        except Exception as exc:
            return "", f"Error fetching {video_id}: {exc}"
    except Exception as exc:
        return "", f"Error fetching {video_id}: {exc}"

    lines = []
    for entry in transcript_list:
        start = entry.get("start", 0)
        text = entry.get("text", "").strip()
        if text:
            lines.append(f"[{start:.1f}s] {text}")

    return "\n".join(lines), ""


def analyze_transcripts(transcripts: dict[str, str], product: str) -> dict[str, str]:
    """Lightweight heuristic analysis; agent can enrich."""
    all_text = " ".join(transcripts.values()).lower()
    hooks = []
    if any(w in all_text for w in ("introducing", "meet", "welcome", "today")):
        hooks.append("- Question or problem-statement opener common")
    if any(w in all_text for w in ("fast", "secure", "easy", "simple")):
        hooks.append("- Benefit-led hooks (speed, security, simplicity)")
    if not hooks:
        hooks.append("- Review transcripts for specific hook patterns")

    structure = [
        "- Typical flow: problem → solution → features → proof → CTA",
        "- Average talking pace ~130-150 WPM in educational product videos",
    ]

    visual = [
        "- Product shots, UI demos, and office/enterprise B-roll common",
        "- On-screen text for key stats and product names",
    ]

    ctas = [
        "- Visit website / request demo / contact sales",
        "- Subscribe or follow for more content (YouTube-native)",
    ]

    opportunities = [
        f"- Differentiate {product} with specific biometric/enterprise proof points",
        "- Address audience FAQs surfaced in comments (see audience-insights.md)",
        "- Match or beat competitor pacing while keeping BioEnable brand tone",
    ]

    excerpts = []
    for vid, text in transcripts.items():
        preview = text[:800] + ("..." if len(text) > 800 else "")
        excerpts.append(f"### {vid}\n\n```\n{preview}\n```\n")

    return {
        "hooks": "\n".join(hooks),
        "structure": "\n".join(structure),
        "visual_style": "\n".join(visual),
        "ctas": "\n".join(ctas),
        "opportunities": "\n".join(opportunities),
        "excerpts": "\n".join(excerpts),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Research competitors via YouTube transcripts")
    parser.add_argument("--project", required=True, help="Project slug")
    parser.add_argument("--urls", nargs="*", default=[], help="YouTube URLs or video IDs")
    parser.add_argument("--merge-comments", help="JSON file with Rube MCP comment data")
    args = parser.parse_args()

    base = ensure_project_dirs(args.project)
    brief_path = base / "brief.md"
    product = args.project.replace("-", " ").title()
    if brief_path.exists():
        for line in brief_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("## Product") or line.startswith("# "):
                name = line.lstrip("#").strip()
                if name and not name.startswith("Video Brief"):
                    product = name.replace("— Video Brief", "").strip()
                    break

    transcripts: dict[str, str] = {}
    video_rows = []
    transcript_dir = base / "research" / "transcripts"

    for url in args.urls:
        vid = extract_youtube_id(url) or url
        text, err = fetch_transcript(vid)
        if err:
            video_rows.append(f"| {vid} | failed | {err} |")
            continue
        transcripts[vid] = text
        out = transcript_dir / f"{vid}.txt"
        out.write_text(text, encoding="utf-8")
        word_count = len(text.split())
        video_rows.append(f"| [{vid}](https://youtube.com/watch?v={vid}) | ok | {word_count} words |")

    analysis = analyze_transcripts(transcripts, product)
    timestamp = utc_now_iso()

    competitor_path = base / "research" / "competitor-analysis.md"
    competitor_path.write_text(
        COMPETITOR_TEMPLATE.format(
            product=product,
            timestamp=timestamp,
            video_table="| Video | Status | Notes |\n|-------|--------|-------|\n"
            + ("\n".join(video_rows) if video_rows else "| (none) | — | Add --urls |"),
            **analysis,
        ),
        encoding="utf-8",
    )

    comment_status = "Pending — use Rube MCP YOUTUBE_LIST_COMMENT_THREADS"
    themes = "- (Run comment analysis via agent + Rube MCP)"
    faqs = "- (Populate from comment threads)"

    if args.merge_comments:
        import json

        comments_path = Path(args.merge_comments)
        if comments_path.exists():
            data = json.loads(comments_path.read_text(encoding="utf-8"))
            comment_status = f"Merged from {comments_path.name}"
            themes = "\n".join(f"- {t}" for t in data.get("themes", [])) or themes
            faqs = "\n".join(f"- {q}" for q in data.get("faqs", [])) or faqs

    audience_path = base / "research" / "audience-insights.md"
    audience_path.write_text(
        AUDIENCE_TEMPLATE.format(
            product=product,
            timestamp=timestamp,
            comment_status=comment_status,
            themes=themes,
            faqs=faqs,
            slug=args.project,
        ),
        encoding="utf-8",
    )

    print(f"Wrote {competitor_path}")
    print(f"Wrote {audience_path}")
    print(f"Transcripts: {len(transcripts)} saved to research/transcripts/")


if __name__ == "__main__":
    main()
