# PLAIN ENGLISH (nightly cascade 2026-11-19T0536Z): writes tonight's Credentialing Board inbox file (one reminder-window op on
# the Optum card) to outbox/cred_updates_2026-11-19T0536Z.json. No AMD or board call.
import json, sys
sys.path.insert(0, "/home/user/effinger-billing-backend/scripts/helpers")
from board_ops import clean_file
STAMP = "2026-11-19T0536Z"; AT = "2026-11-19T05:50:00Z"
ops = [{"op": "update", "collection": "cred", "id": "pay-optum", "set": {"turn": "william"},
        "append": {"checks": [{"ok": "na", "src": "Nightly cred check (reminder window) 11/19",
                               "result": "7-day reminder: UHC/Optum My Practice Profile directory attestation due about Thu 11/26/2026 (90 days after the 8/28 attestation) - attest by Wed 11/25; NPPES 0 changes on 3 NPIs, revalidation TBD x3, OIG LEIE 84,224 rows 0 matches", "when": "11/19"}],
                   "notes": [{"who": "Claude", "at": AT, "text": "7 days out: the UHC / Optum directory attestation comes due about Thu 11/26 (90 days after the 8/28 one). Sign in to the UHC Provider Portal (One Healthcare ID) > My Practice Profile, check the address reads 1891 Capital Cir NE Ste 9 and click Attest by Wed 11/25 - missing it can drop the practice from the UHC/AARP directory, and the removal notice MP-273757-FL is still open on the UHC card. Say done here and the card comes back to me."}]}}]
doc = clean_file({"schema": "cred-board-updates/1", "source": "nightly cascade " + STAMP, "created": AT, "ops": ops})
p = "/home/claude/unbilled/outbox/cred_updates_%s.json" % STAMP
json.dump(doc, open(p, "w"), indent=1); print("wrote", p, len(doc["ops"]), "ops")
