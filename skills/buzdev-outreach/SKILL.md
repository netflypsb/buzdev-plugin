---
name: buzdev-outreach
description: "Use when a business needs to find customers, partners, or collaborators, or research competitors. Provides lead discovery, email finding, and CSV export. Backed by the buzdev-outreach MCP server."
version: 1.0.0
author: BuzDev
license: MIT
metadata:
  tags: outreach leads customers partners email-discovery b2b b2c mcp
  related_skills: buzdev-lead-generation, b2b-lead-harvesting, web-social-search, lead-generation
---

# BuzDev Outreach — Lead Discovery & Email Outreach

Provides the full outreach workflow via MCP tools. The connected agent IS the intelligence — the MCP server provides only data fetching, web search, email discovery, and CSV export. All tools are free — no credits, no external auth required.

## MCP Server

- URL: `https://buzdev-outreach.netflypsb.workers.dev/mcp` (Cloudflare Worker)
- Local stdio: via `web-social-search` MCP in the same plugin
- Auth: Optional (if `BUZDEV_API_KEY` secret is set on the Worker, pass as `Authorization: Bearer <key>`)
- **No credit gate — all 8 tools are free**

## Tools (8)

### Lead Intelligence
1. **buzdev_fetch_website** — Fetch a URL as clean markdown (Jina Reader + direct-fetch fallback)
2. **buzdev_search_web** — Web search via FreeSerp (keyless) + DuckDuckGo fallback + Jina fallback
3. **buzdev_research_company** — Multi-query company research (news, products, team, financials, reviews)
4. **buzdev_search_for_leads** — Search web → scored lead list with page content and emails
5. **buzdev_discover_email** — Multi-method email discovery (Jina + direct fetch + contact pages + pattern guessing + web search)
6. **buzdev_search_social** — Social media search (HN Algolia, GitHub API, Reddit, YouTube)
7. **buzdev_export_leads** — CSV/JSON export (free, no credits)
8. **buzdev_discover_extensions** — Find complementary MCP servers and skills

## Core Workflows

### Lead Discovery Pipeline
```
buzdev_fetch_website(url) → buzdev_search_for_leads(analysis) → buzdev_discover_email(top leads) → buzdev_export_leads(leads, format="csv")
```
All steps are free. The agent is the intelligence — it analyzes, scores, and filters results.

### Partner/Channel Discovery
```
buzdev_fetch_website(url) → buzdev_search_for_leads(analysis, keywords=["partner", "channel"]) → buzdev_discover_email(top partners) → buzdev_export_leads(partners, format="csv")
```

### Competitor Research
```
buzdev_research_company(company_name) → [analyze results] → buzdev_search_web("competitors of " + company_name)
```

### Email-Only Discovery
```
buzdev_discover_email(url, company_name) → [pattern guessing + scraping]
buzdev_discover_email(url, company_name, person_name) → [personal email patterns]
```

## Registry-First Strategy

For regulated/listed niches (schools, clinics, licensed traders, associations), search for official registries BEFORE using `buzdev_search_web`. See the `b2b-lead-harvesting` skill for the full registry-first methodology.

The reliable yield order for institutional prospects:
1. **Official registries** (government, religious affairs, professional boards) — has structured contact fields
2. **Keyword search** (buzdev_search_web) — fills gaps the registry misses
3. **Social search** (buzdev_search_social) — finds individuals and discussions

## B2C Feeder Chain

For B2C businesses (education, healthcare, consumer services), the prospects are the **institutions that feed end customers** — not the end consumers directly. Consumers rarely have public contact records.

Example: For a college → search for feeder schools, not students. The school counselor is the gatekeeper to the students.

## After Completing Core Work

Call `buzdev_discover_extensions(task)` to find complementary tools:
- `render_pitch_deck` → deckpipe, SlidesGPT, python-pptx
- `send_outreach_emails` → reachout_mcp, Resend
- `verify_emails` → Reacher
- `competitive_intelligence` → Agent-Reach, Scrapling
- `social_engagement` → BrowserSkill