# PLAIN ENGLISH (Claimocity backlog import 10/28/2026 - step 1, READ-ONLY, no AMD call):
# Reads a folder of Claimocity DFT^P03 HL7 files (sftp.claimocity.io /download/<yyyymmdd>626627aa54d52f67a80d586a.hl7, the files
# Gregg's AMD integration normally picks up) and writes one JSON record per message: file date, facility (MSH-4), Claimocity patient
# id (PID-3), name, DOB, provider (PV1-7), admit date (PV1-44), FT1 charge lines (DOS, CPT, units, dx pointers), IN1 payer names,
# DG1 codes. Prints the census the way William asks for it (per file, facility, provider, CPT, DOS, hospital / SNF-ALF / CCM).
# Output = feed_parsed_1028.json, the input of feed_match_1028.py (chart match) and feed_import_1028.py (charge entry).
# PID-19 (SSN) is deliberately NOT copied into the output - the fix-holds step reads it from the .hl7 files only when a Stedi MBI lookup needs it.
# A MESSAGE THAT CANNOT BE READ NEVER STOPS THE BATCH (11/11/2026): a message this parser cannot read is skipped and named, and the
#   parser reads on. Until then one such message ended the parser with no parsed file, so nothing of its batch was entered - and the
#   same file stopped every later run. Not readable = no PID segment, no PV1 segment, an FT1 charge line with fewer than the 20 fields
#   the parser reads (FT1_FIELDS), or anything else that fails while the message is read. Such a message is skipped WHOLE (never in
#   part) and written to feed_skipped_<stamp>.json beside the parsed file - one row per message: the file, its place in the file, its
#   message control id (MSH-10) and why. NEVER a patient name, a date of birth or a member id: that list is copied into the import
#   register (claimocity_import.py, "skipped_messages") and from there to the top of the report (claimocity_report.py); a person then
#   looks at the feed file. A message with NO FT1 line can be read and is passed on - the import finds nothing to enter and names it.
#   Every parsed message carries its control id ("ctl") and its place in its file ("msg") so that the import can name it.
# Usage: python3 -I feed_parse_dft_1028.py <folder with *.hl7> feed_parsed_1028.json
import glob, re, sys, collections, json, datetime, os
FT1_FIELDS = 20      # the parser reads FT1-4, FT1-5, FT1-10 and FT1-19 (and FT1-25 when it is there): a charge line shorter than this cannot be read
folder = sys.argv[1]
_dir, _base = os.path.split(sys.argv[2])
SKIPPED_FILE = os.path.join(_dir, ("feed_skipped_" + _base[len("feed_parsed_"):]) if _base.startswith("feed_parsed_") else ("skipped_" + _base))
msgs = []
skipped = []         # the messages this parser could not read: file, place in the file, control id and why - never a name, a date of birth or a member id
for f in sorted(glob.glob(folder + "/*.hl7")):
    raw = open(f, encoding="utf-8", errors="replace").read().replace("\r\n", "\n").replace("\r", "\n")
    fname = f.split("/")[-1][:8]; nth = 0
    for block in re.split(r"(?m)^(?=MSH\|)", raw):
        if not block.startswith("MSH|"): continue
        nth += 1; ctl = ""; why = []; short = []; seen = set(); nft = 0      # nth: the message's place in its file, counted from 1
        try:
            segs = [s.split("|") for s in block.strip().split("\n") if s.strip()]
            ctl = re.sub(r"[^A-Za-z0-9._:\-]", "", segs[0][9])[:40] if len(segs[0]) > 9 else ""      # MSH-10; letters, digits and . _ : - only
            m = {"file": fname, "FT1": [], "IN1": [], "DG1": []}
            for s in segs:
                t = s[0]; seen.add(t)
                if t == "MSH":
                    m["facility"] = s[4].split("^")[-1] if len(s) > 4 else ""
                    m["msgtime"] = s[7] if len(s) > 7 else ""
                elif t == "PID":
                    nm = s[5].split("^") if len(s) > 5 else [""]
                    m["pid"] = s[3] if len(s) > 3 else ""
                    m["name"] = (nm[0] + ", " + (nm[1] if len(nm) > 1 else "")).strip()
                    m["dob"] = s[7] if len(s) > 7 else ""
                elif t == "PV1":
                    prov = s[7].split("^") if len(s) > 7 else [""]
                    m["provider"] = " ".join(prov[1:3]) if len(prov) > 2 else prov[0]
                    m["admit"] = s[44] if len(s) > 44 else ""
                elif t == "FT1":
                    nft += 1
                    if len(s) < FT1_FIELDS: short.append("FT1 line %d has %d fields - the parser reads %d" % (nft, len(s), FT1_FIELDS)); continue
                    m["FT1"].append({"dos": s[4], "posted": s[5], "units": s[10], "dx": s[19], "cpt": s[25].split("^")[0] if len(s) > 25 else ""})
                elif t == "IN1":
                    m["IN1"].append(s[4].split("^")[0] if len(s) > 4 else "")
                elif t == "DG1":
                    m["DG1"].append(s[3])
            why = [w for w in ("" if "PID" in seen else "no PID segment", "" if "PV1" in seen else "no PV1 segment") if w] + short
            m["ctl"] = ctl; m["msg"] = nth
        except Exception as e:      # whatever else fails while ONE message is read: that message is skipped, the rest of the file is read
            why = ["could not be read (%s)" % type(e).__name__]
        if why: skipped.append({"file": fname, "msg": nth, "ctl": ctl, "why": "; ".join(why)}); continue
        msgs.append(m)

print("messages (visits):", len(msgs))
print("messages skipped (could not be read):", len(skipped))
print("files:", collections.Counter(m["file"] for m in msgs))
charges = [(m, c) for m in msgs for c in m["FT1"]]
print("charge lines:", len(charges))
print("unique patients:", len({(m["name"], m["dob"]) for m in msgs}))
print("\nby facility:", collections.Counter(m["facility"] for m in msgs).most_common())
print("\nby provider:", collections.Counter(m["provider"] for m in msgs).most_common())
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
json.dump(skipped, open(SKIPPED_FILE, "w"), indent=1)      # first: a parsed file never stands without its list of skipped messages (an empty list = none)
json.dump(msgs, open(sys.argv[2], "w"), indent=1)
for x in skipped:      # last, so the lines end the parse log (the ingest shows the last lines of every step)
    print("SKIPPED MESSAGE %s (file %s, message %d): %s - not in the parsed file; a person must look at the feed file" % (x["ctl"] or "no control id", x["file"], x["msg"], x["why"]))
