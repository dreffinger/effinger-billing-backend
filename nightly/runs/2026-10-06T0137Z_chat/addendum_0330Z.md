# Addendum 2026-10-06T0330Z - approved packages applied (ask-before-running session, every command tapped by William)

Source: Mandatory Approvals page (collection `approvals`), all 7 read `approved` at 03:2xZ. One AMD login this session (token cached, a once-per-session guard added to the workspace amd.py).

| Package | Result | Dollars |
|---|---|---|
| A-2026-10-05T1710Z-A1 (pat17472396 hospice -> Medicare) | ALREADY APPLIED by run 2026-10-05T2110Z (digest: 5 visits insorder 1 + freq-1 rebill -> 204 x5). Re-read 0330Z: ins9511768 (FLO02) seq 1, end date blank, chart order 1,2; all 5 visits insorder 1, no payments. NOT re-run. That run used the pre-fix act_1710_1005.py (move_to_ins.move(cid,"1") rebills, then freq1_visit rebills) -> each visit may carry 2 rebills; flagged to William. | $946 |
| A-2026-10-06T0137Z-A (pat17470940) | ins9510183 carrier car6404 -> car6600 (AAR01); chart order 1,2; hideexclusions run 1700265 v19455208 / 19455208B success | $21.80 (crossover) |
| A-2026-10-06T0137Z-B (pat12232248) | ins6029665 end 06/21/2025; order 2,1 via the end-dated plan came back blank -> ONE retry via ins9517757 sequence=2,1 landed 2,1; 2025 patient balances -> insurance, no rebill: c23321127/8, 23321504, 23326170/1, 23330068, 23330503/4, 23333440/1 (2025 patbal now 0.00, insbal 1,656.00) | $1,656 moved, no rebill |
| A-2026-10-06T0137Z-C (pat17474493) | chart order 3,2; v19456837 (c23368495) + v19456905 (c23368613) insorder 3,2 + ONE freq-1 rebill each to seq 3 (UNI20) -> 204 x2; v19456976 (c23368705) insorder 3,2, no rebill | $470 re-sent |
| A-2026-10-06T0137Z-D (pat17475338) | manual_post c23337644 FLO02 pay 0.00 WOINS 153.50 chk 819814877 dep 09/19/2026 success; ins balance 184.80 -> 31.30; chart order 2,1 | $153.50 write-off |
| A-2026-10-06T0137Z-E (pat17472143) | ins9511482 carrier -> car6600 (AAR01); chart order 1,2 | $0 |
| A-2026-10-06T0137Z-F (pat17473335) | ins9513920 carrier -> car6600 (AAR01); chart order 1,2 | $0 |

Lesson: `updateinsurance` with `sequence=` sent through an END-DATED plan answers success but leaves the patient insorder blank; send the order through an active plan (B retry).

Fix committed: scripts/helpers/act_1710_1005.py now sets visit insorder with a no-rebill full-visit echo (as chat_1006_cascade.set_insorder) so freq1_visit's rebill is the only one.

Registers: registers/chat_1006_cascade_live_{A..F}_2026-10-06T0330Z.json, chat_1006_cascade_dry_ABCDEF_2026-10-06T0330Z.json, hospice_humana_b9_2026-10-05T1710Z_dry_recheck_0330Z.json (pid-only).
