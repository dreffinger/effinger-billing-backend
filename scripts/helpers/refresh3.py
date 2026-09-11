# PLAIN ENGLISH (9/5 refresh batch 3)
# Decides: The chart fixes and rebills for a specific set of names from the 9/5 TMH pastes (per-patient lines you approved in chat).
# Rules it uses: Same standing rules as elig_fix; each patient's plan order is hard-coded from the facesheet.
# Never touches: Anyone not named in the file.
# ---
# LOCAL ONLY: the body of this script carries patient identifiers (member numbers / dates of birth) in its data table,
# so only the header is mirrored. The full file lives in the workspace (/home/claude/unbilled/refresh3.py) and in the practice's Drive project folder.
