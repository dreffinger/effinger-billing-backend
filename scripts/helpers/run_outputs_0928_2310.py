# PLAIN ENGLISH (run outputs for the 7pm ET 9/28/2026 slot - ehpa cloud run 2026-09-28T2310Z)
# Decides: nothing. Reads this run's registers (scan_0912 before/after, inspector / unbilled-apply / exclusion / ERA registers) and writes:
#   "_run report 9-28 1900.csv" (names allowed - SendUserFile only), board_updates_2026-09-28T2310Z.json (new-chart rows, holds on
#   William's turn, the Pam-admit trail, the Medicaid FFS denial cluster, standing watch appends), a needs_facesheet_list.md section
#   (pat ids only), captured_calls_additions_*.md, the facesheets-needed email body and the chat-history digest (--final adds the mirror result).
# Never touches: AMD, the board databases.
# ---
# LOCAL ONLY: the body of this script carries the DOBs / member ids the board rows and the facesheet email needed, so only this header is
# mirrored. The full file lives in the workspace (/home/claude/unbilled/local/run_outputs_0928_2310.py) and in Drive 'workspace mirror'.
# Shape: scan_0912 summaries + registers -> "_run report 9-28 1900.csv" (122 rows), board_updates_<stamp>.json (27 upsert ops: 8 new-chart
# rows, 6 holds on William's turn incl. the Medicaid FFS 460-claim denial cluster, 7 Pam-admit trail rows, 3 standing appends),
# needs_section_<stamp>.md, captured_calls_additions_<stamp>-7pmET-ehpa-cloud.md.
