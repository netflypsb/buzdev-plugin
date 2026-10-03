#!/bin/bash
# BuzDev poll script: GET /api/poll-pending + ops_events alert check.
# "NO_PENDING" => agent skipped by monitor UNLESS OPS_ALERT lines are present.
SEC=$(cat /opt/data/.buzdev/agent_secret.txt)
OUT=$(curl -s -m 25 https://buzdev.vercel.app/api/poll-pending -H "X-Webhook-Secret: $SEC")
if echo "$OUT" | grep -q '"pending":true'; then
  echo "$OUT"
else
  echo "NO_PENDING"
fi
python3 /opt/data/buzdev-plugin/scripts/ops/buzdev_ops_check.py || true
