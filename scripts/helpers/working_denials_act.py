# PLAIN ENGLISH (Working Denials - ACT: correct and resubmit the denials William approved 9/12/2026)
# Decides: For each planned fix (a JSON plan file, or tonight's built-in plan): void the write-offs that silently closed the
#   visit (WOINSBANK / WOINS), apply the correction on a FULL-visit resave (every live charge echoed - the void trap),
#   move any patient balance back to insurance, set the visit's payer order, reset to frequency 1 and rebill.
# Fix kinds: hospice -> GV modifier (mcode713) on every charge + bill Medicare; dx -> replace or reorder diagnosis codes
#   (nested <diagcodelist> child - the diagcodes attr is ignored on edits); order -> visit insorder only (wrong payer).
# Rules it uses: never touch a visit that has a real payment posted; one write-off void per write-off id; verify after save.
# Never touches: charges outside the planned visits; carrier masters; anything with a payment.
"""Usage: python3 working_denials_act.py [--dry] [--plan plan.json]"""
import amd, resave, txh, void_tx, freq1_visit, era_post, json, re, sys, time, datetime, os
import xml.etree.ElementTree as ET

GV = "mcode713"
LOG = open("working_denials_act.log", "a")
def L(m): print(m, flush=True); LOG.write("%s %s\n" % (datetime.datetime.utcnow().strftime("%H:%M:%S"), m)); LOG.flush()

def charge_state(pid, vid):
    """live charges of a visit from tx history: (cid, payments[], writeoffs[(woid, code, amt)], insbal, patbal)"""
    out = []
    for c in txh.fetch(pid).iter("charge"):
        if c.get("visit") != str(vid) or c.get("void") == "1": continue
        pays = [p for p in c.iter("payment") if p.get("void") != "1" and float(p.get("amount") or 0) != 0]
        wos = [(w.get("id"), w.get("wocode"), w.get("amount")) for w in c.iter("writeoff") if w.get("void") != "1" and float(w.get("amount") or 0) != 0]
        out.append({"cid": c.get("id"), "pays": len(pays), "wos": wos, "insbal": float(c.get("insbal") or 0), "patbal": float(c.get("patbal") or 0), "cpt": c.get("proccode")})
    return out

def save_visit(cid, dx_map=None, dx_reorder_last=None, add_mod=None, insorder=None, dry=False):
    """Full-visit resave. dx_map: {old_dcode: new_dcode}; dx_reorder_last: dcode to move to the end;
    add_mod: mcode id appended to every charge's modcodes; insorder: visit payer order string like '2,1'.
    Balances: patient balance moved back to insurance on every charge (a voided write-off can land on the patient)."""
    vis, pat, allc = resave.visit_charges(cid)
    chg = ""; edited = 0
    for c in allc:
        a = {"id": c.get("id")}
        for f in resave.CHG_FIELDS:
            if c.get(f) is not None: a[f] = c.get(f)
        pb = float(c.get("patbalance") or 0)
        if pb > 0:
            a["insbalance"] = "%.2f" % (float(c.get("insbalance") or 0) + pb); a["patbalance"] = "0.00"
            a["insportion"] = "%.2f" % (float(c.get("insportion") or 0) + float(c.get("patportion") or 0)); a["patportion"] = "0.00"
        if add_mod:
            mods = (a.get("modcodes") or "").split()
            if add_mod not in mods: mods.append(add_mod); a["modcodes"] = " ".join(mods); edited += 1
        child = ""
        dx = (c.get("diagcodes") or "").split()
        if dx_map or dx_reorder_last:
            new = [dx_map.get(x, x) for x in dx] if dx_map else list(dx)
            if dx_reorder_last and dx_reorder_last in new: new = [x for x in new if x != dx_reorder_last] + [dx_reorder_last]
            if new != dx:
                a["diagcodes"] = " ".join(new); edited += 1
                child = "<diagcodelist>%s</diagcodelist>" % "".join('<diagcode id="%s"/>' % re.sub(r"\D", "", x) for x in new)
        chg += "<charge %s>%s</charge>" % (" ".join('%s="%s"' % (k, v) for k, v in a.items()), child)
    va = dict(vis.attrib); va["force"] = "1"
    if insorder: va["insorder"] = str(insorder)
    vs = " ".join('%s="%s"' % (k, v) for k, v in va.items())
    if dry: return "DRY save: %d charges, %d edits, insorder=%s" % (len(allc), edited, va.get("insorder"))
    body = amd.msg("updvisitwithcharges", "chargeentry",
        {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1", "inspectorenabled": "1",
         "batchid": str(era_post.batch()), "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
        "<visit %s><chargelist>%s</chargelist></visit>" % (vs, chg))
    r = amd.post(body); time.sleep(0.8)
    if "Fault" in r: return "FAULT " + re.sub(r"\s+", " ", r[:220])
    v2, p2, c2 = resave.visit_charges(cid)
    det = [(x.get("proccode"), x.get("diagcodes"), x.get("modcodes"), x.get("insbalance"), x.get("patbalance")) for x in c2]
    return "saved: %d live charges (was %d), insorder=%s, charges=%s" % (len(c2), len(allc), v2.get("insorder"), det)

def act(item, dry):
    """item: {who, pid, vid, cid, seq, fix: hospice|dx|order, dx_map, dx_last, insorder, note}"""
    st = charge_state(item["pid"], item["vid"])
    if not st: L("  SKIP %s v%s: no live charges" % (item["who"], item["vid"])); return "skip"
    if any(s["pays"] for s in st): L("  SKIP %s v%s: a payment is posted - never rebill a paid visit" % (item["who"], item["vid"])); return "skip-paid"
    # 1) void write-offs
    for s in st:
        for woid, code, amt in s["wos"]:
            if dry: L("  DRY void write-off %s %s %s on charge %s" % (woid, code, amt, s["cid"])); continue
            ok, msg = void_tx.void_writeoff(item["pid"], s["cid"], woid); L("  void wo %s %s %s -> %s %s" % (woid, code, amt, ok, msg[:80])); time.sleep(0.4)
    # 2) fix + resave (also moves patient balance back to insurance, sets payer order)
    kw = {}
    if item["fix"] == "hospice": kw["add_mod"] = GV
    if item["fix"] == "dx": kw["dx_map"] = item.get("dx_map"); kw["dx_reorder_last"] = item.get("dx_last")
    r = save_visit(item["cid"], insorder=item.get("insorder"), dry=dry, **kw); L("  %s" % r)
    if dry or r.startswith("FAULT"): return r
    # 3) freq-1 + rebill the target sequence
    r2 = freq1_visit.run(str(item["vid"]), str(item["cid"]).replace("charge", ""), item["seq"]); L("  %s" % r2); time.sleep(0.4)
    return r2

if __name__ == "__main__":
    dry = "--dry" in sys.argv
    plan = json.load(open(sys.argv[sys.argv.index("--plan") + 1])) if "--plan" in sys.argv else json.load(open("wd_plan.json"))
    amd.login_cached()
    L("=== WORKING DENIALS ACT %s dry=%s items=%d ===" % (datetime.date.today(), dry, len(plan)))
    res = {}
    for it in plan:
        L("%s v%s %s %s: %s" % (it["who"], it["vid"], it["fix"], it.get("note", ""), "..."))
        try: res[it["vid"]] = act(it, dry)
        except Exception as e: res[it["vid"]] = "ERROR %s" % str(e)[:160]; L("  ERROR %s" % str(e)[:160])
    L("=== done: %s ===" % json.dumps({k: str(v)[:60] for k, v in res.items()}))
    ok = {str(k): datetime.date.today().strftime("%-m/%-d") for k, v in res.items() if "-> 204" in str(v)}
    if ok and not dry:
        prev = json.load(open("wd_resubmitted.json")) if os.path.exists("wd_resubmitted.json") else {}
        prev.update(ok); json.dump(prev, open("wd_resubmitted.json", "w"), indent=1); L("marked %d visits RESUBMITTED" % len(ok))
