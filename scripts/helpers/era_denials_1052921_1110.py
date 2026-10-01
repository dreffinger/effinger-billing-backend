# PLAIN ENGLISH (7 AM ET 10/1/2026 run 2026-10-01T1110Z): denial lines of UHC ERA check 1052921 (W0616257, check date 10/02/2026) that the
#   standing rules settle - CO-29 'time limit for filing has expired' -> WOLATE (prompt v7 step 5(g): CO-29 -> WOLATE; William 9/7: a primary
#   claim over 12 months from DOS and unpaid is written off): pat17475602 (DOD 4/16/2026 per CMS) 2/20/2026 99306+99497 ($389) and 2/26/2026
#   99309 ($141) - UHC was the payer (Medicare answered $0 in May 2026, those lines were voided 9/4 when the visits were re-routed to UHC) and
#   UHC says the 9/4/2026 filing was late; pat21263 8/17/2025 99487+99489 (UHC paid 9/2026 then recouped the same amounts, $105.76 open,
#   13 months from DOS). Each write-off: pay 0, wo = the live open insurance balance (must equal the expected amount), carrier UNI20, the ERA
#   check number as the check number, dated note; --dry first. Register registers/era_denials_1052921_2026-10-01T1110Z[_dry].json.
# Never touches: the OA-18 duplicate lines (recorded only), PR-27 / PR-26 lines (insurance cascade path), CO-B9 hospice lines
#   (hospice_reroute_1110.py), the CO-151 line (William's decision), any charge whose live balance differs from the expected amount.
import amd, manual_post, resave, json, re, time, sys
amd.login_cached(); dry = "--live" not in sys.argv
S = "2026-10-01T1110Z"; NOW = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
# (pid, vid, chargeid, cpt, dos, expected open insurance balance, why)
todo = [
    ("17475602", "19433580", "23340303", "99306", "02/20/2026", 256.00, "CO-29 untimely (UHC W0616257)"),
    ("17475602", "19433580", "23340304", "99497", "02/20/2026", 133.00, "CO-29 untimely (UHC W0616257)"),
    ("17475602", "19434260", "23341236", "99309", "02/26/2026", 141.00, "CO-29 untimely (UHC W0616257)"),
    ("21263", "19413646", "23316734", "99487", "08/17/2025", 68.62, "CO-29 untimely + 12-month rule (UHC W0616257, paid 9/4/2026 then recouped)"),
    ("21263", "19413646", "23316735", "99489", "08/17/2025", 37.14, "CO-29 untimely + 12-month rule (UHC W0616257, paid 9/4/2026 then recouped)"),
]
reg = []
for pid, vid, cid, cpt, dos, amt, why in todo:
    x = resave.detail(cid); m = re.search(r'<charge [^>]*id="charge%s"[^>]*>' % cid, x).group(0)
    live = float(re.search(r'insbalance="([^"]*)"', m).group(1) or 0); pb = float(re.search(r'patbalance="([^"]*)"', m).group(1) or 0)
    if abs(live - amt) > 0.005 or live <= 0:
        print("  SKIP pat%s v%s c%s %s live insbal %.2f != expected %.2f (patbal %.2f)" % (pid, vid, cid, cpt, live, amt, pb))
        reg.append(dict(pid=pid, vid=vid, cid=cid, cpt=cpt, dos=dos, expected=amt, live=live, patbal=pb, outcome="skipped-balance-changed", when=NOW)); continue
    note = "ERA 1052921 (UHC W0616257) %s - write-off, run %s" % (why, S)
    ok, msg = manual_post.post(cid, "UNI20", 0.0, live, "WOLATE", checknumber="W0616257", depositdate="10/02/2026", note=note, dry=dry)
    time.sleep(0.6); after = None
    if not dry and ok:
        x2 = resave.detail(cid); m2 = re.search(r'<charge [^>]*id="charge%s"[^>]*>' % cid, x2).group(0); after = float(re.search(r'insbalance="([^"]*)"', m2).group(1) or 0)
    print("  WOLATE pat%s v%s c%s %s %s %.2f -> %s %s after=%s" % (pid, vid, cid, cpt, dos, live, ok, str(msg)[:90], after))
    reg.append(dict(pid=pid, vid=vid, cid=cid, cpt=cpt, dos=dos, amount=live, why=why, code="WOLATE", ok=ok, msg=str(msg)[:160], insbalance_after=after, when=NOW, dry=dry))
json.dump(reg, open("registers/era_denials_1052921_%s%s.json" % (S, "_dry" if dry else ""), "w"), indent=1)
print("TOTAL written off:", round(sum(r["amount"] for r in reg if r.get("ok")), 2), "dry" if dry else "LIVE")
