# captured_calls additions - 2026-09-23 13:10 UTC (9 AM ET 9/23 slot, ehpa cloud Code Routine run 2026-09-23T1310Z)

No new call shape this run. Calls used, all already in the registry: getclaimcenteroverview, getreviewcharges, getclaiminspectorbatches, getclaiminspectorcharges (10 batches), getclaimunbillablecharges, getclaimrunstatus, getclaimexclusionclaimruns, getclaimexclusioncharges (clearinghouse=1 payer=1), GET /api/era/checks (empty), POST /api/era/locks/release-expired, payreasons.py --list.

Behaviour confirmed: the Claims Center is unchanged from the 1110Z slot (Charge Review 0, Claim Inspector 16, Unbilled 13, Exclusions 2 list rows / overview 3) - every row a standing hold; newest claim run still 1700229 (82 runs), so no new rejections; ERA Center empty before and after. No AMD writes this run.

Bootstrap note: tools/bootstrap_workspace.sh check names columns_inspector2_0908.py and era_details_pull.py as required helpers absent from main - neither blocked the run (insp_<slot>.py scripts are the inspector template since 9/22; era_step_b_0913.py fills the era_details cache itself); listed for the next chat session to restore or to drop from the REQ list.
