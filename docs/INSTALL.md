# Installation & Usage Guide

Complete setup for the **Agent-Driven Product Video Pipeline** in Cursor, Codex, or any terminal.

## Requirements

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.10+ | Scripts and CLI |
| FFmpeg | 4.x+ | Video compositing, QC |
| Git | any | Clone repo |
| Cursor (optional) | latest | Agent + skills + MCP |

**Verify FFmpeg:**
```powershell
ffmpeg -version
ffprobe -version
```

Install FFmpeg on Windows: https://www.gyan.dev/ffmpeg/builds/ (essentials build is enough).

---

## 1. Clone and install

```powershell
git clone https://github.com/YOUR_ORG/Video-Generation.git
cd Video-Generation

python -m venv .venv
.\.venv\Scripts\Activate.ps1   # Windows
# source .venv/bin/activate    # macOS/Linux

pip install -r requirements.txt
copy .env.example .env         # Windows
# cp .env.example .env         # macOS/Linux
```

---

## 2. Sample project (included)

The repo ships **`projects/iriuniverse2-launch/`** — a full BioEnable IriUniverse Two marketing video:

| Artifact | Path |
|----------|------|
| Final video (~92s) | `projects/iriuniverse2-launch/renders/final.mp4` |
| Content plan (HTML) | `projects/iriuniverse2-launch/plan/content-plan.html` |
| Shot list | `projects/iriuniverse2-launch/plan/shot-list.json` |
| Script | `projects/iriuniverse2-launch/script.md` |
| Stock B-roll clips | `projects/iriuniverse2-launch/assets/stock/` |
| Product images | `projects/iriuniverse2-launch/assets/images/` |
| Brand logos | `projects/iriuniverse2-launch/assets/brand/` |
| Research | `projects/iriuniverse2-launch/research/` |

Open `final.mp4` to preview output quality before running anything.

---

## 3. Production modes

### Free mode (default — no API keys)

Uses **edge-tts** (local voice), **Pexels CDN** stock (no key), **FFmpeg** compositing, product images, background music.

```powershell
python run.py render --project iriuniverse2-launch
python run.py render --project iriuniverse2-launch --force   # regenerate VO + segments
```

Config: `projects/<slug>/production.json` → `"mode": "free"`

### Paid mode (ElevenLabs + VEED + fal.ai)

```powershell
python run.py set-mode --project iriuniverse2-launch --mode paid
```

Fill in `.env`:
- `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID`
- `VEED_API_KEY`, `VEED_WEBHOOK_URL`
- `FAL_KEY` (Fabric / Lipsync)

Then:
```powershell
python run.py voiceover --project iriuniverse2-launch
python run.py veed assemble --project iriuniverse2-launch
python run.py veed poll --job-id <id>
```

Switch back:
```powershell
python run.py set-mode --project iriuniverse2-launch --mode free
```

Override via environment: `PRODUCTION_MODE=paid`

---

## 4. CLI reference (`python run.py <command>`)

| Command | Description |
|---------|-------------|
| `new-project` | Bootstrap `projects/<slug>/` with brief + empty shot list |
| `research` | YouTube transcripts → competitor analysis |
| `plan` | Generate `content-plan.html` from shot list |
| `approve` | Set `approved: true` on shot list |
| `validate` | JSON schema + business rule checks |
| `script` | Generate `script.md` + `vo-segments.json` |
| `voiceover` | ElevenLabs TTS (paid mode) |
| `pexels` | Fetch stock via Pexels API |
| `fetch-stock` | Pexels CDN + product image fallbacks (free) |
| `extract-assets` | PDF brochure → images, scrape website images |
| `render` | **Full free marketing render** (recommended) |
| `veed` | VEED assemble / fabric / lipsync / poll |
| `qc` | FFmpeg duration, keyframes, acceptance criteria |
| `thumbnail` | YouTube thumbnail PNG |
| `set-mode` | `free` or `paid` |

**Examples:**
```powershell
python run.py new-project --product "My Product" --slug my-product-launch
python run.py research --project my-product-launch --urls "https://youtube.com/watch?v=..."
python run.py plan --project my-product-launch
python run.py approve --project my-product-launch
python run.py script --project my-product-launch
python run.py fetch-stock --project my-product-launch
python run.py render --project my-product-launch --force
python run.py qc check --project my-product-launch
python run.py thumbnail --project my-product-launch
```

**QC subcommands:**
```powershell
python run.py qc check --project iriuniverse2-launch
python run.py qc check --project iriuniverse2-launch --skip-transcript
python run.py qc concat --project iriuniverse2-launch --output projects/iriuniverse2-launch/renders/draft.mp4
```

**VEED subcommands:**
```powershell
python run.py veed assemble --project iriuniverse2-launch
python run.py veed fabric --image <url> --audio <url> --wait
python run.py veed lipsync --video <url> --audio <url> --wait
python run.py veed poll --job-id <id> --endpoint veed/fabric-1.0
```

---

## 5. Pipeline phases (manual / agent)

```
Brief → Research → Plan (HTML) → [APPROVAL] → Script → Assets → Edit → QC → Publish
```

| Phase | Gate | Output |
|-------|------|--------|
| 1 Research | `brief.md` | `research/competitor-analysis.md` |
| 2 Planning | research done | `plan/content-plan.html`, `shot-list.json` |
| **STOP** | `approved: true` | human sign-off |
| 3 Script | approved | `script.md`, `vo-segments.json` |
| 4 Assets | script | `assets/manifest.json`, stock, vo |
| 5 Edit | manifest | `renders/final.mp4` |
| 6 QA | render | `qa-report.md` |
| 7 Publish | QA pass | YouTube via Rube MCP |

---

## 6. Cursor agent setup

### Project skill (auto-loaded)

`.cursor/skills/product-video-pipeline/SKILL.md` — orchestrates the full pipeline with phase gates.

**Agent prompt:**
```
Create a product marketing video for [product].
Brief: projects/my-slug/brief.md
Reference style: https://www.youtube.com/watch?v=d58Kduairis
Follow product-video-pipeline skill.
```

### MCP servers (optional)

See [mcp-setup.md](mcp-setup.md):
- **Rube** — YouTube search, comments, upload (`https://rube.app/mcp`)
- **Pexels** — stock search MCP
- **VideoDB** — advanced edit/subtitle (`npx skills add video-db/skills`)

Copy `.cursor/mcp.json` or merge into Cursor Settings → MCP.

---

## 7. Environment variables (`.env`)

| Variable | Required for | Get key |
|----------|--------------|---------|
| `PEXELS_API_KEY` | Optional better stock search | https://www.pexels.com/api/ |
| `ELEVENLABS_API_KEY` | Paid voiceover | https://elevenlabs.io |
| `VEED_API_KEY` | Paid edit | VEED workspace → Enable API |
| `FAL_KEY` | Fabric / Lipsync | https://fal.ai |
| `VIDEO_DB_API_KEY` | VideoDB pipeline | https://videodb.io |
| `PRODUCTION_MODE` | Override `free`/`paid` | — |

Free mode works with **none** of these set.

---

## 8. Creating a new video from scratch

```powershell
python run.py new-project --product "IriUniverse Two" --slug iriuniverse2-launch-v2

# Edit projects/iriuniverse2-launch-v2/brief.md
# Add scenes to plan/shot-list.json (or let the agent write them)
# Validate and approve:
python run.py validate --project iriuniverse2-launch-v2
python run.py approve --project iriuniverse2-launch-v2

# One-command render (free):
python run.py render --project iriuniverse2-launch-v2 --force
```

**Style reference:** Save YouTube benchmark URLs; agent writes `research/reference-style-*.md`.  
Example benchmark: [BioEnable E-Gate video](https://www.youtube.com/watch?v=d58Kduairis) — problem → solution → trust → benefits → CTA.

---

## 9. Publishing to YouTube

See [publish.md](publish.md). Requires Rube MCP + OAuth.

```powershell
python run.py qc check --project iriuniverse2-launch   # must PASS
python run.py thumbnail --project iriuniverse2-launch
# Then use agent + Rube: YOUTUBE_UPLOAD_VIDEO
```

---

## 10. Troubleshooting

| Issue | Fix |
|-------|-----|
| `ffmpeg not found` | Install FFmpeg, add to PATH |
| Stock download fails | Run `fetch-stock` — falls back to product image Ken Burns |
| `shot list not approved` | `python run.py approve --project <slug>` |
| Paid commands in free mode | `set-mode --mode paid` or use `render` for free |
| Video too long | Shorten narration in `shot-list.json`, `--force` re-render |
| Dull output | Add `PEXELS_API_KEY`, product photos in `assets/images/`, or use paid mode |

---

## 11. External skills (optional)

Install globally for richer agent capabilities:

```bash
npx skills add video-db/skills
npx skills add https://github.com/pexoai/pexo-skills --skill pexo-agent
```

See README.md for more open-source pipeline repos.
