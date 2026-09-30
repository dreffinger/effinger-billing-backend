# PLAIN ENGLISH (Approval request - William 9/30/2026: "when this happens make a solution to send to me immediately for mandatory approval")
# Decides: nothing about billing. Whenever the run's auto-mode permission classifier REFUSES an AdvancedMD write (a named helper run
#   with --live, or installing a helper William uploaded), the run records the refusal here and this script turns every refusal into
#   ONE approval package: what the write would do (from the helper's --dry register), the exact command, the evidence, the UI steps that
#   do the same thing by hand, and the three ways William can approve. The run then sends the package IMMEDIATELY - Gmail to
#   dreffinger@gmail.com (subject 'APPROVAL NEEDED - backend billing run <stamp>') plus a phone push - and keeps
#   registers/approvals_pending.json so the next run re-checks for his answer (email reply 'APPROVED <id>' or a Working Denials board
#   command 'approve <id>') and re-attempts the helper ONCE, citing the approval.
# Rules it uses: a refusal is never retried, split or re-encoded inside the same run (v9 rule 3); the package carries visit ids and
#   chart ids (names only in the email to William himself); nothing here writes to AMD.
#   python3 approval_request.py add --id A1 --cmd "python3 insp_0930_1310.py --live" --reason "Real-World Transactions" \
#        --what "..." --evidence registers/insp_2026-09-30T1310Z_dry.json --ui "..."      # record one refusal
#   python3 approval_request.py build [--stamp <run stamp>]                                 # -> outbox/approval_request_<stamp>.md (the email body)
#   python3 approval_request.py pending                                                     # list approvals still waiting
#   python3 approval_request.py approved <id> [--note "..."]                                # record William's answer (next run re-attempts once)
import json, os, sys, datetime, argparse
WS = os.path.dirname(os.path.abspath(__file__))
REG = os.path.join(WS, "registers", "approvals_pending.json"); os.makedirs(os.path.join(WS, "outbox"), exist_ok=True)
def now(): return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
def load():
    return json.load(open(REG)) if os.path.exists(REG) else {"items": []}
def save(d): json.dump(d, open(REG, "w"), indent=1)
ap = argparse.ArgumentParser(); ap.add_argument("mode"); ap.add_argument("rest", nargs="?")
ap.add_argument("--id"); ap.add_argument("--cmd"); ap.add_argument("--reason"); ap.add_argument("--what"); ap.add_argument("--evidence")
ap.add_argument("--ui"); ap.add_argument("--stamp"); ap.add_argument("--note"); ap.add_argument("--dollars", default="")
a = ap.parse_args()
d = load()
if a.mode == "add":
    stamp = a.stamp or datetime.datetime.utcnow().strftime("%Y-%m-%dT%H%MZ")
    aid = a.id or "A-%s-%d" % (stamp, len([i for i in d["items"] if i["stamp"] == stamp]) + 1)
    if not aid.startswith("A-"): aid = "A-%s-%s" % (stamp, aid)
    ev = ""
    if a.evidence and os.path.exists(os.path.join(WS, a.evidence)):
        ev = open(os.path.join(WS, a.evidence)).read()[:6000]
    d["items"].append({"id": aid, "stamp": stamp, "at": now(), "cmd": a.cmd, "reason": a.reason, "what": a.what, "dollars": a.dollars,
                       "evidence_file": a.evidence, "evidence": ev, "ui": a.ui, "status": "waiting", "answer": None})
    save(d); print("recorded", aid)
elif a.mode == "build":
    stamp = a.stamp or (d["items"][-1]["stamp"] if d["items"] else "")
    items = [i for i in d["items"] if i["stamp"] == stamp and i["status"] == "waiting"]
    if not items: print("nothing waiting for", stamp); sys.exit(0)
    L = ["APPROVAL NEEDED - backend billing run %s (ehpa cloud)" % stamp, "",
         "The run's permission classifier refused %d AdvancedMD write(s). Each was planned, dry-run verified and NOT retried. Nothing was changed in AMD for these items." % len(items),
         "", "HOW TO APPROVE (pick one):",
         "  1. Reply to this email with the line:  APPROVED <id>   (one per line; add 'NO <id>' to decline). The next run reads the reply and re-attempts that helper once.",
         "  2. Or paste the same text as a command on the Working Denials board (command = 'approve <id>').",
         "  3. Or do it yourself now: the exact command and the AMD UI steps are under each item.",
         "NOTE: an approval lets the next run RE-ATTEMPT the helper; the refusal comes from the routine environment's auto-mode classifier, which does not read approvals.",
         "      The durable fix is on the routine itself (web UI > Edit routine > permission mode not classified for unattended runs, or the allow rules in .claude/settings.json on main - docs/ROUTINE_PERMISSIONS.md).",
         ""]
    for i in items:
        L += ["=" * 78, "ID: %s" % i["id"], "WHAT: %s" % i["what"], "DOLLARS: %s" % (i["dollars"] or "n/a"),
              "COMMAND (cd /home/claude/unbilled): %s" % i["cmd"], "REFUSED AS: %s" % i["reason"],
              "UI STEPS (same result by hand): %s" % (i["ui"] or "-"), "EVIDENCE: %s" % (i["evidence_file"] or "-")]
        if i["evidence"]:
            L += ["--- dry-run register (first lines) ---", i["evidence"][:2500], "---"]
        L.append("")
    body = "\n".join(L)
    path = os.path.join(WS, "outbox", "approval_request_%s.md" % stamp)
    open(path, "w").write(body); print(path); print(body[:400])
elif a.mode == "pending":
    for i in d["items"]:
        if i["status"] == "waiting": print(i["id"], "|", i["cmd"], "|", i["what"][:90])
elif a.mode == "approved":
    for i in d["items"]:
        if i["id"] == a.rest: i["status"] = "approved"; i["answer"] = {"at": now(), "note": a.note or ""}; print("approved", i["id"])
    save(d)
elif a.mode == "done":
    for i in d["items"]:
        if i["id"] == a.rest: i["status"] = "done"; i["answer"] = {"at": now(), "note": a.note or ""}; print("done", i["id"])
    save(d)
