# PLAIN ENGLISH (the "Patient Balances Remaining" page - renders patbal_review_<stamp>.json; names and dollars only, no member ids)
import json, html, collections, datetime, sys
STAMP = "1013"; D = json.load(open("patbal_review_%s.json" % STAMP)); R = D["rows"]; S = D["summary"]
e = lambda s: html.escape(str(s if s is not None else "")); m = lambda x: "$%s" % format(round(float(x or 0), 2), ",.2f")
LABEL = {"WRONG-PAYER": ("Retrievable", "Wrong-payer denial sitting on the patient", "Move back to insurance, Stedi cascade for the real payer, re-route (inside 12 months)"),
         "DENIED-FIX": ("Retrievable", "Other $0 denial on the patient, inside 12 months", "Move back to insurance, fix the claim, resubmit as an original"),
         "NEVER-SENT-LIVE-PLAN": ("Retrievable", "Never adjudicated, a live plan on the chart", "Move to insurance and send it (freq 1)"),
         "DUAL-SEND": ("Retrievable", "Dual patient, never adjudicated, inside 12 months", "Send to the plan (Medicare first), never a statement"),
         "BILL-SECONDARY": ("Retrievable", "Primary paid, a supplement / secondary is on the chart", "Bill the secondary or let the crossover run; timely from the primary's remit"),
         "SELF-PAY-DISCOVERY": ("Retrievable", "No plan on the chart at the DOS, inside 12 months", "Stedi insurance discovery per patient; found -> add the plan and send"),
         "DUAL-WRITEOFF": ("Write off", "Dual / Medicaid-family patient - cost-sharing after Medicare or MA paid", "WOCAID2ND (WOMCAD / WOLATE where nothing paid) - never billed to a Medicaid patient"),
         "WRONG-PAYER-UNTIMELY": ("Write off", "Wrong-payer denial, DOS over 12 months", "WOLATE - past the real payer's window"),
         "DENIED-UNTIMELY": ("Write off", "$0 denial, DOS over 12 months", "WOLATE"),
         "NEVER-SENT-UNTIMELY": ("Write off", "Never adjudicated, plan on the chart, DOS over 12 months", "WOLATE"),
         "SELF-PAY-BAD-DEBT": ("Write off", "No plan on the chart, DOS over 12 months", "Self-pay no-pay -> bad-debt write-off"),
         "SMALL-BALANCE": ("Write off", "Patient cost-sharing, the whole chart under $25", "WOSMBAL"),
         "DECEASED-STATEMENT": ("Write off", "Patient cost-sharing on a deceased chart", "Estate statement once, then write off - your call"),
         "STATEMENT-MEDICARE": ("Statement", "Medicare coinsurance / deductible, no supplement on the chart", "One Stedi discovery per patient for a Medigap; none found -> patient statement"),
         "STATEMENT": ("Statement", "MA / commercial copay or coinsurance", "Patient statement (small-balance policy applies per chart)"),
         "SETTLED": ("Settled", "Cleared on the live chart since the list was pulled", "nothing"), "UNREAD": ("Unread", "Chart not read tonight", "re-run")}
tot = sum(r.get("patbal", 0) for r in R); ret = sum(r.get("patbal", 0) for r in R if r.get("retrievable")); wo = sum(r.get("patbal", 0) for r in R if r.get("wocode")); st = tot - ret - wo
cls = {"Retrievable": "in", "Write off": "out", "Statement": "wait", "Settled": "hold", "Unread": "hold"}
def row(r):
    return "<tr><td class=\"name\">%s <span class=\"code\">%s</span></td><td class=\"code\">%s</td><td>%s</td><td class=\"num\">%d</td><td class=\"code\">%s</td><td>%s</td><td class=\"num wait\">%s</td><td class=\"code\">%s</td><td class=\"code\">%s</td><td class=\"note\">%s%s</td></tr>" % (
        e(r.get("patient")), e(r["pid"]), e(r["vid"]), e(r["dos"]), r["age"], e(r["cpt"]), e(r.get("carrier") or ""), m(r.get("patbal")), e("/".join(r.get("plans") or [])), e(" ".join(r.get("reasons") or [])[:40]),
        ('<span class="flag out">deceased</span> ' if r.get("deceased") else "") + ('<span class="flag hold">dual</span> ' if r.get("dual") else ""), e(r.get("action")))
def table(rows):
    return '<div class="tw"><table><thead><tr><th>Patient / chart</th><th>Visit</th><th>DOS</th><th>Days</th><th>CPT</th><th>Last carrier</th><th>Patient bal</th><th>Plans at DOS</th><th>Reasons</th><th>Recommendation</th></tr></thead><tbody>%s</tbody></table></div>' % "".join(row(r) for r in sorted(rows, key=lambda x: (x.get("patient") or "", x["dos"])))
H = []
H.append('''<title>Patient Balances Remaining</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,500;6..72,600;6..72,700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<style>
/* layout: the Old Claims Disposition token system - four tiles, the verdict table, then one wide table per bucket */
:root{--bg:#F7F3EC;--surface:#FFFDF9;--line:#DDD5C7;--ink:#1F2621;--muted:#66705F;--in:#1F6F4A;--in-soft:#DDEFE4;--out:#8B2E2E;--out-soft:#F3DEDE;--wait:#A9741A;--wait-soft:#F6EBD3;--hold:#4A5F7A;--hold-soft:#E0E7EF;
--disp:'Newsreader',Georgia,'Times New Roman',serif;--sans:'IBM Plex Sans',system-ui,-apple-system,'Segoe UI',sans-serif;--mono:'IBM Plex Mono',ui-monospace,Menlo,Consolas,monospace}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#151917;--surface:#1D2320;--line:#323B36;--ink:#EAE6DD;--muted:#A3AB9C;--in:#6BC29A;--in-soft:#173026;--out:#E07A7A;--out-soft:#3A1F1F;--wait:#E0B25E;--wait-soft:#3A2E14;--hold:#8FA9C8;--hold-soft:#1E2A38;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#151917;--surface:#1D2320;--line:#323B36;--ink:#EAE6DD;--muted:#A3AB9C;--in:#6BC29A;--in-soft:#173026;--out:#E07A7A;--out-soft:#3A1F1F;--wait:#E0B25E;--wait-soft:#3A2E14;--hold:#8FA9C8;--hold-soft:#1E2A38;color-scheme:dark}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:14.5px;line-height:1.45}
.wrap{max-width:1280px;margin:0 auto;padding-block:28px 100px;padding-inline:20px}
h1{font-family:var(--disp);font-weight:700;font-size:34px;letter-spacing:-.01em;margin:0;line-height:1.05;text-wrap:balance}
.asof{font:500 12.5px var(--mono);color:var(--muted);margin-top:6px}
h2{font-family:var(--disp);font-size:22px;font-weight:600;margin:28px 0 8px;text-wrap:balance}
.note{color:var(--muted);font-size:13.5px;max-width:80ch;margin:0 0 12px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;margin:18px 0 10px}
.kpi{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:12px 14px;min-width:0}
.kpi .l{font:500 11.5px var(--sans);letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}.kpi .v{font:600 24px var(--mono);font-variant-numeric:tabular-nums;line-height:1.15;margin-top:4px}.kpi .s{font-size:12.5px;color:var(--muted);margin-top:3px}
.kpi.in .v{color:var(--in)}.kpi.out .v{color:var(--out)}.kpi.wait .v{color:var(--wait)}.kpi.hold .v{color:var(--hold)}
details.pkg{background:var(--surface);border:1px solid var(--line);border-radius:10px;margin-bottom:10px;overflow:hidden}
details.pkg summary{list-style:none;cursor:pointer;display:grid;grid-template-columns:1fr auto;gap:14px;align-items:center;padding:12px 16px}
details.pkg summary::-webkit-details-marker{display:none}
.t{font:600 15.5px var(--sans)}.d{font-size:13px;color:var(--muted);margin-top:2px}
.amt{font:600 18px var(--mono);font-variant-numeric:tabular-nums;text-align:right;white-space:nowrap}.amt small{display:block;font:500 11.5px var(--mono);color:var(--muted)}
details.pkg .body{border-top:1px solid var(--line);padding:10px 16px 14px}
.tw{overflow-x:auto;background:var(--surface);border:1px solid var(--line);border-radius:8px;min-width:0}
table{border-collapse:collapse;width:100%;font-size:13px}th,td{padding:7px 9px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top;font-variant-numeric:tabular-nums}
th{font:600 10.5px var(--sans);letter-spacing:.07em;text-transform:uppercase;color:var(--muted);position:sticky;top:env(safe-area-inset-top,0px);background:var(--surface);white-space:nowrap}
td.name{font-weight:600;white-space:nowrap}td.code,.code{font:500 12px var(--mono);color:var(--muted)}td.num{text-align:right;font:500 12.5px var(--mono);white-space:nowrap}
td.in{color:var(--in)}td.out{color:var(--out)}td.wait{color:var(--wait)}td.note{min-width:28ch;max-width:60ch;font-size:12.5px;color:var(--muted)}
tr:last-child td{border-bottom:0}
.flag{display:inline-block;font:600 10.5px var(--sans);letter-spacing:.04em;text-transform:uppercase;padding:2px 7px;border-radius:999px;margin:0 4px 3px 0;white-space:nowrap}
.flag.in{background:var(--in-soft);color:var(--in)}.flag.out{background:var(--out-soft);color:var(--out)}.flag.wait{background:var(--wait-soft);color:var(--wait)}.flag.hold{background:var(--hold-soft);color:var(--hold)}
.search{width:100%;max-width:420px;padding:9px 12px;border:1px solid var(--line);border-radius:8px;background:var(--surface);color:var(--ink);font:14px var(--sans);margin:8px 0 14px}
.search:focus-visible{outline:2px solid var(--hold);outline-offset:2px}
@media (max-width:760px){.amt{text-align:left}}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
</style>
<div class="wrap"><header><h1>Patient Balances Remaining</h1><div class="asof">Built @@BUILT@@ from the live chart (plans, payments, denial reasons) · @@NCH@@ charges on @@NPT@@ charts carrying a patient balance · nothing is written off or sent until you say so</div></header>'''.replace('@@BUILT@@', D["built"][:16].replace('T',' ') + ' UTC').replace('@@NCH@@', str(len(R))).replace('@@NPT@@', str(len({r['pid'] for r in R}))))
H.append('<div class="kpis"><div class="kpi"><div class="l">Patient balance read</div><div class="v">%s</div><div class="s">live chart figure (list said %s)</div></div><div class="kpi in"><div class="l">Retrievable from an insurance</div><div class="v">%s</div><div class="s">re-route / send / bill the secondary / discovery</div></div><div class="kpi out"><div class="l">Recommended write-off</div><div class="v">%s</div><div class="s">dual, untimely, small balance, no payer anywhere</div></div><div class="kpi wait"><div class="l">The patient\'s own</div><div class="v">%s</div><div class="s">adjudicated cost-sharing - statements (Medigap discovery first on Medicare)</div></div></div>' % (m(tot), m(sum(r.get("patbal_list", 0) for r in R)), m(ret), m(wo), m(st)))
H.append('<p class="note">William\'s test (10/13/2026): every dollar on the patient side is either retrievable by sending it correctly to an insurance, or it gets written off. Retrievable money is the wrong-payer transfers and denials inside 12 months, never-sent lines with a live plan, dual patients Medicaid should answer, and cost-sharing a supplement on the chart owes. Write-offs are the dual / QMB cost-sharing (never balance-billed), anything past 12 months with no payer answer, charts under $25, and self-pay with no plan found. What is left is adjudicated cost-sharing on patients with no other plan: that is theirs - a statement - after one Stedi discovery per Medicare patient looks for a Medigap.</p>')
H.append('<h2>The verdict by bucket</h2><div class="tw"><table><thead><tr><th>Verdict</th><th>Bucket</th><th>Charges</th><th>Patients</th><th>Patient balance</th><th>Share</th><th>Last carrier</th><th>Recommendation</th></tr></thead><tbody>')
for k, b in S.items():
    if not b["charges"]: continue
    v, what, act = LABEL[k]
    H.append('<tr><td><span class="flag %s">%s</span></td><td>%s</td><td class="num">%d</td><td class="num">%d</td><td class="num">%s</td><td class="num">%.0f%%</td><td class="code">%s</td><td class="note">%s</td></tr>' % (cls[v], e(v), e(what), b["charges"], b["patients"], m(b["patbal"]), 100 * b["patbal"] / tot if tot else 0, e(", ".join("%s %d" % kv for kv in b["carriers"].items())), e(act)))
H.append('</tbody></table></div>')
H.append('<input class="search" id="q" type="search" placeholder="Filter rows by patient, chart, visit, carrier, plan or recommendation" aria-label="Filter rows">')
for k, b in S.items():
    rows = [r for r in R if r["bucket"] == k]
    if not rows or k == "SETTLED": continue
    v, what, act = LABEL[k]
    H.append('<details class="pkg"%s><summary><span><div class="t"><span class="flag %s">%s</span> %s</div><div class="d">%s</div></span><span class="amt">%s<small>%d charges · %d patients</small></span></summary><div class="body">%s</div></details>' % (" open" if v == "Retrievable" else "", cls[v], e(v), e(what), e(act), m(b["patbal"]), b["charges"], b["patients"], table(rows)))
H.append('''<script>
(function(){const q=document.getElementById('q');q.addEventListener('input',()=>{const s=q.value.trim().toLowerCase();document.querySelectorAll('details.pkg tbody tr').forEach(tr=>{tr.hidden=!!s&&!tr.textContent.toLowerCase().includes(s);});if(s)document.querySelectorAll('details.pkg').forEach(d=>d.open=true);});})();
</script></div>''')
open("patient_balances_%s.html" % STAMP, "w").write("\n".join(H)); print("wrote patient_balances_%s.html" % STAMP)
