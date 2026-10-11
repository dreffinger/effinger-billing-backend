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
# 10/6/2026 (William: "make this fix to the routine permanent so it doesn't delay billing - use the programs to send emails to link
#   to approval buttons and push notification with link"): the email also comes as HTML (outbox/approval_request_<stamp>.html, the
#   Gmail htmlBody) with one button to the page and one "Review & Approve" button per package that opens THAT card's Approve /
#   Decline buttons (page#<id> scrolls to and outlines the card); the push text always ends with the link (one package -> its card,
#   several -> the page). Both routines (2-hourly billing run, nightly cascade) call this the moment a write is refused.
# Usage:
#   python3 approval_submit.py --stamp 2026-10-06T0137Z --items items.json [--repo <repo root>] [--workspace /home/claude/unbilled]
#          [--run-kind "chat session"] [--trailer "Co-Authored-By: ..."] [--push-main] [--dry]
#   items.json = ONLY the writes newly refused since the last call; letters continue across the run (A, B, C...):
#                [{"letter":"A", "command":"cd /home/claude/unbilled && python3 x.py --live --only A", "reason":"<classifier text>",
#                  "what":"chart ids, visit ids, DOS, CPT - never a name", "dollars":"$21.80", "ui":"...", "evidence":"<one line>",
#                  "evidence_file":"<optional path - referenced, never copied>"}, ...]   exit 2 = privacy gate, exit 3 = id collision
import json, os, re, sys, datetime, argparse, subprocess, html

PAGE = "https://claude.ai/artifact/HuYd2bSm2NxkFgYRqra7wR"
CASCADE = "https://claude.ai/code/session_01JYK9QNpG4udFd3o6dqCupt"   # the ask-mode session that applies approved cards on 'go'
TO = "dreffinger@gmail.com"
SSN = re.compile(r"\d{3}-\d{2}-\d{4}")
MBI = re.compile(r"^[1-9][AC-HJKMNP-RT-Y][AC-HJKMNP-RT-Y0-9]\d[AC-HJKMNP-RT-Y][AC-HJKMNP-RT-Y0-9]\d[AC-HJKMNP-RT-Y]{2}\d{2}$")
IDWORD = re.compile(r"\b(member\s*(?:id|number|no\.?|#)|subscriber(?:\s+(?:id|number))?|policy(?:\s+(?:id|no\.?|number))?)\W{0,12}\d{3,}", re.I)
# review 10/6/2026: alphanumeric member ids, AMD/Stedi field names, dates of birth, VA ICNs and name fields
IDWORD2 = re.compile(r"(member\s*(?:id|number|no\.?|#)?|memberid|subscriber\s*(?:id|num(?:ber)?)?|subscribernum|policy\s*(?:id|no\.?|number|#)?|"
                     r"medicaid\s*(?:id|number|#)?|insured\s*id|mbi)\W{0,12}[A-Z]{0,4}\d{5,}", re.I)
DOB = re.compile(r"(\bdob|date\s*of\s*birth|dateofbirth|birth\s*date|birthdate)\W{0,12}(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{8})", re.I)
VAICN = re.compile(r"\b\d{10}V\d{6}\b")
NAMEFIELD = re.compile(r'"(?:first|last|middle)_?name"\s*:\s*"[A-Za-z]', re.I)
LASTFIRST = re.compile(r"\b[A-Z][A-Z'\-]{1,},\s?[A-Z][A-Z'\-]{1,}(?: [A-Z]\.?(?=[\s(.,;]|$))?")   # AMD's "LAST, FIRST" / "LAST,FIRST" chart-name forms
ADDINS = re.compile(r"add_ins\.py\s+\d+\s+car\d+\s+\S{6,}")   # a plan add carries the member number as its third argument

def now(): return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def privacy_hit(text):
    if SSN.search(text): return "SSN pattern"
    m = IDWORD.search(text) or IDWORD2.search(text)
    if m: return "member/subscriber/policy number '%s'" % m.group(0)
    if DOB.search(text): return "date of birth"
    if VAICN.search(text): return "VA ICN"
    if NAMEFIELD.search(text): return "patient name field"
    if ADDINS.search(text): return "member number in an add_ins command (write a pid-only wrapper)"
    for tok in re.findall(r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?", text):   # dashed display form too
        if MBI.match(tok.replace("-", "")): return "MBI token %s" % tok
    return None

def repo_safe(text):
    """The copy that goes to GitHub carries chart ids, never a chart name ("LAST, FIRST" -> "[name]")."""
    return LASTFIRST.sub("[name]", text or "") if isinstance(text, str) else text

def build_items(raw, stamp, ws):
    """evidence = the caller's one-line summary; evidence_file is referenced by PATH only - its contents (a dry register can hold a
    271 with member ids, names, DOB) are never copied into the register, the page, the email or GitHub (review 10/6/2026)."""
    out = []
    for r in raw:
        ef, ev = r.get("evidence_file"), (r.get("evidence", "") or "")[:600]
        out.append({"id": "A-%s-%s" % (stamp, r["letter"]), "stamp": stamp, "at": now(), "cmd": r["command"], "reason": r["reason"],
                    "what": r["what"], "dollars": str(r.get("dollars", "")), "evidence_file": ef, "evidence": ev,
                    "ui": r.get("ui", ""), "status": "waiting", "answer": None})
    return out

def collisions(path, items):
    """ids already in the register with a DIFFERENT command - a second refusal must take the next free letter."""
    d = json.load(open(path)) if os.path.exists(path) else {"items": []}
    have = {i["id"]: i for i in d["items"]}
    return [i["id"] for i in items if i["id"] in have and have[i["id"]].get("cmd") != i["cmd"]]

def register(path, items, dry, scrub=False):
    d = json.load(open(path)) if os.path.exists(path) else {"items": []}
    have = {i["id"]: i for i in d["items"]}
    new = [i for i in items if i["id"] not in have]
    if new and not dry:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        d["items"] += [dict(i, what=repo_safe(i["what"]), ui=repo_safe(i["ui"]), evidence=repo_safe(i["evidence"]), cmd=repo_safe(i["cmd"]), reason=repo_safe(i["reason"])) if scrub else i for i in new]
        json.dump(d, open(path, "w"), indent=1)
    print("%sregister %s: +%d new, %d already present" % ("DRY " if dry else "", path, len(new), len(items) - len(new)))
    return [have.get(i["id"], i) for i in items]            # stored copy wins: keeps 'at' and any answer already given

def cards(items, kind, stamp):
    writes = [{"op": "set", "collection": "approvals", "doc_id": i["id"],
               "data": {"at": i["at"], "run": "%s %s" % (kind, stamp), "command": i["cmd"], "reason": i["reason"], "what": i["what"],
                        "dollars": i["dollars"], "evidence": i["evidence"], "ui": i["ui"], "status": "waiting",
                        "answeredAt": None, "answeredBy": None, "note": ""}} for i in items]
    return {"url": PAGE, "collection": "approvals", "writes": writes}

def email(items, stamp, kind="backend billing run"):
    n = len(items)
    # the hourly sync skips a package whose id it finds in sent mail under subject:"mandatory approval writes" - so this subject
    # carries those words (review 10/6/2026: the old subject made the sync send a second email + push for every package)
    subj = "mandatory approval writes - %d new to approve (%s %s, AdvancedMD writes refused)" % (n, kind, stamp)
    L = [subj, "", "Approve or decline each card on the Mandatory Approvals page: " + PAGE]
    L += ["  %s  ->  %s#%s" % (i["id"], PAGE, i["id"]) for i in items]
    L += ["", "The permission classifier refused %d AdvancedMD write(s). Each was planned, dry-run verified and NOT retried. "
          "Nothing was changed in AMD for these items." % n, "", "HOW TO APPROVE (pick one):",
          "  1. Tap Approve (or Decline) on the item's card on the Mandatory Approvals page (the link under each item opens that card) - the next",
          "     billing run (every 2 hours) applies an approved card once; to apply it right now, open the cascade session (%s) in ask mode and say 'go'." % CASCADE,
          "  2. Or do it yourself now: the exact command and the AMD UI steps are under each item.",
          "  (Email replies are not read - the card's button is the approval.)",
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

def total_dollars(items):
    total = 0.0
    for i in items:
        m = re.search(r"\d[\d,]*\.?\d*", i["dollars"] or "")
        if m: total += float(m.group(0).replace(",", ""))
    return total

def card_link(i): return "%s#%s" % (PAGE, i["id"])

def push_text(items, stamp):
    """One line under 200 characters that ALWAYS ends with the link: one package -> its card (the Approve button), several -> the page."""
    letters = ",".join(i["id"].rsplit("-", 1)[1] for i in items)
    tail = " - tap Approve: " + (card_link(items[0]) if len(items) == 1 else PAGE)
    head = "APPROVAL NEEDED run %s: %d AMD write(s) refused (items %s, $%.2f)" % (stamp, len(items), letters, total_dollars(items))
    if len(head) + len(tail) > 199: head = "APPROVAL NEEDED: %d AMD write(s), $%.2f" % (len(items), total_dollars(items))
    if len(head) + len(tail) > 199: tail = " - tap Approve: " + PAGE
    return head[:199 - len(tail)] + tail

def title(i, n=150):
    t = re.sub(r"\s+", " ", i["what"] or "").strip()
    return t if len(t) <= n else t[:n].rsplit(" ", 1)[0] + "..."

def html_email(items, stamp, subj):
    """The Gmail htmlBody: a button to the page, then one card per package with a 'Review & Approve' button that opens that
    card's Approve / Decline buttons on the page (page#<id>), then the details. Inline styles only (Gmail drops <style>).
    10/11/2026 (William: 'the email didn't have the green buttons'): Gmail's sanitizer also STRIPS the `background:` shorthand
    from inline styles, so every button sent as background:#1b8037 arrived as white text on white - invisible. Only the
    longhand `background-color:` survives; never use the shorthand in an email."""
    e = lambda s: html.escape(str(s or ""), quote=True)
    btn = ("display:inline-block;background-color:%s;color:#ffffff;padding:12px 20px;border-radius:8px;text-decoration:none;"
           "font:700 15px -apple-system,Segoe UI,Arial,sans-serif")
    H = ['<div style="font:15px -apple-system,Segoe UI,Arial,sans-serif;color:#141413;max-width:640px">',
         '<p style="font-size:17px;font-weight:700;margin:0 0 6px">MANDATORY APPROVAL WRITES: %d new package(s) / $%.2f waiting - tap Approve or Decline</p>'
         % (len(items), total_dollars(items)),
         '<p style="margin:0 0 14px;color:#5f6368">%s</p>' % e(subj),
         '<p style="margin:0 0 20px"><a href="%s" style="%s">Open Mandatory Approvals</a></p>' % (e(PAGE), btn % "#0163aa")]
    for i in items:
        H += ['<div style="border:1px solid #d7d8da;border-radius:12px;padding:14px 16px;margin:0 0 14px;background-color:#f6f7f8">',
              '<div style="font:500 12px monospace;color:#5f6368">%s</div>' % e(i["id"]),
              '<div style="font-weight:700;margin:4px 0">%s</div>' % e(i["dollars"] or "n/a"),
              '<div style="margin:0 0 10px">%s</div>' % e(title(i)),
              '<a href="%s" style="%s">Review &amp; Approve</a>' % (e(card_link(i)), btn % "#1b8037"),
              '<div style="font-size:12.5px;color:#5f6368;margin-top:10px">Refused as: %s<br>Command: <code>%s</code><br>AMD screens (same result by hand): %s</div>'
              % (e(i["reason"]), e(i["cmd"]), e(i["ui"] or "-")),
              '</div>']
    H += ['<p style="font-size:13.5px;margin:18px 0 6px"><b>After you tap Approve</b>, the next billing run (every 2 hours) re-attempts the write '
          'once and the card flips to done. To apply it right now instead, open the <a href="%s">Nightly insurance cascade session</a> '
          'in ask mode and say <b>go</b>.</p>' % e(CASCADE),
          '<p style="font-size:12.5px;color:#5f6368;margin:0">Nothing was changed in AdvancedMD for these items. Each was dry-run verified and not '
          'retried. The card\'s button is the approval - email replies are not read.</p></div>']
    return "\n".join(H)

def put(path, text, dry):
    if dry: print("DRY would write %s (%d chars)" % (path, len(text))); return
    os.makedirs(os.path.dirname(path), exist_ok=True); open(path, "w").write(text); print("wrote", path)

def gate(repo, regpath):
    """tools/mirror/phi_gate.py on the repo register before it is staged: names -> pseudonyms, an identifier = no push (review 10/6/2026)."""
    g = os.path.join(repo, "tools", "mirror", "phi_gate.py")
    if not os.path.exists(g): print("WARN phi_gate.py not in the repo - register not gated"); return True
    r = subprocess.run([sys.executable, g, regpath, regpath], capture_output=True, text=True)
    print(("ok   " if r.returncode == 0 else "FAIL ") + "phi_gate: " + (r.stdout + r.stderr).strip().replace("\n", " | ")[-300:])
    return r.returncode == 0

def git_step(repo, regpath, n, stamp, trailers, push_main, dry):
    if not dry and not gate(repo, regpath): print("register NOT pushed - an identifier is in it; fix the item and run again"); return
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
    if r is not None and r.returncode: print("push to main refused (not fast-forward or protected) - left as is, never forced; the branch push above still carries the register - run `git pull --rebase --autostash origin main` then `git push origin HEAD:main` once")

def checklist(ob, stamp):
    print("\nNEXT - this session makes these three MCP calls now:")
    print("  1. ArtifactData batch  -> url + writes from %s/approval_cards_%s.json" % (ob, stamp))
    print("  2. Gmail send_message  -> to %s (only); subject = %s/approval_subject_%s.txt; htmlBody = %s/approval_request_%s.html (the buttons);"
          " plain-text body, where the tool takes one = %s/approval_request_%s.md" % (TO, ob, stamp, ob, stamp, ob, stamp))
    print("  3. PushNotification    -> status proactive, message = %s/approval_push_%s.txt (ends with the link)" % (ob, stamp))
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
    clash = sorted(set(collisions(ws_reg, items) + collisions(repo_reg, items)))
    if clash: print("ID COLLISION: %s already hold a different command - give this refusal the next free letter (letters continue across the run); nothing written" % ", ".join(clash)); sys.exit(3)
    before = {i["id"] for i in (json.load(open(repo_reg))["items"] if os.path.exists(repo_reg) else [])}
    register(ws_reg, items, a.dry); register(repo_reg, items, a.dry, scrub=True)
    items = [i for i in items if i["id"] not in before]       # announce ONLY what is new in this call - never re-send or re-'set' a card
    if not items: print("nothing new to send - every id is already registered (its outbox files are from the first call)"); sys.exit(0)
    subj, body = email(items, a.stamp, a.run_kind); push = push_text(items, a.stamp)
    put(os.path.join(ob, "approval_cards_%s.json" % a.stamp), json.dumps(cards(items, a.run_kind, a.stamp), indent=1), a.dry)
    put(os.path.join(ob, "approval_request_%s.md" % a.stamp), body, a.dry)
    put(os.path.join(ob, "approval_request_%s.html" % a.stamp), html_email(items, a.stamp, subj), a.dry)
    put(os.path.join(ob, "approval_subject_%s.txt" % a.stamp), subj, a.dry)
    put(os.path.join(ob, "approval_push_%s.txt" % a.stamp), push, a.dry)
    if a.dry: print("\nSUBJECT:", subj, "\nPUSH:", push, "\nCARDS:", ", ".join(i["id"] for i in items), "\n--- body (head) ---\n" + body[:700] + "\n---")
    git_step(a.repo, repo_reg, len(items), a.stamp, a.trailer, a.push_main, a.dry)
    checklist(ob, a.stamp)
