---
name: product-video-pipeline
description: >-
  End-to-end product marketing video pipeline for BioEnable-style videos.
  Use when creating, planning, editing, or publishing product demo videos,
  VEED workflows, shot lists, voiceover, or YouTube marketing content.
---

# Product Video Pipeline

Orchestrate product marketing videos from research through publish. Each phase writes artifacts to `projects/<slug>/`. **Do not skip gates.**

## Reference video style

When user shares a BioEnable or competitor YouTube URL, analyze transcript + structure and save to `research/reference-style-*.md`. Match narrative arc (problem → solution → how → trust → benefits → CTA).

**Benchmark:** https://www.youtube.com/watch?v=d58Kduairis (BioEnable E-Gate, ~1:52)

- Tone: professional B2B, clear, confident
- **Production mode: `free` by default** (edge-tts + FFmpeg — no API keys)
- Set `projects/<slug>/production.json` → `"mode": "paid"` for ElevenLabs/VEED/fal.ai
- Or: `python run.py set-mode --project <slug> --mode paid`
- Aspect ratio: `16:9` (product pages); `9:16` for social cuts
- Duration: 60–120s for product demos
- Reference style: `reference/BioEnable-Videos/`
- Export: H.264 1080p, AAC audio, burned-in subtitles optional

## Phase gates

| Phase | Gate | Required artifact |
|-------|------|-------------------|
| 1 Research | `brief.md` exists | `research/competitor-analysis.md` |
| 2 Planning | research complete | `plan/content-plan.html` + `plan/shot-list.json` |
| **STOP** | `shot-list.json` → `approved: true` | user approval |
| 3 Script | plan approved | `script.md` + `vo-segments.json` |
| 4 Assets | script exists | `assets/manifest.json` (all scenes resolved) |
| 5 Edit | manifest complete | `renders/final.mp4` |
| 6 QA | render exists | `qa-report.md` (all criteria pass) |
| 7 Publish | QA pass | YouTube upload + thumbnail |

**Hard rule:** Never run **paid** asset generation (ElevenLabs, VEED, fal.ai) until `plan/shot-list.json` has `"approved": true` **and** `production.json` has `"mode": "paid"`.

## Production modes

| Mode | Voice | Edit | Command |
|------|-------|------|---------|
| **free** (default) | edge-tts (local) | FFmpeg slides + optional Pexels | `python run.py render --project <slug>` |
| **paid** | ElevenLabs | VEED + fal.ai | `python run.py set-mode --project <slug> --mode paid` then voiceover + veed |

Config file: `projects/<slug>/production.json`

---

## Skill routing table

| Phase | Load this skill / tool | Repo script |
|-------|------------------------|-------------|
| Research transcripts | `youtube-summarizer` | `scripts/research.py` |
| Deep video Q&A | `seek-and-analyze-video` | — |
| YouTube comments/upload | `youtube-automation` (Rube MCP) | `scripts/research.py --comments` |
| Planning HTML | — | `scripts/plan_generator.py` |
| Shot list validation | — | `scripts/validate_shot_list.py` |
| Voiceover (free) | — | `scripts/render_free.py` or edge-tts in render |
| Voiceover (paid) | `voice-ai-development` | `scripts/generate_voiceover.py` |
| Stock B-roll | Pexels MCP or | `scripts/pexels_fetch.py` |
| AI images | `ai-studio-image` / imagegen | agent generates to `assets/images/` |
| VEED edit + Fabric | — | `scripts/veed_client.py` |
| VideoDB subtitle/QC | `videodb-skills` | — |
| QC loop | `audio-transcriber` | `scripts/ffmpeg_qc.py` |
| Thumbnail | `seo-image-gen` / imagegen | `scripts/generate_thumbnail.py` |
| Publish | `youtube-automation` (Rube MCP) | `docs/publish.md` |
| Acceptance | `acceptance-orchestrator` | verify `qa-report.md` |

---

## Phase 1: Research

**Input:** `projects/<slug>/brief.md`

**Actions:**
1. Run `python scripts/research.py --project <slug> --urls <youtube_urls>`
2. Summarize competitor hooks, structure, pacing, CTAs
3. If Rube MCP available: extract comment themes (pain points, FAQs)
4. Optionally use `seek-and-analyze-video` for deep analysis

**Outputs:**
- `research/competitor-analysis.md`
- `research/audience-insights.md`
- `research/transcripts/<video_id>.txt`

---

## Phase 2: Planning

**Actions:**
1. Build `plan/shot-list.json` from brief + research (validate: `python scripts/validate_shot_list.py --project <slug>`)
2. Generate HTML: `python scripts/plan_generator.py --project <slug>`
3. Present `plan/content-plan.html` to user
4. **STOP.** Wait for approval. Set `"approved": true` and `"approved_at"` in shot-list.json

**Shot list schema:** `templates/shot-list.schema.json`

---

## Phase 3: Script

**Actions:**
1. Refine narration to 130–150 WPM
2. Add pronunciation notes for product terms (e.g. Iriuniverse, BioEnable)
3. Write `script.md` and `vo-segments.json` (one segment per scene)

```json
{
  "segments": [
    { "scene_id": "s01", "text": "...", "target_duration_sec": 8 }
  ]
}
```

---

## Phase 4: Assets

**Prerequisite:** `approved: true` in shot-list.json

**Per scene** (from `visual.type`):

| type | Action |
|------|--------|
| `stock_video` | `python scripts/pexels_fetch.py --query "..." --project <slug> --scene s01` |
| `ai_image` | Generate via imagegen; save to `assets/images/s01.png` |
| `talking_head` | `python scripts/veed_client.py fabric --image ... --audio ...` |
| `product_clip` | Copy from `reference/BioEnable-Videos/` or user-provided path |

**Voiceover:** `python scripts/generate_voiceover.py --project <slug>`

**Manifest:** Update `assets/manifest.json` with selected asset per scene:

```json
{
  "scenes": {
    "s01": {
      "selected": "assets/stock/s01.mp4",
      "candidates": ["..."],
      "score": 0.92,
      "source": "pexels",
      "pexels_id": 12345
    }
  }
}
```

Generate 2–3 candidates per scene when possible; pick highest relevance score.

---

## Phase 5: Edit

**Primary: VEED Editing API**

```bash
python scripts/veed_client.py assemble --project <slug>
python scripts/veed_client.py poll --job-id <id>
```

Auth: `Authorization: Bearer $VEED_API_KEY` on all VEED requests.

**fal.ai (Fabric / Lipsync):**

```bash
python scripts/veed_client.py fabric --image assets/images/s01.png --audio assets/vo/s01.mp3
python scripts/veed_client.py lipsync --video assets/clips/s01.mp4 --audio assets/vo/s01.mp3
```

Poll with `python scripts/veed_client.py poll --job-id <id>` or webhook `VEED_WEBHOOK_URL`.

**Fallback: FFmpeg concat**

```bash
python scripts/ffmpeg_qc.py concat --project <slug> --output renders/draft.mp4
```

**VideoDB:** Use `videodb-skills` for subtitle burn-in, clip search, streaming preview.

---

## Phase 6: QA

```bash
python scripts/ffmpeg_qc.py check --project <slug> --video renders/final.mp4
```

Checks:
1. Total duration vs `duration_target_sec` (±5s)
2. Keyframe per scene in `renders/frames/`
3. Transcript match vs `script.md` (via Whisper if available)
4. Each `acceptance_criteria` item → pass/fail in `qa-report.md`

If any fail → patch affected scenes only, re-render, re-QC.

**Do not mark complete until all criteria pass** (acceptance-orchestrator pattern).

---

## Phase 7: Publish

1. Thumbnail: `python scripts/generate_thumbnail.py --project <slug>`
2. YouTube upload via Rube MCP (`YOUTUBE_UPLOAD_VIDEO`) — see `docs/publish.md`
3. Record `publish/youtube.json` with video ID and URL

---

## Environment variables

Copy `.env.example` → `.env`. Required for paid phases:

- `VEED_API_KEY`, `FAL_KEY`, `ELEVENLABS_API_KEY`, `PEXELS_API_KEY`
- Optional: `VIDEO_DB_API_KEY`, `MEMORIES_AI_API_KEY`

---

## New project bootstrap

```bash
python scripts/new_project.py --slug <slug> --product "<name>"
```

---

## User prompt template

```
Create a product marketing video for [product].

Brief: [paste or point to projects/<slug>/brief.md]
Reference videos: [YouTube URLs]
Target: 90s, 16:9, professional B2B tone.

Follow product-video-pipeline skill:
1. Research → 2. Plan (STOP for approval) → 3–7 after approval
```

---

## Cost guidance (90s product video)

- Research: free
- ElevenLabs VO: ~$0.10–0.30
- Pexels stock: free
- Fabric talking head (optional): ~$7 @ 480p
- VEED edit: usage-based
- QC: free (FFmpeg + local Whisper)

Reserve Fabric/Lipsync for presenter scenes only.
