# PLAIN ENGLISH (set the building on a feed visit that went in with none - card ccm-building-not-in-table-1125, 11/25/2026)
# Decides: nothing. William's card: 15 November CCM visits were entered with no building because the feed spelled the building
#   "Oakes Southwood", which the import's facility table does not know. The residents' own nursing visits on those charts carry the
#   Southwood building's record fac1350 (OAKES SOUTHWOOD); this sets that facility on each visit with a full-visit echo save.
# Rules it uses: resave.visit_charges + the round-8 echo guard (nothing sent when the live charges could not all be read or the asked
#   charge is not among them); never saves a billed visit; echoes every live charge with resave.CHG_FIELDS (place of service, codes,
#   amounts, modifiers as read - POS 32 stays); keeps insorder, profile and every other visit attribute; reads back facility, the live
#   charge list and each charge's POS. --dry first.
# Never touches: insurance order, codes, places of service, amounts, balances, plans.
# Usage: python3 set_facility_1125.py <facility> <chargeid> [<chargeid> ...] [--live]
import sys, re, time, json
import amd, resave

def one(fac, chargeid, live):
    resave.READ_NOTE = ""
    vis, pat, allc = resave.visit_charges(re.sub(r"\D", "", chargeid)); note = resave.READ_NOTE
    asked = re.sub(r"\D", "", chargeid); got = [re.sub(r"\D", "", c.get("id") or "") for c in allc]
    if note or not allc or asked not in got:
        return False, "visit %s: nothing sent - charges not all read (%d read; note %s)" % (vis.get("id"), len(allc), note)
    if vis.get("facility") == fac:
        return True, "visit %s facility already %s - skipped" % (vis.get("id"), fac)
    billed = resave.billed_reasons(allc)
    if billed:
        return False, "visit %s already billed (%s) - not saved" % (vis.get("id"), ", ".join(billed))
    pos0 = {c.get("id"): c.get("pos") for c in allc}
    chg = ""
    for c in allc:
        a = {"id": c.get("id")}
        for f in resave.CHG_FIELDS:
            if c.get(f) is not None: a[f] = c.get(f)
        chg += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in a.items())
    va = dict(vis.attrib); va["force"] = "1"; fac0 = va.get("facility"); va["facility"] = fac
    if not live:
        return True, "DRY visit %s facility %s -> %s, insorder %s, %d live charges echoed, pos %s" % (vis.get("id"), fac0, fac, vis.get("insorder"), len(allc), sorted(set(pos0.values())))
    r = amd.post(amd.msg("updvisitwithcharges", "chargeentry", {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1",
                 "inspectorenabled": "1", "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
                 "<visit %s><chargelist>%s</chargelist></visit>" % (" ".join('%s="%s"' % (k, v) for k, v in va.items()), chg)))
    time.sleep(0.8)
    if "Fault" in r:
        return False, "FAULT visit %s: %s" % (vis.get("id"), re.sub(r"\s+", " ", r[:300]))
    resave.READ_NOTE = ""
    v2, p2, c2 = resave.visit_charges(asked)
    live2 = [c.get("id") for c in c2]; pos2 = {c.get("id"): c.get("pos") for c in c2}
    ok = (v2.get("facility") == fac and sorted(live2) == sorted(pos0) and pos2 == pos0 and v2.get("insorder") == vis.get("insorder") and not resave.READ_NOTE)
    return ok, "visit %s facility %s -> %s read back %s; live charges %s (was %s); pos %s; insorder %s%s" % (
        vis.get("id"), fac0, fac, v2.get("facility"), len(live2), len(pos0), sorted(set(pos2.values())), v2.get("insorder"), "" if ok else " - NOT AS ASKED")

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]; live = "--live" in sys.argv
    fac, cids = args[0], args[1:]
    out = []
    for cid in cids:
        try: ok, msg = one(fac, cid, live)
        except Exception as e: ok, msg = False, "charge %s: %s %s" % (cid, type(e).__name__, str(e)[:120])
        print(("OK  " if ok else "NO  ") + msg); out.append({"charge": cid, "ok": ok, "msg": msg})
    if live:
        json.dump(out, open("registers/set_facility_1125_%s.json" % time.strftime("%Y%m%dT%H%MZ", time.gmtime()), "w"), indent=1)
