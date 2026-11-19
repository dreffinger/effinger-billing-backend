# PLAIN ENGLISH (Admission notices and facesheets as data - read the insurance out of HL7 messages)
# Decides: Nothing. Reads HL7 version 2 messages - the hospital admission / discharge notices a health information exchange sends
#   (ADT A01 / A03 / A04 / A08 ..., Florida's Encounter Notification Service delivers them as HL7 or CSV) and the Claimocity charge
#   messages (DFT) - and writes ONE record per message: who (name, birth date, sex), where and when (building, class, admission and
#   discharge dates, the event), and every insurance block the message carries (IN1: company name, member number, plan dates, order).
#   Built 11/19/2026 on William's word ("steps to get info from state health info exchange to set that up and use it to the database
#   and for billing ... build this"): the member numbers typed by hand that night were all on a facesheet somewhere.
# Rules it uses: an insurance block is NOT a medical payer when its name says patient / resident liability, private pay, coinsurance
#   of another plan, pending, dental, vision or life - those rows are kept and marked `skip` with the word that decided it, never
#   offered as the plan to bill; the member number is IN1-36 (policy number), else IN1-49, else IN1-2 when it looks like a number.
#   Output is patient data: it is written under patient_db/adt/ (workspace and the Drive state bundle only - never git). The summary
#   printed to the screen has counts only.
# Never touches: AdvancedMD, Stedi, the feed import. A later step (the insurance cascade, or a person) decides what goes on a chart.
# Usage: python3 adt_ingest.py <file or folder> [...] [--out patient_db/adt/<name>.json]      python3 adt_ingest.py selftest
import os, re, sys, json, glob, collections
NOT_A_PAYER = r"LIABILITY|RESLIAB|PRIVATE PAY|SELF.?PAY|COINSURANCE|CO-INS|PENDING|DENTAL|VISION|\bLIFE\b|PATIENT RESOURCES|HOSPICE"
def _f(seg, i, comp=0):
    """Field i of a segment (already split on |), component comp; '' when absent."""
    try: return (seg[i].split("^")[comp] or "").strip()
    except Exception: return ""
def _date(s):
    s = re.sub(r"\D", "", s or "")[:8]
    return "%s-%s-%s" % (s[:4], s[4:6], s[6:8]) if len(s) == 8 else ""
def parse_message(text):
    rec = {"type": "", "event": "", "sent": "", "patient": {}, "visit": {}, "insurance": []}
    for line in re.split(r"[\r\n]+", text):
        s = line.split("|"); t = s[0].strip()
        if t == "MSH": rec["type"] = _f(s, 8); rec["event"] = _f(s, 8, 1); rec["sent"] = _date(_f(s, 6)); rec["sender"] = _f(s, 3)
        elif t == "EVN": rec["event"] = rec["event"] or _f(s, 1)
        elif t == "PID":
            rec["patient"] = {"id": _f(s, 3), "last": _f(s, 5), "first": _f(s, 5, 1), "dob": _date(_f(s, 7)), "sex": _f(s, 8), "ssn4": re.sub(r"\D", "", _f(s, 19))[-4:]}
        elif t == "PV1":
            rec["visit"] = {"class": _f(s, 2), "location": " ".join(x for x in (s[3].split("^") if len(s) > 3 else []) if x)[:60], "admit": _date(_f(s, 44)), "discharge": _date(_f(s, 45))}
        elif t == "IN1":
            name = _f(s, 4); member = _f(s, 36) or _f(s, 49) or (_f(s, 2) if re.search(r"\d{5,}", _f(s, 2)) else "")
            m = re.search(NOT_A_PAYER, name.upper())
            if m and m.group(0) == "LIFE" and "HEALTH" in name.upper(): m = None      # 'Health and Life Insurance Company' is a medical insurer's name
            rec["insurance"].append({"order": _f(s, 1), "name": name, "member": member, "begin": _date(_f(s, 12)), "end": _date(_f(s, 13)), "group": _f(s, 8),
                                     "skip": m.group(0).lower() if m else ("no member number" if not member else "")})
    return rec
def read(paths):
    out = []
    for p in paths:
        files = [p] if os.path.isfile(p) else [f for f in glob.glob(os.path.join(p, "**", "*"), recursive=True) if os.path.isfile(f)]
        for f in files:
            t = open(f, errors="replace").read()
            for m in re.split(r"(?=^MSH\|)", t.replace("\r", "\n"), flags=re.M):
                if m.strip().startswith("MSH|"):
                    r = parse_message(m); r["file"] = os.path.basename(f); out.append(r)
    return out
def usable(rec):
    """The insurance blocks of a record that may be offered as a plan to bill, in the message's order."""
    return [i for i in rec["insurance"] if not i["skip"]]
if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    if a and a[0] == "selftest":
        pv1 = ["PV1", "1", "I", "5S^514^A^HOSP"] + [""] * 40 + ["20261118"]
        in1 = ["IN1", "1", "P1", "C1", "CAPITAL HEALTH MEDICARE HMO"] + [""] * 3 + ["G1"] + [""] * 3 + ["20260101"] + [""] * 23 + ["CIO00000000"]
        in3 = ["IN1", "3", "", "", "CIGNA DENTAL HMO"] + [""] * 31 + ["D123456"]
        in4 = ["IN1", "4", "", "", "SIERRA HEALTH AND LIFE INSURANCE COMPANY"] + [""] * 31 + ["S123456"]
        m = "\r".join(["MSH|^~\\&|HIE|FAC|ENS|PRACTICE|20261119080000||ADT^A01|1|P|2.5", "PID|1||M1^^^F||DOE^JANE||" + "1940" + "0102" + "|F", "|".join(pv1), "|".join(in1), "IN1|2|||Patient Liability", "|".join(in3), "|".join(in4)])
        r = parse_message(m); u = usable(r)
        assert r["type"] == "ADT" and r["event"] == "A01" and r["patient"]["dob"] == "-".join(["1940", "01", "02"]) and r["visit"]["admit"] == "2026-11-18", r
        assert [x["member"] for x in u] == ["CIO00000000", "S123456"] and [i["skip"] for i in r["insurance"]] == ["", "liability", "dental", ""], r["insurance"]
        print("selftest ok"); sys.exit(0)
    if not a: print(__doc__ or "usage: adt_ingest.py <file or folder> [--out file]"); sys.exit(0)
    recs = read(a); outp = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else os.path.join("patient_db", "adt", "adt_ingest.json")
    os.makedirs(os.path.dirname(outp), exist_ok=True); json.dump(recs, open(outp, "w"))
    kinds = collections.Counter("%s %s" % (r["type"], r["event"]) for r in recs)
    print("messages %d | by kind %s" % (len(recs), dict(kinds)))
    print("with any insurance block %d | with a usable medical plan and member number %d | blocks skipped by reason %s" % (
        sum(1 for r in recs if r["insurance"]), sum(1 for r in recs if usable(r)), dict(collections.Counter(i["skip"] for r in recs for i in r["insurance"] if i["skip"]))))
    print("written (patient data, workspace only): %s" % outp)
