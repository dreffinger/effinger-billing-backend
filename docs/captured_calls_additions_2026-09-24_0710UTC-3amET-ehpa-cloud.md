# captured_calls additions - 2026-09-24 0710 UTC (3 AM ET 9/24 slot, ehpa cloud Code Routine, run 2026-09-24T0710Z)

No new call shape this run. Behaviours (chart ids only):

- `POST /api/era/locks/release-expired` with a JSON object body (`{}`) answers HTTP 400 "Unexpected character encountered while parsing value: {" - the shape era_post.locks() sends is the accepted one; call the helper, not amd.rest_post with a dict.
- `GET /api/era/checkdetails?checkid=` on a check the Post button has already worked returns ONLY the claims still unposted (eracheckdetails had 1 claim for 1052828 after 114 of 115 visits posted); the posted claims drop off the detail, so a cache taken before posting is the only record of the whole check.
- era_clear.py --dry on a check whose only open money is a residual on an already-adjudicated charge (ERA paid 68.62, live insurance balance 0.00, the payment on the charge carries a different check number) reports it as 'postable money' and HOLDS the check - the residual rule (William 9/13) is applied by the run report, not by era_clear; the check stays on the unposted list.
- Columns unchanged for a whole slot (0/20/25/2, all standing holds, no new claim run): the run's only AMD writes were era_post.locks; nothing else touched.
