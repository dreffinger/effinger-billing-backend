# PLAIN ENGLISH: builds this run's board_updates_2026-11-19T0756Z.json (irb-board-updates/1) through board_ops - two ops:
#   (1) a new card for the feed chart 17478470 (HCA admission, no plan anywhere: discovery 0, Medicare look-up AAA 15) on William's turn - its fields come from inbox/board_new_row_0756.json;
#   (2) a check + note on [name]-17478219 (CHP eligibility with the MBI as member id -> AAA 72; the card photo IMG_9007.jpeg confirms
#       the MBI already on the chart; CHP member number still needed). No `updated`, no status change on an existing row.
import json, datetime
from board_ops import clean_file, plan_new_row
NOW = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
STAMP = "2026-11-19T0756Z"
items = []   # the inline board read found no card on chart 17478470 (query amdid == 17478470 -> none)
new_row = json.load(open('inbox/board_new_row_0756.json'))   # the card's fields (PHI) live in inbox/, never in this file
for n in new_row.get('notes', []): n['at'] = n.get('at') or NOW
ops = plan_new_row(items, new_row, same_item=False, now=NOW)
ops.append({"op": "upsert", "collection": "items", "id": "[name]-17478219", "set": {},
    "append": {"checks": [{"ok": "no", "result": "AAA 72 Invalid/Missing Subscriber/Insured ID - CHP does not take the MBI as a member id; the card photo IMG_9007.jpeg (Drive, 07:37Z) shows the same MBI the chart already carries (plan ins9521027), no CHP number on it",
                           "src": "Stedi CHP (95112) eligibility with the MBI as member id, DOS 10/22/2026 - ehpa Billing Button run %s" % STAMP, "when": "11/19"}],
               "notes": [{"who": "Claude", "at": NOW, "text": "Tried CHP's eligibility with the Medicare number from your card photo - CHP answers 'invalid subscriber id' (AAA 72); the Medicare number already on the chart matches the card. Still needed: her Capital Health Plan member number (CHP card or facesheet) - Medicare says CHP is the payer on 10/22/2026, so the two visits ($639) wait on it."}]}})
doc = {"schema": "irb-board-updates/1", "source": "ehpa billing button run %s" % STAMP, "created": NOW, "ops": ops}
doc = clean_file(doc)
json.dump(doc, open("board_updates_%s.json" % STAMP, "w"), indent=1)
print(len(ops), "ops ->", "board_updates_%s.json" % STAMP)
