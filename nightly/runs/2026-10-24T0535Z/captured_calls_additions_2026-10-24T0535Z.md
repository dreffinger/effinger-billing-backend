# captured_calls additions - nightly cascade 2026-10-24T0535Z (1:30 AM ET 10/24/2026)

No new AMD or Stedi call shapes captured this run. Calls used, all already in the registry: AMD login (one attempt, POI0712, 05:49Z), `POST /claim/massrebillsearch` with `{}` (unpaid list, via precheck.py), `GET /api/era/checks` (via era_post.py / era_clear.py), the void_rules.py charge read, Stedi `GET /payers/search` (credential self-check only). 0 vocabulary entries added.

Operational notes for the registry:
- precheck.py `--days 3` found 0 pairs for the seventh night running (Claimocity feed ~10 days behind the unpaid list's newest DOS).
- void_rules.py ran normally tonight (it had been refused by the permission classifier on 10/22 and 10/23) - 1 rule open, no live charge matched.
- cred_check.py: direct egress to npiregistry.cms.hhs.gov, data.cms.gov and oig.hhs.gov all refused from this container ('Max retries exceeded'). Fallback used: the NPI Registry MCP connector (npi_lookup) answers for all three NPIs and matched the 9/20 snapshot - a workable substitute for the NPPES leg of cred_check.py; no connector substitute yet for the revalidation list or the LEIE.
- Branch bookkeeping: the session branch (claude/stoic-clarke-xo3umf) was 3 button-run commits behind main at start and was fast-forwarded before any register copy.
