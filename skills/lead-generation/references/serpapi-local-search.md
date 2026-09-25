# SerpApi Local Search — Google-powered prospect discovery

Use SerpApi (Google Search API) when no official registry covers the prospect
class, or when local geography is a key filter. SerpApi scrapes Google in
real-time and returns structured organic results with titles, links, and
snippets. The `location` parameter restricts results to a geographic area.

## API basics

- Endpoint: `https://serpapi.com/search.json?engine=google&q=QUERY&location=LOC&num=N&api_key=KEY`
- `location` format: `City,Country` (e.g. `Kuala+Lumpur,Malaysia`)
- `num`: results per page (max 100)
- Response: `organic_results[]` with `title`, `link`, `snippet`, `position`
- Free tier: 250 searches/mo (no credit card)
- Paid: Starter $25/mo for 1K searches

## Timeout and batching

Each SerpApi call takes 20-30s (real-time Google scraping). This is much
slower than Brave Search (~1-2s). Two strategies:

**Strategy A — parallelize (batch scripts, CLI tools):**
- Promise.all batches of 3-5 concurrent queries
- With 5 concurrent: 15 queries = ~75-125s
- Set per-search timeout to 30s

**Strategy B — sequential batches with user gates (SaaS products):**
- Run 5 sequential searches per function invocation
- After each batch, pause and show user the lead count so far
- User chooses: "Continue" (run 5 more) or "This is enough" (proceed)
- Each batch: ~125s SerpApi + ~30s Jina = ~155s, well within Vercel Hobby 300s
- Benefit: user controls API spend and can stop early when enough leads found

## Query patterns for lead generation

Generate 3 queries per customer profile, templated:
- `"<industry keyword>" <location>` — broad
- `"<industry keyword>" <location> contact email` — contact-focused
- `"<industry keyword>" <location> site:linkedin.com OR site:facebook.com` — social

For local businesses, always pass the `location` parameter — without it,
Google returns generic global results that miss local prospects.

## Post-search enrichment

1. Fetch top 3-5 organic results per query via Jina Reader (URL → markdown)
2. Regex-extract emails from page content: `[\w.+-]+@[\w-]+\.[\w.-]+`
3. Extract phone numbers if present
4. Deduplicate by URL across all queries
5. Cap at target lead count (e.g. 20 for test stage)

## Social media search (complementary)

For prospects with social presence, use SocialCrawl alongside SerpApi:

- Endpoint: `GET https://socialcrawl.dev/v1/search/everywhere?query=QUERY&lookback_days=7`
- Auth: `x-api-key: sc_...` header (NOT Bearer)
- The host redirects — use `redirect: "follow"` in fetch or `-L` in curl
- 100 free credits, 1 credit per basic call, never expire
- Covers 21 platforms (TikTok, IG, FB, YouTube, X, LinkedIn, Reddit, etc.)

For FB/IG page detail enrichment (email, phone, address, followers, rating):

- Endpoint: `GET https://api.socialapis.io/facebook/pages/details?link=URL`
- Auth: `x-api-token: ...` header
- 200 free calls/mo — call once per company, not per lead

## When to use SerpApi vs registry mining

| Scenario | Use |
|----------|-----|
| Regulated profession (schools, clinics, licensed traders) | Registry mining first |
| Local businesses without a registry (marketing agencies, cafes, retailers) | SerpApi with location |
| Mixed — some registry, some not | Registry for listed, SerpApi to fill gaps |

## Pitfalls

- SerpApi calls are SLOW (20-30s each) because they scrape Google in
  real-time. Never call sequentially in a serverless function — always
  parallelize in batches of 3-5.
- Without the `location` parameter, Google returns global SEO content
  (listicles, aggregators) instead of actual local businesses. Always pass
  `location=City,Country` for local prospect discovery.
- SerpApi free tier (250/mo) runs out fast with 3 queries × 5 profiles = 15
  per run. Track usage and upgrade to Starter ($25/mo) when approaching 250.
- Snippets often contain the business description but NOT contact info.
  Always fetch the full page via Jina Reader to extract emails/phones.