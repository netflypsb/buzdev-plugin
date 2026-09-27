---
name: buzdev-data
description: Use when the BuzDev agent needs commercial-grade web/social/lead data. 11 tools on buzdev-data-mcp backed by KeyAPI (Google Places/SERP), SocialCrawl (LinkedIn + 67 social platforms + web search), and Bright Data (SERP + Web Unlocker, needs zones). Per-job spend caps enforced worker-side.
version: 1.0.0
category: business
---

# buzdev-data — Commercial Data Layer

MCP server: `https://buzdev-data-mcp.netflypsb.workers.dev/mcp` (Bearer auth optional; no per-user keys yet).
Repo: `/root/projects/buzdev-data-mcp/` (worker `buzdev-data-mcp`, KV `BUZDEV_KV`).

## THE FIRST RULE — set a budget

Before ANY paid call on a user job:

```
set_job_budget(job_id="<buzdev job id>", cap_credits=200)   # default cap 200 if unset
```

Every paid tool accepts `job_id`. Spend is tracked in credits across ALL providers (1 credit ≈ $0.001).
When a call would exceed the cap the worker refuses it BEFORE hitting the paid API:
`{"success":false,"error":"job_budget_exhausted: used=N cap=M needed=K. ..."}`
On exhaustion: STOP searching, export what you have, tell the user the cap was hit.
Check anytime with `job_budget_status(job_id)`.

## Tools and exact costs

| Tool | Provider / endpoint | Cost | Use for |
|---|---|---|---|
| `maps_search(q, gl?, location?, hl?, page?)` | KeyAPI `/v1/google/places` | ~2cr | Local SME leads: title, address, **phone**, **website**, rating, cid |
| `serp_search(query, num_results?)` | Bright Data SERP → fallback SocialCrawl `web/search` | 1cr / 2cr | Wide-net discovery (companies, niches, directories) |
| `web_search(query, limit?)` | SocialCrawl `web/search` | 2cr | Cheap exploratory search |
| `linkedin_company_search(query, page?)` | SocialCrawl `linkedin/search/companies` | 10cr | B2B company discovery |
| `linkedin_company_by_domain(domain)` | SocialCrawl `linkedin/company/by-domain` | 5cr | LinkedIn page from website domain |
| `linkedin_company_detail(identifier)` | SocialCrawl `linkedin/company` | 5cr | Company info, size, jobs |
| `social_profile(platform, handle)` | SocialCrawl `/v1/{platform}/profile` | 1cr | TikTok/IG/YT/X/Reddit/GitHub... 67 platforms, one shape |
| `fetch_page(url, format?)` | Bright Data Unlocker → direct fetch | 1cr / 0 | Read a prospect's site; bypasses anti-bot when configured |
| `discover_email(url)` | internal regex over site + /contact pages | 0 | Emails + phones from a live site |
| `set_job_budget(job_id, cap_credits)` | internal | 0 | Set spend cap — ALWAYS FIRST |
| `job_budget_status(job_id)` | internal | 0 | Check remaining |

## Response envelope

Every tool returns `{success, provider, credits_used, data|results|places|content, job_id?, budget?{used,cap}}`.
Errors: `{success:false, error}` with `isError: true`.

## Provider facts and pitfalls

- **SocialCrawl**: unified envelope `{success, platform, data, credits_used, credits_remaining, cached}`. List endpoints return `data={items,next_cursor}` — pass `cursor` back, stop when `has_more:false`. Costs: standard 1cr, advanced 5cr, premium 10cr. Cache hits cost 0. Failures/empty refunded. Intermittent upstream 502s — retry once before giving up. Free runtime catalog: `/v1/utility/endpoints?search=term` and `/v1/utility/endpoint?id=<id>` (0cr) — use it instead of guessing parameters.
- **KeyAPI**: envelope `{code:0, message, data}`; `code!=0` is an error. Auth `Authorization: Bearer sk_live_...`. `maps_search` param is `q` (not `query`). ~2cr per call.
- **Bright Data (LIVE)**: Worker calls POST `https://api.brightdata.com/request` with `{zone, url, format}`. Products on the account (auto-provisioned by the Bright Data hosted MCP): `mcp_unlocker` (Web Unlocker — used for fetch_page fallback, accepts format json|raw only, returns raw HTML which the worker converts to text) and `mcp_browser` (Browser API, unused). NO SERP product yet — `serp_search` currently always falls back to SocialCrawl web/search; if a SERP API product is added on the Scrapers page, set var BRIGHTDATA_SERP_ZONE to its name. **Credit-saving mode:** fetch_page tries the FREE direct fetch first and only spends an Unlocker credit when the direct result is junk (bot-wall signatures: unusual traffic / just a moment / access denied / captcha — NOT "enable javascript"/"not redirected", which appear in legit Google/YT pages). All usage fits inside Bright Data's 5,000 free credits/month.
- **Bright Data hosted MCP (alternative direct connector)**: `https://mcp.brightdata.com/mcp?token=<BD_API_KEY>&groups=advanced_scraping,social,browser,business` — streamable-HTTP works at /mcp, SSE at /sse. Auto-provisions products and gives tools like search_engine + scrape_as_markdown. The token IS the BD API key (never commit the tokenized URL — key lives in .env.data-secrets / worker secrets).
- **fetch_page fallback**: when Bright Data is unconfigured it does a direct fetch with a browser UA. Jina Reader is NOT used (it 429s Cloudflare egress IPs).
- **discover_email**: checks `/`, `/contact`, `/contact-us`, `/about`, `/about-us`; filters noreply/example.com junk; returns `{emails[], phones[]}`. Phones can include false positives (year ranges) — sanity-check before export.

## Auth of record

Secrets on the worker: `KEYAPI_KEY` (sk_live key 1), `SOCIALCRAWL_KEY` (sc key 1), `BRIGHTDATA_KEY` (key 1). Keys 2 of each are spares. Local secret file: `/root/projects/buzdev-plugin/.env.data-secrets` (gitignored — NEVER commit or print).
