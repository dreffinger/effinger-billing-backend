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
