# Universal Practice Optimization: build status (handoff notes)

Updated 2026-11-10, fourth pass: the practice plan's seed files and data pack were refreshed with the facts of November 10, 2026 (section "November 10, 2026 refresh" below). The refreshed seeds are not yet loaded into the database, rendered or published; that follows an independent check. Branch `claude/practice-optimization-upo`, draft PR #28 (not merged; nothing has been pushed to `main`).

## What is live
- **Database.** Schema `upo` on the production branch of the Neon project and on the preview branch `upo-preview`. Loaded from the seed files in this folder with `optimization/tools/upo_load.py`: 13 domains, 117 areas, 198 measures, 299 sources, 60 vendor documents with 381 extracted claims, 4 learning modules, and one practice (117 area assessments, 124 metric rows, 13 risk findings, 18 recommendations, 17 projects, 83 work-list items, 4 valuation rows).
- **App.** `apps/ehpadb` deployed to production (deployment 4), answering at https://app.ehpa.dev and https://ehpa.dev. Sign-in page, then a hub with three links: the universal framework, the framework applied to this practice, and the earlier billing dashboard. Learning modules are under Learn. The same build is on the preview branch (deployment 5), where a browser test signs in and opens every page.
- **Artifacts.** Practice Optimization Universal https://claude.ai/artifact/6DJJFPWWcwtvnDZm5MP2Uw ; Owner-CFO Revenue Cycle https://claude.ai/artifact/VAEP7Z4wDf16ZZxxrFR311 ; Practice Sale Value https://claude.ai/artifact/E8vMzkrvVzLLGFYoHwcTCo ; Growing the Practice https://claude.ai/artifact/AJvDtk4fX2thdKiu7d67ib ; Code and Mechanics https://claude.ai/artifact/Kmf2uvQAombmfaE8VcbLhw
- **Drive.** Folder "aa claude practice optimization framework" https://drive.google.com/drive/folders/1YBCkUHqme2LcYDdC33afn5SpgA27vKh_ : practice report (01), valuation (02), universal framework (03), purchased library review (04), four learning modules (11 to 14), four research notes (21 to 24), seed files as a zip (30). The purchased files stay in "aa claude practice optimization files" and are never committed.
- **Postman.** Collection "ehpa Practice Optimization API" in My Workspace; the same seven requests are in `docs/api_vocabulary.json` and the generated collection file.

## Headline results
- Valuation: enterprise value about $300,000 (range $50,000 to $680,000); normalized EBITDA $88,057 after a $435,000 loaded market wage; subtotal after cash, receivables and debt $257,225 before tax and deal costs. A first version said $650,000; two independent reviews found it used too low a wage, counted stipends no longer received and over-weighted marketplace sales. Method and inputs are in `practices/ehpa/valuation.json`.
- Risk review: 15 findings in `practices/ehpa/risk_findings.json` (13 before the November 10 refresh, which added the October visits entered under the other clinician and the 84 never-billed feed visits). Care management is not flagged for review or held, at the owner's direction; he confirmed on November 10, 2026 that consent, care plans and time records are on file.
- Purchased library: 52 of 60 documents reviewed. Of 96 claims checked against primary sources, 8 were supported, 55 partly right, 24 contradicted, 7 out of date and 2 could not be checked. Use it as an outline, not as a reference.

## November 10, 2026 refresh (seed files and data pack; not yet loaded, rendered or published)
- Seeds after the refresh: 15 risk findings, 20 recommendations, 17 projects, 123 work items, 124 metric rows; `upo_load.py validate` passes. Script: `apply_refresh_1110_full.py` in the session scratchpad (extended from the author's draft). The facts and their aggregates are in `practices/ehpa/data_pack.md` section 6.
- Place of service: the owner's rule went live on the billing branch at 11:14 UTC as rule version 2026-11-10.4 (care management in the five nursing buildings and the monthly visit as 32; weekly visits, admissions and anything unclear as 31). First live batch: 60 visits, $10,368, 24 Brynwood visits at 32. Whether AdvancedMD kept the 32s is not read yet. The past year ($60,015 of Medicare payment at the long-term rate) is not reopened, at the owner's direction.
- Clinician on feed visits: 149 October visits (167 lines) went in under the other clinician; fixed for new batches by version .4. The owner decided the 15 unbilled lines on November 10; the 133 billed and 19 paid lines are open.
- Initial nursing-facility visits: from version 2026-11-10.6 (live 22:46 UTC) every 99306 and its 99497 go in under the physician and the group, on the owner's rule; that is right only if he personally did the visit. The 982 past visits under the nurse practitioner's code are not reopened.
- Never-billed feed visits: 84 visits ($18,802) were released by the insurance check but could never bill (empty insurance-order list); proven by two reviews. The owner approved the remedy on November 10; the fix (version .7) is reviewed but not live, and none is billed yet. The check's HOLD is a label in its report, not a stop: 56 held visits were billed anyway.
- Coverage: the refresh stopped in mid-September; 349 of 503 cards were open on November 10 and 136 with nothing left to bill or collect were closed that day. The monthly coverage run is approved as check-only and not built yet. The look-up savings went live on the billing branch at 23:44 UTC. A reply to the look-up vendor went on November 10 asking for written per-check prices; follow-up November 11.
- Medicare quality program: the group and both clinicians are registered for the neurological option (M0004); billing adds the advance care plan code and M0004 automatically from version .6. If nothing is reported for 2026, about $47,000 to $54,000 is cut in 2028. Attestation January 4 to March 31, 2027 (calendar entry January 4, 9:00 AM). Reminders done: 34 calendar entries, 22 sheet rows, 3 new board rows, one task email.
- Database: the AdvancedMD history tables were corrected at 13:33 UTC (old objects kept as *_before_1110); the charge-detail pull stood at 4,552 of 11,050 charts at 23:05 UTC and continues in two-hour pieces. Posted payments for 2022 to 2025 are a floor; money is read by year of service.
- Credentialing corrections: the physician's Medicaid agreement expires December 27 (target to file December 1); the nurse practitioner's Medicaid is a new application; the UnitedHealthcare attestation is not overdue; TRICARE East is approved; Railroad Medicare is paying.

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
4. Net collection rate cannot be computed until contract rates or allowed amounts are stored per claim. (November 10, 2026: the AdvancedMD history is now in the database, and the charge-detail pull, which carries allowed amounts, stood at 4,552 of 11,050 charts at 23:05 UTC.)
5. The preview database branch `upo-preview` still exists. Delete it when it is no longer wanted.
6. Place of service (added November 10, 2026): answer three questions the rule cannot answer from the chart: is the first visit back from a hospital stay always billed as an initial visit; should a monthly resident's extra sick visit and that month's care management be 32; keep or remove the safeguard that leaves care management at 31 in a month with a hospital visit, a home or assisted living visit, an admission or weekly visits.
7. The October visits entered under the other clinician: mark any that were his own, and decide on the 133 billed and 19 paid lines (corrected claims, or for a paid line a corrected claim or a refund).
8. Name the one improvement activity both clinicians carried out 90 days in a row in 2026, for the attestation.
9. File the Medicaid renewal by December 1 (the agreement expires December 27); reset the Medicaid portal password first.
10. Accept the look-up vendor's new Slack invitation (only he can), and agree no monthly minimum without written per-check prices.
11. Say when the database objects named *_before_1110 may be removed.
12. Whether a HOLD in the insurance check should one day really stop a claim in AdvancedMD (a later change that needs his word).
13. Replace his installed copy of the look-up skill with the new file billing sent him: the routines read the installed copy by name, so the instructions that go with the look-up savings (live November 10, 23:44 UTC) reach them only when he does.
