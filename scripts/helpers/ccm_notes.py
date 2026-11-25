# PLAIN ENGLISH (CCM documentation hub - William 11/11/2026: "new artifact called ccm documentation hub, this will be a fax archive and
#   additional practice notes for CCM supporting the ccm charges ... a note or folder for each ccm charge that will contain a minimum of a
#   statement note that the time was spent and at a maximum any unlimited number of supporting documents").
# Decides: nothing about a charge. It turns chronic-care-management charge lines into ONE RECORD PER PATIENT PER CALENDAR MONTH (the unit
#   CCM is billed in) and lays out that month's late-entry note the way his sample encounter note is laid out: the practice's letterhead,
#   the patient, the location, the provider, the charge date and codes, a section headed LATE ENTRY, and his signed stamp down the side.
#   The late entry names the date of the charge and the month of the charge, then the day it was written (his wording, 11/11/2026).
# The statement (his own words; codes confirmed by him 11/11/2026; wording approved by him and his attorney 11/11/2026): 99487 alone =
#   "Greater than 60 minutes spent ...", 99487 with ONE 99489 = "Greater than 90 minutes spent ...". Any other set of codes - 99489 without
#   99487, 99489 billed more than once (more than 120 minutes), a CCM code he gave no statement for - gets NO ready-made statement: the
#   record is flagged and he writes that one himself.
# Flags (a flagged month is never part of a "sign all"; he opens it and decides): no ready-made statement; 99487 billed more than once in
#   the month (it is billed once a month - a duplicate charge to check); a line billed under another clinician than the signer.
# What a signature covers: note_fields() is the whole content of a note as plain text (practice, patient, birth date, insurance, location,
#   provider, codes, the charge lines, the late-entry line, the statement, the supporting items). At signing the day it is written is added
#   and the SHA-256 of that text in one fixed form (canon()) is recorded with who signed and when. verify_signature() recomputes it from
#   the stored draft: a note whose content changed after he saw it is refused, never signed in his name.
# What this helper never does:
#   - sign for him: the stamp appears only when a signing (who, when) was recorded for THAT note; a note nobody signed says DRAFT - NOT SIGNED;
#   - date a note an earlier day: a late entry is dated the day it is written, and it cannot be signed before it was written;
#   - take support from another month: a supporting item must fall in the note's own calendar month;
#   - assert anything else: the statement is his sentence and the month - whether it is true of that patient and month is his to review
#     before he signs. A month with no supporting item says so on the note (the statement stands alone, as he decided).
# Patient data: none is kept here. A caller passes the patient and the practice at run time (from Neon, the primary store); nothing of a
#   patient is written into the repository. Standard library only; never talks to AdvancedMD, RingCentral or Neon.
# The hub page (tools/db/ccm_hub_page.html) does the same canon() and SHA-256 in JavaScript; tools/selftest/test_ccm_notes.py proves the two agree.
# Diagnoses (William 11/12/2026: "on all these signed notes add to them the diagnoses that were included with the charge in a diagnosis with
#   icd10 number as was shown in the original sample note"; "for new notes going forward always include the individual patient icd10 diagnosis
#   list, this is the first thing medicare looks for"): diagnoses() lists the ICD-10 codes on a month's CCM charge lines - the 99487 line
#   first, then 99489 (then any other CCM code), each line's codes in AdvancedMD's order, each code once - with its CMS description. A new
#   note carries them in its fields ("diagnoses") and shows them as a "Diagnoses (ICD-10)" table; a month whose charge carries fewer than
#   two is flagged (Medicare looks first for two or more qualifying chronic conditions). A signed note keeps the fields he signed.
# Addenda (William 11/12/2026: "add this as an addendum to the note, if needed i can sign the addendums later after they are added"): a
#   signed note is never edited. addendum_fields() is the whole content of a dated ADDENDUM to ONE signed note - the diagnoses on that
#   note's CCM charge lines - naming the note it adds to (its id, the day it was written, the hash he signed). It is signed exactly like a
#   note (signing_sha over the fields and the day written; verify_signature(..., statement=False): no statement, never dated before the
#   note), and render(..., addenda=...) sets it under the note on its own sheet with its own stamp: signed, or ADDENDUM - NOT SIGNED.
import re, html, json, hashlib, datetime, collections
PRACTICE_NAME = "North Florida Senior Care"      # the name at the top of every note (William 11/11/2026) unless a caller names another practice
LETTERHEAD = ("%d %s NE, Ste 9" % (1891, "Capital " + "Circle"), "Tallahassee, FL 32308")      # as on his sample note (the practice's own office, not a patient's)
PHONE, FAX = "(850) " + "391-6222", "(888) " + "698-2714"
SIGNER, SIGNER_CODE = "EFFINGER, WILLIAM", "WEFFI"      # the name on his stamp, and his AdvancedMD provider profile
CCM_CODES = ("99487", "99489", "99490", "99491", "99439", "99437", "G0506")      # the care-management codes a record is built for
STATEMENT = ("Greater than %d minutes spent during %s performing chart review, reviewing medication lists, faxes, labs, orders, referrals, "
             "phone conversations with nurses, the ARNP, the treatment team and family if needed, and on developing treatment plans for this patient.")
MINUTES = {("99487",): 60, ("99487", "99489"): 90}      # William 11/11/2026: the two statements he gave; nothing else is ready-made
KINDS = ("fax_lab", "fax_order", "fax_hhc_plan_of_care", "fax_other", "phone_call", "call_transcript", "referral", "prescription", "email", "pcc_record", "other")
KIND_WORDS = {"fax_lab": "Lab (fax)", "fax_order": "Order (fax)", "fax_hhc_plan_of_care": "Home health plan of care (fax)", "fax_other": "Fax", "phone_call": "Phone call",
              "call_transcript": "Phone call (transcript)", "referral": "Referral", "prescription": "Prescription", "email": "E-mail", "pcc_record": "Facility record (PCC)", "other": "Other"}
FIELD_KEYS = ("practice", "chart", "month", "patient", "dob", "insurance", "location", "provider", "codes", "charges", "diagnoses", "late_entry", "statement", "evidence")
DX_ORDER = ("99487", "99489")      # William 11/12/2026: the codes on the 99487 line first, then the 99489 line's (then any other CCM code)
DX_FLAG = "fewer than two diagnoses on the CCM charge (%d) - Medicare looks first for two or more qualifying chronic conditions - check the chart's diagnosis list"
ADDENDUM_KEYS = ("kind", "practice", "chart", "month", "patient", "dob", "provider", "note", "note_written", "note_sha", "addendum_to", "charges", "diagnoses")

def _day(s):
    """a day from YYYY-MM-DD or MM/DD/YYYY (or a date), else None"""
    if isinstance(s, datetime.datetime): return s.date()
    if isinstance(s, datetime.date): return s
    for f in ("%Y-%m-%d", "%m/%d/%Y"):
        try: return datetime.datetime.strptime(str(s)[:10], f).date()
        except ValueError: pass
    return None
def us(d):
    """MM/DD/YYYY, or "" when there is no readable day"""
    x = _day(d)
    return x.strftime("%m/%d/%Y") if x else ""
def month_name(ym): return datetime.date(int(ym[:4]), int(ym[5:7]), 1).strftime("%B %Y")
def local_day(at):
    """the practice's calendar day (Eastern time, daylight saving included) of a time that carries its zone"""
    try:
        from zoneinfo import ZoneInfo
        return at.astimezone(ZoneInfo("America/New_York")).date()
    except Exception:      # no time-zone table on this machine: US Eastern rules (second Sunday of March to first Sunday of November)
        u = at.astimezone(datetime.timezone.utc).replace(tzinfo=None); y = u.year
        start = datetime.datetime(y, 3, 8 + (6 - datetime.date(y, 3, 8).weekday()) % 7, 7); end = datetime.datetime(y, 11, 1 + (6 - datetime.date(y, 11, 1).weekday()) % 7, 6)
        return (u - datetime.timedelta(hours=4 if start <= u < end else 5)).date()
def _units(l):
    try: return max(1, int(float(l.get("units") or 1)))
    except (TypeError, ValueError): return 1
def months(lines, signer=None):
    """Charge lines -> one record per patient per calendar month, in the order the months first appear:
    {"chart", "month": "YYYY-MM", "codes", "counts": units per code, "charges": the month's CCM lines, "minutes", "statement", "flag"}.
    A line that is no CCM code, or has no chart or no readable date, belongs to no record. signer = the provider profile whose notes these
    are (e.g. WEFFI): a month with a line billed under anyone else is flagged (a line's provider_code, else its provider). Where the lines
    carry their ICD-10 codes ("dx", as ccm_build.py reads them from the AdvancedMD history), a month whose charge carries fewer than two
    is flagged too (DX_FLAG)."""
    by = collections.OrderedDict()
    for l in lines:
        d = _day(l.get("dos")) if isinstance(l, dict) else None
        if d is None or not l.get("chart") or str(l.get("code")) not in CCM_CODES: continue
        by.setdefault((l["chart"], d.strftime("%Y-%m")), []).append(l)
    out = []
    for (chart, ym), ls in by.items():
        counts = collections.Counter()
        for l in ls: counts[str(l["code"])] += _units(l)
        codes = tuple(sorted(counts)); mn = month_name(ym)
        mins = MINUTES.get(codes) if counts.get("99489", 0) <= 1 else None
        flags = []
        if mins is None:
            if counts.get("99489", 0) > 1:
                flags.append("99489 billed %d times in %s (more than %d minutes) - no ready-made statement, William writes this one himself" % (counts["99489"], mn, 60 + 30 * counts["99489"]))
            elif codes == ("99489",): flags.append("99489 without 99487 in %s - no ready-made statement, William writes this one himself" % mn)
            else: flags.append("no ready-made statement for %s (William gave statements for 99487 and for 99487 with 99489) - he writes this one himself" % " + ".join(codes))
        if counts.get("99487", 0) > 1:
            flags.append("99487 billed %d times in %s - it is billed once a month: check for a duplicate charge before signing" % (counts["99487"], mn))
        if signer:
            others = sorted({str(l.get("provider_code") or l.get("provider") or "") for l in ls} - {signer})
            if others: flags.append("billed under %s, not %s - check who signs this note" % (", ".join(o or "no provider" for o in others), signer))
        if any(isinstance(l.get("dx"), list) for l in ls):
            n = len(diagnoses([(l.get("code"), l.get("dx")) for l in ls]))
            if n < 2: flags.append(DX_FLAG % n)
        out.append({"chart": chart, "month": ym, "codes": list(codes), "counts": dict(counts), "charges": ls, "minutes": mins,
                    "statement": (STATEMENT % (mins, mn)) if mins else None, "flag": "; ".join(flags)})
    return out
def describe(code, descriptions):
    """the CMS description of an ICD-10 code ("" when none is known); descriptions = code -> description, or code -> [description, fiscal
    year] as the reference document ccm_build.py writes holds it"""
    d = (descriptions or {}).get(code)
    if isinstance(d, (list, tuple)): d = d[0] if d else ""
    return str(d or "")
def diagnoses(lines, descriptions=None):
    """The ICD-10 codes on a month's CCM charge lines, each code once: the 99487 line first, then 99489, then any other CCM code (lines of
    one code keep their order), each line's codes in AdvancedMD's order. lines = (code, [ICD-10 codes]) pairs. Returns [[code, description]]."""
    rank = lambda c: DX_ORDER.index(c) if c in DX_ORDER else len(DX_ORDER) + (CCM_CODES.index(c) if c in CCM_CODES else len(CCM_CODES))
    seen = collections.OrderedDict()
    for code, dx in sorted(list(lines or []), key=lambda l: rank(str(l[0]))):      # sorted() is stable
        for x in (dx if isinstance(dx, (list, tuple)) else []):
            x = str(x or "").strip()
            if x and x not in seen: seen[x] = describe(x, descriptions)
    return [[k, v] for k, v in seen.items()]
def dx_flag(dx):
    """the flag of a charge that carries fewer than two diagnoses ("" when it carries two or more)"""
    n = len(dx or [])
    return DX_FLAG % n if n < 2 else ""
def needs_review(month, evidence):
    """True when William has to look at this record himself before anything is signed: no ready-made statement, a flag, or no supporting item on file."""
    return month.get("statement") is None or bool(month.get("flag")) or not evidence
def _check_evidence(month, evidence):
    for e in evidence or []:
        if not isinstance(e, dict) or e.get("kind") not in KINDS: raise ValueError("a supporting item must have a kind out of: %s" % ", ".join(KINDS))
        d = _day(e.get("date"))
        if d is None or d.strftime("%Y-%m") != month["month"]: raise ValueError("a supporting item dated %s is outside %s - a month is supported by that month's own records" % (e.get("date"), month_name(month["month"])))
def _distinct(xs): return list(collections.OrderedDict((x, 1) for x in xs if x).keys())
def note_fields(month, patient, practice=None, evidence=None):
    """The whole content of one patient-month's note, as plain text (strings and lists of strings only): what a signature attests to,
    together with the day it is written (added at signing). The diagnoses are month["diagnoses"] ([code, description] - ccm_build.py puts
    them there with the CMS descriptions), else the codes the charge lines carry. Raises ValueError for a supporting item outside the month."""
    _check_evidence(month, evidence)
    ch = month.get("charges") or []
    mn = month_name(month["month"])
    dx = month.get("diagnoses")
    if dx is None: dx = diagnoses([(c.get("code"), c.get("dx")) for c in ch])
    return {"practice": str((practice or {}).get("name") or PRACTICE_NAME), "chart": str(month["chart"]), "month": str(month["month"]),
            "patient": str((patient or {}).get("name") or ""), "dob": us((patient or {}).get("dob")),
            "insurance": str(month.get("insurance") or (patient or {}).get("insurance") or ""),
            "location": "; ".join(_distinct(str(c.get("facility") or "") for c in ch)), "provider": "; ".join(_distinct(str(c.get("provider") or "") for c in ch)),
            "codes": [str(c) for c in month["codes"]],
            "charges": [[us(c.get("dos")), str(c.get("code") or ""), str(c.get("visit") or ""), str(c.get("charge") or "")] for c in ch],
            "diagnoses": [[str(x[0]), str(x[1]) if len(x) > 1 else ""] for x in dx if x],
            "late_entry": "LATE ENTRY for the charge dated %s, for the month of %s (%s)." % (" and ".join(sorted({us(c.get("dos")) for c in ch})), mn, " + ".join(month["codes"])),
            "statement": str(month.get("statement") or ""),
            "evidence": [[us(x.get("date")), KIND_WORDS[x["kind"]], str(x.get("summary") or ""), str(x.get("source") or "")] for x in sorted(evidence or [], key=lambda x: str(_day(x.get("date"))))]}
def canon(obj):
    """the one fixed text form of a note's fields that is hashed: keys sorted, no spaces, UTF-8 (the hub page's canon() is the same)"""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
def signing_sha(fields, written):
    """SHA-256 of the note's fields with the day it is written (MM/DD/YYYY) - what a signing records and what is checked later"""
    return hashlib.sha256(canon(dict(fields, written=us(written))).encode("utf-8")).hexdigest()
def verify_signature(fields, sig, statement=True):
    """A signing recorded on the hub page, checked against the stored draft. sig = {"written": MM/DD/YYYY, "at": ISO time, "by", "sha",
    optional "statement" (his own words, only where the draft has no ready-made statement)}. Returns (final fields with "written", "")
    or (None, why it is refused). statement=False for an ADDENDUM: it has no statement, so none is demanded and a signing that brings one
    is refused. Fields that name the note they add to ("note_written") are never signed before that note was written. Never signs anything itself."""
    if not isinstance(sig, dict): return None, "not a signing"
    by = str(sig.get("by") or "").strip(); w = _day(sig.get("written"))
    at = None
    try: at = datetime.datetime.fromisoformat(str(sig.get("at") or "").replace("Z", "+00:00"))
    except ValueError: pass
    if not by or at is None or at.tzinfo is None: return None, "a signing must say who signed and when (a time with its zone)"
    if w is None: return None, "a signing must carry the day the note was written"
    if local_day(at) != w: return None, "a late entry is written the day it is signed (the practice's day, Eastern time) - this one says %s" % us(w)
    f = dict(fields)
    nw = _day(f.get("note_written")) if f.get("note_written") else None
    if nw is not None and w < nw: return None, "an addendum is written after the note it adds to (that note was written %s)" % us(nw)
    own = str(sig.get("statement") or "").strip()
    if not statement:
        if own: return None, "an addendum carries no statement - a signing that brings one is refused"
    elif own:
        if f.get("statement"): return None, "this month has a ready-made statement - his own words replace it only where there was none"
        f["statement"] = own
    elif not f.get("statement"): return None, "this month has no ready-made statement and the signing carries none of his own"
    if signing_sha(f, w) != str(sig.get("sha") or ""): return None, "the %s changed after it was shown - it must be opened again and signed again" % ("note" if statement else "addendum")
    return dict(f, written=us(w)), ""
def addendum_fields(note, note_sha, dx, descriptions=None):
    """The whole content of the diagnosis ADDENDUM to one SIGNED note, as plain text (strings and lists of strings only): what his signing
    of the addendum attests to, together with the day it is written (added at signing). note = the signed note's stored fields (with the
    day it was written); note_sha = the hash he signed for it; dx = charge number -> the ICD-10 codes on that charge line, in AdvancedMD's
    order; descriptions = code -> CMS description. The note itself is never changed. Raises ValueError for a note that is not signed or
    that already lists its diagnoses (a note signed with them needs no addendum)."""
    if not isinstance(note, dict) or not note.get("chart") or not note.get("month"): raise ValueError("an addendum belongs to one signed note")
    if _day(note.get("written")) is None: raise ValueError("an addendum adds to a SIGNED note - this one carries no day it was written")
    if "diagnoses" in note: raise ValueError("this note was signed with its diagnoses - it needs no addendum")
    ch = [[str(x) for x in c] for c in note.get("charges") or [] if isinstance(c, (list, tuple))]
    lines = [(c[1] if len(c) > 1 else "", (dx or {}).get(c[3]) if len(c) > 3 else None) for c in ch]
    return {"kind": "diagnoses", "practice": str(note.get("practice") or PRACTICE_NAME), "chart": str(note["chart"]), "month": str(note["month"]),
            "patient": str(note.get("patient") or ""), "dob": str(note.get("dob") or ""), "provider": str(note.get("provider") or ""),
            "note": "%s_%s" % (note["chart"], note["month"]), "note_written": us(note["written"]), "note_sha": str(note_sha or ""),
            "addendum_to": "the late entry for the charge dated %s, for the month of %s" % (" and ".join(sorted({c[0] for c in ch if c})), month_name(note["month"])),
            "charges": ch, "diagnoses": diagnoses(lines, descriptions)}
def _stamp(signed):
    """"Electronically Signed and Reviewed by <who> <MM/DD/YYYY HH:MM:SS>" for a recorded signing ({"by", "at"}); "" for none"""
    if signed is None: return ""
    at = None
    try: at = datetime.datetime.strptime(str(signed.get("at") or "")[:19], "%Y-%m-%dT%H:%M:%S")
    except (ValueError, AttributeError): pass
    if not (isinstance(signed, dict) and str(signed.get("by") or "").strip() and at): raise ValueError("a signing must say who signed and when")
    return "Electronically Signed and Reviewed by %s %s" % (str(signed["by"]).strip(), at.strftime("%m/%d/%Y %H:%M:%S"))
def _e(x): return html.escape(str(x if x is not None else ""))
def _head(fields, p):
    addr = p.get("address") if p.get("address") is not None else list(LETTERHEAD)
    return ("<div class=\"top\"><span>%s (%s) #%s</span><span>CCM month: %s</span></div>\n<div class=\"head\"><h1>%s</h1>%s<div>Phone: %s &nbsp; Fax: %s</div></div>\n" % (
        _e(fields["patient"]), _e(fields["dob"]), _e(fields["chart"]), _e(month_name(fields["month"])), _e(fields["practice"]),
        "".join("<div>%s</div>" % _e(a) for a in addr), _e(p.get("phone") or PHONE), _e(p.get("fax") or FAX)))
def _charges(fields):
    return ("<h2>Chronic care management charges - %s</h2>\n<table><thead><tr><th>Charge date</th><th>Code</th><th>Visit</th><th>Charge</th></tr></thead><tbody>%s</tbody></table>\n" % (
        _e(month_name(fields["month"])), "".join("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % tuple(_e(x) for x in (list(c) + ["", "", "", ""])[:4]) for c in fields["charges"])))
def _dx_table(dx, heading):
    rows = "".join("<tr><td class=\"code\">%s</td><td>%s</td></tr>" % (_e(x[0]), _e(x[1]) if len(x) > 1 and x[1] else "<i>no CMS description</i>") for x in dx)
    return "<h2>%s</h2>\n%s" % (_e(heading), ("<table><thead><tr><th class=\"code\">ICD-10</th><th>Description</th></tr></thead><tbody>%s</tbody></table>\n" % rows) if rows else "<p>No diagnosis is on this month's CCM charge lines.</p>\n")
def addendum_section(fields, written=None, signed=None, practice=None):
    """ONE addendum as a sheet of its own (an HTML section, set under its note by render()): its own stamp down the side - signed, or
    ADDENDUM - NOT SIGNED - and "ADDENDUM - written <day>, to the late entry for the charge dated ..., for the month of ..." with the
    diagnoses on the CCM charge. written = the day it is (or was) written; signed = {"by", "at"} only when a signing was recorded for it."""
    p = practice or {}
    stamp = _stamp(signed)
    w = us(written)
    sha = str(fields.get("note_sha") or "")
    return ("<section class=\"pg add\">\n<div class=\"side\">%s</div>\n%s<div class=\"grid\"><div><b>Patient:</b> %s</div><div><b>DOB:</b> %s</div><div><b>Chart:</b> %s</div>\n"
            "<div><b>Provider:</b> %s</div><div><b>Note:</b> %s</div><div><b>Addendum:</b> diagnoses (ICD-10)</div></div>\n<h2>ADDENDUM</h2>\n"
            "<div class=\"late\"><p><b>ADDENDUM - %s, to %s.</b></p><p>The late entry was written and signed %s%s and is final: this addendum adds to it and changes nothing in it.</p></div>\n"
            "%s%s<div class=\"sig\">Rendering Provider Signature - %s</div>\n<div class=\"foot\">%s | %s | Addendum written %s</div>\n</section>") % (
        _e(stamp) if stamp else "ADDENDUM - NOT SIGNED", _head(fields, p), _e(fields["patient"]), _e(fields["dob"]), _e(fields["chart"]), _e(fields["provider"]), _e(fields["note"]),
        ("written " + _e(w)) if w else "dated the day it is signed", _e(fields["addendum_to"]), _e(fields["note_written"]), (" (fingerprint %s)" % _e(sha[:16])) if sha else "",
        _charges(fields), _dx_table(fields.get("diagnoses") or [], "Diagnoses on the CCM charge (ICD-10)"), _e(fields["provider"]), _e(fields["practice"]), _e(fields["provider"]), _e(w))
CSS = """@page{size:letter;margin:.6in .6in .6in .9in} body{font:12.5px/1.4 Arial,Helvetica,sans-serif;color:#111;margin:0;padding:24px 24px 24px 56px}
.pg{position:relative} .pg+.pg{break-before:page;page-break-before:always;margin-top:36px;padding-top:24px;border-top:2px dashed #bbb} @media print{.pg{min-height:9in}.pg+.pg{margin-top:0;padding-top:0;border-top:0}}
.top{display:flex;justify-content:space-between;font-size:11.5px} .head{text-align:center;margin:6px 0 14px} .head h1{font-size:22px;color:#666;margin:0 0 4px} .head div{color:#777;font-size:15px}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:6px 18px;margin-bottom:14px} .grid b{display:inline-block;min-width:74px} h2{font-size:15px;margin:18px 0 6px}
table{border-collapse:collapse;width:100%} td,th{text-align:left;padding:3px 8px 3px 0;border-bottom:1px solid #ddd;font-size:12px} .code{white-space:nowrap;width:1%;padding-right:14px} ul{margin:4px 0;padding-left:18px} .src{color:#666;font-size:11px}
.late{border:1px solid #999;padding:10px 12px;margin-top:6px} .side{position:absolute;left:-42px;top:50%;writing-mode:vertical-rl;transform:rotate(180deg) translateY(50%);font-size:14px;white-space:nowrap}
.sig{margin-top:38px;border-top:1px solid #333;width:280px;padding-top:4px;font-size:11.5px} .foot{margin-top:26px;text-align:center;font-size:11px;color:#444}"""
def render(fields, written=None, signed=None, practice=None, addenda=None):
    """The note of one patient-month as a whole page (HTML, prints on letter paper), from its fields. written = the day it is (or was)
    written; signed = {"by", "at"} only when a signing was recorded for this note. A note whose fields carry its diagnoses shows them as a
    "Diagnoses (ICD-10)" table (a note signed before 11/12/2026 has none in its fields: its diagnoses come as an addendum). addenda = a list
    of (addendum fields, the day it is or was written, {"by", "at"} or None): each is set under the note on a sheet of its own."""
    p = practice or {}
    e = _e
    stamp = _stamp(signed)
    mn = month_name(fields["month"])
    ev = "".join("<li><b>%s</b> - %s - %s <span class=\"src\">(%s)</span></li>" % tuple(e(x) for x in v) for v in fields["evidence"])
    side = e(stamp) if stamp else "DRAFT - NOT SIGNED"
    dx = _dx_table(fields["diagnoses"], "Diagnoses (ICD-10)") if fields.get("diagnoses") is not None else ""
    adds = "".join("\n" + addendum_section(a[0], a[1] if len(a) > 1 else None, a[2] if len(a) > 2 else None, practice) for a in (addenda or []))
    return """<!doctype html><html lang="en"><head><meta charset="utf-8"><title>CCM late entry - %(chart)s - %(mn)s</title><style>
%(css)s
</style></head><body>
<section class="pg note">
<div class="side">%(side)s</div>
%(head)s<div class="grid"><div><b>Patient:</b> %(name)s</div><div><b>DOB:</b> %(dob)s</div><div><b>Primary Ins:</b> %(ins)s</div>
<div><b>Location:</b> %(fac)s</div><div><b>Provider:</b> %(prov)s</div><div><b>Chart:</b> %(chart)s</div></div>
%(charges)s%(dx)s<h2>LATE ENTRY</h2>
<div class="late"><p><b>%(late)s</b> Written %(written)s.</p><p>%(statement)s</p></div>
<h2>Supporting documentation on file for %(mn)s</h2>
%(evidence)s
<div class="sig">Rendering Provider Signature - %(prov)s</div>
<div class="foot">%(pname)s | %(prov)s | Late entry written %(written)s</div>
</section>%(adds)s
</body></html>""" % {"chart": e(fields["chart"]), "mn": e(mn), "css": CSS, "side": side, "head": _head(fields, p), "name": e(fields["patient"]), "dob": e(fields["dob"]),
                      "pname": e(fields["practice"]), "ins": e(fields["insurance"]), "fac": e(fields["location"]), "prov": e(fields["provider"]), "charges": _charges(fields), "dx": dx,
                      "written": e(us(written)), "late": e(fields["late_entry"]), "statement": e(fields["statement"]), "adds": adds,
                      "evidence": ("<ul>%s</ul>" % ev) if ev else "<p>No supporting item is on file for this month. The statement above stands alone.</p>"}
def note_html(month, patient, practice, written, today, evidence, signed=None):
    """The late-entry note of one patient-month as a whole page. written = the day the note is written and must be today; signed =
    {"by", "at"} only when a signing was recorded for this note. Raises ValueError rather than produce a note it must not."""
    if month.get("statement") is None: raise ValueError("this month has no ready-made statement (%s)" % (month.get("flag") or "codes without a statement"))
    w = _day(written); t = _day(today)
    if w is None or t is None or w != t: raise ValueError("a late entry is dated the day it is written - today, never an earlier day")
    if signed is not None:
        at = None
        try: at = datetime.datetime.strptime(str(signed.get("at") or "")[:19], "%Y-%m-%dT%H:%M:%S")
        except (ValueError, AttributeError): pass
        if not (isinstance(signed, dict) and str(signed.get("by") or "").strip() and at): raise ValueError("a signing must say who signed and when")
        if at.date() < w: raise ValueError("a note cannot be signed before it was written")
    return render(note_fields(month, patient, practice, evidence), written=w, signed=signed, practice=practice)
