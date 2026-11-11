#!/usr/bin/env python3
# PLAIN ENGLISH (CCM documentation hub - William 11/11/2026: "do all the notes and give me buttons to sign off on all of them"; his sample
#   note shows the patient's name and birth date at the top).
# Decides: nothing. For the charts that carry a chronic-care-management charge, it reads ONLY the patient's name, birth date and sex as
#   AdvancedMD shows them, with getdemographic - the read boards/board_identity.py and claimocity_import.py already make (captured in
#   docs/captured_calls.md) - so each late-entry note can say who the patient is. Everything else about the charges is already in the
#   practice's Neon database (amd.charges, the AdvancedMD history pulled 11/10/2026); the insurance on a note comes from there too.
# What it never does:
#   - write to AdvancedMD: getdemographic is the only action it sends;
#   - keep anything else from the answer: no address, phone, e-mail, SSN, member id, responsible party, plans or notes;
#   - log in more than once: one amd.login_cached() before the reads (optimization/amd_history/README.md); a session that cannot be
#     opened stops the run (exit 3) - nobody tries again from here;
#   - read while a scheduled billing routine uses AdvancedMD: the same quiet windows as the history pull (amd_pull2.py) - 01:10-02:40,
#     05:30-06:40, 07:10-08:15, 13:10-14:15, 19:10-20:15 UTC; it stops (exit 5) and says when to run it again;
#   - put a patient's data in the repository: it refuses a workspace inside the checkout.
# Patient data: lives only in the workspace (BILLING_WORKSPACE, default /home/claude/unbilled): ccm/ccm_patients.jsonl, one line per chart.
# Input: ccm/ccm_charts.json = {"charts": ["pat123", ...]} (written by scripts/helpers/ccm_build.py charts).
# Usage:
#   python3 scripts/helpers/ccm_patients.py                       the plan only: charts listed, already read, left - no login, no call
#   python3 scripts/helpers/ccm_patients.py --live [--limit N]    the reads; resumable (a chart read once is not read again; a failed one
#                                                                 is tried again next run); a file named STOP in ccm/ ends it after the chart in hand
# Exit: 0 done (or the plan), 2 no or bad input / refused workspace, 3 AdvancedMD session not usable, 4 five failed reads in a row, 5 quiet window or STOP.
# Self-test: python3 tools/selftest/test_ccm_patients.py
import os, sys, re, json, time, html, datetime
QUIET = ((70, 160), (330, 400), (430, 495), (790, 855), (1150, 1215))      # minutes after 00:00 UTC (amd_pull2.py's windows)
PACE = 0.5                 # seconds between two reads
MAX_FAILS_IN_A_ROW = 5
def _now():
    s = os.environ.get("CCM_NOW")      # the self-test sets the clock
    return datetime.datetime.fromisoformat(s.replace("Z", "+00:00")) if s else datetime.datetime.now(datetime.timezone.utc)
def quiet_window(t):
    """(start, end) in minutes when t falls inside a scheduled routine's window, else None"""
    t = t.astimezone(datetime.timezone.utc); m = t.hour * 60 + t.minute
    return next(((a, b) for a, b in QUIET if a <= m < b), None)
def hhmm(m): return "%02d:%02d" % (m // 60, m % 60)
def iso_day(s):
    """MM/DD/YYYY (AdvancedMD) -> YYYY-MM-DD; the 1900-01-01 placeholder and anything unreadable -> \"\""""
    try: d = datetime.datetime.strptime((s or "").strip(), "%m/%d/%Y").date()
    except ValueError: return ""
    return "" if d.year <= 1900 else d.isoformat()
def parse(xml):
    """name, birth date and sex from a getdemographic answer - nothing else"""
    m = re.search(r"<patient\s[^>]*>", xml or "")
    if not m: raise RuntimeError("no <patient> in the answer (%s)" % re.sub(r"\s+", " ", (xml or "")[:120]))
    a = dict(re.findall(r'(\w+)="([^"]*)"', m.group(0)))
    return {"name": html.unescape(a.get("name", "")).strip(), "dob": iso_day(a.get("dob", "")), "sex": a.get("sex", "").strip()}
def main(argv=None, sleep=time.sleep):
    a = list(sys.argv[1:] if argv is None else argv)
    ws = os.path.abspath(os.environ.get("BILLING_WORKSPACE") or "/home/claude/unbilled")
    repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if ws == repo or ws.startswith(repo + os.sep):
        print("ccm_patients: the workspace %s is inside the repository - patient data never goes there; set BILLING_WORKSPACE" % ws); return 2
    d = os.path.join(ws, "ccm"); src = os.path.join(d, "ccm_charts.json"); out = os.path.join(d, "ccm_patients.jsonl")
    try:
        charts = list(dict.fromkeys(c for c in json.load(open(src, encoding="utf-8"))["charts"] if re.fullmatch(r"pat\d+", str(c))))
    except Exception as e:
        print("ccm_patients: no chart list at %s (%s) - write it with: python3 scripts/helpers/ccm_build.py charts" % (src, type(e).__name__)); return 2
    done = set()
    if os.path.exists(out):
        for line in open(out, encoding="utf-8"):
            try: j = json.loads(line)
            except ValueError: continue
            if j.get("chart") and not j.get("error"): done.add(j["chart"])
    left = [c for c in charts if c not in done]
    limit = int(a[a.index("--limit") + 1]) if "--limit" in a and a.index("--limit") + 1 < len(a) else 0
    q = quiet_window(_now())
    print("ccm_patients: %d charts listed, %d already read, %d left%s" % (len(charts), len(charts) - len(left), len(left),
          (" - a scheduled billing routine uses AdvancedMD until %s UTC" % hhmm(q[1])) if q else ""))
    if "--live" not in a: print("ccm_patients: plan only - nothing was read (add --live to read)"); return 0
    if not left: return 0
    if q: print("ccm_patients: not now - run it again after %s UTC" % hhmm(q[1])); return 5
    import amd      # only here, for a live run: the stand-in self-test puts its own amd in place
    try: amd.login_cached()
    except Exception as e:
        print("ccm_patients: the AdvancedMD session could not be opened (%s) - stopping, NOT logging in again" % str(e)[:160]); return 3
    os.makedirs(d, exist_ok=True)
    n = fails = 0
    with open(out, "a", encoding="utf-8") as f:
        for c in left[:limit or None]:
            if os.path.exists(os.path.join(d, "STOP")): print("ccm_patients: STOP file - stopped after %d charts" % n); return 5
            q = quiet_window(_now())
            if q: print("ccm_patients: a scheduled billing routine starts now - stopped after %d charts; run again after %s UTC" % (n, hhmm(q[1]))); return 5
            at = _now().strftime("%Y-%m-%dT%H:%M:%SZ")
            try:
                row = dict({"chart": c, "read_at": at}, **parse(amd.post(amd.msg("getdemographic", "demographics", {"patientid": c, "nocookie": "1"}), timeout=60)))
                fails = 0
            except Exception as e:
                row = {"chart": c, "error": "%s: %s" % (type(e).__name__, str(e)[:160]), "read_at": at}; fails += 1
            f.write(json.dumps(row, sort_keys=True) + "\n"); f.flush(); n += 1
            if fails >= MAX_FAILS_IN_A_ROW: print("ccm_patients: %d reads in a row failed - stopped after %d charts (the last: %s)" % (fails, n, row["error"])); return 4
            sleep(PACE)
    print("ccm_patients: %d charts read this run, %d left" % (n, len(left) - n))
    return 0
if __name__ == "__main__":
    sys.exit(main())
