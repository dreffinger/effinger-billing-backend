# PLAIN ENGLISH (Audit workbook)
# Decides: Builds the PR-transfer audit Excel: patients, facilities, live balances, refresh status.
# Rules it uses: Reads the audit JSON; no AMD writes.
# Never touches: Charts.
# ---
# LOCAL ONLY: the body of this script carries patient identifiers (member numbers / dates of birth) in its data table,
# so only the header is mirrored. The full file lives in the workspace (/home/claude/unbilled/build_pr_audit_wb.py) and in the practice's Drive project folder.
