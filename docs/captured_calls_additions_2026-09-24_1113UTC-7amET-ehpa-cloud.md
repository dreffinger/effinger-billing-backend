# captured_calls additions - run 2026-09-24T1113Z (7am ET 9/24/2026, ehpa cloud Code Routine)
No new call shape this run. Behaviours confirmed:
- getclaimcenteroverview / getreviewcharges / getclaiminspectorbatches+charges / getclaimunbillablecharges / getclaimexclusionclaimruns+charges: 0 / 20 / 25 / 2 (overview exclusioncount 3) - identical to 0510Z and 0910Z; newest claim run still 1700236 (83 runs listed).
- GET /api/era/checks: 1 check (1052828, systemcarriercode FLO02, paymentnumber 819843767, unposted 105.75 of 11504.56); era_fallback_0913b --dry classifies its one detail line as residual-zero ($68.62) + already ($37.13); era_clear --dry holds it ('postable money' 1 by the remit-stored insurancebalance 9.47).
- POST /api/era/locks/release-expired sent (era_step_b_0913).
- Bootstrap note: tools/bootstrap_workspace.sh check now also reports columns_inspector2_0908.py MISSING (the standing prompt names it as the inspector worked example; insp_*.py scripts in nightly/runs are the working template).
