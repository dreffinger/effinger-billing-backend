# PLAIN ENGLISH (9/7 second-pass actions from stedi_pass2 - the clear-cut ones)
# Decides: Applies the second Stedi pass verdicts that need no human judgment: add the Advantage plan / Medicare the payers confirmed, fix a member number the payer corrected, and point the denied (or never-received Medicaid) in-window visits at the right plan order, then re-send each as an original claim.
# Rules it uses: add_ins.add (no group numbers), ins_update.update for a corrected member number, move_to_ins.move + freq1_visit.run per visit (keeps admission dates). Medicare first, Medicaid/LTC second. Only visits the status sweep marked DENIED / FINALIZED-$0 / NOT ON FILE and dated within 12 months. Resumable: a visit whose '   NAME dos -> ' line is already in denial_act3.log is skipped.
# Never touches: Paid visits, claims over 12 months, or any patient not in the ACTIONS table below (those stay on the board for William / discovery).
# ---
# LOCAL ONLY: the body of this script carries patient identifiers (member numbers / dates of birth) in its data table,
# so only the header is mirrored. The full file lives in the workspace (/home/claude/unbilled/denial_act3.py) and in the practice's Drive project folder.
