# BuzDev Plugin — AI-Powered Customer Outreach

A Hermes Agent plugin for lead generation, customer outreach, and business development. No external auth required for core functionality.

## Components

### MCP Servers (2)

| Server | Transport | Tools | Description |
|--------|-----------|-------|-------------|
| **buzdev-outreach** | HTTP (Cloudflare Worker) | 8 | Lead discovery, email finding, CSV export |
| **web-social-search** | stdio (Python) | 10 | Keyless web reading, search, social media access |

### Skills (6)

| Skill | Description |
|-------|-------------|
| **buzdev-lead-generation** | Main workflow: 5-phase agent-driven lead generation with B2B/B2C strategy |
| **buzdev-outreach** | MCP tool documentation and workflow patterns for the 8 outreach tools |
| **b2b-lead-harvesting** | Registry-first prospect list methodology (found 166 leads in one run) |
| **lead-generation** | Prospect sourcing & qualification with registry-mining and SerpApi references |
| **web-social-search** | Multi-platform internet access (14+ platforms, keyless) |
| **agent-reach-internet** | Agent-Reach installation and platform routing guide |

## Key Features

- **No auth required** — all tools work keyless (FreeSerp, DuckDuckGo, HN Algolia, GitHub API, Jina Reader free tier)
- **No credit gate** — all 8 outreach tools are free, including CSV export
- **Registry-first strategy** — finds official registries before generic web search
- **B2C feeder chain** — for B2C businesses, searches for feeder institutions, not end consumers
- **Agent-Reach integration** — optional enhanced social media access (14+ platforms)
- **Agentora-independent** — zero dependencies on the Agentora ecosystem

## Installation

```bash
# Clone or copy to Hermes plugins directory
cp -r buzdev-plugin /root/.hermes/plugins/

# For the buzdev-outreach Worker:
cd buzdev-plugin
npm install
wrangler deploy

# For web-social-search stdio (no install needed — pure Python stdlib)
python3 servers/web-social-search/server.py  # test locally
```

## Architecture

```
Agent (Hermes Cloud or local)
  ├─ buzdev-outreach MCP (HTTP) ── Cloudflare Worker
  │   ├─ buzdev_fetch_website
  │   ├─ buzdev_search_web
  │   ├─ buzdev_research_company
  │   ├─ buzdev_search_for_leads
  │   ├─ buzdev_discover_email
  │   ├─ buzdev_search_social
  │   ├─ buzdev_export_leads
  │   └─ buzdev_discover_extensions
  │
  ├─ web-social-search MCP (stdio) ── Python subprocess
  │   ├─ read_webpage
  │   ├─ search_web
  │   ├─ search_hackernews
  │   ├─ search_youtube
  │   ├─ get_youtube_transcript
  │   ├─ search_reddit
  │   ├─ read_github
  │   ├─ search_github
  │   ├─ read_rss
  │   └─ agent_reach_status
  │
  └─ Skills (loaded contextually)
      ├─ buzdev-lead-generation (5-phase workflow)
      ├─ buzdev-outreach (tool docs)
      ├─ b2b-lead-harvesting (registry-first)
      ├─ lead-generation (registry mining + SerpApi)
      ├─ web-social-search (platform docs)
      └─ agent-reach-internet (Agent-Reach install)
```

## Origin

Forked from the [Agentora Plugin](https://github.com/netflypsb/agentora-plugin) with all Agentora dependencies removed:
- Removed `agentora-core` MCP (26 marketplace tools)
- Removed Agentora credit gate from `sme_export_leads` → `buzdev_export_leads` (free)
- Removed Agentora API key validation (optional `BUZDEV_API_KEY` instead)
- Renamed tools: `sme_*` → `buzdev_*`
- Kept all tool implementations intact (same logic, same backends)
- Kept web-social-search server.py as-is (was already agentora-independent)

## License

MIT