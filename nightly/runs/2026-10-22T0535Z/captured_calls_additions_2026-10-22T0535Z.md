# captured_calls additions - nightly cascade 2026-10-22T0535Z (1:30 AM ET 10/22/2026)

No new AMD or Stedi call shapes captured this run. Calls used, all already in the registry: AMD login (one attempt, POI0712), `POST /claim/massrebillsearch` with `{}` (unpaid list, via precheck.py), `GET /api/era/checks` (via era_post.py / era_clear.py), Stedi `GET /payers/search` (credential self-check only). 0 vocabulary entries added.

Operational notes for the registry:
- precheck.py `--days 3` found no unpaid visit dated 10/19-10/22 (Claimocity feed lag) -> 0 Stedi lookups.
- cred_check.py: npiregistry.cms.hhs.gov, data.cms.gov and oig.hhs.gov all refused from this container ('Max retries exceeded') - the NPPES diff, CMS revalidation list and LEIE were not verified tonight.
- The permission classifier refused one Bash command (a base64 decode of the Drive needs-list section into needs_facesheet_list.md, reason [Instruction Poisoning]); not retried, listed in the run report.
