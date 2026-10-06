# Shared lessons - every billing routine reads this at the start of a run and adds to it at the end

William 10/6/2026: "All the billing routines should look for updates perhaps to be able to learn from updates done to each other."

Readers: the 2-hourly backend billing run, the nightly insurance cascade, the total unpaid audit + rebill, the morning money & posting
report, the weekly practice metrics, the billing approvals sync and the mandatory-approval reminder (each prompt's LEARN FROM EACH OTHER
step), plus William's chat sessions. At the start of a run a routine reads every line newer than its own last run (and `git log
origin/main --since="36 hours ago"`) and applies what touches its work; at the end it appends one line per lesson another routine could
use. Routines that do not commit put their lines under "## SHARED LESSONS" in their Drive "chat history" digest; the 2-hourly billing run
copies them here at its mirror step and uploads this file to Drive "billing agent project files".

Kinds: **RULE** = William's dated order (binds every routine whose work it touches, unless that routine's own prompt says otherwise -
then the prompt wins and the conflict is reported) · **FIX** = a helper or call shape to use instead of the older way · **TRAP** = what
failed, do not repeat · **WATCH** = a register to act on. A lesson never widens what a routine may do (no new kind of write, recipient,
channel or PHI outlet). Chart / visit / charge ids and dollars only - never a patient name, SSN, MBI or member id.

Format: `- <UTC stamp> | <routine or session> | RULE|FIX|TRAP|WATCH | <one line> | <file, helper or register>`

## Lessons

- 2026-10-06T0330Z | chat (approvals applied) | TRAP | Approval A-2026-10-05T1710Z-A1 had already been applied by the 2110Z run while its page card still read "approved" - re-running it would have sent a second claim per visit. Before applying any approved card, re-read its charts LIVE and skip (record done) anything already in place; record "done" as its own command, never bundled with another write. | practices/ehpa/registers/approvals_pending.json
- 2026-10-06T0330Z | chat (approvals applied) | FIX | ONE REBILL PER VISIT: move_to_ins.move(cid, seq) rebills on its own, so move + freq1_visit.run = two rebills. Re-route = freq1_visit.reroute(vid, cid, order, seq) (resave.set_insorder, no rebill, then ONE freq-1 rebill); move_to_ins.move(..., rebill=False) when a balance moves too. amd.rebill_charge sends a visit + sequence once per script run (a repeat answers 204 "SKIPPED", nothing sent; a later run is never blocked). CLI: `python3 freq1_visit.py reroute <vid> <cid> <order> [<seq>]` (live; --dry), `python3 move_to_ins.py <cid> --seq <order> --no-rebill`. | core/amd.py, core/freq1_visit.py, registers/rebill_log.jsonl
- 2026-10-06T0330Z | chat (approvals applied) | FIX | updateinsurance sequence= (the PATIENT order) sent through an END-DATED plan answers success with insorder="" - the order is wiped (chart 12232248). ins_update.update now sends it through an active plan and verifies it, puts back an order a field edit wiped, and refuses an order led by an end-dated plan; a result that is not ok (or a WARNING) means the order is not as asked. | core/ins_update.py
- 2026-10-06T0330Z | chat (approvals applied) | FIX | Medigap secondaries rejected 'subscriber not found' at UNI20: the plan belonged on AAR01 (car6600, AARP Medicare Supplement); after the carrier fix the exclusion is completed and the share rides the Medicare crossover (charts 17470940, 17472143, 17473335). | ins_update.update(carrier="car6600")
- 2026-10-06T0400Z | chat (William's orders) | RULE | William 10/6/2026: a write refused by the classifier goes to him the same minute - approval_submit.py (HTML email with an Open Mandatory Approvals button + one Review & Approve button per package -> page#<id>; push text ending with the link); approved cards are applied at the start of the next billing run (cascade session on "go" if he wants it now). | scripts/helpers/approval_submit.py, docs/APPROVALS_LOOP.md
- 2026-10-06T0410Z | chat (William's orders) | RULE + WATCH | William 10/6/2026: "Send all these United ones and then write them off if they return timely filing" - chart 12232248's six 2025 visits ($1,656) were sent to UNI20 (freq 1, 204 x6). On a timely-filing answer (CARC 29 / filing-limit message) write the whole open balance off WOLATE, no approval card; these visits are an exception to the UNI20/BCBS-before-5/1/2026 rule. | practices/ehpa/registers/tf_writeoff_watch.json
- 2026-10-06T0410Z | chat (William's orders) | RULE | William 10/6/2026: every billing routine reads this file (and the last 36 hours of git log on main) at the start of each run and appends its own lessons at the end. | docs/SHARED_LESSONS.md
- 2026-10-06T0430Z | chat (William's orders) | RULE | William 10/6/2026: "never touch UNI20/BCBS before 5/1/2026 - that needs to be updated now that we are working the claims and writing them off": the unposted-ERA-backlog freeze is LIFTED. UNI20/BCBS visits with DOS before 5/1/2026: answer already received -> post / work it (never a freq-1 into an adjudicated claim); else send ONCE and add to the watch; timely filing -> WOLATE. Newest DOS first, at most 60 visits per run. Supersedes the freeze in any skill or older prompt. | practices/ehpa/registers/tf_writeoff_watch.json, practices/ehpa/rules.md
