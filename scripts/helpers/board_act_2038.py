# PLAIN ENGLISH (Insurance Refresh Board answers of 11/2/2026 afternoon - William's words on three rows, ehpa Billing Button run 2026-11-02T2038Z)
# Decides: nothing new - it carries out what William wrote on each board row between 19:03Z and 20:30Z on 11/2/2026, one lettered section per chart:
#   A DAFFIN 17477533   - 'Date of Birth [DOB]' (Medicare's record): chart DOB [DOB] -> [DOB] (REST PATCH with familyupdate,
#                          placeholder address ALF when the chart has no street), AMD 271 on the FLO02 plan must answer ACTIVE, then the
#                          10/25/2026 CCM v19459144 (99487 $206) goes to Medicare (seq 2) again as an original.
#   B MAPLIN 17469446  - 'write off' (WOCAID2ND, dual residual): the 7/1/2025 99308 residual $12.14 on charge 22484496 (visit v19409077,
#                          held in the Claim Inspector) -> WOCAID2ND, check reference BOARD1102B.
#   C TOLLIVER 17471204    - 'i added the date of birth there resend': the four Aetna (AET07 seq 2) claims 2/3, 2/4, 3/8, 3/9/2026 ($703)
#                          go again as originals (frequency 1), one rebill per visit.
# Rules it uses: one frequency-1 rebill per visit (freq1_visit.run; amd.rebill_charge's per-run guard + deceased guard); manual_post.post for
#   the write-off (never over-apply); patient_patch.get/flatten + the familyupdate PATCH for a DOB (proven 11/2 on charts 47979 / 17478213);
#   elig_amd's free 271 read-only.
# Never touches: charts not named above; payments; the ERA Center. --dry (default) reads and prints the plan; --live writes.
# Usage: python3 board_act_2038.py [--live] [--only A,B,C]   register: registers/board_act_2026-11-02T2038Z.json (chart/visit ids only)
import sys, re, json, time, os, copy, datetime
sys.path.insert(0, "/home/claude/unbilled")
import amd, resave, freq1_visit, manual_post, patient_patch, elig_amd, requests
LIVE = "--live" in sys.argv
ONLY = set(sys.argv[sys.argv.index("--only") + 1].split(",")) if "--only" in sys.argv else None
STAMP = "2026-11-02T2038Z"; REG = "registers/board_act_%s.json" % STAMP
reg = json.load(open(REG)) if os.path.exists(REG) else {"stamp": STAMP, "live": LIVE, "steps": []}
done = set(s["key"] for s in reg["steps"] if s.get("ok") and s.get("live"))
def rec(key, ok, msg):
    print(("OK   " if ok else "FAIL ") + key + " | " + str(msg)[:300], flush=True)
    reg["steps"].append({"key": key, "ok": bool(ok), "msg": str(msg)[:400], "at": datetime.datetime.utcnow().isoformat() + "Z", "live": LIVE})
    json.dump(reg, open(REG, "w"), indent=1)
def want(sec): return ONLY is None or sec in ONLY
def step(key, fn):
    if key in done: print("skip (done)", key); return True
    if not LIVE: print("DRY  " + key); return True
    try: ok, msg = fn()
    except Exception as e: ok, msg = False, "EXC %s" % str(e)[:200]
    rec(key, ok, msg); time.sleep(0.6); return ok

amd.login_cached()

def resend_step(sec, vid, cid, seq):
    def f():
        r = freq1_visit.run(vid, cid, seq); return ("204" in str(r) or "ok" in str(r).lower()), r
    return step("%s freq1 v%s seq %s" % (sec, vid, seq), f)

def patch_dob(pid, dob_iso, addr1):
    web, tok = amd.login_cached()
    p = patient_patch.get(pid); orig = patient_patch.flatten(p); upd = copy.deepcopy(orig)
    cur = {"address1": orig.get("address1") or addr1, "address2": orig.get("address2") or "", "zipcode": orig.get("zipcode") or "32308-4486",
           "city": orig.get("city") or "TALLAHASSEE", "state": orig.get("state") or "FL", "countrycode": "USA"}
    upd.update(cur); upd["dob"] = dob_iso + "T00:00:00"; upd["updateaccounttype"] = False
    for n in upd.get("names", []): n.setdefault("prefixSuffix", {"prefix": n.get("prefix") or "", "suffix": n.get("suffix") or ""})
    body = {"updatedpatient": upd, "originalpatient": orig, "updateaccounttype": False,
            "familyupdate": {"capturepreviousaddress": False, "responsiblepartyid": orig["responsiblepartyfid"], "patientids": [0], "homephone": orig.get("homephone") or "", "newaddress": cur},
            "deleteappointments": False}
    r = requests.patch(patient_patch.H % pid, json=body, timeout=60, headers={"Authorization": "Bearer " + tok, "Accept": patient_patch.ACC, "Content-Type": "application/json"})
    after = patient_patch.flatten(patient_patch.get(pid)).get("dob")
    return (r.status_code in (200, 204) and str(after).startswith(dob_iso)), "HTTP %s dob now %s %s" % (r.status_code, after, r.text[:150])

# ---------------- A DAFFIN 17477533 ----------------
if want("A"):
    pid = "17477533"
    if not LIVE:
        orig = patient_patch.flatten(patient_patch.get(pid)); print("DRY  A chart dob", orig.get("dob"), "address1", orig.get("address1") or "(none -> ALF)")
    if step("A dob [DOB]", lambda: patch_dob(pid, "[DOB yyyy-mm-dd - real value in the Drive workspace-mirror copy]", "ALF")):
        def elig():
            out = []; active = False
            for insid in ("9521009", "9518956"):
                r = elig_amd.run_plan(pid, insid, force=True); line = elig_amd.one_line(r); out.append("ins%s: %s" % (insid, line[:160]))
                if str(r.get("status", "")).upper().startswith("ACTIVE"): active = True
            return active, " | ".join(out)
        if step("A 271 FLO02 after the DOB", elig):
            resend_step("A", "19459144", "23371547", 2)
# ---------------- B MAPLIN 17469446 ----------------
if want("B"):
    note = "William 11/2/2026 board: write off (WOCAID2ND, dual residual) - 7/1/2025 99308 Medicare coinsurance, Humana Medicaid residual"
    if not LIVE:
        print("DRY  B", manual_post.post("22484496", "HUM01", 0.0, 12.14, "WOCAID2ND", "BOARD1102B", None, note, dry=True))
    step("B wo c22484496 WOCAID2ND 12.14", lambda: manual_post.post("22484496", "HUM01", 0.0, 12.14, "WOCAID2ND", "BOARD1102B", None, note))
# ---------------- C TOLLIVER 17471204 ----------------
if want("C"):
    for vid, cid in (("19431511", "23338125"), ("19431654", "23338321"), ("19435174", "23342168"), ("19435175", "23342169")):
        resend_step("C", vid, cid, 2)
print("done; register", REG, "live" if LIVE else "dry")
