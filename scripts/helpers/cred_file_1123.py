# PLAIN ENGLISH (nightly cascade 2026-11-23T0536Z): writes tonight's Credentialing Board inbox file - one 7-day reminder
# op on the we-board card (AOBFP Longitudinal Assessment due 11/30/2026). No board call.
import json, sys
sys.path.insert(0, "/home/user/effinger-billing-backend/scripts/helpers")
from board_ops import clean_file
AT = "2026-11-23T06:05:00Z"
doc = {"schema": "cred-board-updates/1", "source": "nightly cascade 2026-11-23T0536Z", "created": AT, "ops": [
 {"op": "update", "collection": "cred", "id": "we-board", "set": {"turn": "william"}, "append": {
  "checks": [{"ok": "na", "result": "7-day reminder: AOBFP Longitudinal Assessment due 11/30/2026 (yearly, 30 questions); NPPES 0 changes on 3 NPIs, revalidation TBD x3, OIG LEIE 84,224 rows 0 matches", "src": "Nightly cred check (reminder window) 11/23", "when": "11/23"}],
  "notes": [{"who": "Claude", "at": AT, "text": "7 days out: the AOBFP yearly Longitudinal Assessment (30 questions) is due Mon 11/30/2026 - complete it in the AOA/AOBFP physician portal (diplomate 162301). Post 'done' here and the card comes back to me."}]}}]}
clean_file(doc)
p = sys.argv[1]
json.dump(doc, open(p, "w"), indent=1); print(p)
