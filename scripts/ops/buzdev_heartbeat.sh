#!/bin/bash
# BuzDev heartbeat: call once a minute while a claimed job is being processed.
# Usage: buzdev_heartbeat.sh <job_id>
JOB_ID="$1"
[ -z "$JOB_ID" ] && { echo "usage: buzdev_heartbeat.sh <job_id>"; exit 1; }
SEC=$(cat /opt/data/.buzdev/agent_secret.txt)
curl -s -m 10 -X POST https://buzdev.vercel.app/api/webhook \
  -H "X-Webhook-Secret: $SEC" -H "Content-Type: application/json" \
  -d "{\"job_id\":\"$JOB_ID\",\"status\":\"heartbeat\"}" >/dev/null
echo "heartbeat sent: $JOB_ID"
