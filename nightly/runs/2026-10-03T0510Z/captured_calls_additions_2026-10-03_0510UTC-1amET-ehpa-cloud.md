# captured_calls additions - run 2026-10-03T0510Z (1 AM ET 10/3, ehpa cloud)

No new call shapes this run. Lessons:

- 'A payment from the prior payor is required' rows that were released by an earlier run come back on the Unbilled snapshot whenever AMD re-evaluates the visit (a $0 posting, a voided line, a resave) while the primary is still unanswered - the rule (b) release is idempotent: read the visit live (gettxhistory visitid=) and release again; nothing else changes. Seen 10/3 on pat23391 v19392347, pat17470743 v19441047, pat17473343 v19442414 (all released 9/26 as well).
- gettxhistory visitid= on a visit whose charge sits at a SECONDARY carrier (pat23391 v19392347: 99233 carrier BCBS, Payor ID 1414) lists the Medicare payment with carrier/checknumber and the voided + re-posted WOINS pairs; the sibling G0316 charge on the same visit still shows carrier FLO02 - a visit's charges can be at two different payers at once, and the 'prior payor' row is about the one still at the primary.
- era_post.locks('') raises ValueError (int('')) - the helper takes a numeric check id; with one held check in the Center there is nothing to release, so skip it rather than guessing an argument.
