# captured_calls additions - 2026-09-19T0110Z (backend billing run 9 PM ET 9/18, ehpa cloud)

No new AMD or Stedi call shapes this run. Behaviours worth keeping:
- ERA Center: a Humana money check (1051712) that arrives with a single 99309 line auto-posts cleanly through posterapayments (era_post --all-unposted); the fallback's live read-back then reports the line as already-posted (payment carrying the check number is on the charge) and the check leaves GET /api/era/checks without a dismiss call.
- A Humana NO-PAY check (1051713) carrying only PI252/N4 and OA23 lines is dismissed by era_clear once every line is classed 'denial with write-off (cascade handles)'; its PI252 claims are handed to the Working Denials board through the denials inbox note, never manual-posted.
- Board hygiene: a mirrored (PHI-gated) run script carries pseudonymized row ids; re-using it verbatim from GitHub creates duplicate board rows under the pseudonym (seen 9/18 01:32Z). Row ids must come from a local, non-mirrored file (inbox/rowids_*.json) - done this run.
- getclaimrunstatus still lists 1700202 as the newest claim run at 01:15Z 9/19 (78 runs): eighth consecutive worked slot with no nightly claim run.
