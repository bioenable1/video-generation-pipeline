# Pilot Run — Iriuniverse 2 Launch

**Status:** Scaffold complete — ready for API keys and asset generation.

## Completed steps

| Step | Command | Output |
|------|---------|--------|
| Project bootstrap | `new_project.py` | `projects/iriuniverse2-launch/` |
| Research | `research.py --merge-comments` | `research/competitor-analysis.md`, `audience-insights.md` |
| Validation | `validate_shot_list.py` | Passes after duration fix (90s) |
| Content plan | `plan_generator.py` | `plan/content-plan.html` |
| Script | `generate_script.py` | `script.md`, `vo-segments.json` |
| VO dry-run | `generate_voiceover.py --dry-run` | 6 segments ready |
| VEED assemble | `veed_client.py assemble` | `renders/assemble-payload.json` |
| Thumbnail | `generate_thumbnail.py` | `publish/thumbnail.svg` |

## Pending (requires API keys)

1. Copy `.env.example` → `.env` and set keys
2. `pexels_fetch.py --project iriuniverse2-launch --all`
3. `generate_voiceover.py --project iriuniverse2-launch`
4. Generate `assets/images/s04.png` via imagegen skill
5. `veed_client.py assemble` with `VEED_API_KEY` or `ffmpeg_qc.py concat` for draft
6. `ffmpeg_qc.py check --project iriuniverse2-launch`
7. YouTube upload via Rube MCP — see `docs/publish.md`

## Reference asset

Product clip from `reference/BioEnable-Videos/kit and scanners/Iriuniverse2_-VEED.mp4` mapped in manifest for scene s02.

## Next agent prompt

```
Continue the Iriuniverse 2 pilot:
1. Fetch Pexels stock for s01, s03, s05
2. Generate ElevenLabs VO for all scenes
3. Concat draft with ffmpeg_qc.py concat
4. Run QC check
```
