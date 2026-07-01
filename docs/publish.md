# Publish Phase — YouTube Upload via Rube MCP

## Prerequisites

1. Rube MCP configured: `https://rube.app/mcp` (see [mcp-setup.md](mcp-setup.md))
2. YouTube connection ACTIVE via `RUBE_MANAGE_CONNECTIONS`
3. `qa-report.md` shows **PASS**
4. Final video at `projects/<slug>/renders/final.mp4`
5. Thumbnail at `projects/<slug>/publish/thumbnail.png` (or `.jpg`)

## Agent workflow

### 1. Verify QA

```bash
python scripts/ffmpeg_qc.py check --project <slug>
```

Exit code must be 0.

### 2. Prepare metadata

From `plan/shot-list.json` → `metadata`:

- `youtube_title` (max 100 chars)
- `youtube_description` (max 5000 bytes)
- `tags` (max 500 chars total)

### 3. Upload via Rube MCP

Call `RUBE_SEARCH_TOOLS` first, then:

```
YOUTUBE_UPLOAD_VIDEO
  title: <youtube_title>
  description: <youtube_description>
  tags: [<tags>]
  categoryId: "28"   # Science & Technology (adjust as needed)
  privacyStatus: "unlisted"   # or "public" after review
  videoFilePath: { name, mimetype, s3key }  # per Rube schema
```

**Note:** Rube requires `videoFilePath` as an object with `s3key`, not a raw local path. The agent must upload the file through Rube's file handling per current tool schema.

### 4. Set thumbnail (optional)

```
YOUTUBE_UPDATE_THUMBNAIL
  videoId: <from upload response>
  thumbnailFilePath: { name, mimetype, s3key }
```

### 5. Record publish artifact

Save to `projects/<slug>/publish/youtube.json`:

```json
{
  "video_id": "abc123",
  "url": "https://youtube.com/watch?v=abc123",
  "privacy": "unlisted",
  "published_at": "2026-07-01T12:00:00Z"
}
```

## Thumbnail generation

```bash
# Placeholder SVG
python scripts/generate_thumbnail.py --project <slug>

# Or spec for imagegen
python scripts/generate_thumbnail.py --project <slug> --format json
```

Replace `publish/thumbnail.svg` with a 1280×720 PNG/JPG before upload.

## Post-publish

- Update video metadata with `YOUTUBE_UPDATE_VIDEO` if needed
- Add to playlist via `YOUTUBE_INSERT_PLAYLIST_ITEM` (optional)
