#!/usr/bin/env python3
# PLAIN ENGLISH (offline self-test, 11/11/2026): the CCM documentation hub - one record per patient per month, and its late-entry note.
# Decides: nothing. William 11/11/2026: every chronic care management charge gets a record that holds, at the least, his own signed
#   late-entry statement that the time was spent and, at the most, any number of supporting items found for that patient and month.
#   This test proves scripts/helpers/ccm_notes.py on invented charges only:
#     - charge lines are grouped per patient per calendar month (the unit CCM is billed in);
#     - the statement follows the codes he confirmed: 99487 alone = greater than 60 minutes, 99487 with 99489 = greater than 90 minutes;
#       any other set of codes gets NO ready-made statement and is flagged for him;
#     - the note is laid out like his sample (letterhead, patient, location, provider, charge date, "Late entry", the stamp down the side),
#       is dated the day it is written - never an earlier day - and carries the signed stamp ONLY when a signing was recorded for it;
#     - a supporting item must fall in the note's own month; a month with none is said so on the note and flagged;
#     - nothing a caller passes in can break the page (every text is escaped).
# Never touches: AdvancedMD, RingCentral, Neon, Drive. Nothing is started as a program; the helper is loaded from its file and the network
#   is closed first. No patient data: every name, birth day and number here is invented and put together at run time.
# Run: python3 tools/selftest/test_ccm_notes.py   (exit 1 on any failure)
import os, sys, re, datetime, importlib.util
import socket as _socket
def _no_network(*a, **k): raise RuntimeError("the self-test must not use the network")
_socket.socket.connect = _no_network; _socket.socket.connect_ex = _no_network; _socket.create_connection = _no_network
sys.dont_write_bytecode = True
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PATH = os.path.join(ROOT, "scripts", "helpers", "ccm_notes.py")
FAILS = []; RAN = [0]
def check(name, cond, extra=""):
    RAN[0] += 1
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else "  -> " + str(extra)[:600]))
    if not cond: FAILS.append(name)
src = open(PATH, encoding="utf-8").read() if os.path.exists(PATH) else ""
names = {m.split()[0].split(".")[0] for k, r in re.findall(r"^[ \t]*(import|from)[ \t]+([^\n#;]+)", src, re.M) for m in (r.split(",") if k == "import" else [r]) if m.strip()}
check("the helper is there and loads the standard library only (nothing that talks to AdvancedMD, nothing that starts a program)", src != "" and names <= {"os", "sys", "re", "json", "html", "datetime", "collections"}, sorted(names))
if FAILS: print("\ntest_ccm_notes: %d checks, %d failed - the helper is not there" % (RAN[0], len(FAILS))); sys.exit(1)
spec = importlib.util.spec_from_file_location("ccm_notes_t", PATH); C = importlib.util.module_from_spec(spec); spec.loader.exec_module(C)

TODAY = datetime.date(2026, 11, 11)
def shown(n): return "ZZ" + "CCMTEST" + chr(65 + n) + ", " + "Invented" + chr(65 + n)      # put together at run time: the privacy gate does not rewrite it
def person(n): return {"chart": "pat%d" % (9500000 + n), "name": shown(n), "dob": (datetime.date(1938, 1, 1) + datetime.timedelta(days=61 * n)).isoformat(), "insurance": "Test Payer"}
def line(n, day, code, charge): return {"chart": person(n)["chart"], "dos": day, "code": code, "visit": "vst%d" % (700 + charge), "charge": "charge%d" % charge, "facility": "Invented Nursing Center", "provider": "William Effinger, DO"}
LINES = [line(1, "2026-10-31", "99487", 1), line(1, "2026-10-31", "99489", 2), line(1, "2026-09-30", "99487", 3),
         line(2, "2026-10-31", "99487", 4), line(3, "2026-10-31", "99489", 5), line(4, "2026-10-31", "99490", 6), line(2, "2026-10-15", "99309", 7)]
M = {(m["chart"], m["month"]): m for m in C.months(LINES)}
P1, P2, P3, P4 = (person(n)["chart"] for n in (1, 2, 3, 4))

# ---- 1. one record per patient per month, and the statement by the codes
check("1 charge lines are grouped per patient per calendar month; a line that is no CCM code (a visit) belongs to no record",
      sorted(M) == sorted([(P1, "2026-10"), (P1, "2026-09"), (P2, "2026-10"), (P3, "2026-10"), (P4, "2026-10")]) and [c["charge"] for c in M[(P1, "2026-10")]["charges"]] == ["charge1", "charge2"], sorted(M))
check("1 99487 alone: the statement says greater than 60 minutes, for that calendar month", M[(P2, "2026-10")]["minutes"] == 60 and M[(P2, "2026-10")]["statement"].startswith("Greater than 60 minutes") and "October 2026" in M[(P2, "2026-10")]["statement"] and not M[(P2, "2026-10")]["flag"], M[(P2, "2026-10")])
check("1 99487 with 99489: greater than 90 minutes", M[(P1, "2026-10")]["minutes"] == 90 and M[(P1, "2026-10")]["statement"].startswith("Greater than 90 minutes") and M[(P1, "2026-09")]["minutes"] == 60)
check("1 the statement is William's own wording (chart review, medication lists, faxes, labs, orders, referrals, phone conversations, treatment plans) and says nothing else",
      all(w in M[(P2, "2026-10")]["statement"] for w in ("chart review", "medication lists", "faxes", "labs", "orders", "referrals", "phone conversations with nurses", "treatment team", "family if needed", "developing treatment plans for this patient")))
check("1 any other set of codes gets NO ready-made statement and is flagged for him: 99489 without 99487, and a CCM code he gave no statement for",
      M[(P3, "2026-10")]["statement"] is None and "99489 without 99487" in M[(P3, "2026-10")]["flag"] and M[(P4, "2026-10")]["statement"] is None and "99490" in M[(P4, "2026-10")]["flag"], (M[(P3, "2026-10")]["flag"], M[(P4, "2026-10")]["flag"]))

# ---- 2. the note
PRACTICE = {"name": "Invented Senior Care", "address": ["1 Invented Way, Suite 9", "Testville, FL 32300"], "phone": "(555) " + "010-0001", "fax": "(555) 010-0002"}
EV = [{"kind": "fax_lab", "date": "2026-10-07", "source": "ringcentral:9001", "summary": "Lab result received and reviewed"},
      {"kind": "phone_call", "date": "2026-10-21", "source": "ringcentral:call:77", "summary": "Call with the facility nurse about medications"}]
draft = C.note_html(M[(P1, "2026-10")], person(1), PRACTICE, written=TODAY, today=TODAY, evidence=EV)
check("2 the note is laid out like the sample: the practice's letterhead, the patient, the location, the provider, the charge date and the codes",
      all(w in draft for w in ("Invented Senior Care", "1 Invented Way, Suite 9", "Fax: (555) 010-0002", person(1)["name"].replace("&", "&amp;"), "Invented Nursing Center", "William Effinger, DO", "10/31/2026", "99487", "99489")), draft[:300])
check("2 it is headed LATE ENTRY, dated the day it is written, names the month it is for, and carries the statement",
      "LATE ENTRY" in draft and "written 11/11/2026" in draft and "October 2026" in draft and "Greater than 90 minutes" in draft)
check("2 the month's supporting items are listed under the statement, each with its date, kind and source", all(w in draft for w in ("10/07/2026", "Lab result received and reviewed", "ringcentral:9001", "10/21/2026", "Call with the facility nurse about medications")))
check("2 a note nobody has signed says so and carries NO signed stamp", "DRAFT - NOT SIGNED" in draft and "Electronically Signed" not in draft)
signed = C.note_html(M[(P1, "2026-10")], person(1), PRACTICE, written=TODAY, today=TODAY, evidence=EV, signed={"by": "EFFINGER, WILLIAM", "at": "2026-11-11T21:05:00"})
check("2 the stamp down the side appears only when a signing was recorded for this note - who and when", "Electronically Signed and Reviewed by EFFINGER, WILLIAM 11/11/2026 21:05:00" in signed and "DRAFT - NOT SIGNED" not in signed)
def refused(**kw):
    try: C.note_html(M[(P1, "2026-10")], person(1), PRACTICE, **dict({"written": TODAY, "today": TODAY, "evidence": EV}, **kw)); return ""
    except ValueError as e: return str(e)
check("2 a note is never dated an earlier day than the day it is written (no backdating), and never signed before it was written",
      "dated the day it is written" in refused(written=datetime.date(2026, 10, 31)) and "signed before" in refused(signed={"by": "EFFINGER, WILLIAM", "at": "2026-11-10T09:00:00"}), (refused(written=datetime.date(2026, 10, 31)), refused(signed={"by": "X", "at": "2026-11-10T09:00:00"})))
check("2 a signing without a name or a time is refused", "who signed and when" in refused(signed={"by": "", "at": "2026-11-11T21:05:00"}) and "who signed and when" in refused(signed={"by": "EFFINGER, WILLIAM"}))
check("2 a supporting item from another month is refused (a month is supported by that month's own records), and so is a kind nobody listed",
      "outside October 2026" in refused(evidence=[dict(EV[0], date="2026-11-02")]) and "kind" in refused(evidence=[dict(EV[0], kind="something")]))
none = C.note_html(M[(P2, "2026-10")], person(2), PRACTICE, written=TODAY, today=TODAY, evidence=[])
check("2 a month with no supporting item says so on the note - the statement stands alone, and the record is flagged for William", "No supporting item is on file for this month" in none and C.needs_review(M[(P2, "2026-10")], []) and not C.needs_review(M[(P1, "2026-10")], EV))
try: C.note_html(M[(P3, "2026-10")], person(3), PRACTICE, written=TODAY, today=TODAY, evidence=[]); r3 = ""
except ValueError as e: r3 = str(e)
check("2 a month with no statement of its own gets no note from this helper: William writes that one himself", "no ready-made statement" in r3, r3)
evil = C.note_html(M[(P2, "2026-10")], dict(person(2), name="<script>x</script>, A&B"), PRACTICE, written=TODAY, today=TODAY, evidence=[dict(EV[0], summary="<b>bold</b>")])
check("2 whatever text is passed in is shown as text - it cannot break the page", "<script>x</script>" not in evil and "&lt;script&gt;" in evil and "<b>bold</b>" not in evil)
check("2 the page is a whole document that prints on letter paper: its own title, the side stamp set vertically", "<title>" in draft and "@page" in draft and "writing-mode" in draft)

# ---- 3. the words
DOC = open(os.path.join(ROOT, "docs", "CCM_DOCUMENTATION_HUB.md"), encoding="utf-8").read() if os.path.exists(os.path.join(ROOT, "docs", "CCM_DOCUMENTATION_HUB.md")) else ""
DOCN = DOC.replace("\n", " ")
check("3 the hub's document says what the code does: one record per patient per month, the two statements, never signed for him, never backdated, a month without support flagged, Neon the primary store",
      all(w in DOCN for w in ("one record per patient per calendar month", "greater than 60 minutes", "greater than 90 minutes", "99487", "99489", "never signs for him", "never dated an earlier day", "flagged", "Neon", "python3 tools/selftest/test_ccm_notes.py")),
      [w for w in ("one record per patient per calendar month", "greater than 60 minutes", "greater than 90 minutes", "never signs for him", "never dated an earlier day", "flagged", "Neon") if w not in DOCN])
check("3 every kind of supporting item the helper accepts is named in the document", all(("`%s`" % k) in DOC for k in C.KINDS), [k for k in C.KINDS if ("`%s`" % k) not in DOC])
SQL = open(os.path.join(ROOT, "tools", "db", "ccm_schema.sql"), encoding="utf-8").read() if os.path.exists(os.path.join(ROOT, "tools", "db", "ccm_schema.sql")) else ""
check("3 the Neon section is written down as its own schema - months, notes, supporting items, faxes - and a signed note cannot be changed",
      all(w in SQL for w in ("create schema if not exists ccm", "ccm.patient_month", "ccm.note", "ccm.evidence", "ccm.fax")) and "signed_at" in SQL and "ccm.note_signed_is_final" in SQL, [w for w in ("ccm.patient_month", "ccm.note", "ccm.evidence", "ccm.fax") if w not in SQL])
print("\ntest_ccm_notes: %d checks, %d failed%s" % (RAN[0], len(FAILS), "" if not FAILS else " - " + "; ".join(FAILS)[:1200]))
sys.exit(1 if FAILS else 0)
