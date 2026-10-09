# PLAIN ENGLISH (Old-claims disposition - the review page William approves from)
# Decides: nothing. Renders old_claims_disposition_<stamp>.json as one HTML page: the approval packages first (what gets posted,
#   what gets written off, with the payer's own figures beside every line), then the lists that need no approval tonight
#   (adjudicated residuals, denials inside 12 months, pending, review, hold, settled). Names and dollars only - no member ids.
# Never touches: AMD.
"""Usage: python3 old_claims_review_page.py [--stamp 1009]"""
import json, sys, html, collections, datetime
a = sys.argv[1:]; STAMP = a[a.index("--stamp") + 1] if "--stamp" in a else "1009"
D = json.load(open("old_claims_disposition_%s.json" % STAMP)); V = D["visits"]; S = D["summary"]; PK = D["packages"]
e = lambda s: html.escape(str(s if s is not None else ""))
m = lambda x: "$%s" % format(round(float(x or 0), 2), ",.2f")
LETTERS = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]
LIST_ORDER = ["ADJ-RESIDUAL", "CASCADE", "WAIT", "NO-ANSWER", "REVIEW", "REVIEW-ORDER", "HOLD-AET12", "SETTLED"]
LIST_TXT = {"ADJ-RESIDUAL": "Adjudicated - the payer already paid or answered on this visit; what is open is cost-sharing or an unadjusted contractual. Belongs to the insurances-cleaning pass (supplement / Medicaid crossover / patient statement / QMB write-off), not to a claim-status disposition.",
            "CASCADE": "Denied inside 12 months - the denial cascade works these (diagnosis, payer, eligibility fixes), not a write-off.",
            "WAIT": "Pending at the payer, or sent on 10/6-10/7 and on the timely-filing watch - leave alone.",
            "NO-ANSWER": "Inside 12 months and the payer gave no usable claim-status answer tonight - next Sunday sweep.",
            "REVIEW": "The payer says 'not on file' but the visit already carries a payer claim number - a search miss, needs a look before anything.",
            "REVIEW-ORDER": "The balance sits at a secondary plan but no primary payment is posted - the insurance order needs a look.",
            "HOLD-AET12": "Aetna Senior Supplemental crossover claims - on hold by the 9/21 rule, worked from the Aetna side.",
            "SETTLED": "No open insurance balance on the live chart any more (settled since the unpaid list was pulled)."}
def row(r, pkg=True):
    ans = r["answer"]; acts = r["actions"]
    paid = ("%s chk %s %s" % (m(ans["paid"]), ", ".join(ans["checks"]) or "?", ", ".join(ans["dates"]) or "")) if ans["kind"] == "PAID" else (ans["action"] or ("no 277" if not ans["src"] else ans["kind"]))
    wo = ", ".join(sorted({x["wocode"] for x in acts if x.get("wo") and x.get("wocode")}))
    flags = []
    if r["deceased"]: flags.append('<span class="flag out">deceased flag</span>')
    if r["patbal"] > 0: flags.append('<span class="flag wait">patient bal %s</span>' % m(r["patbal"]))
    if r["other_plans"]: flags.append('<span class="flag hold">also on chart: %s</span>' % e("/".join(r["other_plans"])))
    cells = [('<td class="name">%s <span class="code">%s</span></td>' % (e(r["patient"]), e(r["pid"]))), '<td class="code">%s</td>' % e(r["vid"]), '<td>%s</td>' % e(r["dos"]), '<td class="num">%d</td>' % r["age"],
             '<td>%s</td>' % e(r["carrier"]), '<td class="code">%s</td>' % e(r["cpts"]), '<td class="num wait">%s</td>' % m(r["open"]), '<td class="code">%s</td>' % e(paid)]
    if pkg: cells += ['<td class="num in">%s</td>' % (m(r["pay_total"]) if r["pay_total"] else ""), '<td class="num out">%s</td>' % (("%s %s" % (m(r["wo_total"]), wo)) if r["wo_total"] else ("resend" if r["tier"] in ("RESEND", "MEDICARE-UNANSWERED") else ""))]
    cells.append('<td class="note">%s %s</td>' % (" ".join(flags), e("; ".join(r["notes"]))))
    return "<tr>%s</tr>" % "".join(cells)
def table(rows, pkg=True):
    head = ["Patient / chart", "Visit", "DOS", "Days", "Carrier", "CPT", "Open", "Payer's answer (277)"] + (["Post", "Write off"] if pkg else []) + ["Notes"]
    return '<div class="tw"><table><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>' % ("".join("<th>%s</th>" % h for h in head), "".join(row(r, pkg) for r in rows))
def carriers(rows):
    c = collections.Counter(); d = collections.defaultdict(float)
    for r in rows: c[r["carrier"]] += 1; d[r["carrier"]] += r["open"]
    return ", ".join("%s %d (%s)" % (k, n, m(d[k])) for k, n in c.most_common())
out = []
out.append("<title>Old Claims Disposition</title>")
out.append("""<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,500;6..72,600;6..72,700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<style>
/* layout: the Money Ledger's token system (same practice, same reader); packages first, lists after, one wide table per section */
:root{--bg:#F7F3EC;--surface:#FFFDF9;--line:#DDD5C7;--ink:#1F2621;--muted:#66705F;--in:#1F6F4A;--in-soft:#DDEFE4;--out:#8B2E2E;--out-soft:#F3DEDE;--wait:#A9741A;--wait-soft:#F6EBD3;--hold:#4A5F7A;--hold-soft:#E0E7EF;
--disp:'Newsreader',Georgia,'Times New Roman',serif;--sans:'IBM Plex Sans',system-ui,-apple-system,'Segoe UI',sans-serif;--mono:'IBM Plex Mono',ui-monospace,Menlo,Consolas,monospace}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#151917;--surface:#1D2320;--line:#323B36;--ink:#EAE6DD;--muted:#A3AB9C;--in:#6BC29A;--in-soft:#173026;--out:#E07A7A;--out-soft:#3A1F1F;--wait:#E0B25E;--wait-soft:#3A2E14;--hold:#8FA9C8;--hold-soft:#1E2A38;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#151917;--surface:#1D2320;--line:#323B36;--ink:#EAE6DD;--muted:#A3AB9C;--in:#6BC29A;--in-soft:#173026;--out:#E07A7A;--out-soft:#3A1F1F;--wait:#E0B25E;--wait-soft:#3A2E14;--hold:#8FA9C8;--hold-soft:#1E2A38;color-scheme:dark}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:14.5px;line-height:1.45}
.wrap{max-width:1280px;margin:0 auto;padding-block:28px 80px;padding-inline:20px}
h1{font-family:var(--disp);font-weight:700;font-size:34px;letter-spacing:-.01em;margin:0;line-height:1.05;text-wrap:balance}
.asof{font:500 12.5px var(--mono);color:var(--muted);margin-top:6px}
h2{font-family:var(--disp);font-size:22px;font-weight:600;margin:28px 0 8px;text-wrap:balance}
.note{color:var(--muted);font-size:13.5px;max-width:80ch;margin:0 0 12px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;margin:18px 0 10px}
.kpi{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:12px 14px;min-width:0}
.kpi .l{font:500 11.5px var(--sans);letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}.kpi .v{font:600 24px var(--mono);font-variant-numeric:tabular-nums;line-height:1.15;margin-top:4px}.kpi .s{font-size:12.5px;color:var(--muted);margin-top:3px}
.kpi.in .v{color:var(--in)}.kpi.out .v{color:var(--out)}.kpi.wait .v{color:var(--wait)}.kpi.hold .v{color:var(--hold)}
details.pkg{background:var(--surface);border:1px solid var(--line);border-radius:10px;margin-bottom:10px;overflow:hidden}
details.pkg summary{list-style:none;cursor:pointer;display:grid;grid-template-columns:44px 1fr auto;gap:14px;align-items:center;padding:12px 16px}
details.pkg summary::-webkit-details-marker{display:none}
.lt{font:700 20px var(--mono);color:var(--hold)}.t{font:600 15.5px var(--sans)}.d{font-size:13px;color:var(--muted);margin-top:2px}
.amt{font:600 18px var(--mono);font-variant-numeric:tabular-nums;text-align:right;white-space:nowrap}.amt small{display:block;font:500 11.5px var(--mono);color:var(--muted)}
details.pkg .body{border-top:1px solid var(--line);padding:10px 16px 14px}
.tw{overflow-x:auto;background:var(--surface);border:1px solid var(--line);border-radius:8px;min-width:0}
table{border-collapse:collapse;width:100%;font-size:13px}th,td{padding:7px 9px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top;font-variant-numeric:tabular-nums}
th{font:600 10.5px var(--sans);letter-spacing:.07em;text-transform:uppercase;color:var(--muted);position:sticky;top:env(safe-area-inset-top,0px);background:var(--surface);white-space:nowrap}
td.name{font-weight:600;white-space:nowrap}td.code,.code{font:500 12px var(--mono);color:var(--muted)}td.num{text-align:right;font:500 12.5px var(--mono);white-space:nowrap}
td.in{color:var(--in)}td.out{color:var(--out)}td.wait{color:var(--wait)}td.note{min-width:28ch;max-width:62ch;font-size:12.5px;color:var(--muted)}
tr:last-child td{border-bottom:0}
.flag{display:inline-block;font:600 10.5px var(--sans);letter-spacing:.04em;text-transform:uppercase;padding:2px 7px;border-radius:999px;margin:0 4px 3px 0;white-space:nowrap}
.flag.out{background:var(--out-soft);color:var(--out)}.flag.wait{background:var(--wait-soft);color:var(--wait)}.flag.hold{background:var(--hold-soft);color:var(--hold)}
.search{width:100%;max-width:420px;padding:9px 12px;border:1px solid var(--line);border-radius:8px;background:var(--surface);color:var(--ink);font:14px var(--sans);margin:8px 0 14px}
.search:focus-visible{outline:2px solid var(--hold);outline-offset:2px}
.rules{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:12px 16px;margin:12px 0 20px;font-size:13.5px}.rules li{margin:4px 0}
@media (max-width:760px){details.pkg summary{grid-template-columns:36px 1fr}.amt{text-align:left}}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
</style>""")
pk = {k: [r for r in V if r["pkg"] == k] for k in LETTERS}; pkdec = {k: [r for r in V if r["pkg"] == k + "-dec"] for k in LETTERS}
post_total = sum(r["pay_total"] for r in V if r["pkg"]); wo_total = sum(r["wo_total"] for r in V if r["pkg"]); open_pk = sum(r["open"] for r in V if r["pkg"])
lists = {t: [r for r in V if not r["pkg"] and r["tier"] == t] for t in LIST_ORDER}
out.append('<div class="wrap"><header><h1>Old Claims Disposition</h1><div class="asof">Built %s UTC from the live chart and the payers\' 277 answers · %d visits over 90 days on the unpaid list · nothing is posted until a package is approved</div></header>' % (e(D["built"].replace("T", " ")[:16]), len(V)))
out.append('<div class="kpis">' + "".join('<div class="kpi %s"><div class="l">%s</div><div class="v">%s</div><div class="s">%s</div></div>' % x for x in [
    ("wait", "In the approval packages", m(open_pk), "%d visits, open insurance balance" % sum(1 for r in V if r["pkg"])),
    ("in", "Posted from the payers' own figures", m(post_total), "277 paid amount, check number and paid date on %d visits" % sum(1 for r in V if r["tier"] == "POST-277")),
    ("out", "Written off", m(wo_total), "contractual remainder after a 277 payment, untimely never-adjudicated claims, paid-per-payer with no remit"),
    ("hold", "Not in a package", m(sum(r["open"] for r in V if not r["pkg"])), "%d visits: adjudicated residuals, denials inside 12 months, pending, review, hold" % sum(1 for r in V if not r["pkg"]))]) + "</div>")
out.append('<div class="rules"><b>How the packages were built</b><ul>'
           '<li><b>Post per 277 (A, B, C):</b> the payer\'s claim-status answer carries its own paid amount, check/EFT number and paid date. That amount is posted as the payment with that check number and date. The remainder of the charge is written off WOINS (contractual) when the chart has no other plan, WOCAID2ND when the other plan is Medicaid, and is left open when the other plan is a supplement or commercial secondary. Without the 835 the patient-share split is unknown, so the whole remainder is treated as contractual on these old claims.</li>'
           '<li><b>Write off untimely (D, E, F):</b> never adjudicated and the date of service is over 12 months back. WOLATE when the payer answered (not on file / denied / finalized $0), WOINS with the dated untimely note when there is no payer answer. Only balances in the primary position; a secondary with no primary payment is in the review list instead.</li>'
           '<li><b>Resend (G, H):</b> payer says not on file inside 12 months (G), or a Medicare claim inside 12 months with no adjudication on the chart (H): one original-claim send each (freq 1), under the one-rebill-per-visit rule and the deceased guard.</li>'
           '<li>A package letter ending in <b>-dec</b> holds the same action on charts with a deceased flag: confirm the date of service is before the date of death first (a charge after the date of death is voided, never written off).</li></ul></div>')
out.append('<input class="search" id="q" type="search" placeholder="Filter rows by patient, chart, visit, carrier or note" aria-label="Filter rows">')
out.append("<h2>Approval packages</h2>")
for k in LETTERS:
    for suffix, rows in (("", pk[k]), ("-dec", pkdec[k])):
        if not rows: continue
        openv = sum(r["open"] for r in rows); pay = sum(r["pay_total"] for r in rows); wo = sum(r["wo_total"] for r in rows)
        out.append('<details class="pkg" %s id="pkg-%s%s"><summary><span class="lt">%s%s</span><span><div class="t">%s</div><div class="d">%d visits · %s</div></span><span class="amt">%s open<small>%s%s</small></span></summary><div class="body">%s</div></details>'
                   % ("open" if suffix == "" else "", k, suffix.replace("-", ""), k, suffix, e(PK[k]) + (" - DECEASED FLAG charts" if suffix else ""), len(rows), e(carriers(rows)), m(openv),
                      ("post %s · " % m(pay)) if pay else "", ("write off %s" % m(wo)) if wo else ("%d resends" % len(rows)), table(rows, True)))
out.append("<h2>Not in a package tonight</h2><p class=\"note\">Listed so the whole over-90-day book is accounted for. These need no approval and are routed to the pass that owns them.</p>")
for t in LIST_ORDER:
    rows = lists[t]
    if not rows: continue
    out.append('<details class="pkg" id="list-%s"><summary><span class="lt">·</span><span><div class="t">%s</div><div class="d">%d visits · %s</div></span><span class="amt">%s open</span></summary><div class="body"><p class="note">%s</p>%s</div></details>'
               % (e(t.lower()), e(t), len(rows), e(carriers(rows)), m(sum(r["open"] for r in rows)), e(LIST_TXT.get(t, "")), table(rows, False)))
out.append("""</div><script>
(function(){var q=document.getElementById('q');var rows=Array.prototype.slice.call(document.querySelectorAll('tbody tr'));
function run(){var s=(q.value||'').toLowerCase().trim();rows.forEach(function(r){r.hidden=!!s&&r.textContent.toLowerCase().indexOf(s)<0});
if(s){document.querySelectorAll('details.pkg').forEach(function(d){d.open=true})}}
q.addEventListener('input',run);try{var h=location.hash.replace('#','');if(h){var d=document.getElementById(h);if(d){d.open=true;d.scrollIntoView()}}}catch(e){}})();
</script>""")
open("old_claims_review_%s.html" % STAMP, "w").write("\n".join(out))
print("wrote old_claims_review_%s.html (%d visits, %d in packages)" % (STAMP, len(V), sum(1 for r in V if r["pkg"])))
