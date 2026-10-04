# captured_calls additions - 2026-10-04 09:10 UTC (5 AM ET 10/4) backend billing run, ehpa cloud

No new call shapes this run. Behaviours recorded:
- Read-only run: columns 0/20/21/0 -> 0/20/21/0 and ERA Center 1 check ($104.19, 1052906 held) unchanged since the 0710Z run; no AMD write was needed, so nothing was attempted and nothing was refused.
- registers/approvals_pending.json still carried A-2026-10-04T0510Z-A1 / -A2 as 'waiting' although the 0710Z digest recorded them closed - the 0710Z register write did not reach main; closed 'done' this run (approval_request.py done <id> --note ...). Lesson: run `approval_request.py pending` after `done` and commit the register in the same mirror commit.
- GitHub inbox: the Drive 'github mirror' listing by `title contains 'manifest'` is the quick check - every manifest read APPLIED_/SUPERSEDED_, so nothing to apply.
