# PLAIN ENGLISH (approvals register bookkeeping, 3 AM ET 10/14/2026 run 2026-10-14T0710Z)
# Decides: nothing about billing. Marks the five old-claims cards A-2026-10-14T0155Z-C / J / J-dec / K / K-dec "done" in
#   practices/ehpa/registers/approvals_pending.json (the repo copy AND the workspace copy) with the live-verified answer,
#   because the 0310Z run applied them (old_claims_apply.py --live, 10/13 23:47-23:50Z) and the 0710Z run read every
#   named visit live (registers/approvals_verify_2026-10-14T0710Z.json: insbal 0.00 everywhere, write-offs / payments
#   dated 10/13/2026). Step 0h: an already-applied package is recorded done and never run again.
# Never touches: AdvancedMD, the Mandatory Approvals page (updated separately through ArtifactData), any other register item.
import json, sys, shutil
ANS = {
    "A-2026-10-14T0155Z-C": "done 10/13 23:47Z (0310Z run, old_claims_apply --only C): AET07 payments $653.49 + WOINS $373.51 on 4 visits; verified live 0710Z, insbal 0.00",
    "A-2026-10-14T0155Z-J": "done 10/13 23:48Z (0310Z run, old_claims_apply --only J): WOCAID2ND on v19389115; verified live 0710Z, insbal 0.00",
    "A-2026-10-14T0155Z-J-dec": "done 10/13 23:48Z (0310Z run, old_claims_apply --only J-dec): WOINS $69.16 on 4 visits (DOS before the date of death); verified live 0710Z, insbal 0.00",
    "A-2026-10-14T0155Z-K": "done 10/13 23:48-23:50Z (0310Z run, old_claims_apply --only K): WOCAID2ND + WOINS $254.81 on 4 visits; verified live 0710Z, insbal 0.00",
    "A-2026-10-14T0155Z-K-dec": "done 10/13 23:48-23:50Z (0310Z run, old_claims_apply --only K-dec): WOCAID2ND + WOINS $59.11 on 2 visits; verified live 0710Z, insbal 0.00",
}
for path in ("/home/claude/effinger-billing-backend/practices/ehpa/registers/approvals_pending.json", "/home/claude/unbilled/registers/approvals_pending.json"):
    try:
        reg = json.load(open(path))
    except FileNotFoundError:
        print("absent", path); continue
    n = 0
    for it in reg if isinstance(reg, list) else reg.get("items", []):
        if it.get("id") in ANS and it.get("status") != "done":
            it["status"] = "done"; it["answer"] = ANS[it["id"]]; it["doneAt"] = "2026-10-14T07:50:00Z"; it["doneBy"] = "backend billing run 2026-10-14T0710Z (verified; applied by the 0310Z run)"; n += 1
    json.dump(reg, open(path, "w"), indent=1)
    print("updated", n, "items in", path)
