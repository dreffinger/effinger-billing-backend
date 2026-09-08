# PLAIN ENGLISH (9/4 PCC facesheet refresh)
# Decides: For each patient on the 9/4 list: add Medicare if missing, add the Medicaid/MMA plan if missing, end the denying plan, move balances to insurance and rebill.
# Rules it uses: Medicare B first, Medicaid/MMA plan second. PCC 'Medicaid' payer label means custodial, not billable.
# Never touches: Charges with a payment posted.
# ---
# LOCAL ONLY: the body of this script carries patient identifiers (member numbers / dates of birth) in its data table,
# so only the header is mirrored. The full file lives in the workspace (/home/claude/unbilled/batch_refresh.py) and in the practice's Drive project folder.
