# PLAIN ENGLISH (CCM documentation hub - William 11/11/2026: "new artifact called ccm documentation hub, this will be a fax archive and
#   additional practice notes for CCM supporting the ccm charges ... a note or folder for each ccm charge that will contain a minimum of a
#   statement note that the time was spent and at a maximum any unlimited number of supporting documents").
# Decides: nothing about a charge. It turns chronic-care-management charge lines into ONE RECORD PER PATIENT PER CALENDAR MONTH (the unit
#   CCM is billed in) and lays out that month's late-entry note the way his sample encounter note is laid out: the practice's letterhead,
#   the patient, the location, the provider, the charge date and codes, a section headed LATE ENTRY, and his signed stamp down the side.
#   The late entry names the date of the charge and the month of the charge, then the day it was written (his wording, 11/11/2026).
# The statement (his own words; codes confirmed by him 11/11/2026): 99487 alone = "Greater than 60 minutes spent ...", 99487 with 99489 =
#   "Greater than 90 minutes spent ...". Any other set of codes gets NO ready-made statement: the record is flagged and he writes that one.
# What this helper never does:
#   - sign for him: the stamp appears only when a signing (who, when) was recorded for THAT note; a note nobody signed says DRAFT - NOT SIGNED;
#   - date a note an earlier day: a late entry is dated the day it is written, and it cannot be signed before it was written;
#   - take support from another month: a supporting item must fall in the note's own calendar month;
#   - assert anything else: the statement is his sentence and the month - whether it is true of that patient and month is his to review
#     before he signs. A month with no supporting item says so on the note and is flagged for him (needs_review).
# Patient data: none is kept here. A caller passes the patient and the practice at run time (from Neon, the primary store); nothing of a
#   patient is written into the repository. Standard library only; never talks to AdvancedMD, RingCentral or Neon.
import re, html, datetime, collections
PRACTICE_NAME = "North Florida Senior Care"      # the name at the top of every note (William 11/11/2026) unless a caller names another practice
CCM_CODES = ("99487", "99489", "99490", "99491", "99439", "99437", "G0506")      # the care-management codes a record is built for
STATEMENT = ("Greater than %d minutes spent during %s performing chart review, reviewing medication lists, faxes, labs, orders, referrals, "
             "phone conversations with nurses, the ARNP, the treatment team and family if needed, and on developing treatment plans for this patient.")
MINUTES = {("99487",): 60, ("99487", "99489"): 90}      # William 11/11/2026: the two statements he gave; nothing else is ready-made
KINDS = ("fax_lab", "fax_order", "fax_hhc_plan_of_care", "fax_other", "phone_call", "call_transcript", "referral", "prescription", "email", "pcc_record", "other")
KIND_WORDS = {"fax_lab": "Lab (fax)", "fax_order": "Order (fax)", "fax_hhc_plan_of_care": "Home health plan of care (fax)", "fax_other": "Fax", "phone_call": "Phone call",
              "call_transcript": "Phone call (transcript)", "referral": "Referral", "prescription": "Prescription", "email": "E-mail", "pcc_record": "Facility record (PCC)", "other": "Other"}

def _day(s):
    """a day from YYYY-MM-DD or MM/DD/YYYY (or a date), else None"""
    if isinstance(s, datetime.datetime): return s.date()
    if isinstance(s, datetime.date): return s
    for f in ("%Y-%m-%d", "%m/%d/%Y"):
        try: return datetime.datetime.strptime(str(s)[:10], f).date()
        except ValueError: pass
    return None
def month_name(ym): return datetime.date(int(ym[:4]), int(ym[5:7]), 1).strftime("%B %Y")
def months(lines):
    """Charge lines -> one record per patient per calendar month, in the order the months first appear:
    {"chart", "month": "YYYY-MM", "codes", "charges": the month's CCM lines, "minutes", "statement", "flag"}. A line that is no CCM code,
    or has no chart or no readable date, belongs to no record."""
    by = collections.OrderedDict()
    for l in lines:
        d = _day(l.get("dos")) if isinstance(l, dict) else None
        if d is None or not l.get("chart") or str(l.get("code")) not in CCM_CODES: continue
        by.setdefault((l["chart"], d.strftime("%Y-%m")), []).append(l)
    out = []
    for (chart, ym), ls in by.items():
        codes = tuple(sorted({str(l["code"]) for l in ls})); mins = MINUTES.get(codes)
        flag = ""
        if mins is None:
            flag = ("99489 without 99487 in %s - no ready-made statement, William writes this one himself" % month_name(ym)) if codes == ("99489",) else \
                   ("no ready-made statement for %s (William gave statements for 99487 and for 99487 with 99489) - he writes this one himself" % " + ".join(codes))
        out.append({"chart": chart, "month": ym, "codes": list(codes), "charges": ls, "minutes": mins,
                    "statement": (STATEMENT % (mins, month_name(ym))) if mins else None, "flag": flag})
    return out
def needs_review(month, evidence):
    """True when William has to look at this record himself before anything is signed: no ready-made statement, or no supporting item on file."""
    return month.get("statement") is None or not evidence
def _check_evidence(month, evidence):
    for e in evidence or []:
        if not isinstance(e, dict) or e.get("kind") not in KINDS: raise ValueError("a supporting item must have a kind out of: %s" % ", ".join(KINDS))
        d = _day(e.get("date"))
        if d is None or d.strftime("%Y-%m") != month["month"]: raise ValueError("a supporting item dated %s is outside %s - a month is supported by that month's own records" % (e.get("date"), month_name(month["month"])))
def note_html(month, patient, practice, written, today, evidence, signed=None):
    """The late-entry note of one patient-month as a whole page (HTML, prints on letter paper). written = the day the note is written and must
    be today; signed = {"by", "at"} only when a signing was recorded for this note. Raises ValueError rather than produce a note it must not."""
    if month.get("statement") is None: raise ValueError("this month has no ready-made statement (%s)" % (month.get("flag") or "codes without a statement"))
    w = _day(written); t = _day(today)
    if w is None or t is None or w != t: raise ValueError("a late entry is dated the day it is written - today, never an earlier day")
    stamp = ""
    if signed is not None:
        at = None
        try: at = datetime.datetime.strptime(str(signed.get("at") or "")[:19], "%Y-%m-%dT%H:%M:%S")
        except (ValueError, AttributeError): pass
        if not (isinstance(signed, dict) and str(signed.get("by") or "").strip() and at): raise ValueError("a signing must say who signed and when")
        if at.date() < w: raise ValueError("a note cannot be signed before it was written")
        stamp = "Electronically Signed and Reviewed by %s %s" % (str(signed["by"]).strip(), at.strftime("%m/%d/%Y %H:%M:%S"))
    _check_evidence(month, evidence)
    e = lambda x: html.escape(str(x if x is not None else ""))
    us = lambda d: _day(d).strftime("%m/%d/%Y") if _day(d) else e(d)
    mn = month_name(month["month"]); ch = month["charges"]
    first = ch[0] if ch else {}
    rows = "".join("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (us(c.get("dos")), e(c.get("code")), e(c.get("visit")), e(c.get("charge"))) for c in ch)
    ev = "".join("<li><b>%s</b> - %s - %s <span class=\"src\">(%s)</span></li>" % (us(x.get("date")), e(KIND_WORDS[x["kind"]]), e(x.get("summary")), e(x.get("source")))
                 for x in sorted(evidence or [], key=lambda x: str(_day(x.get("date")))))
    side = e(stamp) if stamp else "DRAFT - NOT SIGNED"
    return """<!doctype html><html lang="en"><head><meta charset="utf-8"><title>CCM late entry - %(chart)s - %(mn)s</title><style>
@page{size:letter;margin:.6in .6in .6in .9in} body{font:12.5px/1.4 Arial,Helvetica,sans-serif;color:#111;margin:0;padding:24px 24px 24px 56px;position:relative}
.top{display:flex;justify-content:space-between;font-size:11.5px} .head{text-align:center;margin:6px 0 14px} .head h1{font-size:22px;color:#666;margin:0 0 4px} .head div{color:#777;font-size:15px}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:6px 18px;margin-bottom:14px} .grid b{display:inline-block;min-width:74px} h2{font-size:15px;margin:18px 0 6px}
table{border-collapse:collapse;width:100%%} td,th{text-align:left;padding:3px 8px 3px 0;border-bottom:1px solid #ddd;font-size:12px} ul{margin:4px 0;padding-left:18px} .src{color:#666;font-size:11px}
.late{border:1px solid #999;padding:10px 12px;margin-top:6px} .side{position:fixed;left:14px;top:50%%;writing-mode:vertical-rl;transform:rotate(180deg) translateY(50%%);font-size:14px;white-space:nowrap}
.sig{margin-top:38px;border-top:1px solid #333;width:280px;padding-top:4px;font-size:11.5px} .foot{margin-top:26px;text-align:center;font-size:11px;color:#444}
</style></head><body>
<div class="side">%(side)s</div>
<div class="top"><span>%(name)s (%(dob)s) #%(chart)s</span><span>CCM month: %(mn)s</span></div>
<div class="head"><h1>%(pname)s</h1>%(paddr)s<div>Phone: %(phone)s &nbsp; Fax: %(fax)s</div></div>
<div class="grid"><div><b>Patient:</b> %(name)s</div><div><b>DOB:</b> %(dob)s</div><div><b>Primary Ins:</b> %(ins)s</div>
<div><b>Location:</b> %(fac)s</div><div><b>Provider:</b> %(prov)s</div><div><b>Chart:</b> %(chart)s</div></div>
<h2>Chronic care management charges - %(mn)s</h2>
<table><thead><tr><th>Charge date</th><th>Code</th><th>Visit</th><th>Charge</th></tr></thead><tbody>%(rows)s</tbody></table>
<h2>LATE ENTRY</h2>
<div class="late"><p><b>LATE ENTRY for the charge dated %(dates)s, for the month of %(mn)s</b> (%(codes)s). Written %(written)s.</p><p>%(statement)s</p></div>
<h2>Supporting documentation on file for %(mn)s</h2>
%(evidence)s
<div class="sig">Rendering Provider Signature - %(prov)s</div>
<div class="foot">%(pname)s | %(prov)s | Late entry written %(written)s</div>
</body></html>""" % {"chart": e(month["chart"]), "mn": e(mn), "side": side, "name": e(patient.get("name")), "dob": e(us(patient.get("dob")) if patient.get("dob") else ""),
                      "pname": e(practice.get("name") or PRACTICE_NAME), "dates": e(" and ".join(sorted({us(c.get("dos")) for c in ch}))), "paddr": "".join("<div>%s</div>" % e(a) for a in practice.get("address") or []), "phone": e(practice.get("phone")), "fax": e(practice.get("fax")),
                      "ins": e(patient.get("insurance")), "fac": e(first.get("facility")), "prov": e(first.get("provider")), "rows": rows, "written": w.strftime("%m/%d/%Y"),
                      "codes": e(" + ".join(month["codes"])), "statement": e(month["statement"]),
                      "evidence": ("<ul>%s</ul>" % ev) if ev else "<p>No supporting item is on file for this month. The statement above stands alone.</p>"}
