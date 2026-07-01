# How to Use the Video Generation Pipeline

Universal guide for creating **any** video — product launch, explainer, social short, or tutorial — with free local tools or optional paid APIs.

**Repo:** https://github.com/bioenable1/video-generation-pipeline

---

## 1. Install

```powershell
git clone https://github.com/bioenable1/video-generation-pipeline.git
cd video-generation-pipeline
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

**Requirements:** Python 3.10+, [FFmpeg](https://ffmpeg.org/) in PATH.

Optional API keys in `.env` (paid mode / better stock search): `PEXELS_API_KEY`, `ELEVENLABS_API_KEY`, `VEED_API_KEY`, `FAL_KEY`.

---

## 2. Try the included samples

Two complete projects ship with the repo — play them immediately:

| Sample | Type | Format | Path |
|--------|------|--------|------|
| IriUniverse Two (product marketing) | `product` | 16:9 landscape | `projects/iriuniverse2-launch/renders/final.mp4` |
| 3 Tips for Better Sleep (wellness short) | `social` | 9:16 vertical | `projects/sleep-tips-social/renders/final.mp4` |

```powershell
# Play samples
start projects\iriuniverse2-launch\renders\final.mp4
start projects\sleep-tips-social\renders\final.mp4

# Re-render either (free, no API keys)
python run.py render --project iriuniverse2-launch --force
python run.py render --project sleep-tips-social --force
```

---

## 3. Create your own video (step by step)

### Step A — Bootstrap a project

Pick a **video type** and **subject**:

```powershell
# Product / launch video (16:9)
python run.py new-project --subject "Acme Widget Pro" --type product --slug acme-launch --website acme.com

# Educational explainer (16:9)
python run.py new-project --subject "How blockchain works" --type explainer --slug blockchain-101

# Social short / Reel / TikTok (9:16)
python run.py new-project --subject "Morning routine hack" --type social --slug morning-hack --duration 45

# Step-by-step tutorial (16:9)
python run.py new-project --subject "Deploy with Docker" --type tutorial --slug docker-deploy --duration 180
```

This creates `projects/<slug>/` with:

- `brief.md` — audience, messages, reference URLs
- `brand.json` — colors, logo paths, tagline, contact
- `plan/shot-list.json` — preset scenes with placeholder narration
- `production.json` — `free` mode by default

### Step B — Customize content

Edit these files (or ask the Cursor agent to):

1. **`brief.md`** — who it's for, key messages, YouTube reference URLs, source PDFs/websites
2. **`brand.json`** — your colors, logo file paths, tagline, website
3. **`plan/shot-list.json`** — scene narration, on-screen text, bullets, visual types

Put logos in `assets/brand/`. Put brochures in `assets/source/` or `assets/brochure.pdf`. Add product images to `assets/images/`.

**Visual types per scene:**

| Type | When to use |
|------|-------------|
| `stock_video` | B-roll (uses `catalog_key` or `query`) |
| `product_image` | Your photo over stock background |
| `ai_image` | AI-generated still (prompt in shot-list) |
| `text_card` | Bold text over motion background |
| `logo_slate` | Outro with logo + CTA |
| `screen_recording` | Tutorial screen capture clip |

Stock keys: see `templates/stock_catalog.json` (`crowd_people`, `technology_data`, etc.).

### Step C — Validate and approve

```powershell
python run.py validate --project acme-launch
python run.py approve --project acme-launch
```

**Approval is required** before rendering. The agent must not skip this gate.

### Step D — Generate assets

```powershell
python run.py generate-assets --project acme-launch
```

This will:

- Extract images from PDFs / website URLs in `brief.md`
- Download free Pexels CDN stock per scene
- Download background music
- Write `assets/ai-prompts.json` for any `ai_image` scenes

For AI images: use Cursor **imagegen** / `ai-studio-image` skill, save to `assets/images/s01.png`, then re-run `generate-assets`.

### Step E — Render (free)

```powershell
python run.py render --project acme-launch --force
```

Output: `projects/acme-launch/renders/final.mp4`

Uses **edge-tts** voiceover + **FFmpeg** compositing. Brand colors from `brand.json`.

### Step F — Quality check

```powershell
python run.py qc check --project acme-launch
python run.py thumbnail --project acme-launch
```

Fix any FAIL items in `qa-report.md`, adjust shot-list narration, re-render.

### Step G — Publish (optional)

See [publish.md](publish.md) for YouTube upload via Rube MCP.

---

## 4. Paid mode (optional polish)

```powershell
python run.py set-mode --project acme-launch --mode paid
# Set ELEVENLABS_API_KEY, VEED_API_KEY, FAL_KEY in .env
python run.py voiceover --project acme-launch
python run.py veed assemble --project acme-launch
```

| Mode | Voice | Video | Cost |
|------|-------|-------|------|
| **free** (default) | edge-tts | FFmpeg + Pexels | $0 |
| **paid** | ElevenLabs | VEED + fal.ai | Usage-based |

---

## 5. Use with Cursor agent

Load the **`video-pipeline`** skill (`.cursor/skills/video-pipeline/SKILL.md`).

**Example prompt:**

```
Create a social short about sustainable fashion.
Follow the video-pipeline skill.

python run.py new-project --subject "Sustainable fashion tips" --type social --slug fashion-tips
Then customize brief.md and shot-list.json, get my approval, generate assets, and render.
```

The agent orchestrates: research → plan → **STOP for approval** → assets → render → QC → publish.

MCP setup (Pexels, Rube/YouTube): [mcp-setup.md](mcp-setup.md)

---

## 6. CLI reference

```powershell
python run.py new-project     --subject "..." --type product|explainer|social|tutorial [--slug ...]
python run.py validate        --project <slug>
python run.py approve         --project <slug>
python run.py generate-assets --project <slug>
python run.py render          --project <slug> [--force]
python run.py research        --project <slug> --urls <youtube_urls>
python run.py plan            --project <slug>
python run.py script          --project <slug>
python run.py set-mode        --project <slug> --mode free|paid
python run.py voiceover       --project <slug>      # paid
python run.py veed assemble   --project <slug>      # paid
python run.py qc check        --project <slug>
python run.py thumbnail       --project <slug>
```

---

## 7. Project file map

```
projects/<slug>/
├── brief.md                 # Your creative brief
├── brand.json               # Colors, logo, tagline (renderer reads this)
├── production.json          # free | paid
├── plan/
│   ├── shot-list.json       # Scenes — must have approved: true
│   └── content-plan.html    # Visual plan (optional)
├── assets/
│   ├── brand/               # logo-dark-bg.png, logo-transparent.png
│   ├── images/              # Product shots, AI images
│   ├── stock/               # s01.mp4, s02.mp4, … per scene
│   ├── vo/                  # Voiceover MP3s (auto-generated)
│   ├── music/background.mp3
│   ├── ai-prompts.json      # Pending AI image jobs
│   └── manifest.json        # Asset readiness
├── renders/final.mp4        # ← your output
├── qa-report.md             # After qc check
└── publish/thumbnail.png
```

**Templates:** `templates/video-types/*.json` (presets), `templates/stock_catalog.json` (free B-roll URLs)

---

## 8. Tips

- **Duration:** Final length follows voiceover, not `duration_sec` in shot-list. Write longer narration to hit your target.
- **Vertical video:** Use `--type social` (9:16) or set `"aspect_ratio": "9:16"` in shot-list.
- **No logo?** Outro still works — text-only slate with your brand colors.
- **Better stock:** Set `PEXELS_API_KEY` and add `"query": "your search"` per scene.
- **Style reference:** Add YouTube URLs to `brief.md` — research runs automatically on render.

---

## 9. Troubleshooting

| Problem | Fix |
|---------|-----|
| `ffmpeg failed` | Ensure FFmpeg is installed and in PATH |
| `No stock for s01` | Run `python run.py generate-assets --project <slug>` |
| `Paid mode` error on render | Use `set-mode --mode free` or use voiceover+veed for paid |
| Validation fails on stock | Add `catalog_key` or `query` to each `stock_video` scene |
| Video too short | Lengthen `narration` text in shot-list.json |

More: [INSTALL.md](INSTALL.md)
