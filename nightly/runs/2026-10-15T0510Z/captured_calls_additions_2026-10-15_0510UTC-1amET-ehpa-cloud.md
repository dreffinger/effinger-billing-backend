# captured_calls additions - 2026-10-15 0510UTC (1 AM ET) backend billing run, ehpa cloud

No new AdvancedMD or Stedi call shapes this run (0 vocabulary entries).

Lessons (reads only):
- getdemographic + checkEligibility on chart pat48449: the Florida Blue 271 carries EligibilityOrBenefitInformation EB04/EB05 = 'MA / PRIMARY OVER 65' and 'PR / STANDARD SECONDARY' - the Medigap signature; Medicare goes first on the visit (board card A-2026-10-15T0510Z-D).
- Exclusions run 1700302: 45 Florida Blue secondary claims rejected PREF0283 again after the 10/14 freq-1 resend. Pattern: every one carries a Medicare payment posted WITHOUT an ERA line (old-claims / 277 postings 09-10/2026 or 2022-23 manual posts), so AMD cannot fill the primary payer claim control number in the secondary claim's COB loop. Remit inside 12 months -> complete, crossover-wait (17 rows done); remit older than 12 months -> WOINS + complete (card O).
- Permission classifier (auto mode): board_1015_0510.py --live, unbilled_1015_0510.py --live and excl_1015_0510.py --live --only A,C all refused [Real-World Transactions]; excl_1015_0510.py --live --only B (hideexclusions only, no money) ran. approval_submit.py drew a transient 'Stage 2 classifier error' once (retry succeeded). ArtifactData batch for the cards refused [Auto-Mode Bypass] (hourly sync adds them from main).
- Stedi insurance-discovery answered HTTP 502 three times this run (charts pat17478061, pat17478063, pat17477183 once) - gateway, retried once each.
