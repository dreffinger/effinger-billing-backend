# Approvals loop (set up 2026-10-01, William's order: "approve the billing to run as continuously as possible without delays")

The scheduled billing runs are auto-mode routines, and the permission classifier refuses
AdvancedMD writes in them (see ROUTINE_PERMISSIONS.md). Every write a run could not make
becomes a *package* that William approves with one tap; the writes themselves run in the
chat session "Nightly insurance cascade" (session_01JYK9QNpG4udFd3o6dqCupt) in ask mode.

## Pieces

| Piece | What it is |
|---|---|
| `practices/ehpa/registers/approvals_pending.json` | The source. Each run appends `items[]` (`id`, `stamp`, `at`, `cmd`, `reason`, `what`, `dollars`, `evidence_file`, `evidence`, `ui`, `status` waiting/done, `answer`). |
| Mandatory Approvals page | Artifact https://claude.ai/artifact/HuYd2bSm2NxkFgYRqra7wR. Database collection `approvals`, one document per package, Approve / Decline buttons. Card anchors: `#<package id>`. |
| Routine "billing approvals sync" (`trig_01Bqg5n4YZZG55SULBq79JKJ`) | Hourly at :15, fires into the cascade session. Copies new waiting packages onto the page, emails William the card links (subject `mandatory approval writes - N new to approve`) plus a push, alerts him when a card is approved, marks cards done when the source says applied. Reads, page database, Gmail and push only. |
| Routine "mandatory approval writes" (`trig_01YUgjTTz71pE9Nh65mMUeGY`) | 8:51 AM / 8:51 PM ET reminder into the same session: what is waiting, what is approved, links to the page. |
| The apply step | William opens the cascade session in ask mode and says `go`. The session reads the page database, applies only the packages marked approved, one package per call, each AMD write arriving as a prompt he answers; then records: source item `done` + `answer`, page card `done`, board inbox file, digest addendum, commit. |

## Rules
- No SSNs, MBIs, member ids or policy numbers on the page, in emails or pushes. Chart ids and dollars are fine.
- Declined cards are left alone; waiting cards are never applied without his word.
- The sync never retries a refused call; it notes it and finishes.
- `.claude/settings.json` allows the sync's tools (git read commands, ArtifactData, Gmail search + send, PushNotification) so the hourly firing never stalls on a prompt in the ask-mode session.


## Any session, immediately (William 10/6/2026: "put this through the approval process ... so as to not slow down the billing" / "save that in a code to automatically do")

A chat session (or a routine) whose AdvancedMD write the classifier refuses no longer waits for the hourly sync. One command,
`scripts/helpers/approval_submit.py`, does the whole submission:

```
cd /home/claude/unbilled && python3 approval_submit.py --stamp <run stamp> --items <items.json> --repo /home/claude/effinger-billing-backend --push-main
```

`items.json` = one entry per chart/decision: `letter`, `command` (the exact refused command, with a `--only <letter>` selector when one
script carries several charts), `reason` (the classifier's words), `what`, `dollars`, `ui`, `evidence` (+ optional `evidence_file`).
The script (1) runs the privacy gate (no SSN / MBI / member / policy ids - exit 2 and nothing written on a hit), (2) appends the
items to BOTH `registers/approvals_pending.json` copies (workspace + repo, idempotent by id), (3) writes the page cards file
`outbox/approval_cards_<stamp>.json` (collection `approvals`, one `set` per card in the page's shape), (4) writes the email
(`outbox/approval_request_<stamp>.md`, subject on line 1: `APPROVAL NEEDED - backend billing run <stamp> (<n> AdvancedMD writes
refused)`) with the card links `https://claude.ai/artifact/HuYd2bSm2NxkFgYRqra7wR#<id>`, the push text (`outbox/approval_push_<stamp>.txt`),
and (5) with `--push-main` commits the register and pushes the branch + a fast-forward of `main`. It then prints the three connector
calls the session makes next: ArtifactData batch (the cards file), Gmail send_message to dreffinger@gmail.com (subject + body files),
PushNotification (the push file). If the session cannot make them, the hourly "billing approvals sync" picks the waiting items up from
`main` within the hour. Approval and the re-attempt work exactly as before: William taps Approve on the card (email replies are no longer read - 10/6/2026 review),
and the next run re-attempts that one command once, citing the id.

Rules for the refused script itself: give every multi-chart action script a `--only <letters>` selector so each card can be approved,
declined and re-attempted on its own; a session script whose comments carry patient names stays OUT of the repo (phi_gate) - it is
uploaded to Drive `workspace mirror` (PHI-OK) and the card's command names that file, as the 9/30 `unbilled_repair.py` card did.

## Permanent in the routines (William 10/6/2026: "make this fix to the routine permanent so it doesn't delay billing - use the programs to send emails to link to approval buttons and push notification with link")

The approval loop now lives in the routine prompts themselves (it had only been in repo docs/inserts; the live 2-hourly routine was still v7):

| Routine | What changed |
|---|---|
| Backend billing run, every 2 hours (`trig_01QRqT8KB4Q1H9EyYRG4NBKX`) - `nightly/columns_task_prompt_ehpa_cloud_v11.txt` | Step **0g MANDATORY APPROVALS**: (1) right after login it applies every card marked *approved* (live re-read first - skip and record anything already applied; dry form, then the exact approved command once; its own bookkeeping commit; a second refusal is noted, never retried); (2) any write refused during the run goes to William that same minute through `approval_submit.py` - HTML email with an *Open Mandatory Approvals* button and one *Review & Approve* button per package (`page#<id>` opens that card's Approve / Decline buttons), a push whose text ends with the link, the page cards, and the register pushed to `main`. Plus the ONE REBILL PER VISIT rule in STANDING FLAGS. |
| Nightly insurance cascade (`trig_01XVrVN9dpSdvAbB1ZrsAzFU`) - `nightly/insurance_cascade_prompt_v3.txt` | The same MANDATORY APPROVALS step and ONE REBILL rule (run kind "nightly cascade"). |
| Billing approvals sync, hourly (`trig_01Bqg5n4YZZG55SULBq79JKJ`) - `nightly/approvals_sync_prompt_v2.txt` | Every push ends with the link (one package -> its card, several -> the page); the email's links are styled as buttons; "approved" alerts say the next billing run applies them. |
| Mandatory approval writes reminder, 8:51 AM/PM ET (`trig_01YUgjTTz71pE9Nh65mMUeGY`) - `nightly/approvals_reminder_prompt_v2.txt` | Push texts carry the page / session link; on "go" every package's charts are re-read live first and anything already applied is recorded done, not re-run. |

So an approval now costs William one tap: the email or push arrives the minute a write is refused, the link opens the card's Approve button, and the next billing run (at most 2 hours later) applies it - or the cascade session on "go" if he wants it now.

Code made permanent with it (all in `core/` and `scripts/helpers/`, proven offline by `tools/selftest/test_one_rebill_and_approvals.py`): `amd.rebill_charge` one rebill per VISIT + sequence per script run (a repeat answers 204 "SKIPPED", nothing sent; a later run is never blocked; every rebill logged to registers/rebill_log.jsonl), `resave.set_insorder` (visit order, no rebill), `freq1_visit.reroute` (order + ONE freq-1 rebill), `move_to_ins.move(..., rebill=False)`, `ins_update.update` (patient order through an active plan, verified), `approval_submit.py` (HTML buttons + linked push).
