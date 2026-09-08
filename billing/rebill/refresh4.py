# PLAIN ENGLISH (9/5 refresh batch 4)
# Decides: Sedgwick, Ivens, Jessop Patient850, Kendal, Ambleside, Wexford chart fixes and rebills from the 9/5 facesheets.
# Rules it uses: Hard-coded per patient: which plan to end, which to add, the order by date of service.
# Never touches: Anyone not named in the file.
# ---
# LOCAL ONLY: the body of this script carries patient identifiers (member numbers / dates of birth) in its data table,
# so only the header is mirrored. The full file lives in the workspace (/home/claude/unbilled/refresh4.py) and in the practice's Drive project folder.
