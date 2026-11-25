# PLAIN ENGLISH (write-offs William ordered on the Insurance Refresh Board, 11/25/2026)
# Decides: nothing. William wrote "write off" on two cards tonight (11/25/2026 04:37-04:38 UTC):
#   card-17476912 - WellCare finalized the 6/22/2026 initial NF visit (99306 + 99497, v19445941) at $0 three times
#     (CARC 252, wants documentation): the open insurance balance of both charges is written off WONCS (non-covered).
#   chp-pr242-card-4131654 - Capital Health Plan answered seven CCM / AWV lines PR-242 / CO-243 'not provided by network /
#     primary care providers' (check 4131654, ERA 1053550): the open insurance balance of each named charge is written off WONCS.
# Does: per charge id, reads the LIVE charge (manual_post reads resave.detail), refuses one whose open insurance balance is 0 or that
#   already carries a non-void write-off of this run's reference, posts manual_post.post(cid, <carrier code>, 0.0, <balance>, "WONCS",
#   "BOARD1125", None, "<note>") - --dry prints what it would post. Register registers/board_wo_2026-11-25T0435Z[_dry].json.
# Never touches: payments, other charges, the patient balance. Usage: python3 board_wo_1125.py [--live]
import amd, resave, manual_post, re, json, sys
LIVE = "--live" in sys.argv; S = "2026-11-25T0435Z"
# (card, pid, visit, charge, carrier code, note)
ITEMS = [
    ("card-17476912", "17476912", "19445941", "23354840", "WEL04", "WellCare CARC 252 x3 - William 11/25/2026 'write off'"),
    ("card-17476912", "17476912", "19445941", "23354841", "WEL04", "WellCare CARC 252 x3 - William 11/25/2026 'write off'"),
]
CHP = [("46678", "19442338"), ("46678", "19448386"), ("46678", "19452574"), ("21491", "19459620"), ("48008", "19423586"), ("17474083", "19434037"), ("17476942", "19459617")]
amd.login_cached()
# the CHP visits: every live charge of the visit carrying an insurance balance at CAP07
import txh
for pid, vid in CHP:
    root = txh.fetch_visit(pid, vid)
    for c in root.iter("charge"):
        a = c.attrib
        if a.get("void") == "1": continue
        cid = re.sub(r"\D", "", a.get("id", ""))
        ITEMS.append(("chp-pr242-card-4131654", pid, vid, cid, "CAP07", "CHP check 4131654 PR-242/CO-243 not network/PCP - William 11/25/2026 'write off'"))
reg = []
for card, pid, vid, cid, carrier, note in ITEMS:
    x = resave.detail(cid)
    ch = dict(re.findall(r'(\w+)="([^"]*)"', re.search(r'<charge [^>]*>', x).group(0)))
    bal = float(ch.get("insbalance") or 0); pat = float(ch.get("patbalance") or 0)
    wos = [dict(re.findall(r'(\w+)="([^"]*)"', w)) for w in re.findall(r'<writeoff [^>]*>', x)]
    done = [w for w in wos if w.get("void") != "1" and "BOARD1125" in (w.get("checknumber", "") + w.get("memo", "") + w.get("note", ""))]
    line = {"card": card, "pid": pid, "visit": vid, "charge": cid, "cpt": ch.get("proccode"), "dos": ch.get("begindate"), "insbalance": bal, "patbalance": pat, "carrier": carrier}
    if done: line["result"] = "already written off this run"; print(line); reg.append(line); continue
    if bal <= 0: line["result"] = "no open insurance balance - nothing to write off"; print(line); reg.append(line); continue
    ok, msg = manual_post.post(cid, carrier, 0.0, bal, "WONCS", "BOARD1125", None, note, dry=not LIVE)
    line["result"] = ("LIVE " if LIVE else "DRY ") + str(msg)[:160]; line["ok"] = ok
    print(line); reg.append(line)
json.dump(reg, open("registers/board_wo_%s%s.json" % (S, "" if LIVE else "_dry"), "w"), indent=1)
print("written off:", sum(l["insbalance"] for l in reg if l.get("ok") and LIVE), "on", sum(1 for l in reg if l.get("ok") and LIVE), "charges")
