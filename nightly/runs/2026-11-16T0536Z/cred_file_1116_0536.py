# PLAIN ENGLISH (one-off, nightly cascade 2026-11-16T0536Z): builds cred_updates_2026-11-16T0536Z.json - the 90-day
# malpractice reminder window hit on grp-malpractice. Never touches the board itself.
import json, sys
sys.path.insert(0, "/home/claude/unbilled")
from board_ops import clean_file
NOW = "2026-11-16T05:50:00Z"; STAMP = "2026-11-16T0536Z"
ops = [{"op": "update", "collection": "cred", "id": "grp-malpractice", "set": {"turn": "william", "due": "2027-02-14"}, "append": {
    "checks": [{"ok": "na", "result": "90-day reminder window: policy term read as ending 2/14/2027 (MedPro 815805); NPPES 0 changes on 3 NPIs, revalidation TBD x3, OIG LEIE 84,224 rows 0 matches", "src": "Nightly cred check (reminder window) 11/16", "when": "11/16"}],
    "notes": [{"who": "Claude", "at": NOW, "text": "90 days out: your MedPro malpractice policy [member id] term is read as ending 2/14/2027. It auto-pays quarterly, so this is mostly a check: confirm in MedPro Self Serve (or 800-463-3776) that the 2027 term will renew, and when the new certificate of insurance arrives drop the PDF here - HCA/Parallon, Florida Blue (Medversant) and Cigna each got the last one and will ask again. Say done and the card comes back to me."}]}}]
doc = clean_file({"schema": "cred-board-updates/1", "source": "nightly cascade " + STAMP, "created": NOW, "ops": ops})
json.dump(doc, open("/home/claude/unbilled/cred_updates_%s.json" % STAMP, "w"), indent=1)
print(len(ops), "ops")
