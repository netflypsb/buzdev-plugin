# agent-reach-internet

Use when an AI agent needs to read, search, or extract data from the internet across multiple platforms (web pages, YouTube, Twitter/X, Reddit, Bilibili, RSS, GitHub, LinkedIn). Provides zero-config and authenticated channel routing.

## Overview

Agent Reach (v1.5.0+) is a capability layer that installs and routes to the best available upstream tools for reading content from 14+ internet platforms. It does NOT scrape itself — it selects, installs, and health-checks backends (yt-dlp, Jina Reader, Exa, twitter-cli, etc.).

Key value proposition: platform backends change/break over time. Agent Reach tracks which backend is currently working and auto-routes to the next available one.

## Installation

```bash
# Do NOT install from PyPI (different package)
pip install git+https://github.com/Panniantong/Agent-Reach.git

# Or editable clone:
git clone https://github.com/Panniantong/Agent-Reach.git
cd Agent-Reach && pip install -e ".[all]"
```

## Architecture

Agent Reach is a glue layer, not a wrapper:

```
User Request → Agent Reach → Selects Backend → Agent Calls Backend Directly
                (routing)     (installs if needed)
```

After installation, agents call upstream tools directly. Agent Reach provides:
- `agent-reach doctor` — health check all channels
- `agent-reach install` — install missing backends
- Channel routing logic (which backend is active for each platform)

## Zero-Config Channels (No Auth Required)

These work immediately after install:

### Web Pages — Jina Reader

```bash
# Read any web page
curl -s "https://r.jina.ai/https://example.com/article"
```

Returns clean markdown. No API key. No rate limits for reasonable use.

### YouTube — Subtitles

```bash
# Extract subtitles (no API key)
yt-dlp --write-subs --sub-lang en --skip-download "https://youtube.com/watch?v=VIDEO_ID"

# Or just list available formats
yt-dlp --list-formats "VIDEO_URL"
```

Note: yt-dlp requires a JS runtime. Configure once:
```bash
mkdir -p ~/.config/yt-dlp
echo "--js-runtimes node" >> ~/.config/yt-dlp/config
```

### RSS/Atom Feeds

```python
import feedparser
feed = feedparser.parse("https://example.com/feed.xml")
for entry in feed.entries[:10]:
    print(entry.title, entry.link)
```

### V2EX — Forum

```python
import requests
r = requests.get("https://www.v2ex.com/api/topics/hot.json")
topics = r.json()
```

### Bilibili — Search + Video Info

```bash
# Search (no login required)
bili search "AI tutorial"
# Or: curl with Bilibili search API
```

### GitHub — Public Repos

```bash
# Read repo info
gh repo view owner/repo

# Read issues
gh issue list --repo owner/repo --limit 10

# Search repos
gh search repos "machine learning" --language python
```

Requires `gh` CLI. Authenticate with `gh auth login` for private repos.

## Authenticated Channels (Cookie/Login Required)

⚠️ **RISK: Account bans possible.** Platform detection of automated access may result in suspension. **Always use dedicated burner accounts**, never primary accounts.

### Twitter/X

**Status:** No zero-config path. Anonymous API endpoints blocked. Requires auth.

Options:
1. `twitter-cli` — CLI tool with auth tokens
2. `OpenCLI` — Desktop browser login state (reuses Chrome session)

Setup:
```bash
# Option 1: twitter-cli with auth tokens
pip install twitter-cli
export TWITTER_AUTH_TOKEN="your_token"
export TWITTER_CT0="your_ct0"
twitter search "keyword"

# Option 2: OpenCLI (desktop only, reuses Chrome)
# Install OpenCLI, login to Twitter in Chrome, then run:
opencli twitter search "keyword"
```

### Reddit

**Status:** Anonymous API blocked. Must authenticate.

Options:
1. `OpenCLI` — Desktop Chrome login state
2. `rdt-cli` — Cookie-based CLI

Setup:
```bash
# rdt-cli with cookies
pip install rdt-cli
export REDDIT_COOKIES="your_cookies"
rdt-cli search "keyword" --subreddit python
```

### Facebook

**Status:** Graph API heavily restricted. Browser login state required.

```bash
# OpenCLI only (desktop Chrome session)
opencli facebook search "page name"
```

### Instagram

**Status:** instaloader paths unstable. Browser login state required.

```bash
# OpenCLI (desktop Chrome session)
opencli instagram user username
```

### Xiaohongshu (小红书)

**Status:** Multiple backends available.

```bash
# Option 1: OpenCLI (desktop Chrome session)
opencli xiaohongshu search "keyword"

# Option 2: xiaohongshu-mcp (MCP server)
# Requires cookie export via Cookie-Editor browser extension
```

### LinkedIn

```bash
# mcp-server-linkedin
# Or Jina Reader for public pages only
curl -s "https://r.jina.ai/https://linkedin.com/in/username"
```

## Diagnostic Commands

```bash
# Full health check
agent-reach doctor

# Check specific channel
agent-reach doctor --channel twitter

# Install missing backends
agent-reach install --system

# Dry run (see what would happen)
agent-reach install --dry-run
```

## MCP Server

Agent Reach exposes a minimal MCP server for status checking:

```bash
python -m agent_reach.integrations.mcp_server
```

Tools exposed:
- `get_status` — Returns which channels are installed/active

Note: The MCP server does NOT perform actual reading. Agents call upstream tools directly.

## Backend Routing Table (Current as of 2026-09)

| Platform   | Primary Backend | Fallback(s)                     |
|------------|----------------|---------------------------------|
| Web        | Jina Reader    | —                               |
| YouTube    | yt-dlp         | —                               |
| Bilibili   | bili-cli       | OpenCLI → Search API            |
| Twitter/X  | twitter-cli    | OpenCLI → bird                  |
| Reddit     | OpenCLI        | rdt-cli                         |
| Facebook   | OpenCLI        | —                               |
| Instagram  | OpenCLI        | Graph API (Business/Creator)    |
| Xiaohongshu| OpenCLI        | xiaohongshu-mcp → xhs-cli       |
| LinkedIn   | mcp-server-li  | Jina Reader                     |
| GitHub     | gh CLI         | —                               |
| RSS        | feedparser     | —                               |
| Search     | Exa via mcporter| —                              |
| V2EX       | V2EX API       | —                               |

Backends change as platforms evolve. Run `agent-reach doctor` for current state.

## Integration with Scrapling

Agent Reach and Scrapling complement each other:

- **Agent Reach** → Social media platforms, video subtitles, search
- **Scrapling** → Web scraping, crawling, anti-bot, RAG pipelines

For a full internet data pipeline:
1. Use Agent Reach to discover URLs (search, social media)
2. Use Scrapling to fetch and extract structured data from those URLs

## Security Notes

- Cookie files stored at `~/.agent-reach/config.yaml` (chmod 600)
- Never upload cookie files to git or cloud storage
- Use dedicated burner accounts for cookie-auth platforms
- `agent-reach install` defaults to safe mode (no system changes without `--system`)

## Pitfalls

1. **Not on PyPI**
   - Install from GitHub directly: `pip install git+https://github.com/Panniantong/Agent-Reach.git`
   - PyPI package `agent-reach` is NOT this project

2. **Cookie-auth platforms = ban risk**
   - Twitter, Reddit, Facebook, Instagram, Xiaohongshu
   - Always use burner accounts
   - Check platform ToS before automated access

3. **OpenCLI requires desktop Chrome session**
   - Server/WSL environments cannot use OpenCLI
   - Use cookie-export backends (rdt-cli, xhs-cli) instead

4. **yt-dlp needs JS runtime**
   - Configure `~/.config/yt-dlp/config` with `--js-runtimes node`
   - Or install will fail silently

5. **MCP server is status-only**
   - Only exposes `get_status`, not actual reading tools
   - Agents must call upstream tools directly

## Templates

See `templates/` for:
- `internet_pipeline.py` — Combined Agent Reach + Scrapling pipeline

## Scripts

See `scripts/` for:
- `reach-check.py` — CLI wrapper for `agent-reach doctor`

## Dependencies

- Python 3.10+
- requests, feedparser, yt-dlp, loguru, rich, pyyaml
- Optional: playwright, browser-cookie3, mcp

## Resources

- GitHub: https://github.com/Panniantong/Agent-Reach
- Docs (Chinese): https://github.com/Panniantong/Agent-Reach/blob/main/README.md
- English docs: https://github.com/Panniantong/Agent-Reach/blob/main/docs/README_en.md
