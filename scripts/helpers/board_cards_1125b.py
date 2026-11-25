#!/usr/bin/env python3
# PLAIN ENGLISH (the five Insurance Refresh Board cards William answered 11/25/2026 04:40-05:07 UTC, after the 04:35Z run had read the board)
# Decides: nothing. Each step is a standing rule applied to William's own words on the card (the cards were saved to this session's
#   scratchpad by the board read; nothing is retyped here - the Medicare numbers are read out of his pasted facesheets):
#   (A) [name]-17476021-medicare-number and [name]-48458-medicare-number: he pasted the facility facesheet. The Medicare
#       number on it is tried on the chart exactly as medicare_number_fix.py does (write, AdvancedMD's free check, keep only on
#       ACTIVE, else the old number back), then every unpaid Medicare visit inside 12 months is re-sent ONE frequency-1 claim each
#       (deceased guard inside); older ones are listed. A number identical to the chart's is reported, nothing written.
#   (B) [name]-21839-medicare-number: "write off" - the two visits past Medicare's 12-month filing limit (11/07/2025 99309,
#       11/15/2025 99487+99489) have their open Medicare balance written off WOLATE (manual_post.post, pay 0, reference BOARD1125B).
#   (C) [name]-17473749: "'restore' and they are restored and billed to UHC" - every 2026 visit before the 10/27 CCM whose
#       Medicare $0 answer (CO-24 / CO-109: an Advantage plan is responsible) was written off: void the $0 payment and its WOINS
#       write-off and bill the visit to the chart's UHC Medicare Advantage plan (co24_restore.run - one move_to_ins rebill per visit).
#   (D) [name]-17474537-medicare-number: "i need the date of birth on this" - read-only: the chart's birth date for the reply.
# Never touches: paid visits, other plans, the chart order, charts not named. Usage: python3 board_cards_1125b.py [--live]
import amd, json, re, sys, os, glob, time
import medicare_number_fix as mnf, manual_post, resave, co24_restore, patient_patch
LIVE = "--live" in sys.argv; S = "2026-11-25T0557Z"
BOARD = "/tmp/claude-0/-home-claude-effinger-billing-backend/54dad968-8e54-5d62-b91f-c8705cdd698d/scratchpad/board_0557/items"
MBI = mnf.MBI
def card(cid):
    o = json.load(open(os.path.join(BOARD, cid + ".json"))); return o.get("data", o)
def facesheet_mbi(cid):
    """the Medicare policy number in William's pasted facesheet (the newest note by William)"""
    notes = [n for n in card(cid).get("notes") or [] if str(n.get("who", "")).lower().startswith("william")]
    txt = notes[-1]["text"] if notes else ""
    m = re.search(r"MEDICARE.{0,300}?Policy #\s*([A-Z0-9]{11})", txt, re.I | re.S)
    n = mnf.norm(m.group(1)) if m else ""
    return n if re.fullmatch(MBI, n) else ""
reg = {"stamp": S, "live": LIVE, "cards": {}}
amd.login_cached()
# (A) the two Medicare-number cards
cands = {}
for cid, pid in (("[name]-17476021-medicare-number", "17476021"), ("[name]-48458-medicare-number", "48458")):
    n = facesheet_mbi(cid); cands[pid] = [n] if n else []
    print("== %s: facesheet Medicare number %s" % (cid, "found (%s****)" % n[:2] if n else "NOT FOUND in the paste"))
mnf.feed_numbers = lambda pid: list(cands.get(str(pid), []))     # the candidate comes from William's facesheet paste, not the feed
mreg = {}
for cid, pid in (("[name]-17476021-medicare-number", "17476021"), ("[name]-48458-medicare-number", "48458")):
    try:
        _, plans, _ = __import__("ins_update")._plans(pid)
        cur = [mnf.norm(p.get("subscribernum")) for p in plans.values() if p.get("carrier") == "car6085" and not p.get("enddate")]
        same = bool(cands[pid]) and cands[pid][0] in cur
        if same: print("  the facesheet number is the SAME as the chart's Medicare number")
        rec = mnf.fix(pid, LIVE, False, mreg)
        rec["facesheet_same_as_chart"] = same; rec["source"] = "William's facesheet paste 11/25"
        reg["cards"][cid] = rec
    except Exception as e:
        reg["cards"][cid] = {"error": "%s: %s" % (type(e).__name__, str(e)[:160])}; print("  stopped:", reg["cards"][cid]["error"])
# (B) Floyd: WOLATE on the two visits past 12 months
wo = []
for vid, cid_ in (("19423852", "23329586"), ("19423656", "23329314"), ("19423656", "23329315")):
    x = resave.detail(cid_)
    ch = dict(re.findall(r'(\w+)="([^"]*)"', re.search(r'<charge [^>]*>', x).group(0)))
    bal = float(ch.get("insbalance") or 0)
    wos = [dict(re.findall(r'(\w+)="([^"]*)"', w)) for w in re.findall(r'<writeoff [^>]*>', x)]
    done = [w for w in wos if w.get("void") != "1" and "BOARD1125B" in (w.get("checknumber", "") + w.get("memo", "") + w.get("note", ""))]
    line = {"visit": vid, "charge": cid_, "cpt": ch.get("proccode"), "dos": ch.get("begindate"), "insbalance": bal}
    if done: line["result"] = "already written off this run"
    elif bal <= 0: line["result"] = "no open insurance balance - nothing to write off"
    else:
        ok, msg = manual_post.post(cid_, "FLO02", 0.0, bal, "WOLATE", "BOARD1125B", None, "past Medicare 12-month filing limit - William 11/25/2026 'write off' (board card [name]-21839-medicare-number)", dry=not LIVE)
        line["result"] = ("LIVE " if LIVE else "DRY ") + str(msg)[:160]; line["ok"] = ok
    print("  floyd", line); wo.append(line)
reg["cards"]["[name]-21839-medicare-number"] = {"writeoffs": wo}
# (C) Harvey: restore the 2026 CO-24 / CO-109 write-offs and bill UHC (chart order = seq 2, the UHC MA plan)
try:
    out = co24_restore.run("17473749", "2", "01/01/2026", "10/26/2026", dry=not LIVE, codes=("CO24", "CO109"))
    for l in out: print("  harvey", l)
    reg["cards"]["[name]-17473749"] = {"restore": out}
except Exception as e:
    reg["cards"]["[name]-17473749"] = {"error": "%s: %s" % (type(e).__name__, str(e)[:160])}; print("  harvey stopped:", reg["cards"]["[name]-17473749"]["error"])
# (D) Grant: the chart's birth date (read-only)
try:
    g = patient_patch.get("17474537"); reg["cards"]["[name]-17474537-medicare-number"] = {"dob_on_chart": g.get("dob")}; print("  grant: chart dob", g.get("dob"))
except Exception as e:
    reg["cards"]["[name]-17474537-medicare-number"] = {"error": str(e)[:120]}
json.dump(reg, open("registers/board_cards_%s%s.json" % (S, "" if LIVE else "_dry"), "w"), indent=1)
print("register written")
