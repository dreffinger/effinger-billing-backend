# Status and handoff (updated 2026-11-10 05:15 UTC)

## Done
- `upo` schema written (`db/upo_schema.sql`) and applied on the PREVIEW branch `upo-preview` (br-icy-hall-bcxfu0rb). Not yet on production.
- Loader (`tools/upo_load.py`): validate / schema / load / status / sql, tested on preview with sample seeds (reloads are clean).
- App: hub + Universal + My practice + Learn + the existing dashboard under `#db`. Type-checks, bundles, deployed to the
  PREVIEW branch and passed a full browser run (sign-up, 21 pages, metric search, quiz, work-list save, sign-out).
  Production still runs the old single-dashboard build.
- Practice data pack (`practices/ehpa/data_pack.md`): financial statements 2023 to 9/30/2026, receivables, charges, denials,
  remittances, credentialing, and the public CMS Medicare utilization history 2019-2024 for both clinicians.
- Vendor library: all 62 PDFs + 3 workbooks pulled from Drive and converted to text; 35 of 60 unique documents digested
  (`vendor/digests/`). PDF metadata: author "Perplexity Computer", producer ReportLab, created 2026-09-10 (AI-generated).
- Research: `research/R2_valuation.md` complete.

## Interrupted (the Claude account ran out of usage credits during the parallel run, 05:12 UTC)
- 25 documents not yet digested (list: compare `vendor/manifest.json` with `vendor/digests/`).
- Fact-check of the vendor's claims: 0 of 46 units finished. Each digest already lists its `checkable_claims`.
- Research threads R1 (KPI benchmarks), R3 (growth and payment policy), R4 (compliance), R5 (frameworks): not delivered.

## Next, in order
1. Universal seeds: `universal/domains.json`, `universal/domains/<domain>.json`, `universal/sources.json`, `universal/meta.json`.
2. Practice seeds for `ehpa`: `practices/ehpa/{practice,categories,metrics,risk_findings,recommendations,projects,worklist,valuation}.json`.
3. Learning modules: `learning/*.json` (owner-CFO revenue cycle; maximizing sale value; growing the practice; code and mechanics).
4. `vendor/vendor_items.json` and `vendor/vendor_claims.json` built from the digests and fact-checks.
5. `upo_load.py schema` + `load` on production, then `apps/ehpadb/scripts/deploy-api.sh prod`, then verify.
6. Artifacts, Drive folder, Postman entries, mirror digest.
7. Finish the 25 digests and the fact-check pass when usage allows.
