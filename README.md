# Video Generation Pipeline

Agent-orchestrated **product marketing video factory** for Cursor, Codex, and CLI.  
Turn a product brief into a finished MP4 with research, shot lists, stock B-roll, voiceover, and QA — **free by default**, optional paid APIs for polish.

[![Sample video included](projects/iriuniverse2-launch/renders/final.mp4)](projects/iriuniverse2-launch/renders/final.mp4)

**Sample output:** [IriUniverse Two STQC marketing video](projects/iriuniverse2-launch/renders/final.mp4) (~92s, BioEnable product)

---

## Features

- **7-phase pipeline** with approval gates (research → plan → script → assets → edit → QC → publish)
- **Free mode:** edge-tts + FFmpeg + Pexels CDN stock + product image compositing + music
- **Paid mode:** ElevenLabs + VEED + fal.ai (Fabric, Lipsync)
- **Cursor skill** (`.cursor/skills/product-video-pipeline/`) for agent-driven production
- **Reference style matching** — benchmark against YouTube videos (e.g. BioEnable E-Gate format)
- **Sample project** with full artifacts: `projects/iriuniverse2-launch/`

---

## Quick start

```powershell
git clone https://github.com/bioenable1/video-generation-pipeline.git
cd Video-Generation
python -m venv .venv && .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env

# Play sample output
start projects\iriuniverse2-launch\renders\final.mp4

# Re-render sample (free, no API keys)
python run.py render --project iriuniverse2-launch --force
```

**Full guide:** [docs/INSTALL.md](docs/INSTALL.md)

---

## CLI

```powershell
python run.py new-project --product "My Product" --slug my-launch
python run.py render --project my-launch --force          # free full render
python run.py set-mode --project my-launch --mode paid    # switch to paid APIs
python run.py voiceover --project my-launch                 # ElevenLabs
python run.py veed assemble --project my-launch             # VEED edit
python run.py qc check --project my-launch
```

| Mode | Voice | Video | Cost |
|------|-------|-------|------|
| **free** (default) | edge-tts | FFmpeg + Pexels CDN + product images | $0 |
| **paid** | ElevenLabs | VEED + fal.ai | Usage-based |

---

## Cursor agent

```
Create a product marketing video for IriUniverse Two.
Follow the product-video-pipeline skill.
Brief: projects/iriuniverse2-launch/brief.md
Style reference: https://www.youtube.com/watch?v=d58Kduairis
```

MCP setup: [docs/mcp-setup.md](docs/mcp-setup.md)

---

## Sample project layout

```
projects/iriuniverse2-launch/
├── brief.md
├── production.json          # free | paid
├── plan/
│   ├── shot-list.json
│   └── content-plan.html
├── research/
│   ├── competitor-analysis.md
│   └── reference-style-e-gate.md
├── assets/
│   ├── brand/               # logos
│   ├── images/              # brochure + website
│   ├── stock/               # B-roll clips
│   ├── vo/                  # voiceover MP3s
│   └── music/background.mp3
├── renders/final.mp4        # ← sample output
└── publish/thumbnail.png
```

---

## Requirements

- Python 3.10+
- FFmpeg (in PATH)
- Optional API keys in `.env` for paid mode / Pexels search

---

## License

MIT — see [LICENSE](LICENSE)
