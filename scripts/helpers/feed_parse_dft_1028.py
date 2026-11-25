# PLAIN ENGLISH (Claimocity backlog import 10/28/2026 - step 1, READ-ONLY, no AMD call):
# Reads a folder of Claimocity DFT^P03 HL7 files (sftp.claimocity.io /download/<yyyymmdd>626627aa54d52f67a80d586a.hl7, the files
# Gregg's AMD integration normally picks up) and writes one JSON record per message: file date, facility (MSH-4), Claimocity patient
# id (PID-3), name, DOB, provider (PV1-7), admit date (PV1-44), FT1 charge lines (DOS, CPT, units, dx pointers), IN1 payer names,
# DG1 codes. Prints the census the way William asks for it (per file, facility, provider, CPT, DOS, hospital / SNF-ALF / CCM).
# Output = feed_parsed_1028.json, the input of feed_match_1028.py (chart match) and feed_import_1028.py (charge entry).
# PID-19 (SSN) is deliberately NOT copied into the output - the fix-holds step reads it from the .hl7 files only when a Stedi MBI lookup needs it.
# ONE BROKEN MESSAGE NEVER STOPS THE FEED (11/25/2026). A message without a patient line (PID), or with a charge or diagnosis line cut short (a file that
#   ended in the middle of a message), used to end this step with an error - and with it the whole ingest: no visit of that day was entered, and the same
#   file stopped the next run again. Now every other message is read as before, and of the broken one NOTHING is entered: a message without a patient line
#   is nobody's visit and is left out of the output (the driver and every later step read a Claimocity id from each record); a message with a line cut
#   short keeps its patient and carries NO charge line - not even the lines that could be read ("unreadable" says why; the import's own row 'feed message
#   without a charge line' then names its chart). Each one is counted - file date and number of the message in its file, in fixed words, never a name, a
#   date or an id - in registers/feed_unreadable_<stamp>.json (when this folder has registers/ and the output is named feed_parsed_<stamp>.json; a parse
#   that finds none takes an older one of the same stamp away) and in this step's LAST printed line, which starts UNREADABLE and says TOP OF THE REPORT.
#   The digest reads the register (claimocity_report.py) and says what ends it.
# EVERY MESSAGE THAT CANNOT BE ENTERED AS IT CAME IS COUNTED BY FILE DATE AND MESSAGE NUMBER (11/25/2026, the verification of the change above). Until
#   then four kinds went on without a word, and their visit was skipped or passed over somewhere later while the file was registered as done:
#   - a charge line that ends before its code (fewer than 26 fields - until then only a line of 19 fields or fewer counted as cut short);
#   - a charge line whose code is empty or is not five letters and digits (the file ended inside the code; every procedure code has five);
#   - a message with a patient line and NO charge line at all (the file ended before the charge line). Of the 1,602 messages in the 34 files the
#     daily runs had registered up to that day not one came without a charge line (the file register's count of messages and the rows of the
#     reconciliation registers, which hold only messages with a code, are the same number), so such a message is taken for a broken one, wherever
#     it stands in its file;
#   - a patient line whose Claimocity id (PID-3) is EMPTY: nobody can say by id whose visit it is, the patient map cannot learn it, and no step enters
#     a visit by the name alone. This record is still handed on as it came (the match step weighs the name and date it carries), with "unreadable".
#   The driver does not register a file while this step's register names a message of it (claimocity_ingest.py): the next start reads the file again.
# Usage: python3 -I feed_parse_dft_1028.py <folder with *.hl7> feed_parsed_1028.json
import glob, os, re, sys, collections, json, datetime
folder = sys.argv[1]
msgs = []
NO_PATIENT, CUT_SHORT = "no patient line", "a line of the message is cut short"      # the fixed words of an unreadable message
NO_CODE, NO_CHARGE, NO_ID = "a charge line carries no whole procedure code", "no charge line", "the patient line carries no Claimocity id"      # ... and the three of 11/25/2026 (the driver and the digest hold the same five - the self-test keeps them together)
unreadable = []      # {file date, number of the message in its file, fixed words}
for f in sorted(glob.glob(folder + "/*.hl7")):
    raw = open(f, encoding="utf-8", errors="replace").read().replace("\r\n", "\n").replace("\r", "\n")
    fname = f.split("/")[-1][:8]
    nth = 0      # the number of the message in its file, from 1 - how an unreadable one is named
    for block in re.split(r"(?m)^(?=MSH\|)", raw):
        if not block.startswith("MSH|"): continue
        nth += 1
        segs = [s.split("|") for s in block.strip().split("\n") if s.strip()]
        m = {"file": fname, "FT1": [], "IN1": [], "DG1": []}
        cut = False; nocode = False
        for s in segs:
            t = s[0]
            if t == "MSH":
                m["facility"] = s[4].split("^")[-1] if len(s) > 4 else ""
                m["msgtime"] = s[7] if len(s) > 7 else ""
            elif t == "PID":
                nm = s[5].split("^") if len(s) > 5 else [""]
                m["pid"] = s[3] if len(s) > 3 and s[3].strip() else ""      # (blanks alone are no id)
                m["name"] = (nm[0] + ", " + (nm[1] if len(nm) > 1 else "")).strip()
                m["dob"] = s[7] if len(s) > 7 else ""
            elif t == "PV1":
                prov = s[7].split("^") if len(s) > 7 else [""]
                m["provider"] = " ".join(prov[1:3]) if len(prov) > 2 else prov[0]
                m["admit"] = s[44] if len(s) > 44 else ""
            elif t == "FT1":
                if len(s) < 26: cut = True; continue        # the line ends before its code (field 25): cut short
                code = s[25].split("^")[0]
                if not re.fullmatch(r"[A-Za-z0-9]{5}", code): nocode = True; continue      # an empty code, or one the file ended in: no procedure code has fewer or more than five letters and digits
                m["FT1"].append({"dos": s[4], "posted": s[5], "units": s[10], "dx": s[19], "cpt": code})
            elif t == "IN1":
                m["IN1"].append(s[4].split("^")[0] if len(s) > 4 else "")
            elif t == "DG1":
                if len(s) <= 3: cut = True; continue        # the line ends before its code: cut short
                m["DG1"].append(s[3])
        where = fname if re.fullmatch(r"\d{8}", fname) else "?"
        if "pid" not in m:      # nobody's visit: never handed on
            unreadable.append({"file": where, "message": nth, "why": NO_PATIENT}); continue
        why = CUT_SHORT if cut else NO_CODE if nocode else NO_CHARGE if not m["FT1"] else ""
        if why:                 # nothing is entered from a message that could not be read whole
            m["FT1"] = []; m["unreadable"] = why
            unreadable.append({"file": where, "message": nth, "why": why})
        elif not m["pid"]:      # a whole message nobody can enter: it is handed on as it came (no step enters a visit without a Claimocity id) and counted
            m["unreadable"] = NO_ID
            unreadable.append({"file": where, "message": nth, "why": NO_ID})
        msgs.append(m)

print("messages (visits):", len(msgs))
print("files:", collections.Counter(m["file"] for m in msgs))
charges = [(m, c) for m in msgs for c in m["FT1"]]
print("charge lines:", len(charges))
print("unique patients:", len({(m.get("name"), m.get("dob")) for m in msgs}))
print("\nby facility:", collections.Counter(m.get("facility", "") for m in msgs).most_common())
print("\nby provider:", collections.Counter(m.get("provider", "") for m in msgs).most_common())      # a message without a PV1 line has no provider: counted under an empty name, it no longer ends the step
cpt = collections.Counter(c["cpt"] for _, c in charges)
print("\nby CPT:", cpt.most_common())
dos = collections.Counter(c["dos"][:8] for _, c in charges)
print("\nby DOS:")
for d in sorted(dos): print(" ", d, dos[d])
ccm = {"99487", "99489", "99490", "99491", "99439", "99437"}
hosp = {"99221", "99222", "99223", "99231", "99232", "99233", "99238", "99239", "99497"}
snf = {"99304", "99305", "99306", "99307", "99308", "99309", "99310", "99315", "99316"}
def cat(c):
    return "CCM" if c in ccm else "hospital" if c in hosp else "SNF/ALF" if c in snf else "other"
print("\nby category:", collections.Counter(cat(c["cpt"]) for _, c in charges))
print("\ncharges per file x category:")
for fn in sorted({m["file"] for m in msgs}):
    print(" ", fn, collections.Counter(cat(c["cpt"]) for m, c in charges if m["file"] == fn))
print("\nIN1 payer names (top):", collections.Counter(p for m in msgs for p in m["IN1"] if p).most_common(25))
print("\nmessages with no IN1 at all:", sum(1 for m in msgs if not any(m["IN1"])))
print("admit dates present:", sum(1 for m in msgs if m.get("admit")))
json.dump(msgs, open(sys.argv[2], "w"), indent=1)
# the unreadable messages: the register beside the others of this batch, and this step's last line (the driver shows a step's last lines)
_st = re.fullmatch(r"feed_parsed_(\w+)\.json", os.path.basename(sys.argv[2])); _reg = os.path.join("registers", "feed_unreadable_%s.json" % _st.group(1)) if _st and os.path.isdir("registers") else None
if _reg:
    if unreadable: json.dump({"stamp": _st.group(1), "messages": unreadable}, open(_reg, "w"), indent=1)
    elif os.path.exists(_reg): os.remove(_reg)
if unreadable:
    print("\nUNREADABLE: %d feed message(s) could not be read and NOTHING of them is entered - TOP OF THE REPORT - the ingest keeps their file unregistered and its digest says what ends it: %s%s" % (
        len(unreadable), "; ".join("file %s message %d (%s)" % (u["file"], u["message"], u["why"]) for u in unreadable[:20]) + (" +%d more" % (len(unreadable) - 20) if len(unreadable) > 20 else ""),
        (" - see %s" % _reg) if _reg else ""))
