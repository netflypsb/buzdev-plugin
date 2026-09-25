# Registry Mining — structured lead harvesting from official directories

When the prospect class is regulated or officially listed (schools, clinics, licensed vendors, associations), an official registry beats web search: one authoritative source, uniform fields, real contact rows. Generic lead search then only fills gaps around the harvest.

## Playbook

1. **Find the registry** with targeted web search in the domain's language: `senarai|direktori <prospect type> <state/region>` — target the ministry/department portal, not aggregator blogs. National registries usually expose a per-entity detail page (`...view.php?id=NNNN`); that page is the mining target (principal/owner, phone, email live there, not in the list).
2. **Fetch the list page once and parse locally.** The unfiltered list endpoint can return several MB containing the whole national directory — fetch it, extract entity IDs and names from the link pattern, and filter locally by state/district. Server-side filtered queries on some registries silently drop rows; empty filtered result ≠ empty registry.
3. **Fetch detail pages concurrently.** Stdlib `urllib` + `ThreadPoolExecutor` (12–16 workers) handles hundreds of pages in under a minute. Record per-page errors; never let one failure abort the batch.
4. **Parse row-wise, not position-wise.** Detail pages are `<tr><td><b>Label</b></td><td>:</td><td>value</td></tr>` tables. Take the label from the `<b>` inside each `<tr>` and the value from that row's last `<td>`. Normalise labels: the colon may sit inside the `<b>` tag, and the status label may carry a suffix (e.g. "Status Pendaftaran Negeri").
5. **Clean defensively.** Regex-extract emails (`[\w.+-]+@[\w-]+\.[\w.-]+`) and phones from raw values; truncate values at the next known label — scraped values often carry trailing field leakage ("No. Akaun : ...").
6. **Dedupe on normalised name**, keeping the row with the richest contact (email > phone > first).
7. **Sanity-assert before export:** the client company must appear in zero rows; report contact coverage (rows with email and/or phone); check the state/district/type distribution matches the intended filters.
8. **Export CSV as utf-8-sig** (Excel-safe for non-ASCII names) and deliver through the user's preferred channel.

## Pitfalls

- **Label-position slicing cross-contaminates fields.** A label like "Negeri" also occurs inside compound phrases ("Sekolah Agama Negeri" in a curriculum line); anchoring on the first textual match pulls the wrong value into the wrong field. Row-wise `<b>` parsing with first-occurrence-per-label wins.
- **The same labels appear twice** (search form + detail table). The form copy precedes the real values; that is why row-wise parsing of the detail table matters more than text-position search.
- **Validate the parsed distribution** (count by state/type) right after parsing — a contaminated field shows up immediately as an impossible distribution (e.g. "Negeri" values that are actually school-type codes).
- **Registry contact emails are often institutional inboxes** (school Gmail accounts). Expect moderate response rates; phone follow-up outperforms email for gatekeeper outreach in this segment.