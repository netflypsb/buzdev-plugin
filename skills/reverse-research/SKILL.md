---
name: reverse-research
description: Use when the BuzDev agent needs free keyless social/ads/creator research before spending paid credits. Wraps the `reverse` CLI (github.com/ifccod/social-media-research-cli, MIT) — 26 platforms, 284 commands: LinkedIn companies/people/jobs, Meta/Microsoft/Pinterest/Snapchat ad libraries, TikTok Creative Center/Top Ads, Reddit/YouTube/Twitter/Instagram public search. Try this FIRST; fall back to buzdev-data paid tools on block/rate-limit.
version: 1.0.0
category: business
---

# reverse-research — Free Social & Ads Research Layer

`reverse` is a local-first Python CLI installed by `scripts/install.sh` at
`/opt/data/reverse/` (venv at `/opt/data/reverse/.venv`). No API keys. MIT.
Output: results → stdout, diagnostics → stderr. Machine catalog via
`reverse describe --format json`.

## Setup (once per machine, survives restarts at /opt/data)

```bash
bash <skill_dir>/scripts/install.sh
```

Verifies: `reverse list --json` prints a platform catalog. If install or a
command fails, SKIP this layer silently and use other tools — never block a job on it.

## Entry point

Always invoke as:
```bash
/opt/data/reverse/.venv/bin/reverse <platform> <command> [args] --output /tmp/reverse-out.json
```
`--output` writes JSON to a file (avoids huge stdout); read the file afterwards.
Use a normal shell timeout (60s) per call; these are subprocess calls, not daemons.

## Platforms that matter for BuzDev (use ONLY these unless the job clearly needs others)

| Platform | Key commands | BuzDev use |
|---|---|---|
| `linkedin` | `company`, `company-people`, `company-affiliates`, `company-jobs`, `company-posts`, `person`, `post`, `job-suggest` | Decision-maker enrichment — FIRST choice before paid linkedin_* tools |
| `facebook_ads` | `search-ads`, `page-ads`, `ad-details`, `search-suggest` | Warm B2B leads: businesses already spending on Meta ads |
| `microsoft_ads` | `search-advertisers`, `search-ads`, `get-ad` | Same for Bing ads |
| `pinterest_ads` | `search-ads`, `get-ad`, `search-pins` | B2C brands with ad spend |
| `snapchat_ads` | `search-ads`, `search-sponsored-content` | B2C brands with ad spend |
| `tiktok` | `search-users`, `search-general`, `trending-searchwords`, `creative-trending-hashtags`, `creative-top-ads`, `ads-keyword-ideas`, `one-creator-search` | B2C feeder research, creator/influencer leads, creative intel |
| `reddit` | `search`, `subreddit`, `user`, `user-posts` | Community/opinion research |
| `youtube` | `search`, `comments`, `channel-videos`, `search-suggest` | Content/competitor research |
| `twitter` | `search-posts`, `user`, `user-tweets`, `trending` | Local SME discovery |
| `instagram` | `profile`, `posts`, `post` | Local SME enrichment |

Ignore the China-ecosystem platforms (douyin, zhihu, weibo, wechat*, bilibili,
xiaohongshu, kuaishou, toutiao, xigua, lemon8, pipixia, netease_music) — not
relevant to BuzDev's markets unless the user's job explicitly targets them.

## When to use — the free-first ladder

1. **Enrichment (LinkedIn)**: for every org missing a decision-maker, try
   `reverse linkedin company-people --company <name>` BEFORE the paid
   `linkedin_company_detail` (5 cr) / `linkedin_company_search` (10 cr) tools.
   If reverse returns data → record it, save credits.
2. **Ads intelligence (new capability)**: for B2B jobs, run
   `reverse facebook_ads search-ads "<client niche keywords>"` and record
   advertisers as HIGH-fit leads (they have marketing budget). Note ad presence
   in the lead's `notes` field.
3. **Social research**: prefer Tavily include_domains first (already in the
   main prompt), use `reverse` when you need comments, user post history, or
   structured profile data.
4. **On failure** (429/blocked/`tab_unavailable`/`not_logged_in`/empty):
   fall straight to the buzdev-data paid tool for that gap. Do NOT retry more
   than once — reverse endpoints are reverse-engineered and rate-sensitive.

## Error semantics (from the CLI — treat failure as "unavailable", never as "no results")

- `429` + `Retry-After` → stop the current batch, move on
- `403` or `999` (LinkedIn anti-bot) → one retry, then fall back to paid tools.
  Expect anonymous LinkedIn to be blocked frequently from datacenter IPs —
  that is normal; the value is in ads libraries and other platforms.
- `tab_unavailable` / `not_logged_in` / `runtime_unavailable` → needs a Chrome
  session bridge; NOT available on the hosted agent. Skip these commands.
- Account-bound commands (session login, Creative Studio generation) — DO NOT USE.

## Field notes (verified 2026-10-03 live)

- Output envelope: most commands return top-level `items` (ads), `posts` (reddit),
  or a list (youtube). Read the result FILE, not just the wrapper's `count`.
- `facebook_ads search-ads "<query>"` is the strongest B2B command: returns
  active advertisers with page name/id, landing domains, WhatsApp links, delivery
  dates, like counts. Add `--country MY` when relevant.
- `reddit search "<query>"` returns `posts[]` with `title`/`permalink`/`subreddit`.
- `youtube search "<query>"` returns `items[]` (type video) with channel info.

# Output discipline

- Record the source URL in each lead's `source` field (same as any other tool).
- Ad-library leads: add `lead_type: "organization"`, note "active advertiser"
  in notes, score +1 fit (they have spend).
- Do not save media files; only URLs and metadata.

## Executor helper

`scripts/reverse_run.py` wraps the CLI with typed error output. Args pass
through verbatim (many commands take POSITIONAL args):
`python3 <skill_dir>/scripts/reverse_run.py facebook_ads search-ads klinik --country MY`
returns `{"ok":true,"count":N,"file":"/tmp/...json"}` on success or
`{"ok":false,"error_kind":"rate_limited|blocked|session_required|failed|not_installed"}`.
Read the result file for the actual data. On any `ok:false`, apply the fallback ladder.