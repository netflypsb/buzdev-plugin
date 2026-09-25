#!/usr/bin/env python3
"""Build and verify a leads CSV from harvested registry data (stdlib only).

Usage:
  python3 build_leads_csv.py raw_records.json leads.csv \
      --name-field school_name --client "Client Organisation Name" \
      --primary-region Perlis

Expects raw_records.json to be a JSON array of dicts with at least the name
field plus any of: phone, email, code, school_type/type, gender, boarding,
address, postcode, district, state/region, principal, registered, source.

Output: utf-8-sig CSV, deduped, client-excluded, contactless rows dropped,
priority tiered by region, read back and verified before printing a summary.
"""
import argparse, csv, json, re, sys

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
BAD_EMAIL_SUFFIX = (".png", ".jpg", ".gif", ".svg")

FIELDS = ["priority", "name", "code", "type", "gender", "boarding", "district",
          "state", "address", "postcode", "principal", "phone", "email",
          "registered", "source"]


def clean_email(s):
    if not s:
        return ""
    m = EMAIL_RE.search(s.lower())
    if not m:
        return ""
    e = m.group(0).strip(".,;")
    return "" if e.endswith(BAD_EMAIL_SUFFIX) else e


def clean_phone(s):
    s = re.sub(r"\s+", "", (s or "").strip())
    return s


def clean_text(s):
    return re.sub(r"\s+", " ", (s or "")).strip()


def pick(d, *keys):
    for k in keys:
        v = d.get(k)
        if v:
            return v
    return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("raw_json")
    ap.add_argument("out_csv")
    ap.add_argument("--name-field", default="school_name")
    ap.add_argument("--client", required=True, help="client org name to exclude")
    ap.add_argument("--primary-region", default="", help="state/region value that gets priority 1")
    args = ap.parse_args()

    records = json.load(open(args.raw_json, encoding="utf-8"))
    client_key = args.client.lower()
    rows, seen = [], {}
    for r in records:
        name = clean_text(pick(r, args.name_field, "name"))
        if len(name) < 4:
            continue
        if client_key in name.lower():
            continue  # the client is never a lead
        email, phone = clean_email(pick(r, "email")), clean_phone(pick(r, "phone"))
        if not email and not phone:
            continue
        state = clean_text(pick(r, "state", "region")).title()
        row = {
            "priority": "1-primary" if state and args.primary_region and state.lower() == args.primary_region.lower() else "2-secondary",
            "name": name,
            "code": clean_text(pick(r, "code")),
            "type": clean_text(pick(r, "school_type", "type")),
            "gender": clean_text(pick(r, "gender")),
            "boarding": clean_text(pick(r, "boarding")),
            "district": clean_text(pick(r, "district")).title(),
            "state": state,
            "address": clean_text(pick(r, "address")).title(),
            "postcode": clean_text(pick(r, "postcode")),
            "principal": clean_text(pick(r, "principal")).title(),
            "phone": phone,
            "email": email,
            "registered": clean_text(pick(r, "registered")),
            "source": clean_text(pick(r, "source")),
        }
        key = name.lower()
        old = seen.get(key)
        # keep the row with the better contact; branches often share one email
        if old is None or (row["email"] and not old["email"]) or (not old["phone"] and row["phone"]):
            seen[key] = row

    rows = sorted(seen.values(), key=lambda x: (x["priority"], x["district"], x["name"]))

    with open(args.out_csv, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)

    # read-back verification — never deliver an unverified export
    with open(args.out_csv, encoding="utf-8-sig") as f:
        back = list(csv.DictReader(f))
    leaked = [r["name"] for r in back if client_key in r["name"].lower()]
    assert len(back) == len(rows), f"read-back mismatch: {len(back)} != {len(rows)}"
    assert not leaked, f"client leaked into export: {leaked}"
    emails = sum(1 for r in back if r["email"])
    phones = sum(1 for r in back if r["phone"])
    by_region = {}
    for r in back:
        by_region[r["state"]] = by_region.get(r["state"], 0) + 1
    print(f"OK: {len(back)} leads -> {args.out_csv}")
    print(f"emails: {emails} | phones: {phones}")
    for k, v in sorted(by_region.items(), key=lambda kv: -kv[1]):
        print(f"  {k or '?'}: {v}")


if __name__ == "__main__":
    main()
