#!/usr/bin/env python3
"""Check unnotified ops_events (requeues / hard failures) and print ALERT lines.
Called by buzdev_poll.sh each cycle; marks events notified after printing."""
import json, os, urllib.request

# --- Script integrity check (added after Oct 3 outage): the poll cron is
# sandboxed to /opt/data/scripts — a symlink out of that dir makes the cron
# fail silently ("Blocked: script path resolves outside the scripts dir"),
# which killed all polling on Oct 3. Alert if any cron script is a symlink.
for f in ('buzdev_poll.sh', 'buzdev_heartbeat.sh', 'buzdev_ops_check.py'):
    p = os.path.join('/opt/data/scripts', f)
    if os.path.islink(p):
        print(f"OPS_ALERT|job=infra|event=cron_script_symlink|attempt=0|at=now|{f} is a symlink — cron will be BLOCKED; copy the real file from buzdev-plugin/scripts/ops/")

env = {}
for line in open('/opt/data/.buzdev/supabase.env'):
    line = line.strip()
    if '=' in line and not line.startswith('#'):
        k, v = line.split('=', 1)
        env[k] = v
url = env.get('SUPABASE_URL')
key = env.get('SUPABASE_SERVICE_ROLE_KEY') or env.get('SERVICE_ROLE_KEY')
if not url or not key:
    raise SystemExit(0)  # silently skip if creds missing

def rest(path, method='GET', body=None):
    req = urllib.request.Request(url + path,
        data=json.dumps(body).encode() if body else None, method=method,
        headers={'apikey': key, 'Authorization': 'Bearer ' + key,
                 'Content-Type': 'application/json', 'Prefer': 'return=representation'})
    return json.loads(urllib.request.urlopen(req, timeout=20).read())

try:
    events = rest('/rest/v1/ops_events?notified=eq.false&select=id,job_id,event,attempt,created_at&order=created_at.desc&limit=10')
except Exception:
    raise SystemExit(0)  # table missing or transient error — never break the poll

for e in events:
    kind = e['event']
    detail = 'requeued for retry' if kind == 'requeued' else 'FAILED after max retries — user sees error'
    print(f"OPS_ALERT|job={e['job_id']}|event={kind}|attempt={e['attempt']}|at={e['created_at']}|{detail}")

if events:
    # mark all fetched events notified by id
    try:
        ids = [e['id'] for e in events]
        req = urllib.request.Request(url + '/rest/v1/ops_events?id=in.(' + ','.join(map(str, ids)) + ')',
            data=json.dumps({'notified': True}).encode(), method='PATCH',
            headers={'apikey': key, 'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
        urllib.request.urlopen(req, timeout=20).read()
    except Exception:
        pass
