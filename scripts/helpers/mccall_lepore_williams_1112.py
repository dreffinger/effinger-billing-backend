# PLAIN ENGLISH (three board answers, 9/12 7am ET run):
#  MARLOWE (marlowe-bettina-denials 08:49): (1) patient default order Medicare first = ins_update sequence "2,1"; (2) the 4/29/2026
#    99349 and 5/17/2026 CCM visits: void the partial WOINS, move the patient balance back to insurance, visit insorder 2,1,
#    freq-1 rebill Medicare (seq 2).
#  ABERNATHY (abernathy-corvin 08:55): William added the HIG07 plan (seq 2, car307793); freq-1 + insorder 2 + rebill both April visits.
#  ROWANTREE ULLA (rowantree-ulla-cob 09:15): Care Improvement Plus = CIPSC (car302740); add it with the chart's
#    UHC member id, 3/1/2023-9/30/2023, void the two WOINSBANK on the 6/6/2023 visit, bill that plan.
# Rules: freq-1 before every rebill; full-visit echo; balances never left on the patient.
import amd, ins_update, add_ins, void_tx, freq1_visit, move_to_ins, txh, re, time, json
LOG = open("marlowe_abernathy_rowantree_1112.log", "a")
def L(m): print(m, flush=True); LOG.write(m + "\n"); LOG.flush()
amd.login_cached()
# --- Marlowe
L("== MARLOWE pat17474082")
L("  patient order 2,1: %s" % (ins_update.update("17474082", "ins9515318", sequence="2,1"),))
d = amd.post(amd.msg("getdemographic", "demographics", {"patientid": "17474082", "nocookie": "1"}))
L("  readback patient insorder=%s plans=%s" % (re.search(r'<patient [^>]*insorder="([^"]*)"', d).group(1), [(a.get("id"), a.get("carrier"), a.get("sequence")) for a in (dict(re.findall(r'(\w+)="([^"]*)"', ip)) for ip in re.findall(r'<insplan [^>]*>', d))]))
for vid, cid, wos in (("19440499", "23348188", ["22475812"]), ("19442533", "23350717", ["22475783"]), ("19442533", "23350718", ["22475784"])):
    for wo in wos: L("  void WOINS %s on c%s -> %s" % (wo, cid, void_tx.void_writeoff("17474082", cid, wo))); time.sleep(0.4)
for vid, cid in (("19440499", "23348188"), ("19442533", "23350717")):
    L("  " + freq1_visit.run(vid, cid, 2)); time.sleep(0.4)
    L("  " + str(move_to_ins.move(cid, "2,1", rebill_seq=2))); time.sleep(0.4)
# --- Abernathy
L("== ABERNATHY pat17476115")
for vid, cid in (("19437941", "23345043"), ("19437921", "23345023")):
    L("  " + freq1_visit.run(vid, cid, 2)); time.sleep(0.4)
    L("  " + str(move_to_ins.move(cid, "2", rebill_seq=2))); time.sleep(0.4)
# --- Rowantree Ulla
L("== ROWANTREE ULLA pat24350")
insid, seq = add_ins.add("24350", "car302740", json.load(open("secrets/run_1112_ids.json"))["rowantree_u_member"], "03/01/2023"); L("  add CIPSC -> %s seq %s" % (insid, seq))
if insid:
    L("  end-date 09/30/2023 -> %s" % (ins_update.update("24350", insid, enddate="09/30/2023"),))
    for cid, wo in (("21343887", "22400763"), ("21343888", "22400764")):
        L("  void WOINSBANK %s on c%s -> %s" % (wo, cid, void_tx.void_writeoff("24350", cid, wo))); time.sleep(0.4)
    L("  " + freq1_visit.run("14024968", "21343887", seq)); time.sleep(0.4)
    L("  " + str(move_to_ins.move("21343887", str(seq), rebill_seq=int(seq))))
# balances readback
for pid in ("17474082", "17476115", "24350"):
    root = txh.fetch(pid)
    for c in root.iter("charge"):
        a = c.attrib
        if a.get("void") == "1": continue
        if a.get("id") in ("23348188", "23350717", "23350718", "23345043", "23345023", "21343887", "21343888"):
            L("  readback pat%s c%s %s %s ins=%s pat=%s car=%s insbilled=%s" % (pid, a.get("id"), a.get("proccode"), a.get("dos"), a.get("insbal"), a.get("patbal"), a.get("carrier"), a.get("insbilled")))
