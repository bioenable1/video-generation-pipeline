---
name: video-pipeline
description: >-
  Universal AI video pipeline for any product, concept, or topic.
  Use when creating, planning, editing, or publishing videos — product demos,
  explainers, social shorts, tutorials, VEED workflows, shot lists, voiceover,
  or YouTube content.
---

# Universal Video Pipeline

Orchestrate videos for **any subject** from research through publish. Each project lives in `projects/<slug>/`. **Do not skip gates.**

## Video types

| Type | Use for | Default ratio | Preset |
|------|---------|---------------|--------|
| `product` | Marketing, launches, demos | 16:9 | `templates/video-types/product.json` |
| `explainer` | Education, concepts, how-it-works | 16:9 | `templates/video-types/explainer.json` |
| `social` | Short-form, hooks, ads | 9:16 | `templates/video-types/social.json` |
| `tutorial` | Step-by-step how-to | 16:9 | `templates/video-types/tutorial.json` |

Bootstrap:

```bash
python run.py new-project --subject "Your Topic" --type explainer --slug my-video
```

Customize `brief.md`, `brand.json`, and `plan/shot-list.json` before approving.

## Project files

| File | Purpose |
|------|---------|
| `brief.md` | Audience, messages, reference URLs, source materials |
| `brand.json` | Colors, logo paths, tagline, website, contact |
| `production.json` | `free` (default) or `paid` mode |
| `plan/shot-list.json` | Scenes, narration, visuals — **approval gate** |
| `assets/ai-prompts.json` | Pending AI image prompts (after `generate-assets`) |

## Phase gates

| Phase | Gate | Required artifact |
|-------|------|-------------------|
| 1 Research | `brief.md` exists | `research/competitor-analysis.md` (if refs provided) |
| 2 Planning | research optional | `plan/content-plan.html` + `plan/shot-list.json` |
| **STOP** | `shot-list.json` → `approved: true` | user approval |
| 3 Script | plan approved | `script.md` + `vo-segments.json` |
| 4 Assets | script exists | `python run.py generate-assets --project <slug>` |
| 5 Edit | manifest ready | `renders/final.mp4` |
| 6 QA | render exists | `qa-report.md` (all criteria pass) |
| 7 Publish | QA pass | YouTube upload + thumbnail |

**Hard rule:** Never run **paid** generation (ElevenLabs, VEED, fal.ai) until `approved: true` **and** `production.json` mode is `paid`.

## Production modes

| Mode | Voice | Edit | Command |
|------|-------|------|---------|
| **free** | edge-tts | FFmpeg + Pexels CDN | `python run.py render --project <slug>` |
| **paid** | ElevenLabs | VEED + fal.ai | `python run.py set-mode --project <slug> --mode paid` |

Brand colors and tagline come from `brand.json` — never hardcode per client.

## Skill routing

| Phase | Skill / tool | Script |
|-------|--------------|--------|
| Research | `youtube-summarizer` | `run.py research` |
| Deep video Q&A | `seek-and-analyze-video` | — |
| Planning HTML | — | `run.py plan` |
| Validate shot list | — | `run.py validate` |
| Assets (stock + extract) | Pexels MCP optional | `run.py generate-assets` |
| AI images | `ai-studio-image` / imagegen | save to `assets/images/<scene>.png` |
| AI video / avatar | VEED Fabric, fal.ai | `run.py veed fabric` |
| Voice (free) | — | included in `run.py render` |
| Voice (paid) | `voice-ai-development` | `run.py voiceover` |
| QC | `audio-transcriber` | `run.py qc check` |
| Thumbnail | `seo-image-gen` | `run.py thumbnail` |
| Publish | `youtube-automation` (Rube MCP) | `docs/publish.md` |

## Phase 1: Research (optional)

Only when brief or shot-list includes YouTube reference URLs.

```bash
python run.py research --project <slug> --urls <youtube_urls>
```

Outputs: `research/competitor-analysis.md`, `research/transcripts/*.txt`

If user shares a style reference, save structure notes to `research/reference-style-*.md`.

## Phase 2: Planning

1. Edit or generate `plan/shot-list.json` from video type preset + brief
2. Validate: `python run.py validate --project <slug>`
3. HTML plan: `python run.py plan --project <slug>`
4. **STOP** — wait for user approval → `python run.py approve --project <slug>`

**Schema:** `templates/shot-list.schema.json`

Scene visual types: `stock_video`, `product_image`, `ai_image`, `ai_video`, `screen_recording`, `talking_head`, `text_card`, `logo_slate`

Use `visual.catalog_key` for free stock (see `templates/stock_catalog.json`) or `visual.query` for Pexels API search.

## Phase 3: Script

Refine narration to 130–150 WPM. Write `script.md` and `vo-segments.json`.

## Phase 4: Assets

```bash
python run.py generate-assets --project <slug>
```

This runs extract (PDF/website), stock fetch, and writes `assets/ai-prompts.json` for scenes with `visual.type: ai_image`.

For pending AI images: use Cursor imagegen, save as `assets/images/s01.png`, re-run generate-assets.

## Phase 5: Edit

**Free (default):**

```bash
python run.py render --project <slug> --force
```

**Paid:**

```bash
python run.py voiceover --project <slug>
python run.py veed assemble --project <slug>
```

## Phase 6: QA

```bash
python run.py qc check --project <slug>
```

Check duration, acceptance_criteria, transcript match → `qa-report.md`

## Phase 7: Publish

```bash
python run.py thumbnail --project <slug>
```

YouTube via Rube MCP — see `docs/publish.md`

## User prompt template

```
Create a [product|explainer|social|tutorial] video about [subject].

Brief: projects/<slug>/brief.md
Video type: [type]
Reference style (optional): [YouTube URL]
Target duration: [seconds]
Aspect ratio: [16:9 | 9:16]

Follow video-pipeline skill:
1. new-project or use existing slug
2. Research (if refs) → Plan → STOP for approval
3. generate-assets → render → QC → publish
```

## New project examples

```bash
# Product launch
python run.py new-project --subject "Acme Widget Pro" --type product --website acme.com

# Concept explainer
python run.py new-project --subject "How blockchain works" --type explainer

# Instagram reel
python run.py new-project --subject "Morning routine hack" --type social --duration 30

# Software tutorial
python run.py new-project --subject "Deploy with Docker" --type tutorial --duration 180
```
