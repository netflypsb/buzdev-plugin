---
name: buzdev-support-email
description: Use when a BuzDev support email arrives or needs a reply.
version: 1.0.0
author: hermes-agent
license: MIT
metadata:
  hermes:
    tags: [buzdev, email, support]
    related_skills: [buzdev-queue-processing]
---

## When to Use
When the support-watch cronjob delivers a new inbound email, or the user asks to reply to a BuzDev support thread.

# BuzDev Support Email

Cronjob `buzdev-support-email-watch` (id 7b5ab4528fc1, every 5m, monitor `openmail_check.py`) lists NEW inbound emails from support@buzdev.vercel.app users and delivers to Telegram (origin).

## Rules
1. **The user personally decides communication-sensitive replies.** For each new email: summarize it to the Telegram DM and propose a draft reply. Never send without the user's approval of content. If the user dictates a reply verbatim, send it as dictated (fix only obvious typos, flag anything changed).
2. Send via OpenMail using the threadId from the monitor output. Credentials: `/opt/data/.buzdev/openmail.env` and `/opt/data/.buzdev/openmail_support.env` (chmod 600).
3. Keep replies professional, short, on behalf of BuzDev support. Never promise refunds, SLAs, or pricing changes without explicit user instruction.
4. Account-bound issues (unlock/payment not applied): verify in Supabase (`bi_packs`, `jobs`, unlocks) before replying; quote the actual job/user state.
5. Log sent replies back to the user with threadId so the thread stays traceable.
