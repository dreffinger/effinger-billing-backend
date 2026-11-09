# PLAIN ENGLISH (Board-answer read, 11/09/2026)
# Decides: Nothing. Reads the six charts William answered on the Insurance Refresh Board / pasted facesheets for,
#          so each fix can be made against live data: open charges, balances, payments, plans and chart identity.
# Rules it uses: Read-only.
# Never touches: Anything - it writes nothing to AdvancedMD.
import json, re, sys
import xml.etree.ElementTree as ET
import amd, txh, resave

CHARTS = {
    "LEE (write off)":        ("17477829", ["19456472", "19456474"]),
    "LEWIS (recode 99309)":   ("23083",    ["19443011"]),
    "OLSEN (WOBAD)":          ("17473501", ["19442733", "19442744", "19442953"]),
    "SMITH placeholder":      ("17478345", ["19460486"]),
    "FRITZ (facesheet)":      ("17478346", []),
    "SNYDER (facesheet)":     ("17478319", []),
}
SMITH_CANDIDATES = ["21798", "17469615", "17472040", "17477383", "17477933", "12180395"]

def demo(pid):
    body = amd.msg("getdemographic", "demographics", {"patientid": str(pid), "nocookie": "1"})
    return ET.fromstring(amd.post(body, timeout=120))

def show_chart(label, pid, vids):
    print("=" * 92)
    print(f"### {label}   pat{pid}")
    d = demo(pid)
    p = d.find(".//patient")
    if p is not None:
        a = p.attrib
        print("   patient:", {k: a.get(k) for k in ("id", "chartnumber", "dob", "sex", "gender", "insorder", "lastname", "firstname") if a.get(k)})
    for ad in d.iter("address"):
        print("   address:", {k: v for k, v in ad.attrib.items() if v})
    for ip in d.iter("insplan"):
        a = ip.attrib
        print("   insplan:", {k: a.get(k) for k in ("id", "carrier", "carriercode", "subscribernum", "sequence", "begindate", "enddate", "coverage") if a.get(k)})
    for rp in d.iter("refplan"):
        a = rp.attrib
        print("   refplan:", {k: a.get(k) for k in ("id", "preauth", "begindate", "enddate", "carrier") if a.get(k)})
    root = txh.fetch(pid)
    rows = []
    for c in root.iter("charge"):
        a = c.attrib
        if a.get("void") == "1": continue
        ins = float(a.get("insbal") or a.get("insbalance") or 0)
        pat = float(a.get("patbalance") or a.get("patbal") or 0)
        pays = [(x.attrib.get("carrier"), x.attrib.get("amount"), x.attrib.get("date"), x.attrib.get("checknumber")) for x in c.iter("payment")]
        wos = [(x.attrib.get("code"), x.attrib.get("amount"), x.attrib.get("date")) for x in c.iter("writeoff")]
        rows.append((a.get("dos"), a.get("proccode"), a.get("id"), a.get("visit") or a.get("visitid"),
                     a.get("fee"), ins, pat, a.get("billdate"), a.get("carrier"), pays, wos))
    rows.sort(key=lambda r: (r[0] or ""))
    want = set(re.sub(r"\D", "", v) for v in vids)
    for r in rows:
        star = "  <<<" if (want and (r[3] or "") in want) else ""
        if want and not star and (r[5] == 0 and r[6] == 0): continue
        print(f"   CHG {r[0]} {r[1]} chg{r[2]} vst{r[3]} fee {r[4]} insbal {r[5]:.2f} patbal {r[6]:.2f} billed {r[7] or '-'} car {r[8] or '-'}{star}")
        for pay in r[9]:
            if pay[1] and float(pay[1]) != 0: print("        PAY", pay)
        for w in r[10]:
            if w[1] and float(w[1]) != 0: print("        WO ", w)
    if not rows: print("   (no live charges)")

for label, (pid, vids) in CHARTS.items():
    try: show_chart(label, pid, vids)
    except Exception as e: print("ERROR on", label, pid, repr(e))

print("=" * 92)
print("### SMITH,MYRTLE candidate charts - which one is live?")
for pid in SMITH_CANDIDATES:
    try:
        d = demo(pid)
        p = d.find(".//patient"); a = p.attrib if p is not None else {}
        plans = [(ip.attrib.get("carriercode") or ip.attrib.get("carrier"), ip.attrib.get("subscribernum"),
                  ip.attrib.get("sequence"), ip.attrib.get("enddate")) for ip in d.iter("insplan")]
        root = txh.fetch(pid)
        dates = sorted({c.attrib.get("dos") for c in root.iter("charge") if c.attrib.get("void") != "1" and c.attrib.get("dos")})
        openbal = sum(float(c.attrib.get("insbal") or 0) + float(c.attrib.get("patbalance") or 0)
                      for c in root.iter("charge") if c.attrib.get("void") != "1")
        print(f"   pat{pid}  chart {a.get('chartnumber')}  dob {a.get('dob')}  insorder {a.get('insorder')}  charges {len(dates)}  last DOS {dates[-1] if dates else '-'}  open ${openbal:.2f}")
        for pl in plans: print("        plan", pl)
    except Exception as e:
        print("   pat%s ERROR %r" % (pid, e))
