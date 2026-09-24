# captured_calls additions - 2026-09-24 0310 UTC (11 PM ET 9/23) ehpa cloud run

No new call shape this run. Behaviours confirmed:

- payreasons.py --visit <vid> --pid <pid> --live re-posts a code-less ERA payment WITH its reason codes (CO45/PR2/CO253 now readable on the <payment> via visit_state) but does NOT post the contractual write-off: after the repair the CO45 + CO253 amounts were still open on the insurance balance (pat17476094 v19452631, pat17473422 v19452628: 142.72 + 74.05 each). The follow-up is a bare write-off - manual_post.post(cid, 'FLO02', 0.0, CO45+CO253, 'WOINS', checknumber='819814877', depositdate='09/19/2026') -> success=1 (paymentids 10163908-10163911); the PR2 coinsurance then lands on the patient balance when the chart has no live secondary. Register registers/co45_repair_2026-09-24T0310Z.json.
- lookuppatient class=lookup name='LAST,%' answers a 511-byte empty Results element when no chart exists (a new admit before the first Claimocity charge) - parse for <patient rows, not for success.
- Stedi CMS eligibility with the MBI from a Medicare card (tradingPartnerServiceId CMS) answers the full 271 incl. the Medicare Advantage entity as benefitsInformation code R/U 'Other or Additional Payor' with coordinationOfBenefits date; the MBI lookup by name/DOB alone (MBILUNOSSN) answered AAA 72 for the same person.
