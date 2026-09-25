---
name: web-social-search
description: "Use when an AI agent needs to read, search, or extract data from the internet across multiple platforms (web pages, YouTube, Twitter/X, Reddit, GitHub, RSS, Hacker News). Provides zero-config keyless access and optional authenticated channel routing."
version: 1.0.0
author: BuzDev
license: MIT
metadata:
  tags: web-search social-media youtube reddit github rss internet mcp
  related_skills: buzdev-outreach, buzdev-lead-generation, b2b-lead-harvesting, agent-reach-internet
---

# Web & Social Search — Multi-Platform Internet Access

Provides zero-config web reading, search, and social media access via a stdio MCP server.
No external API keys required for core functionality. Optional keys unlock enhanced capabilities.

## MCP Server

- Transport: stdio (runs locally on the agent's machine)
- Command: `python3 ${PLUGIN_ROOT}/servers/web-social-search/server.py`
- No auth required — keyless by default

## Tools (10)

| Tool | What it does | Keyless? |
|---|---|---|
| **read_webpage** | Read any web page → clean markdown (Jina Reader) | Yes |
| **search_web** | Web search (FreeSerp + Jina fallback) | Yes |
| **search_hackernews** | Search HN stories (Algolia API) | Yes |
| **search_youtube** | Search YouTube videos (yt-dlp or Jina) | Yes |
| **get_youtube_transcript** | Extract subtitles from YouTube video (yt-dlp) | Yes (needs yt-dlp) |
| **search_reddit** | Search Reddit posts (Jina Reader) | Yes |
| **read_github** | Read repo info or specific file (gh CLI or Jina) | Yes (gh for private) |
| **search_github** | Search GitHub repos (gh CLI or Jina) | Yes |
| **read_rss** | Read RSS/Atom feed (feedparser or Jina) | Yes |
| **agent_reach_status** | Check Agent-Reach channel status | Yes |

## Zero-Config Channels (No Auth Required)

These work immediately after plugin install:

- **Web pages** — Jina Reader (free, no API key, no rate limits for reasonable use)
- **YouTube** — yt-dlp for subtitles and search (no API key, requires `pip install yt-dlp`)
- **Reddit** — Jina Reader on Reddit search (no login)
- **GitHub** — gh CLI for public repos (authenticate with `gh auth login` for private)
- **RSS/Atom** — feedparser (requires `pip install feedparser`)
- **Hacker News** — Algolia API (keyless, no auth)
- **Web search** — FreeSerp.ai (keyless, no auth)

## Optional Enhancements

| Enhancement | How | What it unlocks |
|---|---|---|
| `JINA_API_KEY` env var | Sign up at jina.ai | Higher rate limits on Reader + Search fallback |
| `pip install yt-dlp` | `pip install yt-dlp` | YouTube search + transcript extraction |
| `pip install feedparser` | `pip install feedparser` | Structured RSS parsing |
| `gh auth login` | GitHub CLI auth | Private repo access, issues, PRs |
| Agent-Reach install | `pip install git+https://github.com/Panniantong/Agent-Reach.git` | Twitter/X, Instagram, Facebook, Xiaohongshu, Bilibili, V2EX |

## Agent-Reach Integration

Agent-Reach (85k+ stars, MIT) is a capability layer that routes to the best available upstream tools for 14+ platforms. It doesn't scrape itself — it selects, installs, and health-checks backends.

Install for enhanced social media access:
```bash
pip install git+https://github.com/Panniantong/Agent-Reach.git
agent-reach install --system
agent-reach doctor  # check which channels are active
```

**Authenticated channels (burner accounts recommended):**
- Twitter/X — twitter-cli or OpenCLI
- Reddit — rdt-cli or OpenCLI
- Facebook — OpenCLI (desktop only)
- Instagram — OpenCLI (desktop only)
- Xiaohongshu — OpenCLI or xiaohongshu-mcp
- Bilibili — bili-cli

**Security:** Cookie files stored at `~/.agent-reach/config.yaml` (chmod 600). Use dedicated burner accounts. Check platform ToS before automated access.

## Pitfalls

1. **yt-dlp needs JS runtime** — configure `~/.config/yt-dlp/config` with `--js-runtimes node`
2. **OpenCLI requires desktop Chrome** — server/WSL environments cannot use it; use cookie-export backends instead
3. **Agent-Reach is NOT on PyPI** — install from GitHub directly
4. **Cookie-auth platforms = ban risk** — always use burner accounts, never primary accounts

## Backend Routing Table (Current as of 2026-09)

| Platform | Primary Backend | Fallback |
|---|---|---|
| Web | Jina Reader | — |
| YouTube | yt-dlp | Jina Reader |
| Reddit | Jina Reader | — |
| GitHub | gh CLI | Jina Reader |
| RSS | feedparser | Jina Reader |
| Hacker News | Algolia API | — |
| Web Search | FreeSerp.ai | Jina Search |
| Twitter/X | twitter-cli | OpenCLI |
| Facebook | OpenCLI | — |
| Instagram | OpenCLI | Graph API |
| Xiaohongshu | OpenCLI | xiaohongshu-mcp |
| Bilibili | bili-cli | OpenCLI |
| LinkedIn | mcp-server-li | Jina Reader |
| V2EX | V2EX API | — |