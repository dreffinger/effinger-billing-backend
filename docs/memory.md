# Where the project's memory lives

1. **This repository** — every script with its PLAIN ENGLISH header, the call registry (`docs/captured_calls.md`), the Postman mirror (`docs/postman_effinger_amd.json`), the nightly prompt, the board templates and each practice's non-secret configuration. Pushed as we go.
2. **The call registry** — `docs/captured_calls.md`: every AMD / Stedi call that has been captured from a DevTools paste or proven by probing, with its shape and the helper that wraps it. Regenerate the Postman collection whenever it changes.
3. **Postman** — William re-imports `docs/postman_effinger_amd.json` (token as `{{token}}`), his fallback for running the calls himself.
4. **Google Drive → aa claude folders → chat history** — one dated markdown digest per chat: decisions, rules given, calls captured, numbers, open items. Digests can name patients, so they stay in Drive, not here.
5. **The workspace** (`/home/claude/unbilled`) — scripts, logs, registers, `patient_db/` (eligibility answers per chart). Working data, never committed.
6. **Skills** in the Claude account — `advancedmd-api-reference`, `billing-easy-task…`, `billing-hard-task…`, the credentialing skill — the condensed operating rules Claude loads at the start of a run.
