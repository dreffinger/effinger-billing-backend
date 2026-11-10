#!/usr/bin/env python3
"""Checks on the pulled chart documents, run locally (no AdvancedMD call, no database):
  1. every chart listed was pulled or has an error line;  2. the number of charge lines equals AdvancedMD's own item count for the chart;
  3. fee = payments + write-offs + balance on every live charge;  4. only allow-listed keys are present and no value looks like a person's name."""
import os, sys, json, glob, re, collections
S = "/tmp/claude-0/-home-user/5aaa27c8-6973-50aa-bba1-4b473bbc3aa7/scratchpad/amdpull"
CH = {"id", "visit", "dos", "proccode", "proccodetype", "modifiers", "fee", "paid", "patbal", "insbal", "totbal", "carrier", "subcarriercode", "billdate", "agingdate",
      "createtime", "provcode", "npi", "faccode", "facname", "totalvisitcharge", "void", "approvedat", "isinstitutional", "payerinfo", "payments", "writeoffs"}
PAY = {"id", "date", "checknumber", "paycode", "source", "void", "voidoffset", "createtime", "provcode", "amount", "carrier", "reasons"}
WO = {"id", "date", "wocode", "source", "void", "voidoffset", "createtime", "provcode", "amount"}
TOP = {"_written", "chart", "source", "pages", "pages_read", "summary", "charges", "unapplied_payments", "unapplied_writeoffs"}
NAMEY = re.compile(r"[A-Za-z]{2,}\s*,\s*[A-Za-z]{2,}")            # LAST,FIRST
FREE = {"facname", "payerinfo"}                                    # the only free-text fields kept (building name, payer id label)
ids = [l.strip() for l in open(S + "/state/patients.txt") if l.strip().isdigit()]
files = {os.path.basename(f)[3:-5]: f for f in glob.glob(S + "/docs/*/txhistory/pat*.json")}
errs = collections.Counter(); st = collections.Counter(); bad_keys = collections.Counter(); namey = collections.Counter(); odd = collections.Counter()
count_mismatch = []; ident_fail = 0; years = collections.Counter(); money = collections.Counter()
def f2(x):
    try: return float(x)
    except Exception: return None
for pid, f in files.items():
    d = json.load(open(f)); st["charts"] += 1
    for k in d:
        if k not in TOP: bad_keys["top." + k] += 1
    ic = d["summary"].get("itemcount")
    un = len(d.get("unapplied_payments") or []) + len(d.get("unapplied_writeoffs") or [])
    if ic is not None and ic.isdigit() and int(ic) != len(d["charges"]) + un: count_mismatch.append((int(ic), len(d["charges"]), un, d.get("pages")))
    if d.get("pages", 1) > d.get("pages_read", d.get("pages", 1)): st["charts_truncated"] += 1
    for c in d["charges"]:
        st["charges"] += 1
        for k, v in c.items():
            if k not in CH: bad_keys["charge." + k] += 1
            elif isinstance(v, str) and k not in FREE and NAMEY.search(v): namey["charge." + k] += 1
        live = c.get("void") != "1" and not (c.get("fee") or "").startswith("-")
        pay = sum(-(f2(p.get("amount")) or 0) for p in c["payments"] if p.get("void") != "1")
        wo = sum(-(f2(w.get("amount")) or 0) for w in c["writeoffs"] if w.get("void") != "1")
        for p in c["payments"]:
            st["payments"] += 1
            for k, v in p.items():
                if k not in PAY: bad_keys["payment." + k] += 1
                elif isinstance(v, str) and NAMEY.search(v): namey["payment." + k] += 1
        for w in c["writeoffs"]:
            st["writeoffs"] += 1
            for k, v in w.items():
                if k not in WO: bad_keys["writeoff." + k] += 1
                elif isinstance(v, str) and NAMEY.search(v): namey["writeoff." + k] += 1
        if live:
            st["live_charges"] += 1
            fee, bal = f2(c.get("fee")), f2(c.get("totbal"))
            if fee is None or bal is None or abs(fee - pay - wo - bal) > 0.011: ident_fail += 1
            y = (c.get("dos") or "")[-4:]; years[y] += 1; money["fee " + y] += fee or 0; money["paid " + y] += pay
    st["unapplied_payments"] += len(d.get("unapplied_payments") or [])
missing = [i for i in ids if i not in files]
print("charts listed %d | documents %d | not pulled yet %d" % (len(ids), len(files), len(missing)))
print("charge lines %(charges)d (live %(live_charges)d) | payment lines %(payments)d | write-off lines %(writeoffs)d | unapplied payments %(unapplied_payments)d | charts with more than 60 pages %(charts_truncated)d" % collections.defaultdict(int, st))
print("charts whose charge lines + unapplied credits differ from AdvancedMD's item count: %d %s" % (len(count_mismatch), count_mismatch[:5]))
print("live charges where fee <> payments + write-offs + balance: %d" % ident_fail)
print("keys outside the allow-list: %s | name-shaped values outside building/payer labels: %s" % (dict(bad_keys) or "none", dict(namey) or "none"))
print("live charge lines by year of service:", dict(sorted(years.items())))
print("dollars by year of service: " + "; ".join("%s $%s" % (k, format(round(v), ",")) for k, v in sorted(money.items())))
