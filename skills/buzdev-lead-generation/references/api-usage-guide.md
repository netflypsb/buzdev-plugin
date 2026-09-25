# BuzDev API Usage Guide

Detailed usage patterns for each API provider in the BuzDev workflow.

## SerpApi — Google Search API

**Endpoint:** `https://serpapi.com/search.json`
**Auth:** `api_key` query parameter
**Env var:** `SERP_API_KEY` (loaded via Hermes Cloud instance environment)

### Search with location targeting
Use the buzdev_search_web MCP tool, or call SerpApi from Python:
```python
import urllib.request, json, os

api_key = os.environ.get("SERP_API_KEY", "")
url = f"https://serpapi.com/search.json?engine=google&q=sekolah+menengah+Perlis&location=Perlis,+Malaysia&gl=my&hl=en&num=10&api_key={api_key}"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
response = urllib.request.urlopen(req, timeout=30)
data = json.loads(response.read())
```

### Query patterns by use case

| Use case | Query template | Example |
|----------|---------------|--------|
| B2B companies | `<company type> <location>` | `marketing agencies Kuala Lumpur` |
| B2B LinkedIn | `<industry> <location> site:linkedin.com/company` | `digital marketing Kuala Lumpur site:linkedin.com/company` |
| B2C institutions | `<institution type> <location>` | `sekolah menengah Perlis` |
| B2C intermediaries | `<intermediary type> <location> contact` | `tuition center Kedah contact` |
| Government registry | `<sector> registry <location> site:gov.my` | `sekolah registry Malaysia site:gov.my` |
| Contact pages | `<company type> <location> contact email` | `private college Malaysia contact email` |

### Response structure
```json
{
  "organic_results": [
    { "position": 1, "title": "...", "link": "...", "snippet": "..." }
  ],
  "search_information": { "total_results": "..." }
}
```

### Key rules
- Each query takes ~25s (Google real-time scraping). Always use 30s timeout.
- 250 free searches/month. Budget ~5 searches per profile × 5 profiles = 25 searches per run.
- `location` parameter is crucial for local businesses. Use city + country format.
- `gl=my` for Malaysia, `hl=en` for English results.
- If a query returns mostly social posts/news, reformulate with more specific institution types.

## Jina AI — Reader API

**Endpoint:** `https://r.jina.ai/<url>`
**Auth:** `Authorization: Bearer <key>` header + `X-Return-Format: markdown`
**Env var:** `JINA_API_KEY` (loaded via Hermes Cloud instance environment)

### Fetch a page as markdown
Use the buzdev_fetch_website MCP tool, or call from Python:
```python
import urllib.request, os

api_key = os.environ.get("JINA_API_KEY", "")
headers = {"Accept": "text/markdown"}
if api_key:
    headers["Authorization"] = f"Bearer {api_key}"
req = urllib.request.Request(f"https://r.jina.ai/https://example.com", headers=headers)
response = urllib.request.urlopen(req, timeout=15)
markdown = response.read().decode("utf-8")
```

### Keyless fallback (when API key fails)
When `Authorization` returns 401, immediately fall back to keyless mode (no auth header).
- No auth header needed
- 20 RPM free rate limit
- Use for simple, public pages only
- Returns identical clean markdown format

### Extract contact information from page
After fetching, apply regex extraction:
- Email: `[\w.+-]+@[\w-]+\.[\w.-]+` (strip trailing punctuation, exclude .png/.jpg/.gif/.svg)
- Malaysian phone: `0[1-9][-\s]?\d{7,8}|\+60[-\s]?\d{8,10}`
- Facebook URL: `facebook.com/[\w.-]+`
- Instagram URL: `instagram.com/[\w.-]+`
- LinkedIn URL: `linkedin.com/(company|in)/[\w.-]+`

### Batch fetch (concurrent)
Use ThreadPoolExecutor with max_workers=16, timeout=15s per request.
Fetch /about and /contact pages when homepage lacks email.

### Key rules
- 500 RPM with API key, 10M free tokens
- Skip social media post URLs (facebook.com/posts, instagram.com/p/) — they're not lead pages
- Prioritize about/contact pages over homepages for email extraction
- If page is a listicle ("Top 10 X in Y"), extract the companies listed but don't count the listicle itself as a lead
- **Always try keyless fallback on 401 before failing.** The keyless endpoint is reliable and free.

## SocialCrawl — 21-Platform Social Search

**Endpoint:** `https://socialcrawl.dev/v1/`
**Auth:** `x-api-key` header
**Env var:** `SOCIALCRAWL_API_KEY` (loaded via Hermes Cloud instance environment)

### Check balance (free)
```python
import urllib.request, os
api_key = os.environ.get("SOCIALCRAWL_API_KEY", "")
req = urllib.request.Request("https://socialcrawl.dev/v1/credits/balance",
    headers={"x-api-key": api_key})
response = urllib.request.urlopen(req, timeout=15)
```

### Search across all platforms
```python
req = urllib.request.Request(
    "https://socialcrawl.dev/v1/search/everywhere?query=digital+marketing+Malaysia&limit=20",
    headers={"x-api-key": api_key})
response = urllib.request.urlopen(req, timeout=20)
```

### Credit budget
- `/v1/credits/balance` — free, check before expensive calls
- `/v1/search/everywhere` — ~20 credits per call (5 calls max on free tier)
- `/v1/prism/leads` — 50 credits (use once per run for competitor analysis)
- Total budget per run: 2-3 everywhere searches (40-60 credits) + 1 prism (50 credits) = 90-110 credits
- With 100 free credits, use SocialCrawl strategically — max 1-2 searches per run

### Key rules
- Use `redirect: "follow"` in fetch (socialcrawl.dev redirects)
- For B2B: search for company names or industry + location
- For B2C: search for community groups, student forums, parent communities
- Filter results: keep pages/groups/accounts representing institutions, not individual posts

## SocialAPIs — Facebook & Instagram Page Details

**Endpoint:** `https://api.socialapis.io`
**Auth:** `x-api-token` header
**Env var:** `SOCIALAPIS_API_KEY` (loaded via Hermes Cloud instance environment)

### Facebook page details
```python
import urllib.request, os
api_key = os.environ.get("SOCIALAPIS_API_KEY", "")
req = urllib.request.Request(
    "https://api.socialapis.io/facebook/pages/details?link=https://facebook.com/somepage",
    headers={"x-api-token": api_key})
response = urllib.request.urlopen(req, timeout=15)
```

### Instagram profile details
```python
req = urllib.request.Request(
    "https://api.socialapis.io/instagram/profile/details?link=https://instagram.com/someprofile",
    headers={"x-api-token": api_key})
response = urllib.request.urlopen(req, timeout=15)
```

### Response fields
- `name`, `email`, `phone`, `address`, `followers_count`, `likes_count`
- `rating`, `website`, `category`, `business_hours`, `description`

### Key rules
- 200 free calls/month — budget ~10 enrichment calls per run
- Only call for leads that have a FB/IG URL (don't guess URLs)
- FB response may be an array at root; take first element
- This is the best source for small businesses with social media but poor websites

## Environment Variable Access

All API keys are loaded from the Hermes Cloud instance environment via `os.environ.get()`. Never read secrets files directly. The Hermes Cloud instance has keys set in its `~/.hermes/.env` file, which are available as environment variables in the agent's execution context.

```python
import os
api_key = os.environ.get("SERP_API_KEY", "")  # loaded from Hermes Cloud env
```

## Hermes Built-in Tools (when available via Tool Gateway)

If the Hermes Cloud instance has Nous Portal Tool Gateway enabled:

- `web_search(query)` — replaces SerpApi for simple searches (Firecrawl backend). No API key needed. Use for registry discovery and quick lookups.
- `web_extract(urls)` — replaces Jina Reader for page extraction. Returns clean markdown.
- Browser automation — for pages that Jina/SerpApi can't handle (JS-rendered content)

**Strategy:** Use Hermes built-in tools first (free, included in subscription). Fall back to SerpApi/Jina only when:
- Location-targeted Google search is needed (SerpApi's `location` param)
- Built-in web_search doesn't return local results
- Built-in web_extract fails on a specific page

## Budget Planning (Per Run)

| API | Free quota | Per-run usage | Cost |
|-----|-----------|-------------|------|
| SerpApi | 250/mo | 15-25 searches | $0 |
| Jina | 10M tokens | 10-20 fetches | $0 |
| SocialCrawl | 100 credits | 2-3 searches | $0 |
| SocialAPIs | 200/mo | 5-10 enrichment | $0 |
| Hermes web_search | included | 5-10 searches | $0 (Portal sub) |
| Hermes web_extract | included | 5-10 fetches | $0 (Portal sub) |
| LLM (Nous Portal) | varies | 3-5 calls/run | ~$0.02-0.05/run |

**Free tier supports ~10 runs/month** before SocialCrawl credits are exhausted.

## Registry-Specific Patterns

### Education: mySchool.daa-taa.com (Malaysia)
- URL pattern: `https://myschool.daa-taa.com/region/jpn-<state>_XX/<type>`
- Example: `https://myschool.daa-taa.com/region/jpn-perlis_77/Menengah`
- Pages are paginated: `?page=2`, `?page=3`, etc.
- Each school has a detail page: `https://myschool.daa-taa.com/school/<id>`
- Detail page contains: school name, address, phone, email (MOE format: `reaXXXX@moe.edu.my`)
- **Always harvest ALL pages.** Look for pagination links or a total count indicator.
- MOE emails (`reaXXXX@moe.edu.my`) are verified real institutions, not SEO spam.
- Score Islamic schools (SMKA) higher for Islamic college clients even without contact info.

### Registry harvesting workflow
```python
import urllib.request, re, concurrent.futures

# 1. Fetch list page
list_url = "https://myschool.daa-taa.com/region/jpn-perlis_77/Menengah"
req = urllib.request.Request(list_url, headers={"User-Agent": "Mozilla/5.0"})
response = urllib.request.urlopen(req, timeout=25)
html = response.read().decode("utf-8")

# 2. Extract detail URLs
detail_urls = re.findall(r'href="(/school/\d+)"', html)

# 3. Fetch all detail pages (concurrent, max 16)
def fetch_detail(path):
    url = f"https://myschool.daa-taa.com{path}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=25).read().decode("utf-8")

with concurrent.futures.ThreadPoolExecutor(max_workers=16) as ex:
    results = list(ex.map(fetch_detail, detail_urls))

# 4. Parse each detail page
for result in results:
    name = re.search(r'<title>(.*?)</title>', result).group(1)
    email = re.search(r'rea\d+@moe\.edu\.my', result)
    phone = re.search(r'04[-\s]?\d{7,8}', result)
    # add_to_leads(name, email, phone, source="registry")
```

### Education: SIMPENI (JAKIM Islamic Education Registry)
- **URL:** `https://simpeni.islam.gov.my/pages/semakan_sekolah_view.php?sek_id=<id>`
- **List endpoint:** POST to `https://simpeni.islam.gov.my/pages/semakan_sekolah.php` with form data (state filter, school type filter) returns HTML with `sek_id=<NNNN>` links per institution
- **Detail page fields:** JAKIM code, school name, address, postcode, state, district, principal name, phone, email, school type (tahfiz/madrasah/SRA/SMKA), boarding facility, gender, registration status
- **Yield:** 42 institutions in Perlis alone, 314 in Kedah — 166 total with 159 emails and 167 phones in a single harvest
- **This is 9x more productive than SerpApi+SocialCrawl combined** for Malaysian Islamic education leads
- **Parsing:** Detail pages use HTML tables with repeating labels across sections. Use row-wise `<tr>` parsing with first-match-wins, or label-to-label segmentation anchored on `Label :` (colon-space). See b2b-lead-harvesting skill step 5 for the parsing pattern.
- **eduagama.my** is a third-party aggregator of SIMPENI data — useful for discovering what exists, but always harvest from the official SIMPENI source for contact details.

### Registry discovery
Use `web_search` to find registries:
- `"sekolah menengah <state> registry"`
- `"<sector> directory <country> site:gov.<tld>"`
- `"senarai <institution type> <state>"` (Malay-language queries often find local registries)
- `"senarai sekolah menengah Perlis"` → found mySchool.daa-taa.com
- `"sekolah agama Malaysia SIMPENI JAKIM"` → found simpeni.islam.gov.my
