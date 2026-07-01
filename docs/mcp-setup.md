# MCP Setup for Video Generation Pipeline

Configure these MCP servers in Cursor (Settings → MCP) or in `.cursor/mcp.json`.

## Required

### Rube MCP (YouTube search, comments, upload)

```json
{
  "mcpServers": {
    "rube": {
      "url": "https://rube.app/mcp"
    }
  }
}
```

Complete YouTube OAuth when prompted via `RUBE_MANAGE_CONNECTIONS`.

### Pexels MCP (stock video)

Clone and run [pexels-mcp-server](https://github.com/CaullenOmdahl/pexels-mcp-server):

```json
{
  "mcpServers": {
    "pexels": {
      "command": "npx",
      "args": ["-y", "pexels-mcp-server"],
      "env": {
        "PEXELS_API_KEY": "your_key_here"
      }
    }
  }
}
```

Get a free key at https://www.pexels.com/api/

## Optional

### VideoDB

Install the skill: `npx skills add video-db/skills`

Set `VIDEO_DB_API_KEY` in `.env`. Use the VideoDB Python SDK via `scripts/` or the global videodb skill.

### Memories.ai (deep video research)

For the `seek-and-analyze-video` skill. Set `MEMORIES_AI_API_KEY` in `.env`.

## REST APIs (no MCP — use scripts/)

| Service | Env var | Docs |
|---------|---------|------|
| VEED Editing | `VEED_API_KEY` | https://www.veed.io/api |
| fal.ai (Fabric, Lipsync) | `FAL_KEY` | https://fal.ai |
| ElevenLabs | `ELEVENLABS_API_KEY` | https://elevenlabs.io/docs |

Copy `.env.example` to `.env` and fill in all keys before running asset or edit phases.
