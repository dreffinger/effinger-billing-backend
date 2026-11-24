# PLAIN ENGLISH (nightly cascade 2026-11-24T0536Z): writes tonight's Credentialing Board inbox file - one 7-day reminder
# op on the we-medicaid card (Florida Medicaid provider agreement renewal, card due 12/1/2026, agreement expires 12/27/2026). No board call.
import json, sys
sys.path.insert(0, "/home/user/effinger-billing-backend/scripts/helpers")
from board_ops import clean_file
AT = "2026-11-24T06:00:00Z"
doc = {"schema": "cred-board-updates/1", "source": "nightly cascade 2026-11-24T0536Z", "created": AT, "ops": [
 {"op": "update", "collection": "cred", "id": "we-medicaid", "set": {"turn": "william"}, "append": {
  "checks": [{"ok": "human", "result": "7-day reminder: card due 12/1/2026 for the Florida Medicaid provider agreement renewal (individual ID 112928800, agreement expires 12/27/2026); NPPES 0 changes on 3 NPIs, revalidation TBD x3, OIG LEIE 84,224 rows 0 matches", "src": "Nightly cred check (reminder window) 11/24", "when": "11/24"}],
  "notes": [{"who": "Claude", "at": AT, "text": "7 days out: the renewal of your Florida Medicaid provider agreement (ID 112928800) is due on this card Tue 12/1 - the agreement itself expires Sun 12/27/2026. If not filed yet: reset the mymedicaid-florida.com password if needed, file the renewal (fix the address, background-screening proof), save the confirmation PDF and drop it here. If it is already filed, post the confirmation and the card comes back to me."}]}}]}
clean_file(doc)
p = sys.argv[1]
json.dump(doc, open(p, "w"), indent=1); print(p)
