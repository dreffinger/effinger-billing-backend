# captured_calls additions - 2026-09-19T0310Z (backend billing run 11 PM ET 9/18, ehpa cloud)

No new AMD or Stedi call shapes this run. Behaviours worth keeping:
- A Pam admit email whose subject names an existing patient: `lookuppatient class="api" name="LAST,FIRST%"` found the chart in one call (DOB matched the PCC profile photo); getdemographic showed both plans already on the chart with the sheet's numbers, so the only write was the address line-1 fill (addr_line1_fix.py: PATCH 200, line 2 kept).
- The Insurance Refresh Board's sync registry (meta/drive_sync) has not recorded an applied inbox file since 9/15 (lastCheck keeps advancing, version 805): every board_updates_*.json in 'board inbox' is re-applied on each open, and files written with pseudonymized row ids re-create duplicate rows each time. Row ids must come from a local inbox/rowids_*.json; the duplicates are closed by this run's update file; the registry repair is William's / a chat session with write_db.
- getclaimrunstatus still lists 1700202 as the newest claim run at 03:13Z 9/19 (78 runs): ninth consecutive worked slot with no nightly claim run.
- ERA Center empty (0 checks) at 03:16Z 9/19 - era_post / fallback / era_clear all no-ops; the chain script is idempotent on an empty list.
