---
name: b2b-lead-harvesting
description: Use when building a prospect list for a client business.
version: 1.0.0
category: business
author: Hermes Agent
license: MIT
metadata:
  tags: leads, outreach, b2b, registry, scraping, csv
  related_skills: buzdev-outreach, buzdev-lead-generation, lead-generation, web-social-search
---

# B2B Lead Harvesting — registry-first prospect lists

## When to Use

Use when a business needs a prospect/contact list: feeder schools for a college, clinics for a supplier, member firms for a service. Trigger phrases: "find leads for X", "build a contact list", "who should we reach out to". Not for single-company research (one-off enrichment) or consumer marketing lists (consumers have no public contact data).

The reliable yield order for institutional prospects: official registries first, keyword search second, generic web search last. Search engines return SEO spam and dead blogs for niche local sectors; government registries hold the actual register with contact fields.

## Procedure

1. **Scope the client's market before searching.** Pin down region(s), the client's offer, and who the reachable gatekeepers are. For B2C-facing clients the prospects are the institutions that feed end customers (e.g. a college recruits through feeder-school principals), because end consumers rarely have public contact records.
2. **Locate the OFFICIAL registry.** Hermes `web_search` for the sector's registry/directory: government education registries, religious-affairs departments, professional boards, licensing bodies. Confirm it exposes a per-entity detail page (principal/contact person, phone, email, registration status). Avoid third-party aggregator copies when the official source exists.
3. **Harvest the entity list.** Registry list pages (or their query endpoints) usually embed a detail-page URL/ID per entity. Pull all IDs that match the target region/type; filter at list level (region, school type) before fetching details.
4. **Fetch detail pages concurrently.** urllib + ThreadPoolExecutor, `max_workers=16`, per-request timeout ~25s, a real browser User-Agent. One detail page per entity yields: registration code, type, address, postcode, district, principal, phone, email, registration status.
5. **Parse ROW-WISE from the HTML table structure.** Iterate `<tr>` blocks; within each take the `<b>label</b>` cell and the LAST value `<td>`. Never split the flattened text label-to-label — labels recur on the same page (search forms, legends, curriculum lines) and values cross-contaminate between fields. Verify one known entity end-to-end before trusting a bulk parse.
6. **Clean, filter, dedupe.** Regex-extract emails (strip trailing punctuation/image extensions); collapse whitespace in phones; dedupe on lowercase name (keep the row with the better contact — branches often share one email); drop rows with neither email nor phone; drop the CLIENT itself (see Pitfalls).
7. **Export and verify.** Write CSV as `utf-8-sig` so Excel opens it cleanly, then read it back with `csv.DictReader`, count rows/emails/phones, and sanity-check that the client's name appears nowhere before delivering. Use `scripts/build_leads_csv.py` from this skill.
8. **Enrich/export via MCP where available.** The buzdev-outreach MCP (see buzdev-outreach skill) adds single-company email discovery (`buzdev_discover_email`) and the deliverable export (`buzdev_export_leads`, free — no credit gate).

## Pitfalls

- **Never include the client organization itself in the lead export.** Filter it out by name before writing, and grep the final rows for the client's name as a last gate — a deliverable listing the client as its own prospect is junk work.
- **Registry labels repeat across page sections** (form fields, legends, footers). Row-wise `<tr>` parsing with a first-match-wins map is the only safe extraction; label-to-label text slicing silently mixes values between fields.
- **`utf-8-sig` + read-back is mandatory**, not optional polish: spreadsheets garble UTF-8 BOM-less files, and a row-count/verify read-back catches silent truncation before the user sees it.
- **~16 concurrent fetchers is the polite ceiling** for a government registry; higher concurrency risks IP blocks that kill the whole harvest.
## Malaysian Registry Notes

- **SIMPENI** (`simpeni.islam.gov.my`) is the authoritative JAKIM registry for all Islamic education institutions (tahfiz, madrasah, SRA, SMKA, tadika Islam). Detail pages have `sek_id=<NNNN>` URLs. A single state harvest yields 40-300+ institutions with principal, email, phone, address. This is the highest-yield source for any Islamic education lead generation in Malaysia.
- **mySchool** (`myschool.daa-taa.com`) covers government SMK/SMKA only. Use as a complement to SIMPENI for non-Islamic schools.
- **eduagama.my** aggregates SIMPENI data — useful for discovering what exists per state, but always harvest contact details from the official SIMPENI source, not the aggregator.
- SIMPENI detail pages have labels that recur across page sections (search form, curriculum list, legends). The row-wise `<tr>` parsing in step 5 handles this; alternatively, anchor on `Label :` (colon-space) and segment label-to-label. Verify one known entity end-to-end before bulk parsing — the `Negeri` label appears both in the address field and inside curriculum text like "Sekolah Agama Negeri".