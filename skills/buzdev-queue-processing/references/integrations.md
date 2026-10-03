# BuzDev Integrations Reference

## Buffer (social media scheduling)
- API key in `/opt/data/.buzdev/secrets.env` as `BUFFER_API_KEY` (chmod 600).
- Endpoint: `https://api.buffer.com/graphql` — GraphQL, auth via `Authorization: Bearer <key>`.
- IMPORTANT: the legacy REST API (api.bufferapp.com) rejects this key type; do not use it. REST retires 2027-02-01.
- Verified working 2026-10-02. Org: id `6aaa9a27c65a98142964f4b6`, name "My organization".
- Known ops: query channels/profiles, create updates (posts), schedules. Docs: https://developers.buffer.com (Quick Start + API Reference + interactive explorer).
- Purpose: automate BuzDev promo posts across connected social accounts.

## Credential locations
- `/opt/data/.buzdev/agent_secret.txt` — BUZDEV_AGENT_WEBHOOK_SECRET (for buzdev.vercel.app APIs)
- `/opt/data/.buzdev/secrets.env` — BUFFER_API_KEY
- Supabase keys + Vercel token: provided in-session; treat /opt/data/.buzdev/vercel_secrets.json as Vercel env snapshot
- GitHub PAT: fine-grained, expires 2026-12-31; has repo creation + push access
