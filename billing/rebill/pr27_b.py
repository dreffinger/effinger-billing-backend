# PLAIN ENGLISH (Calloway MBI typo + Haverthwaite to Humana)
# Decides: Fixes Calloway' MBI (4F76 to <id>, per CMS) and re-sends Haverthwaite's UHC denials to her Humana MA plan.
# Rules it uses: Stedi/CMS result beats the chart when they disagree.
# Never touches: Anyone else.
# ---
# LOCAL ONLY: the body of this script carries patient identifiers (member numbers / dates of birth) in its data table,
# so only the header is mirrored. The full file lives in the workspace (/home/claude/unbilled/pr27_b.py) and in the practice's Drive project folder.
