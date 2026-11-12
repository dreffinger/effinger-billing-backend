#!/usr/bin/env python3
# PLAIN ENGLISH (merge driver for practices/ehpa/rules.md - 11/10/2026, second ops-and-text review of the place-of-service rule)
# Decides: how two versions of William's rulebook are merged when origin/main moved under a session (mirror.py push_via_proxy and
#   apply_bundle.py both register this driver for rules.md). rules.md is append-only text, so a merge keeps the lines both sides added -
#   git's own union merge (git merge-file --union), exactly as before. But some bullets are REWRITTEN in place when their rule is revised
#   (REPLACED below: the place-of-service rule, the clinician and building of a feed visit, the quality code 1123F with the option code
#   M0004, the initial nursing-facility visit). A plain union merge of a rewritten bullet with a branch that only appended a rule keeps the
#   OLD bullet beside the NEW one (the reviewer's test: 6,884 and 9,273 characters, both "PLACE OF SERVICE ..."). So after the union merge
#   ONE bullet of each such rule stays: a copy that still equals the common ancestor's bullet is the stale one and is dropped - the side that
#   rewrote the bullet wins; two copies with the same words are one. When BOTH sides rewrote the same bullet nothing is guessed: the
#   merge stops as a conflict (exit 1) and a person keeps the right one.
# Never touches: anything but the merge result git hands it.  Usage (git runs it): python3 rules_merge.py %O %A %B  (the result goes into %A)
import sys, subprocess
REPLACED = ("PLACE OF SERVICE IN THE NURSING BUILDINGS (Brynwood", "CLINICIAN AND BUILDING OF A FEED VISIT", "QUALITY CODE 1123F, ADVANCE CARE PLAN",
            "INITIAL NURSING-FACILITY VISIT")
def bullet_of(line):
    """The rewritten rule a rulebook line is the bullet of (its heading stands in the line's first 400 characters), or None."""
    if not line.startswith("- ("): return None
    return next((k for k in REPLACED if k in line[:400]), None)
def one_bullet(merged, base):
    """-> (the merged text with ONE bullet per rewritten rule, the rules still found twice). For a rule found on more than one line: a line equal
    to the common ancestor's bullet of that rule is dropped, and lines with the same words are kept once; two different rewrites are left as
    they are and reported (both sides rewrote that rule - a conflict for a person)."""
    lines = merged.split("\n"); old = {}
    for ln in base.split("\n"):
        k = bullet_of(ln)
        if k: old.setdefault(k, set()).add(ln)
    drop = set(); twice = []
    for k in REPLACED:
        idx = [i for i, ln in enumerate(lines) if bullet_of(ln) == k]
        if len(idx) < 2: continue
        live = [i for i in idx if lines[i] not in old.get(k, ())] or idx[-1:]     # every copy the ancestor had: the newest of them stays
        drop.update(i for i in idx if i not in live)
        seen = set()
        for i in live:
            if lines[i] in seen: drop.add(i)
            seen.add(lines[i])
        if len(seen) > 1: twice.append(k)
    return "\n".join(ln for i, ln in enumerate(lines) if i not in drop), twice
def main():
    o, a, b = sys.argv[1:4]
    r = subprocess.run(["git", "merge-file", "-p", "--union", a, o, b], capture_output=True)
    if r.returncode < 0: sys.exit(2)
    text, twice = one_bullet(r.stdout.decode("utf-8", "surrogateescape"), open(o, encoding="utf-8", errors="surrogateescape").read())
    open(a, "w", encoding="utf-8", errors="surrogateescape").write(text)
    if twice:
        print("rules.md: both sides rewrote the bullet %s - keep the right one by hand" % "; ".join(twice), file=sys.stderr); sys.exit(1)
if __name__ == "__main__": main()
