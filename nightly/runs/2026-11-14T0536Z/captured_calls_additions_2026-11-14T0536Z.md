# captured_calls additions - nightly cascade 2026-11-14T0536Z

No new AMD or Stedi call shapes were captured tonight. Every call used was already in the registry:
- AMD: login (one attempt, cached token), gettxhistory (txh.py), getdemographic + checkEligibility free 271 (elig_amd.py --all), updateinsurance wrapped shape (ins_update.py - enddate cleared + patient order set and verified in one command), updextrainsinfo frequency 1 + chargerebill (rebill_patient_year.py / move_to_ins), ERA Center list / Post / dismiss (engine run_all.py --steps era: 0 checks).
- Stedi: plain Medicare check (CMS) and payer eligibility inside precheck.py (13 calls), insurance discovery (stedi.py disc, 2 priced + 1 HTTP 502).

Observation for the rules (not a new call): a Medicare 271 that lists the Advantage payer under PR with an H-contract (BCBS of Michigan H9572 = Medicare Plus Blue PPO, billed through Florida Blue BlueCard) is a Medicare Advantage verdict even when the chart's BCBS plan is a Florida Blue carrier record - the 9/8/2026 end-dating of pat17472826's BCBS plan read it as a dead commercial plan. Florida Blue's own 271 answers 'PR MED ADV' on such a member.
