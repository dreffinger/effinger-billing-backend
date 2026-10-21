#!/usr/bin/env python3
# PLAIN ENGLISH (dismiss one settled ERA check, 1 PM ET 10/21/2026 run 2026-10-21T1710Z). Florida Blue check 1053245 (trace 423830695,
#   $312.18, 24 claims): every money line is now on its visit - 9 lines Post-buttoned by GitHub slot #128 at 17:2xZ, 3 re-pay lines
#   posted ERA-linked by era_repay_1021_1710.py at 17:4xZ ($47.21 + WOINS 57.71), 1 line ($11.59, v19456195) on a charge already at $0
#   (residual, disregarded per William's 9/13 rule); the rest are $0 PR-22 / PR-1 reversal-and-redeny pairs (net zero, denial handling).
#   era_clear.py cannot dismiss it: its unvalidated-line branch counts a line with money as 'not validated with money' even when the
#   payment is already on the charge (and it skips a check it HELD earlier in the same log).
# Decides: re-reads the three re-pay charges live, confirms each carries a non-void payment with the trace number, then POST
#   /api/era/checks/dismiss (the captured ERA Center dismiss, body = the check id as a JSON string). --dry prints the checks only.
# Usage: python3 era_dismiss_1021_1710.py [--dry]
import json, sys, time, requests
import xml.etree.ElementTree as ET
import amd, resave
from era_post import H
S = "2026-10-21T1710Z"; CHK = 1053245; TRN = "423830695"; dry = "--dry" in sys.argv
MUST = {"23345986": 13.35, "23361186": 16.93, "23363452": 16.93}
amd.login_cached(); ok_all = True
for cid, amt in MUST.items():
    rt = ET.fromstring(resave.detail(cid)); c = [x for x in rt.iter("charge") if x.get("id") == "charge" + cid][0]
    hits = [p for p in c.iter("payment") if p.get("void") != "1" and TRN in (p.get("checknumber") or "") and abs(abs(float(p.get("amount") or 0)) - amt) < 0.005]
    print("charge", cid, "insbalance", c.get("insbalance"), "patbalance", c.get("patbalance"), "trace payment", bool(hits)); ok_all &= bool(hits); time.sleep(0.3)
if not ok_all: print("a re-pay line is missing on its charge - NOT dismissing"); sys.exit(2)
if dry: print("DRY: would dismiss", CHK); sys.exit(0)
API = "https://pm-api-103.advancedmd.com/api"
r = requests.post(API + "/era/checks/dismiss", headers=H(), data=json.dumps(str(CHK)), timeout=60)
print("dismiss", CHK, r.status_code, r.text[:200])
open("era_clear.log", "a").write("DISMISS %s BCBS %s $312.18: by era_dismiss_%s after the re-pay posts -> %s\n" % (CHK, TRN, S, r.status_code))
