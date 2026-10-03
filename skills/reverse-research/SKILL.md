---
name: reverse-research
description: Use when the BuzDev agent needs free keyless ads/creator research before spending paid credits. Wraps the `reverse` CLI (github.com/ifccod/social-media-research-cli, MIT). PRODUCTION WHITELIST: microsoft_ads + youtube ONLY — the commands live-verified to survive a datacenter-IP host. All other platforms (facebook_ads, reddit, linkedin, twitter, instagram, threads) are DROPPED by the managed-sources policy: they are IP-blocked or gray-zone anonymous scraping. Try these two FIRST; on failure skip silently, never as "no results".
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

## Production platform whitelist (user-set managed-sources policy)

| Platform | Key commands | BuzDev use |
|---|---|---|
| `microsoft_ads` | `search-advertisers`, `search-ads`, `get-ad` | Warm B2B leads: businesses spending on Bing ads (official anonymous Ad Library API — survives datacenter IPs) |
| `youtube` | `search`, `comments`, `channel-videos`, `search-suggest` | Channel/community discovery (official endpoints) |

DROPPED (live-verified IP-blocked from the hosted agent's datacenter IP, or gray-zone anonymous scraping): `facebook_ads` (rate_limited), `reddit` (403), `linkedin` (HTTP 999), `twitter`, `instagram`, `threads`, and the entire China ecosystem. Do not re-add them — the block is the steady state, not an outage. Their data comes from managed sources instead: Tavily include_domains, web-social-search MCP, and buzdev-data SocialCrawl tools.

## When to use — the free-first ladder

1. **Advertiser intelligence**: `reverse microsoft_ads search-ads "<niche keywords>"` — record advertisers as warm leads (marketing budget), note "active advertiser", +1 fit.
2. **Channel/community discovery**: `reverse youtube search "<niche>"` for channels and communities; on any {"ok":false} skip reverse for the rest of the job.
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