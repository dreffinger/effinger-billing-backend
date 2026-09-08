# PLAIN ENGLISH (9/6 Unbilled column pass)
# Decides: Which of tonight's 47 unbilled visits can be released: adds the plan Stedi found (Tolliver UHC, Marchetti + Hendricks Medicare, Purcell UMR), points visits with plans already on file at the right sequence (Rothwell, Whitfield, Jarvis, Fenwick, Grantham Jr, Halloran, Hawthorne), and releases the 12 whose inspector holds were cleared.
# Rules it uses: Medicare first, Medicaid/LTC second; no group numbers; a visit is released only after its data is fixed. Patients Stedi could not identify (Merrick CHP id, Oakhurst, Waverly, Torrance medical plan, Dunmore) are NOT released - they go to the board for a facesheet.
# Never touches: Paid visits; any visit not on tonight's unbilled list.
# ---
# LOCAL ONLY: the body of this script carries patient identifiers (member numbers / dates of birth) in its data table,
# so only the header is mirrored. The full file lives in the workspace (/home/claude/unbilled/unbilled_0906.py) and in the practice's Drive project folder.
