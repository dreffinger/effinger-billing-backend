# PLAIN ENGLISH (9/6 denial cascade - actions)
# Decides: Applies tonight's Stedi findings to the Medicare $0-denial patients: bills the Advantage plan Medicare named (LaFleur, Samson, Jacobsen Norcott, Lacroix, Gaines, Orwell), and corrects Edgerton' MBI to the one CMS holds, then re-sends.
# Rules it uses: CO24/CO22/CO16 $0 postings are reversed with co24_restore (void $0 pay + write-off, move balance, rebill) to the plan sequence Stedi confirmed active on the date of service. Chart plans are added only when missing; no group numbers.
# Never touches: Paid visits; hospice patients (already rebilled 9/5); anyone not listed here.
# ---
# LOCAL ONLY: the body of this script carries patient identifiers (member numbers / dates of birth) in its data table,
# so only the header is mirrored. The full file lives in the workspace (/home/claude/unbilled/denial_act_0906.py) and in the practice's Drive project folder.
