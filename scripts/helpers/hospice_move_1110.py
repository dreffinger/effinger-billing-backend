# PLAIN ENGLISH (hospice re-route, second pass 10/2/2026 00:xxZ, package A-2026-10-01T1110Z-A1 approved on the page)
# Decides: nothing new. hospice_reroute_1110.py --live put GV on every charge and reset frequency 1 on all 9 visits, but its
#   chargerebill answered HTTP 500 on every one because the VISIT insurance order still pointed at UHC (insorder 2 on charts 22023
#   and 21263, insorder 1 on chart 17473477) - the 9/22 registry rule: a rebill must go on the sequence the visit is billed to.
#   This pass does what rebill_patient_year does: move_to_ins.move(cid, <Medicare seq>) = full-visit echo with insorder set to the
#   Medicare sequence, then chargerebill on that sequence (204 = sent). Read-back of insorder printed per visit.
# Never touches: payments, write-offs, plans, modifiers, any visit not listed. Register: registers/hospice_move_2026-10-01T1110Z.json
import amd, move_to_ins, json, sys, time
LIVE = "--live" in sys.argv
VISITS = [("22023", "23326012", "1"), ("22023", "23334147", "1"), ("22023", "23337128", "1"), ("22023", "23338626", "1"),
          ("21263", "23350599", "1"), ("21263", "23355341", "1"), ("21263", "23326392", "1"),
          ("17473477", "23350410", "2"), ("17473477", "23358095", "2")]
amd.login_cached(); reg = []
for pid, cid, seq in VISITS:
    r = move_to_ins.move(cid, seq, dry=not LIVE); rec = {"pid": pid, "cid": cid, "seq": seq, "result": str(r)[:220]}
    print(json.dumps(rec)); reg.append(rec); time.sleep(0.6)
if LIVE: json.dump(reg, open("registers/hospice_move_2026-10-01T1110Z.json", "w"), indent=1)
print("DONE", "LIVE" if LIVE else "dry", sum(1 for r in reg if "-> 204" in r["result"]), "sent of", len(reg))
