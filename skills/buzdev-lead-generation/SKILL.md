---
name: buzdev-lead-generation
description: "Use when finding customers or leads for a business."
version: 1.0.1
category: business
author: Hermes Agent
license: MIT
metadata:
  tags: leads, outreach, b2b, b2c, prospect-list, customer-discovery, saas, csv
  related_skills: b2b-lead-harvesting, lead-generation, agent-reach-internet, web-social-search, buzdev-outreach
---

# BuzDev — Agent-Driven Lead Generation

A full lead generation workflow that an AI agent executes with planning, tool chaining, and adaptive search strategy. Designed for the BuzDev SaaS product (Vercel frontend → Hermes Cloud agent backend).

## When to Use

A business owner wants to find potential customers. They provide: business URL, industry, location, and optional context (competitors, ideal customer description, goal). The agent analyzes the business, generates customer profiles, searches across multiple APIs, scores leads, and exports a CSV.

Trigger phrases: "find leads for my business", "who should I sell to", "find customers for", "build a prospect list", "I need leads for".

## API Providers (Environment Variables)

All keys are in the Hermes Cloud instance environment (or `~/.hermes/.env` for local runs).

| Provider | Env Var | Purpose | Constraints |
|----------|---------|---------|-------------|
| SerpApi | `SERP_API_KEY` | Google Search API with location targeting | 250 free/mo, ~25s per query, use 30s timeout. Params: `engine=google`, `q`, `location`, `gl=my`, `hl=en`, `num=10` |
| Jina AI | `JINA_API_KEY` | URL → clean markdown (Reader API) | 500 RPM with key, 10M free tokens. Header: `Authorization: Bearer <key>` + `X-Return-Format: markdown`. URL: `https://r.jina.ai/<url>` |
| SocialCrawl | `SOCIALCRAWL_API_KEY` | 21-platform social search (TikTok, IG, FB, YouTube, X, LinkedIn, Reddit, etc.) | 100 free credits. Header: `x-api-key`. `/v1/search/everywhere` = fan-out. `/v1/prism/leads` = ranked people seeking alternatives (50cr). Check `/v1/credits/balance` (free) before expensive calls |
| SocialAPIs | `SOCIALAPIS_API_KEY` | FB/IG page metadata (email, phone, followers, rating, address) | 200 free/mo. Header: `x-api-token`. `/facebook/pages/details?link=<url>`, `/instagram/profile/details?link=<url>` |
| Hermes web_search | (built-in) | Keyless web search via Tool Gateway or FreeSerp | Use as SerpApi fallback or for quick lookups |
| Hermes web_extract | (built-in) | URL → markdown via Tool Gateway or Jina | Equivalent to Jina Reader when gateway is active |

## Workflow (5 Phases with User Gates)

The agent receives a structured input from the Vercel frontend:
```json
{
  "business_url": "https://example.com",
  "business_name": "Optional",
  "industry": "Education",
  "goal": "new_customers",
  "location": "Perlis, Kedah, Perak, Kelantan, Malaysia",
  "competitors": ["https://competitor1.com"],
  "ideal_customer_description": "Optional free-text description",
  "business_type": "b2b|b2c|mixed"
}
```

The agent executes phases 2-5 (phase 1 is the client-side wizard). Between phases, the frontend polls `/v1/runs/{run_id}` for status and presents user gates.

### Phase 2: Business Analysis & Customer Profile Generation

**Goal:** Understand the business deeply and generate 3-5 ideal customer profiles.

**Steps:**
1. Fetch the business website with Jina Reader (`https://r.jina.ai/<url>` with `Authorization: Bearer $JINA_API_KEY`). Extract: what they sell, target audience, value proposition, pricing signals, geographic focus.
2. If competitors are provided, fetch 1-2 competitor sites to understand market positioning.
3. Use `web_search` to find the industry context: market size, common customer types, pain points.
4. Synthesize all information and generate 3-5 customer profiles as JSON.

**Each profile must include:**
- `title` — short label (e.g., "B40 families seeking affordable Islamic diplomas")
- `description` — 2-3 sentence description with pain points and buying signals
- `search_keywords` — 3-5 Google search queries to find this profile (or institutions serving them)
- `social_keywords` — 2-3 social media search queries (for SocialCrawl)
- `industry` — the profile's industry
- `location_hint` — where to focus searches
- `business_type` — b2b, b2c, or institutional
- `feeder_strategy` — for B2C: what institutions/intermediaries reach this demographic

**B2B vs B2C profile generation is critical:**
- **B2B profiles describe the COMPANIES that buy.** Search keywords target companies directly: "marketing agencies Kuala Lumpur", "manufacturing companies Perak", "private hospitals Malaysia".
- **B2C profiles describe the END CUSTOMERS, but leads are the INSTITUTIONS that reach them.** A college targeting B40 families doesn't search for "B40 families" — it searches for feeder schools, tuition centers, community organizations, religious teachers, scholarship programs, and education fairs. The `feeder_strategy` field captures this.
- **Institutional profiles (schools, government, NGOs):** Search official registries first, Google second. Registry data has contact fields; Google finds SEO spam.

**Output JSON:**
```json
{
  "business_summary": "...",
  "value_proposition": "...",
  "target_market_analysis": "...",
  "customer_profiles": [ ... ]
}
```

**USER GATE:** Frontend displays profiles. User selects which to target, can add custom profiles (max 5 total), then clicks "Search for Leads."

### Phase 3: Lead Search (Batched, User-Gated)

**Goal:** Find real leads (companies, institutions, or individuals) matching selected profiles.

**Search strategy — tiered by reliability:**

1. **Official registries (B2B/institutional first).** Before any Google search, check if the sector has a government registry/directory. Use `web_search` to find it: `"<sector> registry Malaysia", "<sector> directory site:gov.my"`. Registries have structured contact data (name, address, phone, email, principal). If found, harvest the registry — this yields higher quality than Google. See b2b-lead-harvesting skill for the registry harvesting pattern.

**Malaysia-specific registry priority:**
- **Islamic education (tahfiz, madrasah, SRA, SMKA):** SIMPENI (`simpenti.jais.gov.my` or `simpenti.jakim.gov.my`) is the authoritative JAKIM registry. It lists ALL registered Islamic institutions with detail pages containing principal name, email, phone, address, district, and JAKIM registration code. A SIMPENI harvest routinely yields 100-200 leads per state. This is 10x more productive than searching Google for individual schools.
- **Government SMK/SMKA:** mySchool.daa-taa.com (MOE-affiliated) lists government secondary schools with contact info, but covers only government schools, not private Islamic institutions.
- **General business:** SSM company registry, industry association directories.
- **Healthcare:** Ministry of Health clinic directories.
- **Religious:** JAKIM/JAIPS state directories, MAIPs/MAIK/MAIWP portals.

**MCP search tools vs registry harvesting:** The buzdev-outreach MCP (FreeSerp-based web search) and SerpApi Google search excel at finding partner organizations, zakat bodies, and yayasan funders — but they are NOT effective for harvesting individual institution contact data. For school/institution-level leads, always use direct registry harvesting (SIMPENI, mySchool) with concurrent detail-page fetching. On the same test business, API-only search found 18 leads; the registry harvest found 166 with richer contact data.

2. **SerpApi Google search (primary web search).** For each selected profile, run 2-3 targeted Google searches:
   - Use `location` parameter when user specified a location: `location=Perlis, Malaysia`
   - Set `gl=my` (Malaysia) and `hl=en` for Malaysian results
   - Use 30s timeout per query (SerpApi scrapes Google in real-time, ~25s)
   - `num=10` results per query
   - **Query construction matters enormously.** Bad queries find social posts and news. Good queries find institutions:
     - ❌ `"B40 families Perlis education"` → finds news articles, Facebook posts, research papers
     - ✅ `"sekolah menengah Perlis"` → finds actual secondary schools
     - ❌ `"students looking for college Malaysia"` → finds blog posts
     - ✅ `"private college Malaysia contact email"` → finds college websites with contact pages
     - ❌ `"marketing agencies in Malaysia"` → finds listicle SEO spam
     - ✅ `"digital marketing agency Kuala Lumpur site:linkedin.com/company"` → finds actual companies
   - **Query templates by business type:**
     - B2B: `"<company type> <location>"`, `"<industry> companies <location> contact"`, `"<industry> <location> site:linkedin.com/company"`
     - B2C institutional: `"<institution type> <location>"`, `"<feeder institution> <location> contact"`, `"<sector> directory <location>"`
     - B2C social: use SocialCrawl instead of Google — social posts aren't useful leads

3. **SocialCrawl (social media search).** For each profile, run 1 SocialCrawl search:
   - `/v1/search/everywhere?query=<social_keywords>` — fan-out across 21 platforms
   - Use for finding social media presence of B2B leads, or for B2C finding communities/groups/pages related to the target demographic
   - Check `/v1/credits/balance` before expensive calls. `/v1/search/everywhere` costs ~20 credits.
   - For B2C: search for community pages, student groups, parent forums — these are the intermediaries, not the end customers
   - Results include platform, title, URL, content, author, engagement rate

4. **Jina Reader (content extraction).** For each promising search result (top 3-5 per query):
   - Fetch the page with Jina Reader: `https://r.jina.ai/<url>` with API key
   - **Keyless fallback:** If `Authorization: Bearer` returns 401, immediately fall back to keyless mode: `curl -s https://r.jina.ai/<url>` (20 RPM free, no auth header). Do not retry with the same key.
   - Extract: company name, email addresses (regex: `[\w.+-]+@[\w-]+\.[\w.-]+`), phone numbers (Malaysian format: `0[1-9][-\s]?\d{7,8}` or `\+60[-\s]?\d{8,10}`), social media links, address
   - **Skip social media post URLs** (facebook.com/posts, instagram.com/p/) — these are not lead pages. Look for official websites, about pages, contact pages.
   - **Prioritize about/contact pages**: if a search result links to an about or contact page, fetch that directly instead of the homepage.

**Batching rule (from user requirement):**
- Run 5 searches sequentially (SerpApi + SocialCrawl combined)
- After each batch of 5, STOP and report total leads found so far
- User decides: "Continue" (run 5 more) or "This is enough" (proceed to Phase 4)
- Cap at 20 leads for test stage

**Lead record structure:**
```json
{
  "company_name": "...",
  "website": "...",
  "title": "Page title or company name",
  "email": "extracted email or null",
  "all_emails": ["list of all emails found"],
  "phone": "extracted phone or null",
  "all_phones": ["list of all phones"],
  "facebook": "FB page URL or null",
  "instagram": "IG profile URL or null",
  "linkedin": "LinkedIn URL or null",
  "twitter": "Twitter/X URL or null",
  "industry": "inferred industry",
  "location": "inferred location",
  "source_query": "which search query found this",
  "source_platform": "google|socialcrawl|jina|registry",
  "snippet": "search snippet or page excerpt"
}
```

**Email/phone extraction rules:**
- Email regex: `[\w.+-]+@[\w-]+\.[\w.-]+` — strip trailing punctuation, exclude image extensions (.png, .jpg, .gif, .svg)
- Phone regex (Malaysian): `0[1-9][-\s]?\d{7,8}|\+60[-\s]?\d{8,10}` — do NOT extract Facebook IDs, date ranges, or timestamps as phone numbers
- Deduplicate emails across all sources
- Only keep leads with at least a company name + website (email/phone are bonus)

**USER GATE:** Frontend shows lead count + samples. User clicks "Continue" or "This is enough."

### Phase 4: Lead Scoring & Refinement

**Goal:** Score each lead 1-10, filter out irrelevant ones, enrich top candidates with social media data.

**Steps:**
1. For each lead, use the LLM to score based on:
   - Industry match (does this company/institution match the customer profile?)
   - Location match (is it in the target region?)
   - Contact availability (email = +2, phone = +1)
   - Website relevance (does the page content match what the business sells?)
   - Decision-maker accessibility (for B2B: can we identify a decision-maker?)
   - For B2C feeder institutions: does this institution actually serve the target demographic?

2. Score guide:
   - 8-10 (high): Strong match, has contact info, right industry/location
   - 5-7 (medium): Partial match, some signals of fit
   - 1-4 (low): Weak match, likely irrelevant — filter out

**Scoring nuance for education B2C:**
- SMKA (Islamic secondary schools) score +2 for Islamic colleges even without contact info — the demographic match is perfect.
- Schools in the same mukim/district as the client score +1 for proximity.
- Schools with MOE email (`reaXXXX@moe.edu.my`) are verified real institutions, not SEO spam.
- A lead with perfect demographic match but no contact is still medium priority (score 5-6); do not filter it out.

3. **Enrich top candidates with SocialAPIs** (5-10 leads max, 200 free calls/mo):
   - If a lead has a Facebook page URL: `GET /facebook/pages/details?link=<url>` with `x-api-token` header
   - If a lead has an Instagram URL: `GET /instagram/profile/details?link=<url>`
   - Adds: verified email, phone, address, followers, rating, business hours, category
   - This is especially valuable for small businesses that have social media but poor websites

4. **Deep research on top 5 leads:**
   - Fetch their about/contact pages with Jina Reader
   - Look for decision-maker names, titles, direct contact info
   - For B2B: identify the role that would buy (CEO, Marketing Director, Head of Operations)
   - For B2C institutional: identify the person who refers students (principal, counselor, head of program)

5. **Filter:** Remove leads scoring <5. Sort by score descending.

**Output JSON:**
```json
{
  "refined_count": 8,
  "high_priority": 5,
  "medium_priority": 3,
  "filtered_out": 12,
  "leads": [ { ...lead fields, "fit_score": 8, "priority": "high", "notes": "..." } ]
}
```

**USER GATE:** Frontend shows refined count + top leads. User clicks "Download CSV."

### Phase 5: CSV Export

**Goal:** Format leads as a downloadable CSV.

**CSV columns:**
```
Company Name, Website, Title, Email, All Emails, Phone, All Phones,
Facebook, Instagram, LinkedIn, Twitter, Industry, Location,
Fit Score, Priority, Followers (FB), Rating (FB), Address (FB),
Notes, Source Query, Source Platform
```

**Rules:**
- UTF-8 with BOM (`utf-8-sig`) so Excel opens cleanly
- Read back and verify row count before delivering
- NEVER include the client's own business in the CSV
- Deduplicate by company name (keep the row with the best contact info)

Use `scripts/build_leads_csv.py` from the b2b-lead-harvesting skill if the data is in JSON format — it handles cleaning, dedup, client-exclusion, and read-back verification.

## B2B vs B2C Strategy (Critical)

### B2B (Business-to-Business)

**Who the leads are:** The companies that buy from the client.

**Search approach:**
- SerpApi Google search for company types directly: `"marketing agencies Kuala Lumpur"`, `"manufacturing companies Perak"`
- LinkedIn company pages are excellent B2B leads: add `site:linkedin.com/company` to queries
- Official registries (SSM company registry, industry associations) for structured data
- SocialCrawl for LinkedIn/Twitter presence of companies
- SocialAPIs for FB/IG page details of companies
- Jina Reader on company websites → about/contact pages for decision-maker names and emails

**Scoring emphasis:**
- Company size and industry match
- Decision-maker identifiability (can we find a name + title + email?)
- Website quality (established companies have real websites)
- LinkedIn presence (active = more likely to respond)

### B2C (Business-to-Consumer)

**Who the leads are:** NOT the consumers themselves (they have no public contact data). The leads are the INSTITUTIONS and INTERMEDIARIES that reach the target demographic.

**The feeder chain concept:**
```
Client (e.g., college) → Feeder Institution (e.g., secondary school) → End Customer (e.g., student)
```

The agent searches for feeder institutions, not end customers. A college targeting B40 families in Perlis searches for:
- Secondary schools (sekolah menengah) in Perlis → principals, counselors
- Tuition centers in Perlis/Kedah → owners who refer students
- Mosques and religious centers → community programs, youth coordinators
- Community organizations (PERTIWI, MAIPs) → program managers
- Education fairs and exhibitions → organizers
- Scholarship programs → administrators who can refer students
- Social media communities (Facebook groups for SPM students, parent groups)

**Search approach:**
- SerpApi Google for institution types: `"sekolah menengah Perlis"`, `"tuition center Kedah"`, `"masjid Perlis"`
- Government registries (Ministry of Education school directory, JAKSIM, MAIPs)
- SocialCrawl for community groups, student forums, parent communities
- SocialAPIs for FB pages of schools, tuition centers, community organizations
- Jina Reader on institution websites → contact pages for principal/coordinator info

**Scoring emphasis:**
- Does this institution actually serve the target demographic?
- Geographic proximity to the client
- Accessibility of a contact person (principal, coordinator, owner)
- Existing referral relationships (do they already send students somewhere?)

### Mixed (B2B + B2C)

Some businesses serve both. Generate profiles for both segments, search both ways, and label each lead with `business_type` so the user can filter in the CSV.

## API Chaining Patterns

### Pattern 1: Registry → Detail Harvest (B2B/Institutional)
```
web_search("<sector> registry Malaysia site:gov.my")
  → find registry URL
  → Jina fetch registry list page
  → extract entity IDs + detail page URLs
  → Jina fetch each detail page (concurrent, max 16)
  → parse name, address, phone, email, principal
  → build_leads_csv.py → verified CSV
```
This is the highest-yield pattern. Registry data has structured contact fields that Google search results don't.

**Registry pagination:** Many registries paginate (e.g., `?page=2`, `?page=3`). The agent must discover and harvest ALL pages, not just the first. Look for pagination links or a total count indicator (e.g., "30 sekolah ditemui — Halaman 1 daripada 3").

### Pattern 2: Google → Website → Contact Page (B2B)
```
SerpApi search("<company type> <location>")
  → 10 results
  → filter: keep company websites, skip social posts/news/listicles
  → Jina fetch each website homepage
  → extract: company name, email, phone, social links
  → if no email on homepage: Jina fetch /contact or /about page
  → if has FB page: SocialAPIs enrichment
```

### Pattern 3: Social Discovery → Web Enrichment (B2C/Social)
```
SocialCrawl search("<social keywords>")
  → results across 21 platforms
  → filter: keep pages/groups/accounts that represent institutions or communities
  → for FB/IG URLs: SocialAPIs page details
  → for websites found in social profiles: Jina fetch for contact info
```

### Pattern 4: Competitor Analysis → Lookalike Search
```
Jina fetch competitor website → extract their customer types
  → SerpApi search for similar companies/institutions
  → SocialCrawl for competitor's social presence → find their followers/community
  → these are likely the same audience the client should target
```

## Agent Planning Guidelines

The agent should NOT blindly run all searches in sequence. It should PLAN based on the business type and profiles:

1. **Assess business type first.** Is this B2B, B2C, or institutional? This determines the entire search strategy.
2. **Check for registries before Google.** For education, healthcare, government, religious institutions — there are official registries. Finding and harvesting a registry is 10x more productive than 20 Google searches.
3. **Adapt based on results.** If the first 5 Google searches return mostly social posts and news, the agent should recognize this and switch strategy: try different query patterns, switch to registry search, or use SocialCrawl for community discovery.
4. **Quality over quantity.** 10 well-researched leads with emails and decision-maker names are worth more than 50 shallow results with just URLs. Spend Jina fetches on the most promising results.
- **Context management.** The agent has full Hermes context management — it can offload search results to files, summarize findings, and maintain a running list of leads without hitting context limits. Use `write_file` to save intermediate lead lists to `/tmp/buzdev_leads_<session>.json` after each batch.
- **Jina Reader keyless fallback.** If the `JINA_API_KEY` returns 401/403, immediately switch to keyless mode: `curl -s https://r.jina.ai/<url>` (no auth header, 20 RPM free). Do not retry with the same key.
6. **Dedup throughout.** Dedup by website URL and company name (lowercase) at every stage. Don't wait until the end.
7. **Exclude the client.** Always filter out the client's own website/name from results. Grep the final CSV for the client's name as a last gate.
8. **Batch gates are mandatory stops.** After each batch of 5 searches, STOP and present results to the user. Never auto-continue to the next batch, even if results look promising. The user must explicitly click "Continue" or "This is enough." This prevents runaway API usage and gives the user control over quality vs. quantity.

## Session State Management

- For Hermes Cloud runs: the agent maintains state via memory and files in `/tmp/buzdev_*`. Write intermediate lead lists to JSON after each batch so they survive context compression.
- For Vercel-only runs: use an in-memory `Map` keyed by `session_id` cookie, with TTL cleanup. Each phase POSTs the full state back to the frontend.
- When using `execute_code` to run Python that needs env vars: environment variables are available via `os.environ.get()` in the Hermes Cloud instance. All API keys are set in the instance's `~/.hermes/.env` and loaded into the execution context automatically.

## Common Pitfalls

- **Searching for the demographic instead of the institution.** A college wants B40 families, but you can't Google-search for families. Search for the schools, tuition centers, and community organizations that SERVE those families.
- **Social posts are not leads.** A Facebook post about a scholarship is not a lead. The organization that posted it might be. Always trace back to the institution, not the post.
- **Listicle SEO spam.** Queries like "best marketing agencies Malaysia" return listicles (blog posts ranking agencies). These are useless. Search for actual agencies directly, or use LinkedIn.
- **Phone number false positives.** Facebook IDs, date ranges, and timestamps can match loose phone regexes. Only accept numbers that look like real phone numbers (Malaysian: starts with 01, 03, 04, 05, 06, 07, 08, 09 or +60).
- **Email false positives.** Image file extensions (.png, .jpg) can match email regexes. Strip these. Example addresses (example@…) are not leads.
- **UTF-8 encoding.** CSVs without BOM garble in Excel. Always use `utf-8-sig` encoding.
- **Client in their own lead list.** The #1 embarrassment. Filter by name before export and grep the final CSV.
- **Jina Reader API key failure.** If `Authorization: Bearer` returns 401, immediately fall back to keyless mode: `curl -s https://r.jina.ai/<url>` (20 RPM free, no auth header). Do not retry with the same key.
- **Environment variables in execute_code.** Use `os.environ.get("KEY", "")` to access API keys. The Hermes Cloud instance loads keys from its `~/.hermes/.env` into the execution context automatically.
- **Registry pagination.** Many registries paginate (e.g., `?page=2`, `?page=3`). The agent must discover and harvest ALL pages, not just the first. Look for pagination links or a total count indicator.
- **SocialAPIs FB pages are private for Malaysian institutions.** Facebook pages of Malaysian schools (SMK, SMKA, madrasah) are typically set to private. SocialAPIs returns `PRIVATE_PAGE` error. Do not waste SocialAPIs credits on Malaysian school FB pages — the registry emails/phones are already sufficient contact info.
- **SerpApi timeout.** Each query takes ~25s (Google scraping). Use 30s timeout. Don't run more than 5 in a single batch.
- **Context window.** gpt-oss:120b has 128K context. 20 leads with full page content can consume 40K+ tokens. The agent should summarize page content (extract only contact info + key facts) rather than keeping full page text in context.

## Integration with Hermes Cloud

This skill is designed to run on a Hermes Cloud instance as the backend for the BuzDev SaaS frontend.

**Hermes Cloud instance configuration:**
- Model: any Nous Portal model (Claude, GPT, Gemini) or Ollama Cloud (gpt-oss:120b, kimi-k2.6)
- API server enabled: `API_SERVER_ENABLED=true`, `API_SERVER_KEY=<secret>`
- CORS: `API_SERVER_CORS_ORIGINS=https://buzdev.vercel.app` (or custom domain)
- Environment variables: `SERP_API_KEY`, `JINA_API_KEY`, `SOCIALCRAWL_API_KEY`, `SOCIALAPIS_API_KEY`
- Concurrency: `max_concurrent_runs=10` (default, handles 10 simultaneous customers)
- MCP servers: both transports supported — stdio (web-social-search, launched as subprocess) and HTTP (buzdev-outreach, Cloudflare Worker). For stdio servers, API keys must be explicitly passed via the `env:` config key — Hermes does NOT inherit the full shell environment for MCP subprocesses.

**Frontend (Vercel) integration:**
1. Frontend POSTs wizard data to Hermes `/v1/runs` (async submit)
2. Frontend polls `/v1/runs/{run_id}` every 3-5s for status
3. When `status=pending_phase2`, display profiles + user gate
4. User selects profiles → frontend POSTs selection to `/v1/runs/{run_id}/resume`
5. Agent continues to Phase 3 (search), polls again for batch results
6. User gates at each phase: continue/stop after search, confirm after refine, download CSV

## Architecture: Hermes Cloud + Vercel + Supabase

The BuzDev SaaS has three layers:

- **Vercel frontend** (thin): auth (email magic link), wizard, editable profile gate, dashboard, CSV download
- **Hermes Cloud agent** (heavy): runs the full lead generation pipeline autonomously using the BuzDev plugin
- **Supabase** (state): user accounts, jobs table with status flow (`analyzing → gated → queued → running → completed → failed`), CSV storage, email notifications

### Workflow: Option B (Single Gate)

1. User authenticates via email magic link (Supabase)
2. User submits business URL + description → Vercel creates job (status: `analyzing`) → submits to Hermes Cloud `POST /v1/runs`
3. Hermes agent fetches website, analyzes business, generates 3-5 customer profiles → returns to Vercel → stored in Supabase → displayed to user
4. **GATE**: User reviews/edits/adds/deletes profiles in the frontend → clicks "Start Search" → Vercel updates job (status: `queued`, profiles finalized) → submits to Hermes Cloud
5. Hermes agent runs full pipeline autonomously (no timeout): registry-first search → web search → email discovery → social search → scoring → CSV export
6. Agent completes → Vercel polls `GET /v1/runs/{run_id}` → stores CSV in Supabase Storage → Supabase trigger sends email notification
7. User returns (hours/days later) → dashboard shows completed job → downloads CSV

**Key design decisions:**
- Single gate (not 3) — the B2B/B2C + profile decision is the highest-leverage checkpoint; after that, the agent runs autonomously
- Job persists in Supabase — user can close browser and come back later
- Email notification on completion — user doesn't need to poll manually
- Queue management — Hermes Cloud has `max_concurrent_runs=10`; Supabase queue handles overflow with position display
- Free tier: 1 concurrent job per user (rate limiting)

## BuzDev Plugin (No Agentora Components)

The BuzDev plugin is a standalone Hermes Agent plugin, separate from the Agentora ecosystem. It contains only lead-generation components — no marketplace, credits, or publishing.

**MCP servers (2):**
1. **buzdev-outreach** — fork of customer-outreach MCP with Agentora credit gate and API key validation stripped out. All 8 tools (`buzdev_fetch_website`, `buzdev_search_web`, `buzdev_research_company`, `buzdev_search_for_leads`, `buzdev_discover_email`, `buzdev_search_social`, `buzdev_export_leads`, `buzdev_discover_extensions`) are free, no credit deduction. Deployed as a Cloudflare Worker.
2. **web-social-search** — stdio Python MCP (zero Agentora deps). 10 keyless tools: `read_webpage`, `search_web`, `search_hackernews`, `search_youtube`, `get_youtube_transcript`, `search_reddit`, `read_github`, `search_github`, `read_rss`, `agent_reach_status`. Deployed as a local subprocess on the Hermes Cloud instance.

**Hermes Cloud supports BOTH MCP transports:** stdio (`command` + `args`, launched as subprocess) and HTTP/StreamableHTTP (`url` + `headers`). For stdio servers, Hermes does NOT pass the full shell environment — API keys must be explicitly listed in the `env:` config key per server.

**Skills (6) bundled in the plugin:**
1. `buzdev-lead-generation` — this skill (main workflow)
2. `buzdev-outreach` — MCP tool documentation and workflow patterns
3. `b2b-lead-harvesting` — registry-first methodology, `build_leads_csv.py`
4. `lead-generation` — prospect sourcing, registry-mining reference, SerpApi local search reference
5. `web-social-search` — social search tool documentation
6. `agent-reach-internet` — Agent-Reach installation + 14-platform routing

**Agent-Reach** (github.com/Panniantong/Agent-Reach) is a separate open-source project, NOT part of Agentora. It routes to the best available backend per platform (Twitter, IG, FB, Xiaohongshu, Bilibili). The `agent_reach_status` tool in web-social-search checks if it is installed.

**What is EXCLUDED from the BuzDev plugin:**
- agentora-core MCP (26 tools) — content marketplace, credits, publishing
- Agentora credit gate — no `/credits/spend` calls, no API key validation against Agentora
- agentora-post skill, sme-outreach-mcp skill — Agentora-dependent

## Yield Lesson: Registry-First vs API-Only

A direct comparison on the same business (IPTIP, Perlis Islamic college):
- **API-only approach** (SerpApi + SocialCrawl + Jina, no registry): 18 leads, mostly government SMK schools with generic MOE emails, no principal names.
- **Registry-first approach** (SIMPENI harvest + b2b-lead-harvesting skill): 166 leads with principal names, school-specific emails, phones, addresses, JAKIM registration codes, boarding/gender info.

The registry-first approach is **~9x more productive** and yields richer data. The API-only approach is a fallback when no registry exists, not the primary strategy. Always check for an official registry before running SerpApi/SocialCrawl searches.

## References

- `b2b-lead-harvesting` skill — registry-first prospect lists, `build_leads_csv.py` script
- `lead-generation` skill — prospect sourcing methodology, registry-mining and SerpApi local search references
- `agent-reach-internet` skill — Agent-Reach 14-platform routing installation
- BuzDev project: `/root/projects/buzdev/` — Next.js frontend, API clients, PLAN.md
- BuzDev AGENTS.md: project context, credentials, tech stack details
- See `references/api-usage-guide.md` in this skill for detailed curl examples and query templates
- See `templates/system-prompt.md` in this skill for the Hermes Cloud agent system prompt
