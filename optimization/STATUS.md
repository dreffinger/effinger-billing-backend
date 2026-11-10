# Universal Practice Optimization: build status (handoff notes)

Updated 2026-11-10, third pass. Branch `claude/practice-optimization-upo`, draft PR #28 (not merged; nothing has been pushed to `main`).

## What is live
- **Database.** Schema `upo` on the production branch of the Neon project and on the preview branch `upo-preview`. Loaded from the seed files in this folder with `optimization/tools/upo_load.py`: 13 domains, 117 areas, 198 measures, 299 sources, 60 vendor documents with 381 extracted claims, 4 learning modules, and one practice (117 area assessments, 124 metric rows, 13 risk findings, 18 recommendations, 17 projects, 83 work-list items, 4 valuation rows).
- **App.** `apps/ehpadb` deployed to production (deployment 4), answering at https://app.ehpa.dev and https://ehpa.dev. Sign-in page, then a hub with three links: the universal framework, the framework applied to this practice, and the earlier billing dashboard. Learning modules are under Learn. The same build is on the preview branch (deployment 5), where a browser test signs in and opens every page.
- **Artifacts.** Practice Optimization Universal https://claude.ai/artifact/6DJJFPWWcwtvnDZm5MP2Uw ; Owner-CFO Revenue Cycle https://claude.ai/artifact/VAEP7Z4wDf16ZZxxrFR311 ; Practice Sale Value https://claude.ai/artifact/E8vMzkrvVzLLGFYoHwcTCo ; Growing the Practice https://claude.ai/artifact/AJvDtk4fX2thdKiu7d67ib ; Code and Mechanics https://claude.ai/artifact/Kmf2uvQAombmfaE8VcbLhw
- **Drive.** Folder "aa claude practice optimization framework" https://drive.google.com/drive/folders/1YBCkUHqme2LcYDdC33afn5SpgA27vKh_ : practice report (01), valuation (02), universal framework (03), purchased library review (04), four learning modules (11 to 14), four research notes (21 to 24), seed files as a zip (30). The purchased files stay in "aa claude practice optimization files" and are never committed.
- **Postman.** Collection "ehpa Practice Optimization API" in My Workspace; the same seven requests are in `docs/api_vocabulary.json` and the generated collection file.

## Headline results
- Valuation: enterprise value about $300,000 (range $50,000 to $680,000); normalized EBITDA $88,057 after a $435,000 loaded market wage; subtotal after cash, receivables and debt $257,225 before tax and deal costs. A first version said $650,000; two independent reviews found it used too low a wage, counted stipends no longer received and over-weighted marketplace sales. Method and inputs are in `practices/ehpa/valuation.json`.
- Risk review: 13 findings in `practices/ehpa/risk_findings.json`. The largest is complex chronic care management billed for most of the census each month.
- Purchased library: 52 of 60 documents reviewed. Of 96 claims checked against primary sources, 8 were supported, 55 partly right, 24 contradicted, 7 out of date and 2 could not be checked. Use it as an outline, not as a reference.

## How the content is produced
- Seed files here are the source of truth. `python3 optimization/tools/upo_load.py validate`, then `load --target preview` or `load --target prod`. Do not import the loader as a module: it runs its command line on import.
- Tables in "keep" mode (practices, risk findings, work-list items, meta) are upserted and never deleted, so a person's edits in the app survive a reload. The other tables are replaced to match the seeds.
- The authoring helpers (brief, skeleton, checker, renderers for the artifacts and the Drive documents) lived in the session scratchpad, not in the repository. The domain files and practice files are complete without them.
- No patient-level data is in any seed, table in `upo`, artifact or commit. Aggregates only.

## Verification state
- `rcm-charge-coding` was checked statement by statement by an independent reviewer (96 checked, 19 corrected, 3 removed).
- The other twelve domains and the practice analysis were under independent review when this note was written. Reviewer reports are summarized in the pull request description once they finish.
- Signed-in pages were tested on the preview branch only. Production serves the same build and the same data, but nobody has signed in there from this work.

## Open items for the owner
1. Merge PR #28 before anyone redeploys the app from `main`; `main` does not contain the new pages.
2. Production sign-up is open with no email verification. Access to data is limited by the allowed-email list, but sign-up should be closed or verified.
3. The QuickBooks connector needs to be re-authorized before monthly financials can be pulled automatically.
4. Net collection rate cannot be computed until contract rates or allowed amounts are stored per claim.
5. The preview database branch `upo-preview` still exists. Delete it when it is no longer wanted.
