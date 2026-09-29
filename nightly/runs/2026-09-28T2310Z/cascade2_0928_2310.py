# PLAIN ENGLISH (second-round lookups, 7pm ET 9/28/2026 run 2026-09-28T2310Z): for the new HCA charts whose Medicare record names an MA
#   entity (Humana / Emphesys / Capital Health Plan) ask that payer's Stedi eligibility with the MBI as member id (the UHC-87726 pattern that
#   returns the MA member number); retry insurance discovery where the first pass answered 502 (pat17477892, pat17477894 - also GA for the
#   Thomasville chart); UHC 87726 with the discovery member id for pat17477895; discovery for the two straight-Medicare-plus-'OT UHC' charts
#   (pat17477897, pat17477900) to name the AARP Medigap id. Also reads the plans of the five Pam-admit charts that exist in AMD.
# Decides: nothing (writes cascade2_2310.json). Never touches: AMD writes.
import amd, stedi, elig_amd, json, time, re
amd.login_cached(); inv = json.load(open("inv_2310.json")); out = {}
def L(m): print(m, flush=True)
def nm(pid):
    name = inv[pid]["name"]; last, first = (name.split(",") + [""])[:2]; first = first.strip().split(" ")[0]; last = last.strip()
    dob = inv[pid]["dob"]; m = re.match(r"(\d\d)/(\d\d)/(\d{4})", dob); return first, last, "%s%s%s" % (m.group(3), m.group(1), m.group(2))
def summ(j):
    try: return stedi.summarize_elig(j) if hasattr(stedi, "summarize_elig") else j
    except Exception as e: return "summ err %s" % e
DOS = "20260922"
plan = [("17477893", "61101", "Humana PPO MA"), ("17477899", "61101", "Emphesys/Humana PPO MA"), ("17477898", "95112", "CHP MA"), ("17477850", "95112", "CHP MA"), ("17477897", "87726", "UHC OT (Medigap?)"), ("17477900", "87726", "UHC OT (Medigap?)")]
for pid, payer, why in plan:
    first, last, dob8 = nm(pid); mbi = inv[pid]["mbi"]["mbi"]
    try:
        j = stedi.elig(payer, first, last, dob8, mbi, DOS, pid=pid); out[pid] = {"payer": payer, "why": why, "raw_keys": list(j.keys())[:12]}
        sub = j.get("subscriber", {}); errs = j.get("errors"); plans = j.get("planStatus"); pinfo = j.get("planInformation"); pdi = j.get("planDateInformation")
        out[pid].update({"memberId": sub.get("memberId"), "errors": errs, "planStatus": plans, "planInformation": pinfo, "planDateInformation": pdi, "payerName": (j.get("payer") or {}).get("name")})
        L("== pat%s %s payer %s -> memberId=%s errors=%s planStatus=%s payer=%s dates=%s" % (pid, why, payer, sub.get("memberId"), json.dumps(errs)[:300], json.dumps(plans)[:400], (j.get("payer") or {}).get("name"), json.dumps(pdi)[:200]))
    except Exception as e: out[pid] = {"payer": payer, "exc": str(e)[:200]}; L("== pat%s %s EXC %s" % (pid, why, str(e)[:200]))
    time.sleep(1.0)
for pid, st in [("17477892", "FL"), ("17477894", "GA"), ("17477894", "FL"), ("17477897", "FL"), ("17477900", "FL")]:
    first, last, dob8 = nm(pid)
    try: d = stedi.disc(first, last, dob8, st, DOS); s = stedi.disc_summ(d); out.setdefault(pid, {})["disc_" + st] = s; L("== pat%s discovery %s: %s" % (pid, st, json.dumps(s)[:900]))
    except Exception as e: out.setdefault(pid, {})["disc_" + st] = "EXC %s" % str(e)[:160]; L("== pat%s discovery %s EXC %s" % (pid, st, str(e)[:160]))
    time.sleep(1.5)
# pat17477894 GA MBI lookup
first, last, dob8 = nm("17477894")
try: j = stedi.mbi(first, last, dob8, "GA", DOS, pid="17477894"); s = stedi.med_summ(j); out["17477894"]["mbi_GA"] = s; L("== pat17477894 MBI GA: mbi=%s A=%s B=%s errors=%s other=%s" % (s.get("mbi"), s.get("partA"), s.get("partB"), s.get("errors"), json.dumps(s.get("other"))[:400]))
except Exception as e: L("== pat17477894 MBI GA EXC %s" % str(e)[:160])
# Yacobi UHC check with the discovery member id
first, last, dob8 = nm("17477895")
try:
    j = stedi.elig("87726", first, last, dob8, "908407085", DOS, pid="17477895"); sub = j.get("subscriber", {})
    out["17477895"] = {"memberId": sub.get("memberId"), "errors": j.get("errors"), "planStatus": j.get("planStatus"), "planDateInformation": j.get("planDateInformation"), "payerName": (j.get("payer") or {}).get("name")}
    L("== pat17477895 UHC 87726 -> memberId=%s errors=%s planStatus=%s dates=%s" % (sub.get("memberId"), json.dumps(j.get("errors"))[:200], json.dumps(j.get("planStatus"))[:400], json.dumps(j.get("planDateInformation"))[:200]))
except Exception as e: L("== pat17477895 UHC EXC %s" % str(e)[:160])
# Pam admit charts - plans + 271
pam = {}
for pid in ["17477828", "17471384", "20863", "20729", "17477496"]:
    pa, pl = elig_amd.plans(pid); rows = []
    for p in pl:
        rec = {"id": p.get("id"), "carrier": p.get("carrier"), "seq": p.get("sequence"), "begin": p.get("begindate"), "end": p.get("enddate"), "num": p.get("subscribernum"), "fin": p.get("finclasscode")}
        if not p.get("enddate"):
            try: rec["elig"] = elig_amd.one_line(elig_amd.run_plan(pid, p["id"].replace("ins", "")))[:300]
            except Exception as e: rec["elig"] = "ERR %s" % str(e)[:100]
            time.sleep(0.4)
        rows.append(rec)
    pam[pid] = {"name": pa.get("name"), "dob": pa.get("dob"), "insorder": pa.get("insorder"), "plans": rows}
    L("== PAM pat%s %s dob %s insorder=%s" % (pid, pa.get("name"), pa.get("dob"), pa.get("insorder")))
    for r in rows: L("   plan %s %s seq %s %s-%s num=%s | %s" % (r["id"], r["carrier"], r["seq"], r["begin"], r["end"], r["num"], r.get("elig", "(ended)")))
    time.sleep(0.3)
out["_pam"] = pam
json.dump(out, open("cascade2_2310.json", "w"), indent=1, default=str); L("DONE")
