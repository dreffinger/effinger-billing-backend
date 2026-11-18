# PLAIN ENGLISH (nightly cascade 2026-11-18T0536Z): writes tonight's Credentialing Board inbox file (one reminder-window op on
# the Centene card) to outbox/cred_updates_2026-11-18T0536Z.json. No AMD or board call.
import json, sys
sys.path.insert(0, "/home/user/effinger-billing-backend/scripts/helpers")
from board_ops import clean_file
STAMP = "2026-11-18T0536Z"; AT = "2026-11-18T05:50:00Z"
ops = [{"op": "update", "collection": "cred", "id": "pay-centene", "set": {"turn": "william"},
        "append": {"checks": [{"ok": "na", "src": "Nightly cred check (reminder window) 11/18",
                               "result": "7-day reminder: the two remaining Sunshine Health Relias courses are due Wed 11/25/2026; NPPES 0 changes on 3 NPIs, revalidation TBD x3, OIG LEIE 84,224 rows 0 matches", "when": "11/18"}],
                   "notes": [{"who": "Claude", "at": AT, "text": "7 days out: the last two of Sunshine Health's eight required Relias courses are due by Wed 11/25 (your calendar has Tue 11/24, 9:00 AM). Finish them at sshp.training.reliaslearning.com (login = the practice TIN) and keep the completion record; Sunshine can suspend a provider for non-compliance. Say done here and the card comes back to me."}]}}]
doc = clean_file({"schema": "cred-board-updates/1", "source": "nightly cascade " + STAMP, "created": AT, "ops": ops})
p = "/home/claude/unbilled/outbox/cred_updates_%s.json" % STAMP
json.dump(doc, open(p, "w"), indent=1); print("wrote", p, len(doc["ops"]), "ops")
