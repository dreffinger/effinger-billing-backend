# PLAIN ENGLISH (1 AM ET 10/5 slot, run 2026-10-05T0510Z - ehpa cloud copy)
# Decides: nothing new - applies the standing rules to this run's Unbilled and Exclusion rows:
#  - a duplicate feed chart gets the real chart's plan copied (no group number), the visits set to it and released (10/4 Smythe Myra precedent)
#  - 'Subscriber sex is invalid' -> gender set from the real chart; 'Patient address is incomplete' -> the real chart's street via the captured Edit-address PATCH
#  - 'DOS outside coverage' on an end-dated UNI20 -> visit insorder to the live Medicare sequence (full-visit echo), released
#  - PREF0201 (Sunshine secondaries sent without a frequency code) -> freq1_visit.run per visit (frequency 1, no ref number) then hideexclusions
#  - PREF0283 Florida Blue Medigap secondaries already at frequency 1 -> completed per the 9/20 crossover-wait rule (Medicare crossover carries them), no rebill
# Never touches: paid charges, write-offs, the Hatherley inspector hold, the Delmar row (live read refused this run).
import amd, resave, add_ins, ins_update, move_to_ins, freq1_visit, patient_patch, payreasons, json, time, re, sys
amd.login_cached()
REG = {"stamp": "2026-10-05T0510Z", "steps": []}
def log(*a):
    print(*a, flush=True); REG["steps"].append(" ".join(str(x) for x in a))
def release(vid):
    ok, msg = payreasons.release_visit(vid); log("release", vid, ok, msg[:100]); return ok
def hide_excl(runid, pairs):
    r = amd.post(amd.msg("hideexclusions", "claimsreports", {"claimrunid": str(runid), "hide": "-1", "nocookie": "1"},
                 "<visitlist>%s</visitlist>" % "".join('<visit id="%s" claimid="%s"/>' % (v, c) for v, c in pairs)))
    log("hideexclusions", runid, len(pairs), re.sub(r"\s+", " ", r)[:160]); return r
try:
    # W1 SMYTHE MYRA JENNA pat17477933 - gender U -> F (real chart pat21798 F), then release v19456467
    code, txt, before = patient_patch.patch("17477933", {"gender": "F"}); after = patient_patch.flatten(patient_patch.get("17477933"))
    log("W1 smith gender PATCH", code, txt[:80], "before", before.get("gender"), "after", after.get("gender"))
    if after.get("gender") == "F": release("19456467")
    time.sleep(0.5)
    # W2 OSGOOD RAVENSCAR pat17477870 (duplicate of pat17470849) - address line 1 from the real chart, then release v19456058
    code, txt, addr = patient_patch.family_address("17477870", "5532 MOSSY TOP WAY", "", "32303", "TALLAHASSEE", "FL")
    log("W2 osgood address", code, txt[:80], addr)
    if addr.get("address1"): release("19456058")
    time.sleep(0.5)
    # W3 HOLLIS pat17476042 v19456866 - UNI20 ended 8/19/2026, Medicare seq 2 live -> visit insorder 2, release
    r = move_to_ins.move("23368527", "2"); log("W3 hollis insorder->2", str(r)[:120])
    vis, pat, allc = resave.visit_charges("23368527"); log("W3 readback insorder", vis.get("insorder"))
    if vis.get("insorder") == "2": release("19456866")
    time.sleep(0.5)
    # W4 FORSYTH DELWEN pat17477976 (duplicate of pat17477828): copy UNI20 981644036 (UHC MA C-SNP, begin 3/1/2026, no group), 271, visits insorder 1, address, release
    r = add_ins.add("17477976", "car6404", "981644036", begindate="03/01/2026"); log("W4 forsyth add_ins", str(r)[:160])
    m = re.search(r"ins(\d+)", str(r)); insid = m.group(0) if m else None
    if insid:
        try:
            e = amd.check_eligibility(insid.replace("ins", "")); st = re.search(r'eligibilitystatus\w*="([^"]*)"', e); log("W4 forsyth 271", st.group(1) if st else e[:120])
        except Exception as ex: log("W4 forsyth 271 ERR", ex)
        try: log("W4 forsyth patient order", str(ins_update.update("17477976", insid, sequence="1"))[:100])
        except Exception as ex: log("W4 forsyth ins_update ERR", ex)
        for cid, vid in (("23368608", "19456902"), ("23368615", "19456907")):
            r2 = move_to_ins.move(cid, "1"); log("W4 forsyth visit", vid, "insorder->1", str(r2)[:100])
            vis, pat, allc = resave.visit_charges(cid); log("W4 readback", vid, vis.get("insorder"), [(c.get("id"), c.get("void")) for c in allc])
            if vis.get("insorder") == "1": release(vid)
        code, txt, addr = patient_patch.family_address("17477976", "PO BOX 7461", "", "31758", "THOMASVILLE", "GA"); log("W4 forsyth address", code, txt[:80], addr)
    time.sleep(0.5)
    # W5 PRIMROSE pat17476358 - 7 Sunshine secondaries (claim run 1700266, PREF0201): frequency 1 + rebill seq 3, then complete
    primrose = [("19440713", "23348457", "19440713F"), ("19440868", "23348625", "19440868F"), ("19440883", "23348639", "19440883F"), ("19441282", "23349132", "19441282F"),
            ("19441284", "23349134", "19441284F"), ("19441299", "23349149", "19441299F"), ("19441368", "23349219", "19441368E")]
    done = []
    for vid, cid, claim in primrose:
        r = freq1_visit.run(vid, cid, 3); log("W5 primrose", vid, r)
        if "204" in str(r): done.append((vid, claim))
        time.sleep(0.6)
    if done: hide_excl("1700266", done)
    # W6 SIMMONDS pat17477260 - 9 Florida Blue Medigap secondaries already frequency 1 (PREF0283): complete per the 9/20 crossover-wait rule
    simp = [("19451560", "19451560D"), ("19451573", "19451573C"), ("19451596", "19451596C"), ("19451901", "19451901C"), ("19451911", "19451911C"),
            ("19451921", "19451921C"), ("19452058", "19452058C"), ("19452152", "19452152C"), ("19452159", "19452159C")]
    hide_excl("1700266", simp)
except Exception as ex:
    log("EXC", repr(ex)[:300])
json.dump(REG, open("registers/act_2026-10-05T0510Z.json", "w"), indent=1)
