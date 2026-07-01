# Video Generation Pipeline

Agent-orchestrated **universal AI video factory** for Cursor, Codex, and CLI.  
Turn any brief — product, concept, tutorial, or social clip — into a finished MP4 with research, shot lists, stock B-roll, voiceover, and QA. **Free by default**, optional paid APIs for polish.

**Sample outputs (included in repo):**

| Video | Type | Format | File |
|-------|------|--------|------|
| IriUniverse Two product launch | `product` | 16:9 | [final.mp4](projects/iriuniverse2-launch/renders/final.mp4) (~92s) |
| 3 Tips for Better Sleep | `social` | 9:16 | [final.mp4](projects/sleep-tips-social/renders/final.mp4) (~28s) |

---

## Video types

| Type | Best for | Aspect | Command |
|------|----------|--------|---------|
| **product** | Launches, demos, B2B marketing | 16:9 | `--type product` |
| **explainer** | Concepts, education, thought leadership | 16:9 | `--type explainer` |
| **social** | Shorts, reels, ads | 9:16 | `--type social` |
| **tutorial** | How-to, step-by-step | 16:9 | `--type tutorial` |

---

## Features

- **7-phase pipeline** with approval gates (research → plan → script → assets → edit → QC → publish)
- **Per-project branding** via `brand.json` (colors, logo, tagline — not hardcoded)
- **Free mode:** edge-tts + FFmpeg + Pexels CDN + compositing + music
- **Paid mode:** ElevenLabs + VEED + fal.ai (Fabric, Lipsync)
- **Cursor skill:** `.cursor/skills/video-pipeline/`
- **Sample projects:** `iriuniverse2-launch` (product) + `sleep-tips-social` (vertical social)

---

## Quick start

```powershell
git clone https://github.com/bioenable1/video-generation-pipeline.git
cd Video-Generation
python -m venv .venv && .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env

# New project — any subject
python run.py new-project --subject "How solar panels work" --type explainer --slug solar-explainer

# Edit brief.md, brand.json, plan/shot-list.json — then:
python run.py approve --project solar-explainer
python run.py generate-assets --project solar-explainer
python run.py render --project solar-explainer --force

# Play samples
start projects\iriuniverse2-launch\renders\final.mp4
start projects\sleep-tips-social\renders\final.mp4

# Re-render samples (free, no API keys)
python run.py render --project iriuniverse2-launch --force
python run.py render --project sleep-tips-social --force
```

**How to use:** [docs/USAGE.md](docs/USAGE.md) · **Install:** [docs/INSTALL.md](docs/INSTALL.md)

---

## CLI

```powershell
python run.py new-project --subject "My Topic" --type product --slug my-video
python run.py generate-assets --project my-video    # stock + sources + AI prompts
python run.py render --project my-video --force     # free full render
python run.py set-mode --project my-video --mode paid
python run.py voiceover --project my-video          # ElevenLabs
python run.py veed assemble --project my-video      # VEED edit
python run.py qc check --project my-video
```

| Mode | Voice | Video | Cost |
|------|-------|-------|------|
| **free** (default) | edge-tts | FFmpeg + Pexels CDN | $0 |
| **paid** | ElevenLabs | VEED + fal.ai | Usage-based |

---

## Cursor agent

```
Create an explainer video about quantum computing.
Follow the video-pipeline skill.
python run.py new-project --subject "Quantum computing basics" --type explainer
```

MCP setup: [docs/mcp-setup.md](docs/mcp-setup.md)

---

## Project layout

```
projects/<slug>/
├── brief.md              # Audience, messages, reference URLs
├── brand.json            # Colors, logo, tagline, contact
├── production.json       # free | paid
├── plan/
│   ├── shot-list.json    # Scenes + approval gate
│   └── content-plan.html
├── assets/
│   ├── brand/            # Logos
│   ├── images/           # Product / AI images
│   ├── stock/            # B-roll per scene
│   ├── ai-prompts.json   # Pending AI image jobs
│   └── music/
├── renders/final.mp4
└── publish/thumbnail.png
```

Presets: `templates/video-types/*.json`  
Stock catalog: `templates/stock_catalog.json`

---

## Requirements

- Python 3.10+
- FFmpeg (in PATH)
- Optional API keys in `.env` for paid mode / Pexels search

---

## License

MIT — see [LICENSE](LICENSE)
