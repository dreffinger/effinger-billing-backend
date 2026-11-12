#!/usr/bin/env python3
# PLAIN ENGLISH (What the billing engine's recent ERA steps left - READ ONLY)
# Decides: nothing, writes nothing, calls nothing outside this repository. It reads the run reports in reports/button/ -
#   <stamp>.json (the GitHub Actions engine every two hours and at 05:35 UTC, a Billing Button press, the nightly cascade's own era step)
#   and <stamp>-<tag>.json (a Claude routine's engine pass) - and the engine's schedule in .github/workflows/billing-button.yml, and
#   answers two questions for the nightly cascade (nightly/live/cascade.txt STEP 3; William 11/12/2026: read the engine's ERA step
#   instead of pressing the Post button a second time at the same minute):
#   1. Is the engine posting? Only a LIVE report whose era step read the ERA Center (it carries 'unposted before') and did not fail
#      counts; dry runs and failed or crashed era steps are passed over and named. The first line printed is the VERDICT:
#        exit 0 - such a report is at most --max-age hours old: post nothing here;
#        exit 4 - nothing that fresh, but an engine slot started in the last --due-minutes minutes, its report has not landed, and the
#                 schedule committed a LIVE scheduled report in the 3 hours before the slot (it is running): an engine pass is under way -
#                 re-check later (dry scheduled runs and page-button dispatches are no evidence that the schedule posts);
#        exit 3 - only older usable reports and no pass under way: the engine is down, dry or failing - the routine runs the step itself;
#        exit 2 - no usable report at all and no pass under way - the same.
#      An exit 0 that rests on a report older than an engine pass now under way also prints a NOTE, so the routine works the lines after
#      that pass lands.
#   2. What is waiting? The newest usable report's ERA waiting lines (every check still carrying money, and why), then the one-time
#      lines (CO-45 relink faults and review counts, fallback orphans, write-off reversal notes) of the other live reports of the last
#      --since hours - also of a live pass whose era step failed - each printed once with the newest report that carries it and how many
#      earlier passes repeated it. A report whose waiting list the privacy gate withheld is named, so the routine rebuilds the held list
#      itself (python3 era_clear.py --dry).
# Output: chart, visit and check ids and dollars only - the reports on main are PHI-light already. GitHub engine reports carry a
#   github.com run_url.
# Usage: python3 tools/button/era_waiting.py [--max-age 3] [--since 26] [--due-minutes 25] [--reports reports/button] [--workflow <yml>]
import datetime, json, os, re, sys

a = sys.argv[1:]


def opt(name, default):
    return float(a[a.index(name) + 1]) if name in a else default


MAX_AGE = opt("--max-age", 3.0)
SINCE = opt("--since", 26.0)
DUE_MIN = opt("--due-minutes", 25.0)
HERE = os.path.dirname(os.path.abspath(__file__))
DIR = a[a.index("--reports") + 1] if "--reports" in a else os.path.join(HERE, "..", "..", "reports", "button")
WORKFLOW = a[a.index("--workflow") + 1] if "--workflow" in a else os.path.join(HERE, "..", "..", ".github", "workflows", "billing-button.yml")
STAMP_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{4}Z)(-[A-Za-z0-9]+)?\.json$")
STAMP_IN_TEXT = re.compile(r"\d{4}-\d{2}-\d{2}T\d{4}Z(?:-[A-Za-z0-9]+)?")
# the waiting lines run_all.py's era step writes (tools/button/run_all.py, Run.era) - nothing else is an ERA line
ERA_LINE = re.compile(r"^(ERA check |ERA CO-45 pass|CO-45 relink check |ERA fallback: |write-off reversal|era_clear wrote |\d+ write-off reversal)")
ONE_TIME = re.compile(r"^(ERA CO-45 pass|CO-45 relink check |ERA fallback: |write-off reversal|era_clear wrote |\d+ write-off reversal)")
WITHHELD = re.compile(r"^[1-9]\d* item\(s\) - see the run log$")
REST_FILES, REST_DAYS = 60, 7   # how far back the verdict looks when nothing usable is inside --since


def stamp_time(stamp):
    try:
        return datetime.datetime.strptime(stamp, "%Y-%m-%dT%H%MZ").replace(tzinfo=datetime.timezone.utc)
    except ValueError:
        return None


def load(path):
    try:
        rep = json.load(open(path, encoding="utf-8"))
    except Exception:
        return None
    return rep if isinstance(rep, dict) else None


def era_of(rep):
    steps = rep.get("steps")
    return next((s for s in steps if isinstance(s, dict) and s.get("name") == "era"), None) if isinstance(steps, list) else None


def waiting_of(rep):
    w = rep.get("waiting")
    return [x for x in w if isinstance(x, str)] if isinstance(w, list) else []


def flat(x, n=120):
    s = " ".join(str(x).split())
    return s if len(s) <= n else s[:n] + "..."


def usable(rep):
    """(era step, None) for a live run whose era step read the ERA Center and did not fail; (None, reason) otherwise."""
    era = era_of(rep)
    if not era:
        return None, "no era step"
    if era.get("status") in ("skipped", "failed"):
        # the failure itself, not the first warning: run_all's fail() writes 'era: <reason>' to the report's top-level errors
        top = [e for e in (rep.get("errors") if isinstance(rep.get("errors"), list) else []) if isinstance(e, str) and e.startswith("era: ")]
        errs = era.get("errors") if isinstance(era.get("errors"), list) else []
        why = top[-1][5:] if top else (errs[-1] if errs else "")
        return None, "era step %s%s" % (era.get("status"), (": " + flat(why, 100)) if why else "")
    if rep.get("mode") != "live":
        return None, "%s run - nothing was posted" % (rep.get("mode") or "unknown-mode")
    if not isinstance(era.get("dollars"), dict) or "unposted before" not in era["dollars"]:
        return None, "the era step never read the ERA Center"
    return era, None


def withheld(rep):
    return any(WITHHELD.match(w) for w in waiting_of(rep))


def ended(rep):
    era = era_of(rep) if rep else None
    return str((era or {}).get("ended") or "")


def money(x):
    try:
        return float(x or 0)
    except (TypeError, ValueError):
        return 0.0


def is_github(rep):
    return bool(rep) and "github.com" in str(rep.get("run_url") or "")


def is_scheduled(rep):
    """A report of the engine's own schedule (the workflow writes note 'scheduled-<profile>'), not a page-button dispatch or a routine pass."""
    return is_github(rep) and str(rep.get("note") or "").startswith("scheduled")


def field_values(f, lo, hi):
    if f == "*":
        return list(range(lo, hi + 1))
    if f.startswith("*/"):
        return list(range(lo, hi + 1, int(f[2:])))
    out = []
    for part in f.split(","):
        if "-" in part:
            x, y = part.split("-")
            out += list(range(int(x), int(y) + 1))
        else:
            out.append(int(part))
    return [v for v in out if lo <= v <= hi]


def engine_slots():
    """[(minute, hour)] UTC of the engine workflow's daily cron lines; [] when the file cannot be read or holds no daily schedule."""
    try:
        text = open(WORKFLOW, encoding="utf-8").read()
    except OSError:
        return []
    slots = []
    for m in re.finditer(r"-\s*cron:\s*[\"']([^\"']+)[\"']", text):
        parts = m.group(1).split()
        if len(parts) != 5 or parts[2:] != ["*", "*", "*"]:
            continue
        try:
            slots += [(mi, h) for mi in field_values(parts[0], 0, 59) for h in field_values(parts[1], 0, 23)]
        except ValueError:
            continue
    return slots


def last_slot(now, slots):
    best = None
    for back in (0, 1):
        d = (now - datetime.timedelta(days=back)).date()
        for mi, h in slots:
            t = datetime.datetime(d.year, d.month, d.day, h, mi, tzinfo=datetime.timezone.utc)
            if t <= now and (best is None or t > best):
                best = t
    return best


def main():
    now = datetime.datetime.now(datetime.timezone.utc)
    names = sorted((m.group(1), f) for f in os.listdir(DIR) for m in [STAMP_RE.match(f)] if m) if os.path.isdir(DIR) else []
    window, rest, passed = [], [], []
    for stamp, name in names:
        t = stamp_time(stamp)
        if t is None:
            passed.append((name, "unreadable stamp"))
            continue
        if t > now + datetime.timedelta(minutes=10):
            passed.append((name, "stamp in the future"))
            continue
        age = (now - t).total_seconds() / 3600.0
        (window if age <= SINCE else rest).append((stamp, name, os.path.join(DIR, name), age, t))
    loaded = [(stamp, name, load(path), age, t) for stamp, name, path, age, t in window]
    loaded.sort(key=lambda e: (e[0], ended(e[2])), reverse=True)   # newest first; within one minute the era step that ended later first
    newest, others = None, []
    for stamp, name, rep, age, t in loaded:
        if rep is None:
            if newest is None:
                passed.append((name, "unreadable"))
            continue
        era, why = usable(rep)
        if era is None:
            if why == "no era step":
                continue
            if newest is None:
                passed.append((name, why))
            if rep.get("mode") == "live":
                others.append((name, rep, why))   # a live pass whose era step failed can still carry fault lines from before the failure
            continue
        if newest is None:
            newest = (stamp, name, rep, era, age)
        else:
            others.append((name, rep, None))
    if newest is None:   # nothing usable in the window: the newest usable older report (bounded), for the verdict
        for stamp, name, path, age, t in list(reversed(rest))[:REST_FILES]:
            if age > SINCE + 24 * REST_DAYS:
                break
            rep = load(path)
            era, why = usable(rep) if rep else (None, "unreadable")
            if era is not None:
                newest = (stamp, name, rep, era, age)
                break
    fresh = newest is not None and newest[4] <= MAX_AGE
    due = None
    slots = engine_slots()
    slot = last_slot(now, slots) if slots else None
    if slot is not None and (now - slot).total_seconds() / 60.0 <= DUE_MIN:
        sched = [(t, rep) for stamp, name, rep, age, t in loaded if is_scheduled(rep)]
        landed = any(t >= slot - datetime.timedelta(minutes=2) for t, rep in sched)
        running = any(slot - datetime.timedelta(hours=3) <= t < slot - datetime.timedelta(minutes=2) and rep.get("mode") == "live" for t, rep in sched)
        if not landed and running:
            due = slot
    if fresh:
        stamp, name, rep, era, age = newest
        print("VERDICT exit 0: the newest usable ERA step is report %s (%s), %.1f h old - post nothing here (nightly/live/cascade.txt STEP 3)" % (
            name, "GitHub engine" if is_github(rep) else "routine pass or press", age))
        if due is not None:
            print("NOTE: the engine pass of the %s UTC slot started %d min ago and has not landed - it will replace this report; work the lines after STEP 5 from a fresh pull and helper run (nightly/live/cascade.txt STEP 3)" % (
                due.strftime("%H:%M"), int((now - due).total_seconds() // 60)))
        code = 0
    elif due is not None:
        print("VERDICT exit 4: the engine pass of the %s UTC slot started %d min ago and has not landed (allow until about %s UTC) - post nothing now and re-check as nightly/live/cascade.txt STEP 3 says" % (
            due.strftime("%H:%M"), int((now - due).total_seconds() // 60), (due + datetime.timedelta(minutes=DUE_MIN)).strftime("%H:%M")))
        code = 4
    elif newest is not None:
        print("VERDICT exit 3: the newest usable ERA step is report %s, %.1f h old - older than %.1f h and no engine pass is under way: after one more pull and re-check, run the era step yourself (nightly/live/cascade.txt STEP 3)" % (
            newest[1], newest[4], MAX_AGE))
        code = 3
    else:
        print("VERDICT exit 2: no live report with a usable era step in %s and no engine pass is under way: after one more pull and re-check, run the era step yourself (nightly/live/cascade.txt STEP 3)" % DIR)
        code = 2
    for nm, why in passed[:6]:
        print("passed over: %s (%s)" % (nm, why))
    if len(passed) > 6:
        print("passed over: ... +%d more" % (len(passed) - 6))
    lines = []
    if newest is not None:
        stamp, name, rep, era, age = newest
        d = era.get("dollars") or {}
        c = era.get("counts") if isinstance(era.get("counts"), dict) else {}
        print("newest usable ERA step: report %s (%s), %.1f h old" % (name, "GitHub engine" if is_github(rep) else "routine pass or press", age))
        print("  note: %s" % flat(rep.get("note") or "", 160))
        print("  status %s: %s" % (era.get("status"), era.get("summary") or ""))
        print("  unposted before $%.2f -> after $%.2f; posted this run $%.2f%s%s" % (
            money(d.get("unposted before")), money(d.get("unposted after")), money(d.get("posted this run")),
            "; fallback posted $%.2f" % money(d["fallback posted"]) if d.get("fallback posted") else "",
            "; posted after write-off reversals $%.2f" % money(d["posted after write-off reversal"]) if d.get("posted after write-off reversal") else ""))
        keep = {k: v for k, v in c.items() if not isinstance(v, (dict, list))}
        if keep:
            print("  counts: " + "; ".join("%s %s" % (k, v) for k, v in keep.items()))
        for e in era.get("errors") if isinstance(era.get("errors"), list) else []:
            print("  WARNING: %s" % flat(e, 400))
        if withheld(rep):
            print("  WITHHELD: the privacy gate withheld this report's waiting list - rebuild the held list here with `python3 era_clear.py --dry`")
        lines = [w for w in waiting_of(rep) if ERA_LINE.match(w)]
        print("  ERA waiting lines: %d" % len(lines))
        for w in lines:
            print("   - %s" % w)
    seen = set(STAMP_IN_TEXT.sub("<stamp>", w) for w in lines)
    groups, order = {}, []
    for nm, rp, why in others:   # newest first
        if withheld(rp):
            k = "WITHHELD " + nm
            groups[k] = {"line": "WITHHELD: the privacy gate withheld this report's waiting list - its one-time lines are only in its run log", "newest": nm, "oldest": nm, "n": 1, "why": why}
            order.append(k)
        for w in waiting_of(rp):
            if not ONE_TIME.match(w):
                continue
            k = STAMP_IN_TEXT.sub("<stamp>", w)
            if k in seen:
                continue
            g = groups.get(k)
            if g is None:
                groups[k] = {"line": w, "newest": nm, "oldest": nm, "n": 1, "why": why}
                order.append(k)
            else:
                g["oldest"] = nm
                g["n"] += 1
    print("one-time ERA lines of the other live reports of the last %.0f h: %d" % (SINCE, len(order)))
    for k in order:
        g = groups[k]
        print("   - [%s%s] %s%s" % (g["newest"], ", " + g["why"] if g["why"] else "", g["line"],
                                   " (also in %d earlier pass(es), oldest %s)" % (g["n"] - 1, g["oldest"]) if g["n"] > 1 else ""))
    return code


if __name__ == "__main__":
    sys.exit(main())
