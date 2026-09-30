# Keeping the nightly/2-hourly routines from blocking themselves (fix 2026-09-30)

What happened 9/30 1:30 AM ET: the session runs in auto permission mode; its classifier denied the AMD-write batch
(`void_rules.py`, `era_clear.py`) and the `cred_check.py` / `build_money.py` batch, and also refused an edit of
`.claude/settings.json` ("Self-Modification"). An agent cannot grant itself permissions, so this is set by the owner:

1. Routine settings (web UI, Edit routine): set the permission mode so unattended runs are not prompted or classified, or
2. Commit `.claude/settings.json` on `main` yourself with allow rules:
   `Bash(python3 *)`, `Bash(cd /home/claude/unbilled && python3 *)`, `Bash(cd /home/claude/effinger-billing-backend && python3 tools/mirror/*)`,
   `Bash(git add|commit|push|pull|fetch *)`, `Bash(cp *)`, `Bash(mkdir *)`, `Bash(chmod 600 *)`,
   `Write(/home/claude/unbilled/**)`, `Edit(/home/claude/unbilled/**)`, `Artifact`, `mcp__Google-Drive__*`, `mcp__github__*`, `PushNotification`.

Also fixed in this change: `tools/nightly_bootstrap.sh` (rebuilds /home/claude/unbilled incl. money_template.html + openpyxl),
and a real patient name/DOB/member id redacted from `scripts/helpers/board_updates_1510_build.py` (the PHI gate blocked the mirror on it).
NOTE: that PHI is still in git history (commit 65725ac and later) - purge history or confirm the repo is private.
Missing on a cold start and needed from Drive 'workspace mirror': `pseudonyms.json` (-> secrets/), `void_rules.json`.

## Mandatory approval request on every refusal (William 9/30/2026 13:40 UTC)

"When this happens make a solution to send to me immediately for mandatory approval." Every refused AdvancedMD write now becomes an
approval package the same minute: `scripts/helpers/approval_request.py` (add / build / pending / approved / done) records the refusal with the
exact command, the classifier's reason, the dollars, the dry-run evidence and the AMD UI steps, builds `outbox/approval_request_<stamp>.md`,
and the run emails it to dreffinger@gmail.com ("APPROVAL NEEDED - backend billing run <stamp>") plus a phone push before working the next
column. William answers with "APPROVED <id>" (email reply or Working Denials command `approve <id>`), or does it himself with the command /
UI steps. The next run re-attempts an approved helper once and reports "approved by William, still refused by the environment" if the
classifier refuses again. Routine text: `nightly/columns_task_prompt_ehpa_cloud_v10_insert.txt` (step 0g rule 5). The register
`practices/ehpa/registers/approvals_pending.json` rides the repo. The durable fix is still the routine's permission mode / the allow rules
above - the run never edits either.
