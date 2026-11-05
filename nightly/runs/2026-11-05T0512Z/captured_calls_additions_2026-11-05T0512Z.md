# captured_calls additions - ehpa Billing Button run 2026-11-05T0512Z (12:12 AM ET 11/5, live, no brief)

No new AdvancedMD or Stedi call shapes. Calls used (all in the registry): login (one, columns_scan 05:18Z), getclaimcenteroverview, getreviewcharges, getclaiminspectorbatches / getclaiminspectorcharges, getclaimunbillablecharges, getclaimrunstatus / getclaimexclusioncharges, getdemographic, gettxhistory, getchargedetaildataicd10, lookuppatient, updvisitwithcharges (full-visit echo, insorder - resave.set_insorder), updextrainsinfo + POST /api/claim/chargerebill (freq1_visit), hideunbillablevisits (unbilled_release), updateinsurance sequence (ins_update), GET /api/era/checks (0), Stedi MBI lookup x5 (precheck), NPPES / LEIE (cred_check).

## Observations
- The overview lagged again (Unbilled 27 / Exclusions 7 on getclaimcenteroverview vs 1 / 1 on the list calls).
- A chart whose seq-1 plan is a Medicare Advantage plan must carry the MA plan ALONE in the visit and patient insurance order; an order of MA,Medicare makes AMD build a Medicare secondary claim and hold it for an MSP code (chart 17473090 v19459892).
- New helper on main: tools/bootstrap/transcript_extract.py (decode Drive / Gmail connector payloads from the session transcript - byte-exact, never retyped).
