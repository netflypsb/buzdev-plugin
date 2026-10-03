---
name: buzdev-development
description: Use when developing or deploying BuzDev app changes.
version: 1.0.0
author: hermes-agent
license: MIT
metadata:
  hermes:
    tags: [buzdev, deployment, supabase, nextjs]
    related_skills: [buzdev-queue-processing]
---

## When to Use
Any task that modifies the BuzDev SaaS (Next.js app on Vercel + Supabase) — product features, schema changes, paywall/billing logic. For processing queued jobs, use `buzdev-queue-processing` instead.

# BuzDev Development & Deployment

## Credentials (all in /opt/data/.buzdev/, chmod 600)
- `github.env` — GITHUB_USER / GITHUB_TOKEN (fine-grained PAT; user netflypsb, repo netflypsb/buzdev, branch main, admin perms)
- `supabase.env` — SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_ANON_KEY
- `stripe.env` — STRIPE_PUBLISHABLE_KEY, STRIPE_SECRET_KEY (live keys)
- `vercel.env` — VERCEL_TOKEN (check expiry before trusting; the user supplies a fresh one in chat when invalid)
- `agent_secret.txt` — X-Webhook-Secret for buzdev.vercel.app endpoints

Never echo token values into chat output; read them from these files at runtime.

## Procedure for a code change
1. Working tree: /opt/data/workspace/buzdev_impl (Next app root). Clone fresh for git ops:
   `git clone https://x-access-token:$GITHUB_TOKEN@github.com/netflypsb/buzdev.git buzdev_git`
   Plain https URLs with a username prompt fail headless — always inline the token as x-access-token.
2. Implement changes; keep the repo layout as-is (`src/` contains the Next app, package.json inside src/) — reshuffling top-level dirs risks breaking Vercel's root-directory build config.
3. Verify before push: `npm install` then `npm run build` in the Next app root. tsc alone misses Next's generated types; the full build is the gate.
4. Commit and push to main: repo git identity is not configured globally — run `git config user.email dev@netflypsb && git config user.name netflypsb` in the repo before the first commit.
5. Deploy via POST https://api.vercel.com/v13/deployments (Bearer $VERCEL_TOKEN, from /opt/data/.buzdev/vercel.env) with body `{"name":"buzdev","target":"production","gitSource":{...}}` — WITHOUT `target:"production"` the deployment builds as a preview and NEVER serves buzdev.vercel.app (verified Oct 2). Push first: deploying an unpushed sha fails with incorrect_git_source_info. Poll GET /v13/deployments/{id} until readyState READY/ERROR. After any deploy, verify the LIVE API behavior with a probe request — a READY deployment is not proof the new code is serving (check the old-path response signature too).
6. Repo layout: Oct 2 the remote was force-pushed (squash) to a flattened layout that broke the Vercel build (project Root Directory = `src`, so package.json must live in repo `src/`). Restored layout: repo/src = Next app root (package.json, tsconfig `@/* → ./src/*`), repo/src/src = app code (app/, lib/), repo/src/src/supabase/migrations. Keep this layout; buzdev_impl mirrors it (impl/src = app root).
7. buzdev_impl can drift stale vs origin (it missed the socialUrl commit once) — always diff impl files against fresh `git show origin/main:<path>` before copying impl → repo; overwrite is fine only when the impl version is a strict superset of HEAD.

## Supabase migrations
- Inspect schema via the OpenAPI root (`GET /rest/v1/` returns definitions with every table/column) — compare against the intended schema before and after changes.
- DDL cannot run via REST: write the SQL to supabase/migrations/<topic>.sql in the repo and have the user paste it into the Supabase SQL editor. Keep migrations additive (create table if not exists, add column if not exists, drop policy if exists + create) so they're safe to run while the site is live.
- After the user runs a migration, verify by re-fetching the OpenAPI root — the user saying 'done' is not verification.
- Set RLS with read-only own-row policies; do all mutations through server routes with the service-role key.

## App architecture notes
- Auth: Supabase email auth; user_id on jobs/leads. Jobs created via POST /api/analyze; leads listed via GET /api/leads; Stripe per-request $10 unlock sets jobs.unlocked.
- Leads dedupe across jobs via leads.master_lead_id → master_leads (matched on website, else name+address); reveal/dedupe logic uses it.
- Paywall design (agreed with user): 1 request/day, 3 full reveals from a credit balance (+3 per purchase, 72h expiry, cap 6 live grants), shaded previews of locked contact fields, card-on-file (Stripe Setup Session) after first request. Full spec: /opt/data/workspace/buzdev_freemium_spec.md.
- Next.js 16: the repo's AGENTS.md warns APIs may differ from training data — read node_modules/next/dist/docs/ before writing unfamiliar Next code.

## Pitfalls
- Source recovered from a Vercel deploy may be stored wrapped as {"data": "<base64>"} JSON per file — decode to real files before editing, and push real sources to replace wrapped ones.
- Binary files (favicons etc.) survive snapshot exports corrupted: if `npm run build` fails decoding an image, delete or regenerate it rather than debugging the bytes.
- write_file on a file seen only via grep/partial read gets refused — read_file the full target first.
- The dashboard (src/app/page.tsx) renders raw DB values into interactive elements: before reporting a display fix, pull real lead rows from Supabase and check the rendered output (e.g. social links) end to end — the leads table stores a bare `social_handle`, so any link built without its `social_platform` opens a dead relative URL on the site itself. A `socialUrl(platform, handle)` helper at the top of page.tsx does this mapping; reuse it for any new social-field rendering.
