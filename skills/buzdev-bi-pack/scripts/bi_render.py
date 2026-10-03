#!/usr/bin/env python3
"""bi_render.py — validate a BuzDev agent output's business_intelligence block
and preview the rendered markdown.

Usage: python3 bi_render.py <output.json>   (file containing the full agent
output with a top-level "business_intelligence" key, or the BI block itself)

Exit 0 = valid (renders preview). Exit 1 = validation failure (errors listed).
"""
import json
import sys
import re

SECTION_IDS = [
    ("customer_profiles", 1),
    ("market_research", 2),
    ("competitor_analysis", 3),
    ("gtm_strategy", 4),
    ("roadmap", 5),
]
ID_SET = {i for i, _ in SECTION_IDS}
POS = dict(SECTION_IDS)
TITLES = {
    "customer_profiles": "Customer Profiles & Personas",
    "market_research": "Market Research & Opportunity Sizing",
    "competitor_analysis": "Competitor Analysis & Positioning",
    "gtm_strategy": "Go-To-Market & Growth Strategy",
    "roadmap": "Business & Monetization Roadmap",
}


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: bi_render.py <output.json>", file=sys.stderr)
        return 1
    data = json.load(open(sys.argv[1], encoding="utf-8"))
    if isinstance(data.get("business_intelligence"), dict):
        sections = data["business_intelligence"].get("sections", [])
    elif isinstance(data.get("sections"), list):
        sections = data["sections"]
    else:
        print("ERROR: no business_intelligence.sections found", file=sys.stderr)
        return 1

    errors = []
    seen = set()
    for s in sections:
        sid = s.get("id")
        if sid not in ID_SET:
            errors.append(f"unknown section id: {sid}")
            continue
        if sid in seen:
            errors.append(f"duplicate section: {sid}")
        seen.add(sid)
        summary = s.get("summary")
        if summary and len(summary) > 500:
            errors.append(f"{sid}: summary >500 chars ({len(summary)})")
        content = s.get("content")
        body = None
        if isinstance(content, dict):
            body = content.get("body")
        elif isinstance(content, str):
            body = content
        if s.get("status") == "insufficient_data":
            print(f"  [skip] {sid}: insufficient_data")
            continue
        if not body or not str(body).strip():
            errors.append(f"{sid}: empty content body")
        pos = s.get("position")
        if pos is not None and pos != POS[sid]:
            errors.append(f"{sid}: position {pos} != expected {POS[sid]}")

    missing = ID_SET - seen
    if missing:
        print(f"  NOTE: missing sections: {sorted(missing)} (allowed only if marked insufficient_data in a prior section list)")

    if errors:
        print("INVALID:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print("VALID — rendered preview:")
    print()
    for sid, _ in SECTION_IDS:
        for s in sections:
            if s.get("id") != sid:
                continue
            if s.get("status") == "insufficient_data":
                print(f"## {TITLES[sid]}\n\n(insufficient data)\n")
                break
            body = (
                s["content"]["body"] if isinstance(s["content"], dict) else s["content"]
            )
            print(f"## {TITLES[sid]}\n\n{body}\n")
            break
    return 0


if __name__ == "__main__":
    sys.exit(main())