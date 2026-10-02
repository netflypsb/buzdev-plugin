#!/usr/bin/env python3
"""Thin executor for the reverse-research skill.

Usage: reverse_run.py <platform> <command> [key=value args...] [--raw]

Wraps /opt/data/reverse/.venv/bin/reverse with:
- key=value args converted to --key value flags
- JSON stdout captured to a file and pretty-validated
- typed error classification: prints {"ok":false,"error_kind":...} on failure
  so the agent can decide fallback instead of guessing.
"""
import json, os, subprocess, sys, tempfile

VENV_REVERSE = "/opt/data/reverse/.venv/bin/reverse"
TIMEOUT = 60

def main():
    if len(sys.argv) < 3 or not os.path.exists(VENV_REVERSE):
        print(json.dumps({"ok": False, "error_kind": "not_installed",
                          "message": "run scripts/install.sh first"}))
        sys.exit(0)  # exit 0: treat as "unavailable", not a crash
    platform, command = sys.argv[1], sys.argv[2]
    args, raw = [], "--raw" in sys.argv
    for a in sys.argv[3:]:
        if a == "--raw":
            continue
        args.append(a)  # pass args through verbatim: many commands take
        # POSITIONAL args (e.g. `reverse linkedin company <slug>`); for flag-style
        # parameters write them yourself as `--key value` — check
        # `reverse describe <platform> <command>` for the signature first.
    out_path = tempfile.mktemp(suffix=".json", dir="/tmp")
    # --output/--timeout/--retries are PLATFORM-level flags: they go BEFORE the
    # command (usage: reverse <platform> [--output X] <command> [args...]).
    cmd = [VENV_REVERSE, platform, "--output", out_path, command, *args]
    if raw:
        cmd.remove("--output"); cmd.remove(out_path)
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        print(json.dumps({"ok": False, "error_kind": "timeout",
                          "message": f"reverse {platform} {command} exceeded {TIMEOUT}s"}))
        return
    if p.returncode != 0:
        kind = "rate_limited" if "429" in p.stderr else \
               "blocked" if ("403" in p.stderr or "999" in p.stderr) else \
               "session_required" if any(t in p.stderr for t in
                   ("tab_unavailable", "not_logged_in", "runtime_unavailable")) else "failed"
        print(json.dumps({"ok": False, "error_kind": kind,
                          "stderr_tail": p.stderr[-400:]}))
        return
    if raw:
        print(p.stdout); return
    if not os.path.exists(out_path):
        # no --output support for this command; stdout is the result
        print(json.dumps({"ok": True, "stdout": p.stdout[:20000]}))
        return
    try:
        with open(out_path) as f:
            data = json.load(f)
        n = len(data) if isinstance(data, list) else 1
        print(json.dumps({"ok": True, "count": n, "file": out_path}))
        os.unlink(out_path) if n == 0 else None
        if n == 0:
            print(json.dumps({"ok": True, "count": 0}))
    except json.JSONDecodeError:
        print(json.dumps({"ok": True, "stdout": open(out_path).read()[:20000]}))

if __name__ == "__main__":
    main()