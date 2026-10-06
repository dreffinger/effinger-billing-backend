# PLAIN ENGLISH (Florida Blue 'diagnosis invalid for the date of service' corrected claim - pat17475338 v19431100, 9 PM ET 10/5/2026 run)
# Decides: Florida Blue's 9/7/2026 letter (claim H100001347265276, acct 19431100E, DOS 01/27/2026 99223 $310) says the
#   diagnosis M86.8X8 'is invalid for the date of service - resubmit a corrected claim'. The visit carries two diagnoses:
#   M86.171 (other acute osteomyelitis, right ankle and foot) first and M86.8X8 (other osteomyelitis, other site) second.
#   William's dx cascade order (9/14): DELETE the refused code if another acceptable code remains -> M86.171 stays as the
#   only (and more specific) diagnosis; nothing is invented, no I10 needed. Medicare already PAID this visit (check 819814877,
#   $125.20, 9/19/2026) so the resend is NOT a frequency-1 rebill of a paid visit: it is the SECONDARY corrected claim to
#   Florida Blue, frequency 7 with Florida Blue's own claim number (William 9/14: frequency 7 with the payer's claim number
#   once it is in hand). Visit insurance order set Medicare first, Florida Blue second so the secondary claim carries the COB.
# Rules it uses: live read before every write; full-visit echo on the dx save with read-back verification; --dry first.
# Never touches: the Medicare payment, balances, any other visit, the Medicare contractual (the 51-line 'repair them' question
#   is William's, row paper-eob-writeoffs-0923).
import amd, dx_primary_fix as D, move_to_ins, freq7_visit, amdw, resave, json, sys, re, time, datetime
PID, VID, CID = "17475338", "19431100", "23337644"
ICN = "H100001347265276"; KEEP = ["dcode1034545247"]; BAD = "dcode1037453494"
DRY = "--live" not in sys.argv; STAMP = "2026-10-06T0110Z"
amd.login_cached(); log = []
def L(s): print(s, flush=True); log.append(s)
pl, resp, dob, name, _ = amdw.plans(PID)
seqs = {p.get("carriercode") or p.get("carrier"): p.get("seq") for p in pl if "id" in p}
L("plans: %s" % [(p.get("id"), p.get("carriercode") or p.get("carrier"), p.get("seq"), p.get("end")) for p in pl if "id" in p])
car = {p.get("seq"): (p.get("carriercode") or p.get("carrier")) for p in pl if "id" in p and not p.get("end")}
L("carriers by seq: %s" % car)
med_seq = next((s for s, c in car.items() if c in ("car6085", "FLO02")), None)
fb_seq = next((s for s, c in car.items() if c in ("car6062", "BCBS")), None)
if not med_seq or not fb_seq:
    L("STOP: cannot identify Medicare/Florida Blue sequences - %s" % car); sys.exit(1)
st = D.live_state(PID, VID); L("live: %s" % st)
vis, pat, allc, m = D.visit_dx(CID)
cur = [(c.get("id"), (c.get("diagcodes") or "").split()) for c in allc]
L("dx now: %s -> %s" % (cur, {d: m.get(d) for d in sum([x[1] for x in cur], [])}))
if [x[1] for x in cur if x[0] == "charge" + CID] == [KEEP]:
    L("dx already corrected")
else:
    r, det = D.save_visit_dx(CID, {"charge" + CID: KEEP}, dry=DRY); L("dx save: %s %s" % (r, det))
    if not DRY:
        if r.startswith("FAULT") or det.get("charge" + CID, (None, None))[1] != KEEP:
            L("VERIFY-FAILED - stopping before the resend"); json.dump(log, open("registers/act_%s.json" % STAMP, "w"), indent=1); sys.exit(1)
order = "%s,%s" % (med_seq, fb_seq)
r2 = move_to_ins.move(CID, seq=order, dry=DRY); L("insorder %s: %s" % (order, r2))
if DRY:
    L("DRY: would send freq7 icn %s to seq %s" % (ICN, fb_seq))
else:
    r3 = freq7_visit.run(VID, CID, fb_seq, ICN); L("freq7: %s" % r3)
    time.sleep(0.5); d2 = resave.detail(CID)
    L("readback: %s | %s" % (re.findall(r'<diagcode [^>]*code="([^"]+)"', d2), re.findall(r'(insorder|resubmissioncode|origrefnum)="([^"]*)"', d2)))
json.dump({"stamp": STAMP, "live": not DRY, "log": log, "at": datetime.datetime.utcnow().isoformat() + "Z"},
          open("registers/act_%s%s.json" % (STAMP, "" if not DRY else "_dry"), "w"), indent=1)
