# nightly/live - the prompts that fire (11/2/2026)

William 11/2/2026: "make it permanent where I don't have to manually push anything." A Claude Code routine's stored prompt cannot be edited by an agent when the routine was created in the claude.ai UI, and a routine an agent creates cannot carry the repository or the connectors in this organization - so the stored prompt of each billing routine is now a SHORT POINTER (`nightly/live/_stub_<routine>.txt`) and the instructions live here, in files `mirror.py sync` pushes to `main` on its own:

| routine | stored prompt (pointer) | instructions |
|---|---|---|
| ehpa Billing Button (trig_01S771Si8VJ8DvcwgHMHGYB5, agent-updatable) | `_stub_billing_button.txt` | `billing_button.txt` |
| Backend billing run - Claims Center columns every 6 hours (trig_01QRqT8KB4Q1H9EyYRG4NBKX, UI-created) | `_stub_columns.txt` | `columns.txt` |
| Nightly insurance cascade (trig_01XVrVN9dpSdvAbB1ZrsAzFU, UI-created) | `_stub_cascade.txt` | `cascade.txt` |

To change what a routine does: edit its file here, `mirror.py sync` - the next firing fetches `main` and follows the new text. Nothing is pasted into a routine again. The pointer stubs change only if the file path or the bootstrap changes.

The files are the texts that were live on 11/2/2026 plus the 11/2 board rule (never `updated` in a board_updates set; one card per work item, twinned by chart): `columns.txt` is the v7 9/15/2026 generation with the 10/28 FEED step (NOT the repo's v12 file - the two drifted; consolidating them is William's call), `cascade.txt` is the 10/22 generation (without the 10/6 additions of the v3 file - same drift), `billing_button.txt` is v3 10/31 with the retired 5(b2) UNI20/BCBS passage replaced by the rules.md 11/2 pointer (the stored prompt was at the 65,536-byte cap).
