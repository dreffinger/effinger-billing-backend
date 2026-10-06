# PLAIN ENGLISH (Approval submit - William 10/6/2026: "save that in a code to automatically do and back it up to the triple mirror
#   so as to never slow down the billing")
# Decides: nothing about billing. When ANY session (chat or routine) has an AdvancedMD write REFUSED by the permission classifier,
#   this ONE command turns the refusal into a complete Mandatory Approvals submission: the items go into the pending register in the
#   workspace AND in the repo (so the hourly sync finds them on main), the page cards are prepared for the Mandatory Approvals artifact,
#   the email body / subject / push text are written to the outbox, and the repo register is committed and pushed (--push-main).
#   The session then makes three MCP calls (printed as a checklist) so William gets the package NOW, not at the next hourly sync.
# Rules it uses: a refusal is never retried here; one item per chart/section so each can be approved or declined alone; ids are
#   A-<stamp>-<letter>; an id already in a register is skipped (idempotent, safe to re-run); the privacy gate runs BEFORE anything is
#   written (no SSNs, MBIs, member/subscriber/policy numbers on the page, in the email or the push - docs/APPROVALS_LOOP.md); the
#   push to main is fast-forward only and a refusal is printed, never forced. Pure standard library.
# Never touches: AdvancedMD (no reads, no writes), the page database, Gmail or the phone - it only writes the files those calls use.
# Usage:
#   python3 approval_submit.py --stamp 2026-10-06T0137Z --items items.json [--repo <repo root>] [--workspace /home/claude/unbilled]
#          [--run-kind "chat session"] [--trailer "Co-Authored-By: ..."] [--push-main] [--dry]
#   items.json = [{"letter":"A", "command":"cd /home/claude/unbilled && python3 x.py --live --only A", "reason":"<classifier text>",
#                  "what":"...", "dollars":"$21.80", "ui":"...", "evidence":"...", "evidence_file":"<optional path>"}, ...]
import json, os, re, sys, datetime, argparse, subprocess

PAGE = "https://claude.ai/artifact/HuYd2bSm2NxkFgYRqra7wR"
TO = "dreffinger@gmail.com"
SSN = re.compile(r"\d{3}-\d{2}-\d{4}")
MBI = re.compile(r"^[1-9][AC-HJKMNP-RT-Y][AC-HJKMNP-RT-Y0-9]\d[AC-HJKMNP-RT-Y][AC-HJKMNP-RT-Y0-9]\d[AC-HJKMNP-RT-Y]{2}\d{2}$")
IDWORD = re.compile(r"\b(member\s*(?:id|number|no\.?|#)|subscriber(?:\s+(?:id|number))?|policy(?:\s+(?:id|no\.?|number))?)\W{0,12}\d{3,}", re.I)

def now(): return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def privacy_hit(text):
    if SSN.search(text): return "SSN pattern"
    m = IDWORD.search(text)
    if m: return "member/subscriber/policy number '%s'" % m.group(0)
    for tok in re.findall(r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?", text):   # dashed display form too
        if MBI.match(tok.replace("-", "")): return "MBI token %s" % tok
    return None

def build_items(raw, stamp, ws):
    out = []
    for r in raw:
        ef, ev = r.get("evidence_file"), r.get("evidence", "") or ""
        if ef:
            p = ef if os.path.exists(ef) else os.path.join(ws, ef)
            if os.path.exists(p): ev = open(p).read()[:6000]
        out.append({"id": "A-%s-%s" % (stamp, r["letter"]), "stamp": stamp, "at": now(), "cmd": r["command"], "reason": r["reason"],
                    "what": r["what"], "dollars": str(r.get("dollars", "")), "evidence_file": ef, "evidence": ev,
                    "ui": r.get("ui", ""), "status": "waiting", "answer": None})
    return out

def register(path, items, dry):
    d = json.load(open(path)) if os.path.exists(path) else {"items": []}
    have = {i["id"]: i for i in d["items"]}
    new = [i for i in items if i["id"] not in have]
    if new and not dry:
        os.makedirs(os.path.dirname(path), exist_ok=True); d["items"] += new; json.dump(d, open(path, "w"), indent=1)
    print("%sregister %s: +%d new, %d already present" % ("DRY " if dry else "", path, len(new), len(items) - len(new)))
    return [have.get(i["id"], i) for i in items]            # stored copy wins: keeps 'at' and any answer already given

def cards(items, kind, stamp):
    writes = [{"op": "set", "collection": "approvals", "doc_id": i["id"],
               "data": {"at": i["at"], "run": "%s %s" % (kind, stamp), "command": i["cmd"], "reason": i["reason"], "what": i["what"],
                        "dollars": i["dollars"], "evidence": i["evidence"], "ui": i["ui"], "status": "waiting",
                        "answeredAt": None, "answeredBy": None, "note": ""}} for i in items]
    return {"url": PAGE, "collection": "approvals", "writes": writes}

def email(items, stamp):
    n = len(items)
    subj = "APPROVAL NEEDED - backend billing run %s (%d AdvancedMD writes refused)" % (stamp, n)
    L = [subj, "", "Approve or decline each card on the Mandatory Approvals page: " + PAGE]
    L += ["  %s  ->  %s#%s" % (i["id"], PAGE, i["id"]) for i in items]
    L += ["", "The permission classifier refused %d AdvancedMD write(s). Each was planned, dry-run verified and NOT retried. "
          "Nothing was changed in AMD for these items." % n, "", "HOW TO APPROVE (pick one):",
          "  1. Tap Approve (or Decline) on the item's card on the Mandatory Approvals page - the cascade session applies approved cards on your 'go'.",
          "  2. Or reply to this email with the line:  APPROVED <id>   (one per line; add 'NO <id>' to decline). The next run reads the reply and re-attempts that helper once.",
          "  3. Or do it yourself now: the exact command and the AMD UI steps are under each item.",
          "NOTE: an approval lets the next run RE-ATTEMPT the helper; the refusal comes from the auto-mode permission classifier, which does not read approvals.",
          "      The durable fix is on the routine itself (web UI > Edit routine > permission mode not classified for unattended runs, "
          "or the allow rules in .claude/settings.json on main - docs/ROUTINE_PERMISSIONS.md).", ""]
    for i in items:
        L += ["=" * 78, "ID: %s   (card: %s#%s)" % (i["id"], PAGE, i["id"]), "WHAT: %s" % i["what"], "DOLLARS: %s" % (i["dollars"] or "n/a"),
              "COMMAND: %s" % i["cmd"], "REFUSED AS: %s" % i["reason"], "UI STEPS (same result by hand): %s" % (i["ui"] or "-"),
              "EVIDENCE: %s" % (i["evidence_file"] or "-")]
        if i["evidence"]: L += ["--- evidence (first lines) ---", i["evidence"][:2500], "---"]
        L.append("")
    return subj, "\n".join(L)

def push_text(items, stamp):
    letters = ",".join(i["id"].rsplit("-", 1)[1] for i in items)
    total = 0.0
    for i in items:
        m = re.search(r"\d[\d,]*\.?\d*", i["dollars"])
        if m: total += float(m.group(0).replace(",", ""))
    tail = " - approve on the Mandatory Approvals page"
    head = "APPROVAL NEEDED run %s: %d AMD write(s) refused (items %s, $%.2f)" % (stamp, len(items), letters, total)
    if len(head) + len(tail) > 189: head = "APPROVAL NEEDED run %s: %d AMD write(s) refused ($%.2f)" % (stamp, len(items), total)
    return (head + tail)[:189]

def put(path, text, dry):
    if dry: print("DRY would write %s (%d chars)" % (path, len(text))); return
    os.makedirs(os.path.dirname(path), exist_ok=True); open(path, "w").write(text); print("wrote", path)

def git_step(repo, regpath, n, stamp, trailers, push_main, dry):
    msg = "approvals: %s %d package(s) waiting" % (stamp, n) + ("\n\n" + "\n".join(trailers) if trailers else "")
    cmds = [["git", "-C", repo, "add", os.path.relpath(regpath, repo)], ["git", "-C", repo, "commit", "-m", msg],
            ["git", "-C", repo, "push", "origin", "HEAD"], ["git", "-C", repo, "push", "origin", "HEAD:main"]]
    if dry or not push_main:
        print("git commands (%s):" % ("DRY - not run" if dry else "not run; pass --push-main to run them"))
        for c in cmds: print("  " + " ".join(json.dumps(x) if (" " in x or "\n" in x) else x for x in c))
        return
    r = None
    for c in cmds:
        if c[3] == "commit" and subprocess.run(["git", "-C", repo, "diff", "--cached", "--quiet"]).returncode == 0:
            print("ok   git commit: register already committed - nothing new to commit"); continue   # re-run: still push
        r = subprocess.run(c, capture_output=True, text=True)
        print("%s git %s: %s" % ("ok  " if r.returncode == 0 else "FAIL", " ".join(c[3:]), (r.stdout + r.stderr).strip()[-300:]))
        if r.returncode and c[-1] != "HEAD:main": print("git step stopped here (nothing forced)"); return
    if r is not None and r.returncode: print("push to main refused (not fast-forward or protected) - left as is, never forced; the branch push above still carries the register")

def checklist(ob, stamp):
    print("\nNEXT - this session makes these three MCP calls now:")
    print("  1. ArtifactData batch  -> url + writes from %s/approval_cards_%s.json" % (ob, stamp))
    print("  2. Gmail send_message  -> to %s (only); subject = %s/approval_subject_%s.txt; body = %s/approval_request_%s.md (its first line is the subject)" % (TO, ob, stamp, ob, stamp))
    print("  3. PushNotification    -> text = %s/approval_push_%s.txt" % (ob, stamp))
    print("If this session cannot make them, the hourly 'billing approvals sync' routine picks the waiting items up from main.")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stamp", required=True); ap.add_argument("--items", required=True)
    ap.add_argument("--repo", default=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    ap.add_argument("--workspace", default="/home/claude/unbilled"); ap.add_argument("--run-kind", default="chat session")
    ap.add_argument("--trailer", action="append", default=[]); ap.add_argument("--push-main", action="store_true")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    if not os.path.isdir(os.path.join(a.repo, ".git")):   # copied into the workspace? the default --repo would resolve to /home
        print("--repo %s is not a git checkout - pass --repo <repo root> (e.g. /home/claude/effinger-billing-backend)" % a.repo); sys.exit(1)
    items = build_items(json.load(open(a.items)), a.stamp, a.workspace)
    if not items: print("no items in", a.items); sys.exit(1)
    for i in items:                                   # privacy gate BEFORE any write
        for f in ("what", "ui", "evidence", "dollars", "reason", "cmd"):
            hit = privacy_hit(str(i[f] or ""))
            if hit: print("PRIVACY GATE: %s in %s of %s - nothing written:\n%s" % (hit, f, i["id"], str(i[f])[:400])); sys.exit(2)
    ws_reg = os.path.join(a.workspace, "registers", "approvals_pending.json")
    repo_reg = os.path.join(a.repo, "practices", "ehpa", "registers", "approvals_pending.json")
    ob = os.path.join(a.workspace, "outbox")
    register(ws_reg, items, a.dry); stored = register(repo_reg, items, a.dry)
    items = [i for i in stored if i["status"] == "waiting"]   # re-run: never re-announce or reset a card William already answered
    if not items: print("all ids already answered - nothing to send"); sys.exit(0)
    subj, body = email(items, a.stamp); push = push_text(items, a.stamp)
    put(os.path.join(ob, "approval_cards_%s.json" % a.stamp), json.dumps(cards(items, a.run_kind, a.stamp), indent=1), a.dry)
    put(os.path.join(ob, "approval_request_%s.md" % a.stamp), body, a.dry)
    put(os.path.join(ob, "approval_subject_%s.txt" % a.stamp), subj, a.dry)
    put(os.path.join(ob, "approval_push_%s.txt" % a.stamp), push, a.dry)
    if a.dry: print("\nSUBJECT:", subj, "\nPUSH:", push, "\nCARDS:", ", ".join(i["id"] for i in items), "\n--- body (head) ---\n" + body[:700] + "\n---")
    git_step(a.repo, repo_reg, len(items), a.stamp, a.trailer, a.push_main, a.dry)
    checklist(ob, a.stamp)
