# Universal Practice Optimization: build status (handoff notes)

Updated 2026-11-10, second pass. Branch `claude/practice-optimization-upo`, draft PR #28.

## Done
- Schema `upo` (applied on the preview branch only so far), loader `optimization/tools/upo_load.py`, app pages (hub, framework, my practice, learn, legacy dashboard). Fixed build redeployed to preview (deployment 2).
- Seeds written: `universal/sources.json` (72), `universal/domains.json` (13), `universal/meta.json`, all of `practices/ehpa/*` (profile, 117 area assessments, 124 metric rows, 12 risk findings, 18 recommendations, 17 projects, 78 work-list items, valuation with 4 method rows), `learning/*.json` (4 modules), `vendor/vendor_items.json` and `vendor_claims.json` (built by a script from the digests; re-run it when more digests land).
- Valuation conclusion: enterprise value about $650,000 (range $400,000 to $1,000,000); normalized EBITDA $170,057; indicative owner proceeds $622,225 before tax and deal costs.
- Learning modules published as artifacts: Owner-CFO Revenue Cycle https://claude.ai/artifact/VAEP7Z4wDf16ZZxxrFR311 ; Practice Sale Value https://claude.ai/artifact/E8vMzkrvVzLLGFYoHwcTCo ; Growing the Practice https://claude.ai/artifact/AJvDtk4fX2thdKiu7d67ib ; Code and Mechanics https://claude.ai/artifact/Kmf2uvQAombmfaE8VcbLhw
- Drive folder for outputs: "aa claude practice optimization framework" https://drive.google.com/drive/folders/1YBCkUHqme2LcYDdC33afn5SpgA27vKh_ (inside "aa claude folders"). Purchased zips are in "aa claude practice optimization files".

## In flight (background)
- Three workflows writing and reviewing `universal/domains/<domain>.json` from the skeleton (117 areas, 186 measures). Authoring helpers live outside the repo in the session scratchpad (`author/skeleton.json`, `AUTHOR_BRIEF.md`, `check_domain.py`). New sources the writers add land in `author/new_sources/<domain>.json` and must be merged into `universal/sources.json`.
- Digest workflows resumed for the remaining vendor documents and for the fact-check pass (50 of 60 documents reviewed, 32 of 365 claims checked at last count).

## Next, in order
1. When the 13 domain files exist: merge new sources, `upo_load.py validate`, fix reference errors, `load --target preview`, smoke test.
2. Publish the "Practice Optimization Universal" artifact (generated from the seeds).
3. `upo_load.py schema --target prod`, `load --target prod`, `apps/ehpadb/scripts/deploy-api.sh prod`, verify at app.ehpa.dev.
4. Drive exports, Postman vocabulary entries for `/api/upo/*`, mirror digest, commit and push.
5. Rebuild the vendor tables after the last digests and fact-checks, reload.
