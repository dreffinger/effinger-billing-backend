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
`main` within the hour. Approval and the re-attempt work exactly as before: William taps Approve on the card (or replies `APPROVED <id>`),
and the next run re-attempts that one command once, citing the id.

Rules for the refused script itself: give every multi-chart action script a `--only <letters>` selector so each card can be approved,
declined and re-attempted on its own; a session script whose comments carry patient names stays OUT of the repo (phi_gate) - it is
uploaded to Drive `workspace mirror` (PHI-OK) and the card's command names that file, as the 9/30 `unbilled_repair.py` card did.
