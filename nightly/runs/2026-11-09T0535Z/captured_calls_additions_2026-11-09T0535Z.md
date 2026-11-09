# captured_calls additions - nightly cascade run 2026-11-09T0535Z (12:35 AM ET Mon 11/9/2026)

No new AdvancedMD or Stedi call shapes were learned tonight. Every call the run made is already in the registry:

- AMD login (one attempt, `amd.login_cached()`), the unpaid list read inside `precheck.py`, `gettxhistory` inside `void_rules.py`, `GET /api/era/checks` inside the engine's ERA step (`era_list.py` / `era_post.py --all-unposted` / `era_clear.py`).
- Stedi: 1 payer eligibility (Florida Blue BCBSF, DOS 11/7/2026) from `precheck.py`; 1 free `payers/search` probe.
- Credentialing: NPPES API and the OIG LEIE download both answered `Max retries exceeded` from this container tonight (`npiregistry.cms.hhs.gov`, `oig.hhs.gov`) - no diff possible, snapshot unchanged; the CMS revalidation list and reminder windows ran from the local files.

Vocabulary +0. Postman: unchanged.
