# PLAIN ENGLISH (Claimocity backlog import, William 10/28/2026 02:23 ET: "enter all of these encounters into advanced md
#   and bill them out, i dont care if we get duplicates later" - Gregg's pickup paused).
# Decides: for every DFT^P03 message in the 10/16-10/27 SFTP files whose patient has an AMD chart, creates the visit with
#   its charges (updvisitwithnewcharges on a NEW visit: id=""), diagnosis list, admission date on hospital stays, modifier
#   25 on 99497 / 99489 as the practice's existing charges carry it, facility/POS/profile copied from how the feed's own
#   earlier visits look in AMD. Charges enter Charge Review (approval=1, inspector on) like any feed charge.
# Dedupe: a feed line whose patient already has a live (non-void) charge with the same CPT + DOS is skipped.
# No plan at entry (11/10/2026, round 7): a visit entered while its chart has NO plan gets insorder "1" but AdvancedMD builds no insurance-order list
#   for it (no claim, no work list). Every register row records chart_insorder and open_plans_at_entry (open_plan_seqs_at_entry; None = the chart
#   could not be read), and each such visit is counted and printed "NO PLAN AT ENTRY". The insurance check saves it again once a plan is there.
# Clinician, building and admission date (11/10/2026): each visit takes them from ITS OWN feed message (MSH-4, PV1-7, PV1-44), found by
#   the message's patient id and its (code, DOS) lines. Until then ONE value per feed PATIENT was used - the last message read - so in a
#   batch that held a resident's CCM (the physician's) and the nurse practitioner's visits, the visits went in under the physician (149
#   visits in the October batches; registers/feed_recon_* name each message's own clinician). The per-patient value is now only the
#   fallback for a message the raw files do not answer exactly once, and that fallback is counted and reported.
# Initial nursing-facility visit (William 11/10/2026, STANDING - practices/ehpa/rules.md): a message with the initial visit code 99306 goes in
#   under the PHYSICIAN's profile whatever clinician it names - every line of that visit, its 99497 included (INITIAL_NF, build()).
# Place of service (William 11/10/2026, STANDING - practices/ehpa/rules.md): Claimocity can only send 31 for the nursing buildings, so the
#   place of service is set here per charge line BY WILLIAM'S FREQUENCY RULE (nobody has checked the building's Part A list): CCM
#   99487/99489 -> 32; a nursing facility visit -> 32 for the monthly visit, 31 when the resident is seen once or twice a week or the
#   chart shows a new stay; whatever the chart does not show stays 31.
#   ALF / home (13), hospital (21) and unknown-building lines are entered exactly as before. See NF_KINDS / nf_visit_kind / pos_lines below.
# Quality code (William 11/10/2026, STANDING - practices/ehpa/rules.md): the advance-care-plan code 1123F goes on as a no-charge line, once
#   per patient per year, with the next nursing-facility, home or assisted-living visit of every patient 65 or older whose first plan is
#   Medicare Part B and whose last insurance check showed Medicare first (hospital visits are not coded in this version). A pilot first;
#   any doubt means no line; the visit itself always goes in. See QUALITY_* below. Once that pilot is proven, the option code M0004 rides
#   with the 1123F line once per clinician per year (William 11/10/2026: "use it"). See MVP_* below.
# A feed message that cannot be read never stops the batch (11/11/2026): a message with no FT1 line (no date of service, no code - nothing to
#   enter) used to stop main() at the line that builds the visit's key: the visits before it were entered, the ones after it were not, and every
#   re-run stopped at the same message. Such a message is now skipped, and so is everything the parser could not read (no PID or PV1 segment, a
#   short FT1 line - its list feed_skipped_<stamp>.json). Each is named in the import register under "skipped_messages" (message control id,
#   file, place in the file, reason, who skipped it - never a name, a date of birth or a member id), printed as a SKIPPED MESSAGE line and put
#   at the top of the report by the digest: a person must look at the feed file. See unreadable / skipped_rows below.
# Never touches: insurance plans (the cascade/precheck step verifies them afterwards), existing visits, patients without a chart.
# Usage: python3 feed_import_1028.py --dry | --one <feed pid> | --all [--limit N]
import os as _os
STAMP = _os.environ.get("FEED_STAMP", "1028")            # batch stamp: every feed_*_<STAMP>.* file and register belongs to one ingest run
HL7_DIR = _os.environ.get("FEED_HL7_DIR", "/tmp/claude-0/-home-claude/b8abe0d4-8133-5488-ad3a-bd2fb16f50f8/scratchpad/hl7/claimocity_oct")
DXCACHE = _os.environ.get("FEED_DX_CACHE", "dx_cache_feed.json")   # ICD-10 -> dcode map shared by every run (null = not in AMD's table)
CHART_PREFIX = _os.environ.get("FEED_CHART_PREFIX", "F" + STAMP)   # chart-number series for charts this run creates
import amd, resave, txh, re, json, sys, time, datetime, collections
import xml.etree.ElementTree as ET
PARSED = json.load(open(("feed_parsed_%s.json" % STAMP)))
MATCH = json.load(open(("feed_match_%s.json" % STAMP)))
DX = json.load(open(DXCACHE))
REG = ("registers/feed_import_%s.json" % STAMP)
PCODE = {"99487": "pcode492676", "99489": "pcode492677", "99223": "pcode65084", "99232": "pcode65089", "99233": "pcode65090",
         "99239": "pcode65095", "99497": "pcode492667", "99498": "pcode492668", "99306": "pcode65116", "99308": "pcode65118",
         "99309": "pcode65119", "99316": "pcode65122", "99344": "pcode601053"}
FEE = {"99223": "310.00", "99232": "111.00", "99233": "160.00", "99239": "163.00", "99306": "256.00", "99308": "107.00", "99309": "141.00",
       "99487": "206.00", "99489": "109.00", "99497": "133.00", "99344": "300.00", "99316": "207.00", "99498": "115.00"}
PROFILE = {"1225327380": "prof13", "1235128869": "prof15"}          # Effinger DO / Garland-G ARNP
# INITIAL NURSING-FACILITY VISIT (William 11/10/2026, STANDING - practices/ehpa/rules.md): "going forward the 99306 should always be billed under
# effinger npi and group npi as i am the one who is doing the initial hps 99306 and 99497". A message that carries one of these codes is entered under
# the physician's profile (his number with the group's), whatever clinician the message names - the whole visit, every line of the message, its
# 99497 included; a 99497 that comes without them keeps the clinician of its own message. Only 99306 is in the code table today (PCODE).
INITIAL_NF = {"99304", "99305", "99306"}
PHYSICIAN = "prof13"                                                 # the physician's profile: his NPI with the group's
INITIAL_WHY = "initial nursing-facility visit: always the physician (William 11/10/2026)"
FAC = {"HCA Florida Capital Hospital": ("fac29", "21"), "BRYNWOOD OPERATIONS LLC": ("fac34", "31"), "Aspire of Tallahassee": ("fac32", "31"),
       "Centre Pointe Health And Rehab Center": ("fac33", "31"), "Westminster Oaks-Bertrand Health Center": ("fac58", "31"),
       "Oakes Southwood": ("fac1350", "31"), "Azalea Gardens ALF": ("fac37", "13"), "Tapestry Senior Living Lakeshore": ("fac55", "13"),
       "Opal Hermitage Boulevard ALF": ("fac53", "13"), "Capital Square at Tallahassee": ("fac54", "13"), "Canterfield of Tallahassee ALF": ("fac38", "13"),
       "Sodalis Senior Living ALF": ("fac65", "13"), "Allegro Senior Living ALF": ("fac57", "13")}
HOSP = {"99221", "99222", "99223", "99231", "99232", "99233", "99238", "99239"}
MOD25 = {"99497", "99489"}
def mdy(yyyymmdd):
    return "%s/%s/%s" % (yyyymmdd[4:6], yyyymmdd[6:8], yyyymmdd[0:4])
# ---- PLACE OF SERVICE IN THE NURSING BUILDINGS (William 11/10/2026, STANDING - practices/ehpa/rules.md) -------------------------------
# The five nursing buildings arrive from Claimocity as POS 31 whatever the resident's status ("that is the only way we have to do it in
# claimocity"), so the place of service is decided here by William's frequency rule, per charge line, when the charge is entered. It is
# an operating rule read from the chart's visit pattern, not a check of the building's Part A list. How the code reads Medicare's line: 31 is
# what was billed before; 32 is for a resident who is not in a Part A stay, and Medicare can match a 32 line to the facility's Part A claim. So 32 is
# given only where the chart SHOWS the long-term pattern, and everything unclear keeps the feed's 31 - exactly what was billed before.
#   CCM 99487 / 99489          -> 32: "all the ccm services performed in the nursing facility setting by us are done on our long term
#                                 residents that are not being actively skilled". ALF / home CCM keeps its home location (13).
#                                 Exception: the chart shows the resident seen at skilled frequency, admitted or readmitted in the CCM's
#                                 own calendar month -> the line stays at the feed's 31 and is listed for William.
#   nursing facility visit     -> 32 for "the snf residents that are being billed monthly face to face visits": the previous nursing visit
#   99304-99310, 99315, 99316     was MONTHLY_MIN_DAYS to MONTHLY_MAX_DAYS earlier, was not a discharge, and none of our hospital visits
#                                 falls in between.
#                              -> 31 for "the ones being billed once or twice weekly ... because they are being skilled": the previous
#                                 nursing visit was no more than SKILLED_GAP_DAYS earlier; and 31 for an initial visit 99304-99306, the first
#                                 nursing visit on the chart, the first visit after a discharge, after one of our hospital visits or after
#                                 more than MONTHLY_MAX_DAYS (a new stay), and for a gap between weekly and monthly (nothing shown).
#   any other line (99497/8)   -> the place of service of the visit line of the SAME date in the message, else the feed's.
# Only a line in a KNOWN nursing building (FAC says 31) is ever changed, and each message is read with ITS OWN building: a feed patient
# whose messages come from two buildings is handled message by message. Only when a message's own building cannot be read and the
# patient shows two buildings does the rule step aside for that visit - and says so (POS RULE NOT APPLIED).
# Hospital (21), ALF / home (13), HCA REHAB (the inspector step) and the unknown-building default are entered exactly as before. Any error
# in the rule falls back to the feed's place of service for the whole message and is counted as "POS RULE NOT APPLIED" - the import
# never stops for this rule.
POS_RULE_VERSION = "2026-11-11.1"       # change this line with EVERY revision of the rule - mirror.py PROTECTED, the runbook grep (step c) and the ingest guard name it
CCM = {"99487", "99489"}
NF_INITIAL = {"99304", "99305", "99306"}
NF_DISCHARGE = {"99315", "99316"}
NF_VISIT = NF_INITIAL | NF_DISCHARGE | {"99307", "99308", "99309", "99310"}
HOSP_VISIT = {"99221", "99222", "99223", "99231", "99232", "99233", "99234", "99235", "99236", "99238", "99239"}
HOME_VISIT = {"99341", "99342", "99344", "99345", "99347", "99348", "99349", "99350"}     # our home / assisted-living visits: the resident was out of the building
# which building a nursing visit on the chart was in, read from the facility name gettxhistory gives (one key per nursing building; any
# other name - another nursing home, the hospital's rehab unit - is its own key). The Southwood building has two facility records.
BUILDING_KEYS = (("BRYNWOOD", "fac34"), ("ASPIRE", "fac32"), ("CENTRE POINTE HEALTH", "fac33"), ("WESTMINSTER BERTRAND", "fac58"), ("WESTMINSTER OAKS", "fac58"), ("SOUTHWOOD", "fac1350"))
def building_key(facname):
    """The nursing building a facility name belongs to (its fac id), another building's own name, or None when no name is known."""
    n = " ".join(str(facname or "").upper().split())
    if not n: return None
    for word, fac in BUILDING_KEYS:
        if word in n: return fac
    return n
SKILLED_GAP_DAYS = 14      # weekly / twice-weekly visits (feed 9/1-11/5/2026: 100 gaps of 1-7 days, 10 of 8-14, 6 of 15-20, 41 of 21-35, 9 longer)
MONTHLY_MIN_DAYS = 21      # 32 needs the monthly pattern actually shown: previous nursing visit 21 ...
MONTHLY_MAX_DAYS = 92      # ... to 92 days back (the 60-day schedule fits; longer than that is a new stay, not a monthly visit)
BATCH_NF = {}              # chart -> {(cpt, DOS) or (cpt, DOS, building)}: nursing, hospital and home visits of THIS feed batch and the visits earlier batches could not enter (main() fills it); read with the chart's history
BATCH_NF_ERR = [""]        # why the batch list could not be built (then no nursing-building line is 32 in this run) - reaches the DONE line
FACS = {}                  # feed patient id -> every building name its messages carry in this batch
MSGOF = {}                 # one feed message (see msg_key) -> {(building name, clinician NPI, admission date)} read from the raw files
MSGLAST = {}               # one feed message -> the LAST raw copy read of it: where its copies differ in the admission date, the message's own last copy answers (11/10/2026, review W2) - never another message of the patient
# ---- QUALITY CODE: ADVANCE CARE PLAN, Medicare measure 047 (William 11/10/2026, STANDING - practices/ehpa/rules.md) -------------------------
# "yes for all: billing adds 1123F automatically, once per patient, to the next Medicare claim for every patient 65 and older." 1123F says an
# advance care plan or a surrogate decision-maker is documented in the medical record - William's statement for every patient the practice follows.
# CMS counts the code from the Medicare Part B claim itself: a no-charge line on the SAME claim as an eligible visit (2026 claims specification
# of measure 047; the code list below was read for 2026 only - QUALITY_YEARS). It pays nothing. The line goes into the SAME create call as the
# visit's charges (a second call on the visit that left the other charges out would void them). A reporting code never holds a charge: if
# AdvancedMD refuses a visit that carries the line, the visit is entered again without it and no further line is tried in that run.
# WHO GETS IT: quality_due below. Every condition must be SHOWN; whatever is unclear means no line.
# HOSPITAL VISITS ARE NOT CODED IN THIS VERSION (11/10/2026, second Medicare review; QUALITY_POS_SKIP): AdvancedMD keeps the admission date
# per charge code; this import writes it for the visit's own hospital codes only; the Claim Inspector's hospital edit ("Hospitalization
# From Date ... empty") may look at every line at place of service 21, and nobody has ever sent an admission-date write for a reporting
# code; a hold caused by the line would count as a refusal and could switch the code off for every setting. For the 2026 score one counted
# line for each clinician is what matters, and the nursing-facility and home visits give that. The other visit lines of a message are still
# looked at; a hospital visit that met every other condition is counted (quality_skipped_hospital in the gate) - William decides for 2027.
# THE PILOT, A LEDGER OF LINES (rebuilt 11/10/2026 after the reviewers' findings): nobody has yet seen how AdvancedMD treats a no-charge line.
# Every run rebuilds where things stand from ALL import registers, oldest first, the register of its own stamp included (a second start under
# one stamp, --limit, --one): first each register's "quality_gate", then its rows. A LINE is one register row that carries the code. What
# became of a line is read from AdvancedMD (its own charge detail, _line); once it is decided it is not read for its outcome again (a line
# read as left off is the one exception, below) - the gate carries the charge numbers and their dates forward:
#   BILLED    the line is listed as billed to insurance.
#   LEFT OFF  the line is live and never billed while its visit's own charge is billed - and that is still so QUALITY_LEFT_OFF_DAYS (3) days
#             after the visit's newest billed date (11/10/2026, second state-machine review: a line can be billed a day after its visit;
#             before the third day the line is simply not decided). AdvancedMD left it off the claim: that line is dead and its patient is
#             due again. It is listed for William; no routine voids it. It is read again until QUALITY_LEFT_OFF_REREAD (30) days after
#             that billed date - billed after all, it counts as billed and its patient as coded.
#   VOID      the line itself says void. If the visit's own charge is still live, a person took the line off: the code is OFF until
#             William restarts it. If the visit's own charge is void too, the visit is gone and its place in the round is free. A line
#             the inspector step or the insurance check took off a held visit by itself (registers' "quality_removed") is void too, but
#             the routine's doing, not a person's - see removal() in quality_state.
#   open / unknown: not decided - the pilot WAITS. Unknown = the charge is not in the answer, shows no procedure or another one, its code
#             text is not 1123F, or the read failed. Unknown is never taken for void.
# A ROUND is the lines entered at the current amount since the last restart. A round holds at most QUALITY_PILOT lines that are not void, and
# never more than twice that in all. While one of its lines is open or unknown, no new line is added.
#   - PROVEN: a line of the round is BILLED, AdvancedMD shows it stored 1123F (its charge detail names the code text 1123F for pcode65441,
#     or the chart's history shows a live 1123F on that date - otherwise the round waits), its visit was never held, and the insurance
#     check of its own batch did not hold the chart or name another payer than Medicare. From then on every eligible visit carries the
#     line - at most QUALITY_DAILY a run until Medicare's own answer is on file, then no cap. MEDICARE'S OWN ANSWER: after proof each run
#     reads up to QUALITY_LOOKS billed lines for a payment line that Medicare Part B posted on them (_payments); the first one found is
#     kept in the gate. A person can lift the cap too, by writing registers/quality_n620_seen.json. Lines entered after proof are never
#     read back for their outcome; the proven round's own lines are read until each is decided.
#   - A $0.00 line LEFT OFF while no line of that round is billed -> new lines carry $0.01 (CMS allows either): a new round. One cent stays
#     until a restart, also when the $0.00 line turns out billed later. A one-cent line LEFT OFF -> OFF.
#   - OFF UNTIL WILLIAM RESTARTS IT (one sentence, kept in the gate and carried forward by every later run): a line taken off by a person;
#     a one-cent line left off; refusals (below); a round whose lines keep being voided, or that is full with nothing proven; AdvancedMD's
#     id for the line read with another code text than 1123F; a visit that carries the line and is HELD while the line could NOT be taken
#     off - before proof any Claim Inspector hold, after proof a hold whose words name the line (since 11/10/2026 the inspector step takes
#     the line off a held visit by itself: William's decision, quoted in practices/ehpa/rules.md); at any time when the insurance check
#     could not set the visit's order (its words: insorder not applied, resave FAULT, detail read mismatch); QUALITY_CODE=stop.
# LINES TAKEN OFF A HELD VISIT by the routine: the visit went through without it (released) = ONE refusal (below) and no second try for that
# patient that year; the visit stayed held anyway = nothing counts, the place is free and the patient is due again; such a line is never the proof.
# A REGISTER THAT CANNOT BE READ: an import register of this year that is there but cannot be parsed means the state is not known - no line
# in that run (the visits are imported as always), and the report says so at the top from the second run in a row.
# REFUSALS: AdvancedMD answers a fault to a visit that carries the line -> the import reads the chart again (three tries). Nothing of the
# visit stored -> the SAME visit goes in without the line, that patient gets no second try that year, no further line in that run.
# Refusals (or visits stored without their line, or lines taken off a held visit that then went through) in a row at one amount with no
# line stored in between - before proof ONE, after proof
# TWO - move the amount to one cent (a new round); at one cent they switch the code OFF. A fault although the chart shows the visit, or
# the chart cannot be read: the visit is NOT sent again, and the code is OFF from then on - William looks at that visit.
# SWITCHES (William's; QUALITY_CODE in the environment of the import and of the retry command; case and spaces do not matter): off = no
# line in this run; stop = OFF until restarted; reset = a new round at $0.00, honoured ONLY when the code is OFF until restarted (left in
# a routine it does nothing); any other value that is not empty = no line in this run, and the log says which value was not understood.
QUALITY_CODE = "1123F"; QUALITY_PCODE = "pcode65441"       # AdvancedMD's own id for 1123F (lookupproccode 11/10/2026 09:43Z, name "ACP DISCUSS/DSCN MKR DOCD" - docs/captured_calls.md)
QUALITY_SAME = {"1123F", "1124F"}                          # either one on the chart in the same year = already reported
QUALITY_PILOT = 3                                            # lines a pilot ROUND may hold before one of them is proven (void lines not counted; never more than twice this in all)
QUALITY_LOOKS = 6                                            # quality lines read per run for their outcome (one read of the line; one of its visit's own charge where the outcome needs it); after proof, as many again for Medicare's answer
QUALITY_DAILY = 10                                           # after proof: lines per run until Medicare's own answer is on file (a payment line read by the import, or QUALITY_N620)
QUALITY_MIN_AGE = 65
QUALITY_YEARS = {"2026"}                                     # dates of service the code list below and William's word were read for (measure 047, 2026); another year gets no line until William renews it
QUALITY_POS_SKIP = {"21", "22", "23"}                        # places of service whose visit lines never carry the line in this version: hospital inpatient, hospital outpatient, emergency department (HOSPITAL VISITS above)
QUALITY_LEFT_OFF_DAYS = 3                                    # a line that reads open while its visit's own charge is billed is called LEFT OFF only this many calendar days after that charge was billed
QUALITY_LEFT_OFF_REREAD = 30                                 # ... and a line called left off is read again until this many days after that date (billed after all = it counts as billed)
QUALITY_ANSWER_AGE = 10                                      # Medicare's answer: billed lines this many days old or older are read first
MEDICARE_B = "car6085"                                       # FLORIDA MEDICARE - the plan a Medicare Part B claim goes to; a payment line of that carrier carries its number without "car" (carrierfid)
MEDICARE_LEAD = "FLO02"                                      # ... and what the insurance check calls it when it leads
QUALITY_EXCEPTIONS = "registers/quality_exceptions.json"     # William's list of charts that never get the automatic line: a JSON object or list of chart ids, e.g. {"pat123": "declined"}
QUALITY_N620 = "registers/quality_n620_seen.json"            # a second way to lift the daily cap: a person writes this file once a 1123F line was seen on a Medicare remittance; the import only looks whether it exists
# the measure's eligible visit codes (2026 specification); CCM, advance care planning and discharge codes are not among them
QUALITY_VISITS = set("99304 99305 99306 99307 99308 99309 99310 99341 99342 99344 99345 99347 99348 99349 99350 99221 99222 99223 99231 99232 99233 "
                     "99234 99235 99236 99202 99203 99204 99205 99212 99213 99214 99215".split())
# ---- OPTION CODE M0004: QUALITY CARE FOR PATIENTS WITH NEUROLOGICAL CONDITIONS (William 11/10/2026, STANDING - practices/ehpa/rules.md) ----------
# M0004 is in AdvancedMD's procedure list (procedure id pcode692183, "QUAL CARE NEUROLOGIC CND MVP", read 11/10/2026 10:24Z - docs/captured_calls.md)
# and William said "use it": the group and both clinicians are registered for this option (an MVP) for 2026. CMS (the MVP implementation guide and the
# 2026 claims quick start): a practice that reports an option by claims puts the option's code on AT LEAST ONE Medicare Part B claim that also carries
# a quality code, on its own no-charge line. Whether one claim covers both clinicians is not known, so each clinician gets ONE such line a year.
# It pays nothing and never holds or delays a charge.
# WHEN IT RIDES (mvp_due): only on a visit that carries the 1123F line in the same call - right after it, with the same date, place of service, amount
#   and ONE diagnosis, no modifier - only once the 1123F pilot is proven, only for a date of service in MVP_YEARS, only when the visit's clinician is
#   known from its OWN feed message (not the per-patient fallback, not the physician profile an unknown id falls back to), never on a hospital or
#   emergency-department line (QUALITY_POS_SKIP), and only when that clinician - the profile the visit is ENTERED under - has no M0004 line this year
#   that is billed or not decided yet.
# ITS OWN SMALL LEDGER (mvp_state; the register's "mvp_gate"), built like the 1123F ledger from the same registers: an M0004 line is read in
#   AdvancedMD (its own charge detail, _line) until it is decided. BILLED = that clinician is done for the year. VOID = it may ride again. LEFT
#   OFF (its visit billed, the line not, and still so QUALITY_LEFT_OFF_DAYS days after the visit's billed date) = that clinician gets it once more;
#   the line is read again until QUALITY_LEFT_OFF_REREAD days after that date (billed after all = done). Open / unknown = no second line for that
#   clinician. The line is known by its code text: the charge detail must name pcode692183 as M0004.
# OFF UNTIL WILLIAM RESTARTS IT (the gate's "off_until_reset" - the specification's mvp_off_until_reset; only MVP_CODE=reset ends it, a restart of
#   1123F does not): AdvancedMD refused a visit that carried M0004 and took it with the 1123F line only; AdvancedMD stored a visit without its M0004
#   line; M0004 left off MVP_LEFT_OFF_MAX claims since the last restart; the routine took the M0004 line off a held visit that then went through, or
#   could not take it off; a hold whose words name M0004 while the line could not be taken off; the insurance check could not set such a visit's
#   order; AdvancedMD stores pcode692183 as another code; a visit that carried M0004 was refused and the chart did not show it free of the visit.
# REFUSALS: a visit with 1123F + M0004 that AdvancedMD refuses goes in again with the 1123F line only (that form is proven) once a fresh read of the
#   chart shows nothing of it stored; refused that way too, it goes in plain and the refusal counts against 1123F (REFUSALS above), M0004 is not
#   blamed. MEDICARE'S ANSWER: a billed M0004 line is read for a live Medicare Part B payment line, per clinician (the report shows it).
# SWITCHES: QUALITY_CODE=off / stop stop M0004 too (it never rides without the 1123F line); MVP_CODE=off = no M0004 line in this run; MVP_CODE=reset =
#   M0004 starts again after it was switched off until restarted (honoured only then); any other MVP_CODE value = no M0004 line in this run, and the
#   log says which value was not understood.
MVP_CODE = "M0004"; MVP_PCODE = "pcode692183"                # AdvancedMD's own id for M0004 (lookupproccode 11/10/2026 10:24Z, name "QUAL CARE NEUROLOGIC CND MVP" - docs/captured_calls.md)
MVP_YEARS = {"2026"}                                          # the year the group and both clinicians are registered for the option; another year gets no M0004 line until William renews it
MVP_ON = True                                                 # William 11/10/2026, about M0004: "use it"
MVP_LEFT_OFF_MAX = 2                                          # M0004 lines read as left off since the last restart that switch M0004 off (left off once: that clinician gets it once more)
MVP_LOOKS = 6                                                 # M0004 reads per run for their outcome (a line and, where needed, its visit's own charge or the visit's other charges); as many again for Medicare's answer
# this run's state (main() fills it: quality_state from the import registers, quality_files from the other registers). done: (chart, year)
# coded or refused, and ("feed:<feed patient id>", year) for a feed patient who carries a line under any chart; dead: (chart, code, DOS) of
# lines read as left off the claim; wait: a line of the round is not decided yet; budget: the lines this run may add (None = no cap);
# verify: chart -> (decision, lead payer) of its newest EARLIER insurance check. Until main() has read the registers, verify is empty - and
# then nobody gets a line. Dates the gate keeps are written MM/DD/YYYY; "since" / "in" fields hold the name of the register of the run in
# which something began, so the digest can tell what is new in its own run from what only still stands.
def _quality_fresh(): return {"fee": "0.00", "confirmed": False, "off": "", "off_until_reset": "", "wait": False, "added": 0, "budget": QUALITY_PILOT, "done": set(), "dead": set(), "dead_rows": [],
                              "pending": [], "pending_since": "", "billed_lines": [], "void_lines": [], "left_off_lines": [], "proof": None, "notes": [], "loud": "", "zero_not_billed": False, "reset": False, "reset_after": None, "twice": 0,
                              "round": {"n": 1, "fee": "0.00", "since": "", "lines": 0, "void": 0, "open": 0}, "n620": False, "history_shows_line": None, "refused": set(), "verify": {}, "exceptions": set(), "not_renewed": {},
                              "left_off_seen": {}, "left_off_on": {}, "late_billed": {}, "late_rows": [], "billed_on": {}, "code_text_lines": [], "wrong_code_text": "", "proof_wait": None,
                              "medicare_answer": None, "medicare_wait": None, "skipped_hospital": 0, "unread": [], "unread_prev": []}
QUALITY = _quality_fresh()
# the option code M0004's state for this run (mvp_state fills it from the registers): done / wait = (clinician profile, year) with an M0004 line that
# is billed / not decided yet - neither gets another line; added = the clinicians whose visit got the line in this run; the rest is its ledger
def _mvp_fresh(): return {"off": "", "off_until_reset": "", "reset": False, "reset_after": None, "loud": "", "done": set(), "wait": set(), "added": [], "notes": [], "lines": 0,
                          "billed_lines": [], "void_lines": [], "left_off_lines": [], "billed_on": {}, "left_off_on": {}, "left_off_seen": {}, "late_billed": {}, "late_rows": [],
                          "swaps": {}, "wrong_code_text": "", "answer": {}, "answer_wait": {}, "clinicians": {}}
MVP = _mvp_fresh()
def _any_day(s):
    """The calendar day of a date as AdvancedMD writes it (MM/DD/YYYY, with or without a time after it; YYYY-MM-DD), or None."""
    s = str(s or "").strip(); m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)
    if m: return _d8_day("%s%02d%02d" % (m.group(3), int(m.group(1)), int(m.group(2))))
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    return _d8_day("".join(m.groups())) if m else None
def _mdy_day(s):
    try: return datetime.datetime.strptime((s or "")[:10], "%m/%d/%Y").date()
    except Exception: return None
def _d8_day(s):
    """The calendar day of an 8-digit date (YYYYMMDD), or None when it is not a real date (month 13, day 00, 02/30 ...)."""
    try: return datetime.date(int(s[:4]), int(s[4:6]), int(s[6:8])) if len(s) == 8 else None
    except Exception: return None
def run_day():
    """The calendar day of this run: the date in the batch stamp (20261111T1240Z, 2026-11-11T1240Z, a retry's ...R), else today's (UTC).
    The quality code counts days from it: when a line counts as left off its claim, how long Medicare's answer has been waited for."""
    m = re.match(r"(\d{4})-?(\d{2})-?(\d{2})T", str(STAMP))
    return (_d8_day("".join(m.groups())) if m else None) or datetime.datetime.utcnow().date()
def _fmt_day(d): return d.strftime("%m/%d/%Y") if d else ""
def medicare_first(ctx, dos_mdy):
    """True when the chart's FIRST plan in billing order is Medicare Part B and is in force on that date (ctx['plans'] rows: plan id, carrier,
    begin date, end date, sequence; ctx['insorder'] = the sequences in billing order). An EMPTY begin date is no lower limit (15 of 684 real
    Medicare plan rows have none). A begin or end date that is there but cannot be read shows nothing: False."""
    day = _mdy_day(dos_mdy); first = (str(ctx.get("insorder") or "").replace(" ", "").split(",") or [""])[0]
    if day is None or not first: return False
    for row in ctx.get("plans") or ():
        try: _pid, car, beg, end, seq = row[:5]
        except Exception: continue
        if str(seq) != first: continue
        b = _mdy_day(beg); e = _mdy_day(end)
        return car == MEDICARE_B and (not str(beg or "").strip() or (b is not None and b <= day)) and (not str(end or "").strip() or (e is not None and e >= day))
    return False
def names_line(words, charge=""):
    """True when the words of a hold name the quality line: its code, AdvancedMD's id for it, its own charge number, or a zero amount
    ("zero" or "$0" together with "charge" or "amount")."""
    w = str(words or ""); low = w.lower(); n = re.sub(r"\D", "", str(charge or ""))
    if QUALITY_CODE.lower() in low or QUALITY_PCODE in low: return True
    if n and re.search(r"(?<!\d)%s(?!\d)" % n, w): return True
    return bool(re.search(r"zero|\$0", low)) and bool(re.search(r"charge|amount", low))
def names_lines(words, qcharge="", mcharge=""):
    """For a visit that carries the 1123F line AND the M0004 line: (the words name the 1123F line, the words name the M0004 line). A line is named by
    its code, AdvancedMD's id for it or its own charge number; words about a zero amount ("zero" or "$0" with "charge" or "amount") name the line whose
    code is not named - both lines when neither is named by its code. The inspector step and the insurance check use the same test (11/10/2026)."""
    w = str(words or ""); low = w.lower()
    def named(code, pcode, charge):
        n = re.sub(r"\D", "", str(charge or ""))
        return code.lower() in low or pcode in low or bool(n and re.search(r"(?<!\d)%s(?!\d)" % n, w))
    q = named(QUALITY_CODE, QUALITY_PCODE, qcharge); m = named(MVP_CODE, MVP_PCODE, mcharge)
    zero = bool(re.search(r"zero|\$0", low)) and bool(re.search(r"charge|amount", low))
    return (q or (zero and not m)), (m or (zero and not q))
def mvp_due(own_ok, prof, year, pos):
    """True when the option code M0004 rides with the 1123F line of a visit (build() asks only when that line rides): M0004 is on and not switched
    off, the quality code is not off and its pilot is proven, the year of the date of service is in MVP_YEARS, the visit's clinician is known from its
    OWN feed message (own_ok), the place of service is not a hospital or emergency-department one, and that clinician (prof - the profile the visit is
    entered under) has no M0004 line this year that is billed or not decided yet - an M0004 line added earlier in this run counts as not decided."""
    if not MVP_ON or MVP.get("off") or QUALITY.get("off") or QUALITY.get("confirmed") is not True: return False
    if own_ok is not True or not isinstance(prof, str) or not prof or str(year) not in MVP_YEARS or str(pos) in QUALITY_POS_SKIP: return False
    return (prof, str(year)) not in MVP["done"] and (prof, str(year)) not in MVP["wait"]
def mvp_undo(info):
    """A visit built with the M0004 line did not keep it (not created, refused, stored without it): that clinician's mark for the year is freed."""
    try:
        if info.get("mvp_codes") and info.get("mvp_prof"):
            MVP["wait"].discard((info["mvp_prof"], str(info.get("mvp_dos") or "")[-4:]))
            if info["mvp_prof"] in MVP["added"]: MVP["added"].remove(info["mvp_prof"])
    except Exception: pass
def quality_due(msg, ctx, lines, lpos=None, why=None):
    """Index of the visit line the advance-care-plan code rides with, or None. The FIRST visit line of the message for which EVERYTHING is
    shown (every visit line is looked at, not only the first):
      1. the code is not switched off, no line of the round waits for its outcome, and the run still has room (budget);
      2. the line's code is one of the measure's visit codes and its date of service is a real date in a year of QUALITY_YEARS;
      3. the feed's date of birth is a real calendar date, not the year-1900 placeholder, and the age on that date of service is 65 to 115;
      4. Medicare Part B is the chart's first plan in billing order and in force that day (medicare_first);
      5. the chart's NEWEST insurance check of an EARLIER batch released it with Medicare leading (a first-ever visit gets no line; the
         next batch's visit does);
      6. no 1123F / 1124F for that year - not in the registers (by chart, and by the feed's own patient id: the same feed patient matched
         to a second chart gets no second line), not live on the chart (a line read as left off the claim does not count) - the chart is
         not on William's exception list, and the patient was not refused with the line that year;
      7. never a line whose place of service, as the import will send it, is one of QUALITY_POS_SKIP: hospital visits (21, 22) are not
         coded in this version, and the measure leaves out the emergency department (23). The other visit lines of the message are still
         looked at - a message with a hospital line and a nursing line carries the line with its nursing line.
    lpos = the place of service of every line (build() gives it). why = a list the caller passes: it receives "hospital" when the message
    gets no line ONLY because of point 7 (for one of its visit lines every other condition is shown) - main() counts those visits.
    A visit that would carry the line but is dated in a year AFTER the years the list was read for is counted in QUALITY['not_renewed']
    (year -> charts) - the report says so in January."""
    if QUALITY["off"]: return None
    pid = ctx.get("pid"); dob = re.sub(r"\D", "", str(msg.get("dob") or ""))[:8]
    if _d8_day(dob) is None or dob[:4] <= "1900": return None                # no date of birth, not a real date, or the year-1900 placeholder: age not shown
    chk = (QUALITY.get("verify") or {}).get(pid)
    if not chk or chk[0] != "RELEASE" or chk[1] != MEDICARE_LEAD: return None   # no earlier insurance check, a hold, or another payer leads
    if pid in (QUALITY.get("exceptions") or ()): return None
    live = [r[:2] for r in ctx.get("live") or () if len(r) >= 2]; dead = QUALITY.get("dead") or ()      # a line AdvancedMD left off the claim is on the chart but was never reported
    fid = _feed_mark(msg.get("pid")); hospital = False
    for k, c in enumerate(lines):
        if c.get("cpt") not in QUALITY_VISITS: continue
        d8 = re.sub(r"\D", "", str(c.get("dos") or ""))[:8]
        if _d8_day(d8) is None or not (dob[:4] <= d8[:4]): continue
        skip = lpos is not None and str(lpos[k]) in QUALITY_POS_SKIP
        age = int(d8[:4]) - int(dob[:4]) - (1 if d8[4:] < dob[4:] else 0)
        if age < QUALITY_MIN_AGE or age > 115: continue
        if not medicare_first(ctx, mdy(d8)): continue
        if (pid, d8[:4]) in QUALITY["done"] or (fid and (fid, d8[:4]) in QUALITY["done"]): continue
        if any(code in QUALITY_SAME and str(d or "")[-4:] == d8[:4] and (pid, code, d) not in dead for code, d in live): continue
        if d8[:4] not in QUALITY_YEARS:                 # everything else is shown, but the list was not read for that year: no line. A LATER year is counted - William renews the rule each January
            if d8[:4] > max(QUALITY_YEARS) and not skip: QUALITY.setdefault("not_renewed", {}).setdefault(d8[:4], set()).add(pid)
            continue
        if QUALITY.get("wait"): return None
        if QUALITY.get("budget") is not None and QUALITY["added"] >= QUALITY["budget"]: return None
        if skip: hospital = True; continue              # everything else is shown, but this line is a hospital line: no line with it - the next visit line of the message is looked at
        return k
    if hospital and why is not None: why.append("hospital")
    return None
def _feed_mark(feed_id):
    """How QUALITY['done'] names a FEED patient (the feed's own patient id), apart from the charts: ('feed:<id>', year)."""
    return ("feed:%s" % feed_id) if isinstance(feed_id, (str, int)) and not isinstance(feed_id, bool) and str(feed_id).strip() else None
def quality_undo(info, pid, feed_id=None):
    """A visit that was built with the quality line was not created after all: its slot under the pilot cap and its once-a-year marks are freed."""
    try:
        if info.get("quality_dos"):
            QUALITY["added"] = max(0, QUALITY["added"] - 1); QUALITY["done"].discard((pid, str(info["quality_dos"])[-4:]))
            if _feed_mark(feed_id): QUALITY["done"].discard((_feed_mark(feed_id), str(info["quality_dos"])[-4:]))
    except Exception: pass
# what nf_visit_kind can answer: kind -> (place of service, the words for the register; %d = days since the previous nursing visit)
NF_KINDS = {
    "initial":      ("31", "31 by rule: initial visit"),
    "dischargeday": ("31", "31 by rule: discharge visit (kept at the feed's place of service)"),
    "first":        ("31", "31 by rule: no earlier nursing visit on the chart (read as a new admission)"),
    "hospital":     ("31", "31 by rule: first nursing visit after one of our hospital visits (%d days after the previous nursing visit)"),
    "away":         ("31", "31 by rule: one of our home or assisted-living visits since the previous nursing visit (%d days earlier)"),
    "discharge":    ("31", "31 by rule: the previous nursing visit, %d days earlier, was a discharge"),
    "moved":        ("31", "31 by rule: the previous nursing visit, %d days earlier, was in another building"),
    "preadmission": ("31", "31 by rule: an initial visit follows within two weeks (%d days after the previous nursing visit)"),
    "skilled":      ("31", "31 by rule: seen %d days after the previous nursing visit (weekly or more)"),
    "extra":        ("31", "31 by rule: seen %d days after the previous nursing visit, no admission visit at the start of this run of visits (an extra visit on a monthly resident?)"),
    "stale":        ("31", "31 by rule: %d days since the previous nursing visit, not a monthly pattern"),
    "between":      ("31", "31 by rule: %d days since the previous nursing visit, between weekly and monthly"),
    "monthly":      ("32", "32 by rule: %d days since the previous nursing visit (the monthly visit)"),
}
# a visit of one of these kinds in the CCM's month (or one of our hospital or home / assisted-living visits that month) keeps the CCM at the feed's 31, for William
SKILLED_KINDS = ("initial", "dischargeday", "first", "hospital", "away", "discharge", "moved", "preadmission", "skilled", "extra", "stale")
def _day(mdy_s):
    return datetime.datetime.strptime(mdy_s, "%m/%d/%Y").date()
def _history(nf_history):
    """Chart + batch rows -> (nursing visits {day: {codes}}, their buildings where known {day: {keys}}, days of our hospital visits, days of
    our home / assisted-living visits). A row is (cpt, 'MM/DD/YYYY') or (cpt, 'MM/DD/YYYY', facility name); odd rows are skipped."""
    visits = {}; where = {}; hosp = set(); home = set()
    for row in nf_history:
        try: c, d = row[0], row[1]
        except Exception: continue
        if not d or not isinstance(c, str): continue
        fam = "n" if c in NF_VISIT else "h" if c in HOSP_VISIT else "a" if c in HOME_VISIT else ""
        if not fam: continue
        try: dd = _day(d)
        except Exception: continue
        if fam == "h": hosp.add(dd)
        elif fam == "a": home.add(dd)
        else:
            visits.setdefault(dd, set()).add(c)
            try: k = building_key(row[2])
            except Exception: k = None
            if k: where.setdefault(dd, set()).add(k)
    return visits, where, hosp, home
def _kind_at(day, codes, hist, here=None):
    """(kind, days since the previous nursing visit) for a nursing visit with `codes` on `day`. hist = what _history returns; here = the
    building key of the visit when it is known. Everything that is not plainly the monthly visit answers a kind that is 31."""
    visits, where, hosp, home = hist
    codes = set(codes) | visits.get(day, set())
    if codes & NF_INITIAL: return "initial", 0
    if codes & NF_DISCHARGE: return "dischargeday", 0
    days = sorted(d for d in visits if d < day)
    if not days: return "first", 0
    here = here or next(iter(sorted(where.get(day, ()))), None)
    def new_stay(i, d2, here2):                          # does the nursing visit of d2 (the one after days[i-1] ...) start a stay?  i = index of the visit before it, or -1
        if i < 0: return True
        q = days[i]
        if (d2 - q).days > MONTHLY_MAX_DAYS or (visits[q] & NF_DISCHARGE): return True
        if any(q <= h <= d2 for h in hosp) or any(q <= a <= d2 for a in home): return True
        wq = where.get(q)
        return bool(here2 and wq and wq != {here2})      # a day that also names another building is not "the same building"
    prev = days[-1]; gap = (day - prev).days
    if any(prev <= h <= day for h in hosp): return "hospital", gap
    if any(prev <= a <= day for a in home): return "away", gap
    if visits[prev] & NF_DISCHARGE: return "discharge", gap
    if here and where.get(prev) and where[prev] != {here}: return "moved", gap      # chart and feed name two buildings for that day: unclear, so 31
    if len(where.get(day, ())) > 1: return "moved", gap                             # this visit's OWN day is named under two buildings (the feed sent the same visit from two - 11/10/2026, review C1): unclear, so 31
    if any(day < d <= day + datetime.timedelta(days=SKILLED_GAP_DAYS) and (visits[d] & NF_INITIAL) for d in visits): return "preadmission", gap
    if gap <= SKILLED_GAP_DAYS:
        i = len(days) - 1                                # walk back through the run of close visits to its first visit
        while True:
            d2 = days[i]; h2 = next(iter(sorted(where.get(d2, ()))), None)
            if (visits[d2] & NF_INITIAL) or new_stay(i - 1, d2, h2): return "skilled", gap
            if (d2 - days[i - 1]).days > SKILLED_GAP_DAYS: return "extra", gap
            i -= 1
    if gap > MONTHLY_MAX_DAYS: return "stale", gap
    if gap < MONTHLY_MIN_DAYS: return "between", gap
    return "monthly", gap
def nf_visit_kind(cpt, dos_mdy, nf_history, here=None):
    """(kind, days) for ONE nursing facility visit line in a nursing building - see NF_KINDS. nf_history: iterable of (cpt, 'MM/DD/YYYY')
    or (cpt, 'MM/DD/YYYY', facility name): every nursing, hospital and home visit known for the resident (the chart's live charges + this
    feed batch). here = the building key of this line. Pure: no AMD call, no file."""
    return _kind_at(_day(dos_mdy), {cpt}, _history(nf_history), here)
def nf_visit_pos(cpt, dos_mdy, nf_history, here=None):
    """(pos, why) for ONE nursing facility visit line in a nursing building. why carries no date."""
    kind, gap = nf_visit_kind(cpt, dos_mdy, nf_history, here); pos, text = NF_KINDS[kind]
    return pos, (text % gap if "%d" in text else text)
def seen_at_skilled_frequency(dos_mdy, nf_history, here=None):
    """True when the chart shows, in the calendar month of dos_mdy, one of our hospital visits, one of our home / assisted-living visits (the
    resident was out of the building that month) or a nursing visit the rule reads as weekly, an admission, a discharge or a new stay (any
    kind in SKILLED_KINDS) - or, when the CCM's own building is known (here), that the resident's latest nursing visit up to the CCM's date, or
    a nursing visit of the CCM's month, is known to be in ANOTHER building (11/10/2026, second reviewers: the resident came to this building that
    month or the buildings disagree). Then a CCM line of that month stays at the feed's 31, for William."""
    day = _day(dos_mdy); hist = _history(nf_history); visits, where, hosp, home = hist
    same = lambda d: (d.year, d.month) == (day.year, day.month)
    if any(same(h) for h in hosp) or any(same(a) for a in home): return True      # the resident was in the hospital or out of the building that month
    if here:                                             # the CCM's own building is not where the resident's nursing visits are known to be
        _upto = [d for d in visits if d <= day]
        if _upto and where.get(max(_upto)) and where[max(_upto)] != {here}: return True
        if any(same(d) and where.get(d) and where[d] != {here} for d in visits): return True
    for d in sorted(visits):
        if same(d) and _kind_at(d, visits[d], hist)[0] in SKILLED_KINDS: return True
    return False
def pos_lines(cpt_dos, feed_pos, nursing, nf_history, here=None):
    """Place of service for every line of ONE feed message. cpt_dos = [(cpt, 'MM/DD/YYYY')] in line order; nursing = the message comes from
    one of the practice's nursing buildings; here = that building's key. Returns ([pos per line], [why per line], [kind per line])."""
    n = len(cpt_dos)
    if not nursing: return [feed_pos] * n, [""] * n, [""] * n
    hist = []
    for row in nf_history:
        try: hist.append((row[0], row[1], row[2] if len(row) > 2 else None))
        except Exception: continue
    for cpt, d in cpt_dos:
        if cpt in NF_VISIT: hist.append((cpt, d, None))   # the message's own visit lines count as history for each other
    out = []; why = []; kinds = []; by_day = {}
    for cpt, d in cpt_dos:
        if cpt in CCM:
            if seen_at_skilled_frequency(d, hist, here): p, w, k = feed_pos, "31 kept: the chart shows a hospital visit, a home / assisted-living visit, nursing visits in this CCM month that the rule reads as weekly, an admission or a new stay, or the resident's nursing visits in another building - for William", "ccm-skilled-month"
            else: p, w, k = "32", "32 by rule: CCM in a nursing building", "ccm"
        elif cpt in NF_VISIT:
            k, gap = nf_visit_kind(cpt, d, hist, here); p, text = NF_KINDS[k]; w = text % gap if "%d" in text else text
            by_day[d] = "31" if "31" in (p, by_day.get(d)) else p     # two visit lines on one day: any 31 keeps the day at 31
        else: p, w, k = None, "", ""
        out.append(p); why.append(w); kinds.append(k)
    for i, (cpt, d) in enumerate(cpt_dos):
        if out[i] is None:
            if d in by_day: out[i] = by_day[d]; why[i] = "same place of service as the visit line of that day"; kinds[i] = "with-visit"
            else: out[i] = feed_pos
    return out, why, kinds
def _line(charge_id, pcode=None, code=None, seen=None):
    """ONE read of one charge's own detail in AdvancedMD -> (state, what):
      'billed'   the charge is live and listed as billed to insurance; what = the dates
      'open'     live and never billed (when pcode is given: and it shows that procedure)
      'void'     ONLY when that charge itself says void="1"
      'unknown'  everything else - the charge is not in the answer, it shows no procedure or another one (pcode given), the detail's list of
                 procedures names that procedure with another code text than `code`, or the read failed; what = [the reason in words].
                 Unknown is never an outcome: the caller waits.
    THE CODE TEXT (11/10/2026, second Medicare review): the charge detail lists every procedure id it uses with its code text
    (proccodelist/proccode id= code=, the way dx_primary_fix reads it). When `code` is given and that list names the charge's procedure,
    the text must be `code` (1123F for pcode65441) - otherwise AdvancedMD's id is not the code the practice means. seen = a dict the
    caller passes: it receives 'text' (the code text read; '' when the list does not name the procedure) and 'wrong' (a text that is not `code`)."""
    cid = re.sub(r"\D", "", str(charge_id or ""))
    if not cid: return "unknown", ["no charge number is recorded"]
    try: root = ET.fromstring(resave.detail(cid))
    except Exception as e: return "unknown", ["the read failed (%s)" % type(e).__name__]
    for c in root.iter("charge"):
        if re.sub(r"\D", "", c.get("id") or "") != cid: continue
        if pcode and c.get("proccode") and c.get("proccode") != pcode: return "unknown", ["AdvancedMD shows another procedure for it (%s)" % c.get("proccode")]
        if code and c.get("proccode"):
            txt = next(((p.get("code") or "").strip() for p in root.iter("proccode") if p.get("id") == c.get("proccode") and (p.get("code") or "").strip()), "")
            if isinstance(seen, dict): seen["text"] = txt
            if txt and txt.upper() != str(code).upper():
                if isinstance(seen, dict): seen["wrong"] = txt
                return "unknown", ["AdvancedMD stores procedure id %s as %s, not %s" % (c.get("proccode"), txt, code)]
        if c.get("void") == "1": return "void", []
        if pcode and not c.get("proccode"): return "unknown", ["AdvancedMD shows no procedure for it"]
        out = [b.get("billeddate") for b in c.findall("insbilllist/insbill") if b.get("billeddate")]
        if not out and c.get("insbilled") == "1" and (c.get("datebilled") or "").strip(): out = [c.get("datebilled").strip()[:10]]
        return ("billed", out) if out else ("open", [])
    return "unknown", ["it is not in AdvancedMD's answer"]
def _payments(charge_id):
    """MEDICARE'S OWN ANSWER (11/10/2026): the payment lines AdvancedMD lists on one charge - its own detail, charge/paymentlist/payment
    (amount, carrierfid = the carrier's number without "car", date, void ...) - as a list of attribute dicts. Reason and remark codes are
    not in this answer. Raises when the detail cannot be read or does not hold the charge (the caller says so and reads it again next run)."""
    cid = re.sub(r"\D", "", str(charge_id or ""))
    if not cid: raise ValueError("no charge number is recorded")
    for c in ET.fromstring(resave.detail(cid)).iter("charge"):
        if re.sub(r"\D", "", c.get("id") or "") == cid: return [dict(p.attrib) for p in c.iter("payment")]
    raise ValueError("the charge is not in AdvancedMD's answer")
def answer_charges(r):
    """Every charge AdvancedMD's answer lists, in its order: [(charge number, procedure id, amount, place of service)], '' where the answer
    does not carry a value."""
    out = []
    for m in re.finditer(r"<charge\b([^>]*)>", r or ""):
        a = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
        if re.match(r"charge\d+$", a.get("id") or ""): out.append((a["id"], a.get("proccode") or "", a.get("fee") or "", a.get("pos") or ""))
    return out
def quality_in_answer(ans, n_codes, fee):
    """Which of the answer's charges is the quality line (its index), or None when the answer does not hold it: by its procedure; else the ONE
    charge whose amount is the line's amount ($0.00 or $0.01 - no visit code has such a fee); else, when the answer names no procedure at
    all and lists more charges than the message has codes, the last one."""
    by = [i for i, c in enumerate(ans) if c[1] == QUALITY_PCODE]
    if by: return by[0]
    def money(x):
        try: return round(float(x), 2)
        except Exception: return None
    f = money(fee); same = [i for i, c in enumerate(ans) if c[2] != "" and money(c[2]) == f]
    if f is not None and len(same) == 1: return same[0]
    return len(ans) - 1 if (len(ans) > n_codes and not any(c[1] for c in ans)) else None
def lines_in_answer(ans, n_codes, fee):
    """For a visit sent with the 1123F line AND the M0004 line: (index of the 1123F charge, index of the M0004 charge) in AdvancedMD's answer, None
    where the answer does not hold one. By their procedure ids when the answer names procedures; else the TWO charges whose amount is the lines' amount
    (no visit code has such a fee), the first of them the 1123F line - the order sent; ONE charge at that amount = one of the two was not stored and
    which one is not known: None, None; else, when the answer names no procedure at all and lists two charges more than the message has codes, the
    LAST two in the order sent. A line found by amount or place may be the other one: the first read of the M0004 line in a later run checks its
    procedure and corrects that (mvp_state). Anything else: None, None (not shown stored)."""
    if any(c[1] for c in ans):
        return next((i for i, c in enumerate(ans) if c[1] == QUALITY_PCODE), None), next((i for i, c in enumerate(ans) if c[1] == MVP_PCODE), None)
    def money(x):
        try: return round(float(x), 2)
        except Exception: return None
    f = money(fee); same = [i for i, c in enumerate(ans) if c[2] != "" and money(c[2]) == f]
    if f is not None and len(same) == 2: return same[0], same[1]
    if not same and len(ans) == n_codes + 2: return len(ans) - 2, len(ans) - 1
    return None, None
def chart_lines_now(pid):
    """(code, DOS) of every live charge on the chart right now - one read of the chart's history, the same lines chart_ctx calls live."""
    out = set()
    for c in txh.fetch(re.sub(r"\D", "", pid)).iter("charge"):
        a = c.attrib
        if a.get("void") == "1" or (a.get("fee") or "").startswith("-"): continue
        out.add((a.get("proccode"), a.get("dos")))
    return out
def quality_files(own_stamp):
    """What the quality code reads from the registers folder besides the import registers - one pass at the start of a run, nothing in AdvancedMD:
      verify       chart -> (decision, lead payer code): its NEWEST insurance check of an EARLIER batch (quality_due, point 5)
      checks       batch stamp -> {chart: (decision, lead payer code)}: every insurance check (a line proves the code only when the check of
                   its own batch did not hold the chart or name another payer)
      check_holds  visit number -> [(register, [the hold's words])]: the visits of charts the insurance check put on HOLD
      held         visit number -> [(register, the Claim Inspector's words, True when the inspector step itself marked the line as named)]
      removed      batch stamp -> [(register, entry)]: the quality lines the inspector step or the insurance check TOOK OFF a held visit by
                   themselves (William 11/10/2026: a reporting line never holds a visit) - the "quality_removed" entries {visit, pid, charge,
                   fee, why, void_ok, released, at}: top level in an inspector register, inside the chart's entry in an insurance-check register
      exceptions   the charts William has taken out (QUALITY_EXCEPTIONS)
      n620         True when QUALITY_N620 exists: Medicare's own answer to a 1123F line was seen on a remittance
      problems     files that are there but cannot be read - then NO line is added in this run (a patient William took out, a hold or
                   another payer could be hidden in them)"""
    import glob as _g
    out = {"verify": {}, "checks": {}, "check_holds": {}, "held": {}, "removed": {}, "exceptions": set(), "n620": _os.path.exists(QUALITY_N620), "problems": []}
    def removed(f, st, entries):      # entry by entry: an odd entry is passed over
        for e in (entries if isinstance(entries, list) else []):
            if isinstance(e, dict) and isinstance(e.get("charge"), str) and re.sub(r"\D", "", e["charge"]): out["removed"].setdefault(st, []).append((_os.path.basename(f), e))
    num = lambda x: re.sub(r"\D", "", str(x or "")); stamp_of = lambda f, kind: re.sub(r"^feed_%s_|\.json$" % kind, "", _os.path.basename(f))
    for f in sorted(_g.glob("registers/feed_verify_*.json"), key=lambda f: stamp_of(f, "verify")):
        try:
            st = stamp_of(f, "verify"); d = json.load(open(f))
            if not isinstance(d, dict): raise ValueError("not an object")
            for chart, v in d.items():
                if not isinstance(v, dict): continue
                lead = v.get("lead") if isinstance(v.get("lead"), dict) else {}; row = (str(v.get("decision") or ""), str(lead.get("code") or ""))
                out["checks"].setdefault(st, {})[chart] = row
                if st != own_stamp and st < own_stamp: out["verify"][chart] = row      # sorted oldest first: the newest earlier check stays
                removed(f, st, v.get("quality_removed"))
                if row[0] == "HOLD":
                    words = [str(x) for k in ("hold", "fixes") for x in (v.get(k) if isinstance(v.get(k), list) else [])]
                    for vis in (v.get("visits") if isinstance(v.get("visits"), list) else []):
                        if num(vis): out["check_holds"].setdefault(num(vis), []).append((_os.path.basename(f), words))
        except Exception as e: out["problems"].append("%s (%s)" % (f, type(e).__name__))
    for f in sorted(_g.glob("registers/feed_inspector_*.json")):
        try:
            d = json.load(open(f))
            if not isinstance(d, dict): raise ValueError("not an object")
            for h in (d.get("held") if isinstance(d.get("held"), list) else []):
                if isinstance(h, dict) and num(h.get("visit")): out["held"].setdefault(num(h.get("visit")), []).append((_os.path.basename(f), str(h.get("why") or ""), h.get("names_line") is True))
            removed(f, stamp_of(f, "inspector"), d.get("quality_removed"))
        except Exception as e: out["problems"].append("%s (%s)" % (f, type(e).__name__))
    try:
        if _os.path.exists(QUALITY_EXCEPTIONS):
            x = json.load(open(QUALITY_EXCEPTIONS)); ids = list(x.keys()) if isinstance(x, dict) else x
            if not isinstance(ids, list): raise ValueError("neither an object nor a list")
            for i in ids:
                if isinstance(i, str) and i.startswith("_"): continue          # a key such as "_note" is a comment, not a chart
                m = re.match(r"^(?:pat)?(\d+)$", str(i).strip()) if isinstance(i, (str, int)) and not isinstance(i, bool) else None
                if not m: raise ValueError("an entry that is not a chart id")
                out["exceptions"].add("pat" + m.group(1))
    except Exception as e: out["exceptions"] = set(); out["problems"].append("%s (%s)" % (QUALITY_EXCEPTIONS, type(e).__name__))
    return out
def quality_state(regs, look, reset=False, stop=False, files=None, day=None):
    """Fill QUALITY from the import registers, oldest first (main() passes this stamp's own register too). regs = [(file name, register)];
    files = what quality_files read. look=False (a dry run) reads nothing in AdvancedMD: a line that is not decided then simply means
    'wait'. reset / stop = William's switches. day = the calendar day of this run (run_day() when not given). See the PILOT comment above
    for every state. Nothing here can stop the import: the caller turns any error into 'no line this run'."""
    day = day or run_day(); today = _fmt_day(day)
    q = _quality_fresh(); notes = []; files = files if isinstance(files, dict) else {}
    _d = lambda k: files.get(k) if isinstance(files.get(k), dict) else {}
    held = _d("held"); chold = _d("check_holds"); checks = _d("checks"); n620 = bool(files.get("n620")); rem = {k: list(v) for k, v in _d("removed").items() if isinstance(v, list)}
    S = {"fee": "0.00", "off": "", "proven": set(), "proof": None, "hist": None, "znb": False, "count": 0, "n": 1, "answer": None, "pwait": None, "wrong": "", "unread_prev": []}
    billed = set(); void = set(); left = set(); refused = set(); lines = []; era = [0]      # lines: every quality line of the registers, oldest first; era: where the lines entered since the last restart begin
    texts = set(); billed_on = {}; lseen = {}; lon = {}; late = {}; late_rows = []      # carried by the gates: code text read as 1123F, billed dates, when a visit was first seen billed, left-off dates, lines billed late
    base = lambda name: _os.path.basename(str(name)); num = lambda x: re.sub(r"\D", "", str(x or ""))
    def restart():      # William's word: a new round at $0.00. What was switched off, refused in a row or proven before no longer counts; a line that exists still counts once a year
        S.update(fee="0.00", off="", proof=None, hist=None, znb=False, count=0, pwait=None, wrong=""); S["proven"] = set(); S["n"] += 1; era[0] = len(lines)
    def refusal(f, what, name):      # one more refusal (or a visit stored without its line) at amount f: before proof ONE is enough, after proof TWO in a row
        if f != S["fee"] or S["off"]: return
        S["count"] += 1
        if S["count"] < (2 if S["fee"] in S["proven"] else 1): return
        if S["fee"] == "0.00":
            S.update(fee="0.01", count=0); S["n"] += 1; notes.append("AdvancedMD %s at $0.00 (%s) - new lines carry $0.01, a new round" % (what, base(name)))
        else: S["off"] = "AdvancedMD %s with a one-cent charge too (%s) - William looks" % (what, base(name))
    def created_row(name, r, gconf):
        qc = r.get("quality_codes") if isinstance(r.get("quality_codes"), list) else []; qid = r.get("quality_charge") if isinstance(r.get("quality_charge"), str) else ""
        pid = r.get("pid") if isinstance(r.get("pid"), str) else ""; d = str(r.get("quality_dos") or r.get("dos") or "")
        if r.get("quality_refused") or r.get("quality_not_stored"):
            f = str(r.get("quality_refused_fee") or r.get("quality_not_stored") or r.get("quality_fee") or "0.00")
            if r.get("quality_refused") and pid and len(d) >= 4: refused.add((pid, d[-4:]))      # the patient of a refused visit gets no second try that year
            refusal(f, "refused a visit that carried the code" if r.get("quality_refused") else "stored a visit without its quality line", name)
        elif qc and qid:
            f = str(r.get("quality_fee") or "0.00"); ch = r.get("charges") if isinstance(r.get("charges"), list) else []
            lines.append({"reg": base(name), "chart": pid, "visit": r.get("visit") if isinstance(r.get("visit"), str) else "", "charge": qid, "fee": f, "dos": d,
                          "own": next((c for c in ch if isinstance(c, str) and c != qid), ""),      # the visit's own charge = the first recorded charge that is not the quality line
                          "feed": r.get("feed_id") if isinstance(r.get("feed_id"), str) else "",    # the feed's own patient id: once per patient also by it (13.6)
                          "mvp": r.get("mvp_charge") if (r.get("mvp_codes") and isinstance(r.get("mvp_charge"), str)) else "",      # the same visit's M0004 line (the option code's own ledger reads it)
                          "pilot": gconf != f})                                                       # entered while the code was not proven at that amount: read until it is decided
            if f == S["fee"]: S["count"] = 0                                                          # a stored line clears the count of refusals in a row
    def removal(regname, e):
        """A quality line the inspector step or the insurance check TOOK OFF a held visit (William 11/10/2026: the routine takes the line off
        by itself, so that a reporting line never holds a visit). Void and final - the routine's doing, not a person's. released (the visit
        went through without it: the line was the cause) = ONE refusal, and that patient gets no second try this year; not released (held
        anyway) = nothing counts, the place in the round is free and the patient is due again. A void that failed = the visit is held WITH
        its line: OFF until William restarts it. An entry for the visit's M0004 line (code M0004) is the option code's own business (mvp_state);
        an entry whose charge the row recorded as its M0004 line is this row's 1123F line (the answer named no procedures, and the two were swapped)."""
        if str(e.get("code") or "").strip().upper() == MVP_CODE: return
        L = next((L for L in reversed(lines) if num(L["charge"]) == num(e.get("charge"))), None) or next((L for L in reversed(lines) if L.get("mvp") and num(L["mvp"]) == num(e.get("charge"))), None)
        if L is None: notes.append("%s names quality charge %s, which no import register row carries - passed over" % (regname, e.get("charge"))); return
        L["removed"] = dict(e, register=regname)
        if e.get("void_ok") is not True:
            S["off"] = S["off"] or "the Claim Inspector holds visit %s and the routine could not take its quality line off (%s: \"%s\") - William looks" % (L["visit"], regname, str(e.get("why") or "")[:140])
            return
        void.add(L["charge"])
        if e.get("released") is not True and (e.get("still_named") is True or e.get("resave_ok") is False):
            # the line is gone, but the visit is still listed for the edit about it: the re-save after the void failed, or AdvancedMD did not inspect
            # the visit again (confirm review NH2-2). That is not the visit's own reason - OFF until William has looked; one re-save should release it
            S["off"] = S["off"] or "the routine took the quality line off held visit %s, but the visit is still listed for the edit about the line (%s: \"%s\") - William looks; one re-save of the visit should release it" % (L["visit"], regname, str(e.get("why") or "")[:140])
            return
        if e.get("released") is True:
            if len(L["dos"]) >= 4: refused.add((L["chart"], L["dos"][-4:]))
            refusal(L["fee"], "held visit %s because of its quality line (the routine took the line off and the visit went through)" % L["visit"], regname)
    def failed_row(name, r, _gconf):
        info = r.get("info") if isinstance(r.get("info"), dict) else {}; pid = r.get("pid") if isinstance(r.get("pid"), str) else ""
        d = str(info.get("quality_dos") or info.get("dos") or ""); who = "chart %s, visit %s, %s" % (pid or "?", r.get("empty_visit") or "?", base(name))
        if not (r.get("quality_sent") or r.get("quality_unknown") or (r.get("stored") and "quality_tried" in info)): return
        if pid and len(d) >= 4: refused.add((pid, d[-4:]))
        if r.get("quality_sent"): refusal(str(r.get("quality_sent")), "refused a visit that carried the code", name)      # refused with the line, and the send without it failed: counted like a refusal
        elif r.get("quality_unknown"):      # the call that carried the line ended in an error - or the run was cut while it was out (the provisional row main() writes before that call)
            S["off"] = S["off"] or ("the run was cut while a call that carried the quality line was out; nobody knows whether AdvancedMD kept that visit and its line - William looks (%s)" if r.get("provisional")
                                    else "a call that carried the quality line ended in an error; nobody knows whether AdvancedMD kept that visit - William looks (%s)") % who
        else:                               # a fault, and the chart shows the visit or could not be read: the visit was not sent again
            st = r.get("stored") if isinstance(r.get("stored"), list) else [r.get("stored")]
            S["off"] = S["off"] or (("AdvancedMD answered a fault to a visit that carried the quality line and the chart could not be read afterwards - William looks (%s)"
                                     if any(isinstance(x, str) and x.startswith("chart not read") for x in st) else "AdvancedMD answered a fault but kept the visit - William looks (%s)") % who)
    def rows(fn, name, rs, gconf):          # row by row: an odd row is passed over, the rows after it are still read
        for r in rs:
            try:
                if isinstance(r, dict): fn(name, r, gconf)
            except Exception: continue
    for name, reg in sorted(regs, key=lambda x: str(x[0])):
        try:
            if not isinstance(reg, dict): continue
            g = reg.get("quality_gate") if isinstance(reg.get("quality_gate"), dict) else {}
            cr = reg.get("created") if isinstance(reg.get("created"), list) else []; fl = reg.get("failed") if isinstance(reg.get("failed"), list) else []
            gconf = g.get("fee") if (g.get("confirmed") is True and g.get("fee") in ("0.00", "0.01")) else None
            cut = [0, 0]
            if g.get("reset") is True:      # the pilot was started again in that run. Rows an earlier start under the same stamp had already written stay in the old round
                ra = g.get("reset_after")
                if isinstance(ra, list) and len(ra) == 2 and all(isinstance(x, int) and not isinstance(x, bool) and x >= 0 for x in ra): cut = ra
                rows(created_row, name, cr[:cut[0]], None); rows(failed_row, name, fl[:cut[1]], None); restart()
            if g.get("fee") == "0.01" and S["fee"] == "0.00": S.update(fee="0.01", count=0); S["n"] += 1      # once at one cent, it stays there until a restart
            if g.get("zero_not_billed") is True and S["fee"] == "0.01": S["znb"] = True
            if isinstance(g.get("round"), dict) and isinstance(g["round"].get("n"), int) and not isinstance(g["round"].get("n"), bool): S["n"] = max(S["n"], g["round"]["n"])
            if isinstance(g.get("off_until_reset"), str) and g["off_until_reset"].strip(): S["off"] = g["off_until_reset"].strip()
            if gconf is not None and gconf == S["fee"]:
                S["proven"].add(gconf); S["proof"] = g.get("proof") if isinstance(g.get("proof"), dict) else S["proof"]
                if isinstance(g.get("history_shows_line"), bool): S["hist"] = g["history_shows_line"]
            for k, s in (("billed_lines", billed), ("void_lines", void), ("left_off_lines", left)):      # what earlier runs read as final is never read again
                s.update(x for x in (g.get(k) if isinstance(g.get(k), list) else []) if isinstance(x, str))
            for x in (g.get("refused_charts") if isinstance(g.get("refused_charts"), list) else []):
                if isinstance(x, list) and len(x) >= 2 and isinstance(x[0], str) and isinstance(x[1], str): refused.add((x[0], x[1]))
            for k, d_ in (("billed_on", billed_on), ("left_off_seen", lseen), ("left_off_on", lon), ("late_billed", late)):
                if isinstance(g.get(k), dict): d_.update((a, b) for a, b in g[k].items() if isinstance(a, str) and isinstance(b, (str, dict)))
            texts.update(x for x in (g.get("code_text_lines") if isinstance(g.get("code_text_lines"), list) else []) if isinstance(x, str))
            if S["answer"] is None and isinstance(g.get("medicare_answer"), dict) and g["medicare_answer"].get("charge"): S["answer"] = dict(g["medicare_answer"])      # the first answer found stays
            if "proof_wait" in g: S["pwait"] = dict(g["proof_wait"]) if isinstance(g.get("proof_wait"), dict) else None
            if isinstance(g.get("wrong_code_text"), str) and g["wrong_code_text"]: S["wrong"] = g["wrong_code_text"]
            if g: S["unread_prev"] = [x for x in (g.get("unread") if isinstance(g.get("unread"), list) else []) if isinstance(x, str)]      # what the run before this one could not read
            rows(created_row, name, cr[cut[0]:], gconf); rows(failed_row, name, fl[cut[1]:], gconf)
            for regname, e in rem.pop(re.sub(r"^feed_import_|\.json$", "", base(name)), []):      # the lines that batch's inspector step / insurance check took off - after its own rows, in time order
                try: removal(regname, e)
                except Exception: continue
        except Exception: continue
    for st in sorted(rem):      # removals of a batch whose import register is not here: still void, after everything else
        for regname, e in rem[st]:
            try: removal(regname, e)
            except Exception: continue
    if stop:
        if S["off"]: notes.append("QUALITY_CODE=stop was given; the code was already off")
        else: S["off"] = "stopped on William's word (QUALITY_CODE=stop) - off until he says to start again"
    if reset:
        if S["off"]: restart(); q["reset"] = True; notes.append("the pilot was started again in this run (QUALITY_CODE=reset)")
        else: q["loud"] = "NOTHING TO RESTART - QUALITY_CODE=reset was ignored (the code is not switched off; take the switch out of the routine)"; notes.append(q["loud"])
    # HELD VISITS: a visit that carries the line and was entered since the last restart. Since 11/10/2026 the inspector step takes the line
    # off a held visit by itself (removal above): such a hold is the visit's own business, and the rule below is left for a line that could
    # NOT be taken off (no removal recorded - an older inspector copy, or a row without its quality charge)
    eraL = lines[era[0]:]; proven = S["fee"] in S["proven"]
    for L in eraL:
        L["held"] = False
        for regname, why, marked in (held.get(num(L["visit"])) or ()) if num(L["visit"]) else ():
            L["held"] = True
            if L.get("removed"): continue
            if not S["off"] and (not proven or marked or (names_lines(why, L["charge"], L["mvp"])[0] if L.get("mvp") else names_line(why, L["charge"]))):      # before proof ANY hold; after proof only a hold whose words name the line (beside an M0004 line: words that name only M0004 are M0004's business)
                S["off"] = "the Claim Inspector holds visit %s, which carries the quality line (%s: \"%s\") - William looks" % (L["visit"], regname, why[:140])
        for regname, words in (chold.get(num(L["visit"])) or ()) if num(L["visit"]) else ():
            L["held"] = True                # any insurance-check HOLD: this visit can never be the proof
            for why in words:
                named = set(re.findall(r"vst\d+", why))
                if not S["off"] and re.search(r"insorder not applied|resave FAULT|detail read mismatch", why) and (not named or L["visit"] in named):
                    S["off"] = "the insurance check could not set the order of visit %s, which carries the quality line (%s: \"%s\") - William looks" % (L["visit"], regname, why[:140])
    # a line has ONE state, its newest reading: an older gate still lists a line as left off that a later run read billed (13.1b) or void - billed and void win
    left -= billed; left -= void
    final = lambda L: "billed" if L["charge"] in billed else "void" if L["charge"] in void else "left" if L["charge"] in left else ""
    looks = [QUALITY_LOOKS]
    def read(L):
        """One read of a line and, where the outcome needs it, of its visit's own first charge. A final outcome goes into billed / left / void."""
        looks[0] -= 1; L["seen"] = True; sn = {}
        st, what = _line(L["charge"], QUALITY_PCODE, QUALITY_CODE, sn)
        if sn.get("text", "").upper() == QUALITY_CODE.upper(): texts.add(L["charge"])
        if sn.get("wrong"):      # AdvancedMD's id for the line is not 1123F: nothing is built on it
            S["wrong"] = sn["wrong"]; S["off"] = S["off"] or "AdvancedMD stores procedure id %s as %s, not %s - William looks" % (QUALITY_PCODE, sn["wrong"], QUALITY_CODE); return
        if st == "billed": billed.add(L["charge"]); billed_on[L["charge"]] = what[0]; return
        if st == "unknown": notes.append("the quality line of visit %s (%s) is not decided: %s - the pilot waits; William looks if this stays" % (L["visit"], L["charge"], what[0])); return
        own, owhat = _line(L["own"]) if L["own"] else ("none", [])
        if st == "open":
            if own == "billed":      # LEFT OFF needs time: a line can be billed a day after its visit (second state-machine review). The newest billed date of the visit's own charge counts; when it cannot be read, the day this import first saw the charge billed
                bday = max([d_ for d_ in map(_any_day, owhat) if d_] or [None])
                if bday is None: lseen.setdefault(L["charge"], today); bday = _mdy_day(lseen[L["charge"]]) or day
                if (day - bday).days >= QUALITY_LEFT_OFF_DAYS:
                    left.add(L["charge"]); lon[L["charge"]] = {"on": today, "billed": _fmt_day(bday)}
                    notes.append("visit %s was billed %s without its $%s quality line, and the line is still not billed %d days later - left off the claim" % (L["visit"], _fmt_day(bday), L["fee"], (day - bday).days))
                else: notes.append("visit %s was billed %s; its $%s quality line is not billed yet - not decided before %s (a line can be billed a day after its visit)" % (L["visit"], _fmt_day(bday), L["fee"], _fmt_day(bday + datetime.timedelta(days=QUALITY_LEFT_OFF_DAYS))))
            elif own == "void": notes.append("the own charge of visit %s is void while its quality line is still live - not decided; William looks" % L["visit"])
        elif own in ("billed", "open"): void.add(L["charge"]); L["taken"] = True; notes.append("the quality line of visit %s was taken off the visit (void) while the visit itself is still there" % L["visit"])
        elif own in ("void", "none"): void.add(L["charge"]); notes.append("visit %s is no longer on the chart (void), its quality line with it" % L["visit"])
        else: notes.append("the quality line of visit %s is void, but the visit's own charge is not decided: %s" % (L["visit"], owhat[0]))
    def proof_ok(L):      # never held, and the insurance check of the line's own batch did not hold the chart or name another payer (no check of that batch is accepted)
        c = (checks.get(re.sub(r"^feed_import_|\.json$", "", L["reg"])) or {}).get(L["chart"])
        return not L.get("held") and (c is None or (c[0] == "RELEASE" and c[1] == MEDICARE_LEAD))
    wait = False; pending = []
    for _pass in (0, 1):      # a second pass only when the amount moved to one cent in this run
        fee = S["fee"]; rnd = [L for L in eraL if L["fee"] == fee]
        if S["off"] or fee in S["proven"]: break
        for L in rnd:         # the lines of the round that are not decided, oldest first
            if not final(L) and look and looks[0] > 0: read(L)
        if S["off"]: break    # a read showed that AdvancedMD's id is not 1123F
        taken = [L for L in rnd if L.get("taken")]; good = [L for L in rnd if final(L) == "billed" and proof_ok(L)]
        lo = [L for L in rnd if final(L) == "left"]; undecided = [L for L in rnd if not final(L)]; nonvoid = [L for L in rnd if final(L) != "void"]
        for L in rnd:
            if final(L) == "billed" and not proof_ok(L): notes.append("the quality line of visit %s is billed but cannot be the proof: the visit was held, or the insurance check of its batch did not show Medicare first" % L["visit"])
        if taken:
            S["off"] = "%d earlier quality line(s) were taken off their visits (void) while the visits are still there (%s) - William looks" % (len(taken), ", ".join(L["visit"] for L in taken[:6]))
        elif good:      # THE CODE TEXT: a billed line proves the code only when AdvancedMD shows it stored 1123F - its charge detail named the code text, or the chart's history shows a live 1123F on that date
            L = next((G for G in good if G["charge"] in texts), None); by_history = False
            if L is None and look:
                for G in good:
                    try: shows = (QUALITY_CODE, G["dos"]) in chart_lines_now(G["chart"])
                    except Exception as e: notes.append("the history of chart %s could not be read (%s): whether it shows 1123F is not known" % (G["chart"], type(e).__name__)); continue
                    if shows: L = G; by_history = True; break
            if L is None:      # billed, but nothing shows the code text yet: not the proof - the round waits (the report says so at the top after three days)
                wait = True; pending = good + undecided
                if not (isinstance(S["pwait"], dict) and S["pwait"].get("since")): S["pwait"] = {"since": today}
                S["pwait"].update(visit=good[0]["visit"], charge=good[0]["charge"])
                notes.append("the quality line of visit %s is billed, but neither its charge detail nor the chart's history shows the code text %s - not the proof yet; the pilot waits" % (good[0]["visit"], QUALITY_CODE))
            else:
                S["proven"].add(fee); S["hist"] = True if by_history else None; S["pwait"] = None
                S["proof"] = {"register": L["reg"], "chart": L["chart"], "visit": L["visit"], "charge": L["charge"], "billed": billed_on.get(L["charge"]) or "read in an earlier run", "fee": fee}
                if look and not by_history:      # ONE read of that chart's history: does it list a no-charge line at all? If not, a 1123F / 1124F entered by hand is invisible to the import
                    try: S["hist"] = (QUALITY_CODE, L["dos"]) in chart_lines_now(L["chart"])
                    except Exception as e: notes.append("the history of chart %s could not be read after the proof (%s): whether it lists a no-charge line is not known" % (L["chart"], type(e).__name__))
                    if S["hist"] is False: notes.append("the history of chart %s does NOT list the proven quality line: a 1123F or 1124F entered by hand is invisible to the import - William names such patients in %s" % (L["chart"], QUALITY_EXCEPTIONS))
        elif lo and not any(final(L) == "billed" for L in rnd):
            if fee == "0.00":
                S.update(fee="0.01", znb=True, count=0); S["n"] += 1
                notes.append("new lines carry $0.01: AdvancedMD left the $0.00 line of visit %s off its claim and no $0.00 line of the round is billed" % lo[0]["visit"]); continue
            S["off"] = "AdvancedMD billed visit %s (%s) without its one-cent quality line too - William looks" % (lo[0]["visit"], (lon.get(lo[0]["charge"]) or {}).get("billed") or "read in an earlier run")
        elif undecided:
            wait = True; pending = undecided
            if not look: notes.append("dry run: %d earlier quality line(s) were not looked up - a live run reads them" % len(undecided))
        elif min(QUALITY_PILOT - len(nonvoid), 2 * QUALITY_PILOT - len(rnd)) <= 0:      # the round is full, every line is decided, nothing is proven
            S["off"] = ("the pilot's lines keep being voided (%d lines in this round, none billed) - William looks" % len(rnd)) if not nonvoid else (
                        "the pilot round is full (%d lines) and none of them can be the proof - William looks" % len(rnd))
        break
    cur = set(id(L) for L in eraL if L["fee"] == S["fee"])
    for i, L in enumerate(lines):      # then the other lines that were entered before proof and are not decided yet, oldest first (so every $0.00 line is read in the end) - the
        # proven round's own undecided lines too: since a line is called LEFT OFF only three days after its visit was billed, a round can be proven while one of its lines waits
        if S["off"] or not look or looks[0] <= 0: break
        if (id(L) in cur and S["fee"] not in S["proven"]) or final(L) or not L["pilot"] or L.get("seen"): continue
        read(L)
        if L.get("taken") and i >= era[0] and S["fee"] not in S["proven"]:
            S["off"] = "the quality line of visit %s was taken off the visit (void) while the visit is still there - William looks" % L["visit"]
    for L in lines:      # a line called LEFT OFF is read again, after everything above, until QUALITY_LEFT_OFF_REREAD days after its visit was billed: billed after all = it counts as billed
        if not look or looks[0] <= 0: break
        w = lon.get(L["charge"]) if isinstance(lon.get(L["charge"]), dict) else {}; b = _mdy_day(str(w.get("billed") or ""))
        if final(L) != "left" or L.get("seen") or b is None or (day - b).days > QUALITY_LEFT_OFF_REREAD: continue
        looks[0] -= 1; L["seen"] = True; sn = {}
        st, what = _line(L["charge"], QUALITY_PCODE, QUALITY_CODE, sn)
        if sn.get("text", "").upper() == QUALITY_CODE.upper(): texts.add(L["charge"])
        if sn.get("wrong"): S["wrong"] = sn["wrong"]; S["off"] = S["off"] or "AdvancedMD stores procedure id %s as %s, not %s - William looks" % (QUALITY_PCODE, sn["wrong"], QUALITY_CODE); continue
        if st == "billed":      # it went out after all: its patient counts as coded; nothing else changes (the amount stays where it is)
            left.discard(L["charge"]); billed.add(L["charge"]); billed_on[L["charge"]] = what[0]; late[L["charge"]] = today
            again = [M["visit"] for M in lines if M is not L and M["chart"] == L["chart"] and M["dos"][-4:] == L["dos"][-4:] and final(M) == "billed"]      # "two billed lines" only when the later one IS billed
            late_rows.append([L["chart"], L["visit"], L["charge"], str(w.get("on") or ""), again[0] if again else "", L["dos"][-4:]])
            notes.append("the quality line of visit %s, read as left off its claim on %s, was billed later (%s): %s counts as coded" % (L["visit"], w.get("on") or "?", what[0], L["chart"]))
        elif st == "void": left.discard(L["charge"]); void.add(L["charge"]); notes.append("the quality line of visit %s, read as left off its claim, is void now" % L["visit"])
    fee = S["fee"]; proven = fee in S["proven"]; rnd = [L for L in eraL if L["fee"] == fee]; nonvoid = [L for L in rnd if final(L) != "void"]
    bl = [L for L in lines if final(L) == "billed"]; mwait = None
    if proven and S["answer"] is None:      # MEDICARE'S OWN ANSWER: a payment line from Medicare Part B posted on a billed 1123F line (lines billed QUALITY_ANSWER_AGE days ago or longer first)
        age = lambda L: (lambda d_: (0 if d_ is None or (day - d_).days >= QUALITY_ANSWER_AGE else 1, d_ or datetime.date.min, L["charge"]))(_any_day(billed_on.get(L["charge"])))
        for L in (sorted(bl, key=age)[:QUALITY_LOOKS] if look else []):
            try: pays = _payments(L["charge"])
            except Exception as e: notes.append("Medicare's answer: the payment lines of the quality line of visit %s could not be read (%s)" % (L["visit"], type(e).__name__)); continue
            hit = next((p for p in pays if str(p.get("void") or "0") != "1" and re.sub(r"\D", "", str(p.get("carrierfid") or "")) == re.sub(r"\D", "", MEDICARE_B)), None)
            if hit:
                S["answer"] = {"charge": L["charge"], "visit": L["visit"], "date": str(hit.get("date") or ""), "amount": str(hit.get("amount") or ""), "register": L["reg"]}
                notes.append("Medicare's remittance shows the 1123F line on visit %s: a Medicare payment line of $%s posted %s" % (L["visit"], S["answer"]["amount"], S["answer"]["date"])); break
        if S["answer"] is None:
            ds = [d_ for d_ in (_any_day(billed_on.get(L["charge"])) for L in bl) if d_]
            mwait = {"lines": len(bl), "oldest": _fmt_day(min(ds)) if ds else "", "days": (day - min(ds)).days if ds else None}
    if S["off"]: wait = False; pending = []
    for L in lines:      # once per patient per year - from the registers, whatever the chart history shows; by the chart and by the feed's own patient id
        if not L["chart"] or len(L["dos"]) < 4 or final(L) == "void": continue      # a void line was never reported: its patient is due again
        if final(L) == "left": q["dead"].add((L["chart"], QUALITY_CODE, L["dos"])); q["dead_rows"].append([L["chart"], L["visit"], L["charge"]])      # left off the claim: dead, its patient is due again
        else:
            q["done"].add((L["chart"], L["dos"][-4:]))
            if _feed_mark(L.get("feed")): q["done"].add((_feed_mark(L["feed"]), L["dos"][-4:]))
    q["done"] |= refused
    pw = dict(S["pwait"], days=(day - (_mdy_day(S["pwait"].get("since")) or day)).days) if (wait and not proven and isinstance(S["pwait"], dict)) else None
    q.update(billed_on={k: v for k, v in billed_on.items() if k in billed}, code_text_lines=sorted(texts), left_off_seen={k: v for k, v in lseen.items() if k not in billed and k not in void and k not in left},
             left_off_on={k: v for k, v in lon.items() if k in left}, late_billed=dict(late), late_rows=late_rows, wrong_code_text=S["wrong"], proof_wait=pw,
             medicare_answer=S["answer"] if proven else None, medicare_wait=mwait, unread_prev=list(S["unread_prev"]))
    q.update(fee=fee, confirmed=proven, off=S["off"], off_until_reset=S["off"], wait=wait, proof=S["proof"] if proven else None, notes=notes[:20], zero_not_billed=bool(S["znb"] and fee == "0.01"),
             budget=0 if (S["off"] or wait) else (None if (n620 or S["answer"]) else QUALITY_DAILY) if proven else max(0, min(QUALITY_PILOT - len(nonvoid), 2 * QUALITY_PILOT - len(rnd))),
             billed_lines=sorted(billed), void_lines=sorted(void), left_off_lines=sorted(left - billed - void), refused=refused, n620=n620, history_shows_line=S["hist"] if proven else None,
             pending=[L["visit"] for L in pending], pending_since=pending[0]["reg"] if pending else "",
             round={"n": S["n"], "fee": fee, "since": rnd[0]["reg"] if rnd else "", "lines": len(rnd), "void": len(rnd) - len(nonvoid), "open": len([L for L in rnd if not final(L)])})
    QUALITY.clear(); QUALITY.update(q)
def quality_gate(reg_name="", added=0):
    """What a run writes into its register as "quality_gate": where the code stands, for the next run and for the digest. off = why no line
    is added in THIS run; off_until_reset = the sentence of an OFF that only William's restart ends; round = the pilot round (n, amount,
    the register it began in, its lines, how many of them are void / not decided); budget = what this run was allowed to add (null = no cap)."""
    Q = QUALITY; rnd = dict(Q.get("round") or {})
    if added: rnd.update(lines=int(rnd.get("lines") or 0) + added, open=int(rnd.get("open") or 0) + (0 if Q["confirmed"] else added), since=rnd.get("since") or _os.path.basename(str(reg_name)))
    return {"code": QUALITY_CODE, "fee": Q["fee"], "confirmed": bool(Q["confirmed"]), "proof": Q.get("proof"), "zero_not_billed": bool(Q.get("zero_not_billed")),
            "off": Q["off"], "off_until_reset": Q.get("off_until_reset") or "", "wait": bool(Q.get("wait")), "pending": list(Q.get("pending") or []), "pending_since": Q.get("pending_since") or "",
            "billed_lines": list(Q.get("billed_lines") or []), "void_lines": list(Q.get("void_lines") or []), "left_off_lines": list(Q.get("left_off_lines") or []), "dead_zero_lines": list(Q.get("dead_rows") or []),
            "reset": bool(Q.get("reset")), "reset_after": Q.get("reset_after") if Q.get("reset") else None, "round": rnd, "budget": Q.get("budget"), "pilot_cap": None if Q["confirmed"] else QUALITY_PILOT,
            "n620": bool(Q.get("n620")), "history_shows_line": Q.get("history_shows_line"), "refused_charts": sorted([c, y] for c, y in (Q.get("refused") or ())),
            "not_renewed": {y: len(v) for y, v in sorted((Q.get("not_renewed") or {}).items())},
            # the ledger's dates (MM/DD/YYYY): billed_on = when each billed line was read billed; code_text_lines = lines whose charge detail named
            # the code text 1123F; left_off_seen = the day a visit's own charge was first seen billed when its billed date could not be read;
            # left_off_on = when a line was called left off and its visit's billed date (read again until 30 days after it); late_billed / late_rows =
            # left-off lines found billed later (late_rows: this run's, [chart, visit, charge, called left off on, a later line of that patient, year])
            "billed_on": dict(Q.get("billed_on") or {}), "code_text_lines": list(Q.get("code_text_lines") or []), "left_off_seen": dict(Q.get("left_off_seen") or {}),
            "left_off_on": dict(Q.get("left_off_on") or {}), "late_billed": dict(Q.get("late_billed") or {}), "late_rows": list(Q.get("late_rows") or []),
            "wrong_code_text": Q.get("wrong_code_text") or "", "proof_wait": Q.get("proof_wait"),      # proof_wait: a billed line whose code text nothing shows yet {since, visit, charge, days}
            "medicare_answer": Q.get("medicare_answer"), "medicare_wait": Q.get("medicare_wait"),         # Medicare's own answer {charge, visit, date, amount, register}; while none: {lines billed, oldest billed date, days}
            "quality_skipped_hospital": int(Q.get("skipped_hospital") or 0),                              # hospital visits that met every other condition: not coded in this version
            "unread": list(Q.get("unread") or []), "unread_prev": list(Q.get("unread_prev") or []),        # import registers of this year that this run / the run before could not read
            "notes": list(Q.get("notes") or [])}
def quality_log(n, dry):
    """The ONE line a run prints about the quality code (the runbook reads it by its start). It says 'pilot:' exactly while a pilot round is open."""
    Q = QUALITY
    words = ("off until William restarts it (one run with QUALITY_CODE=reset)" if Q.get("off_until_reset") else
             ("no cap (a quality line was seen billed)" if (Q.get("n620") or Q.get("medicare_answer")) else "at most %d a run (a quality line was seen billed; no Medicare payment line is posted yet on the billed lines the import reads - lines added after proof are not read back)" % QUALITY_DAILY) if Q["confirmed"] else
             "pilot: waiting for the outcome of %d earlier line(s) - none added" % len(Q.get("pending") or []) if Q.get("wait") else "pilot: at most %d visit(s) until one is seen billed" % QUALITY_PILOT)
    return "QUALITY 1123F: %s x%d visit(s), line amount $%s, %s%s%s" % ("would be on" if dry else "on", n, Q["fee"], words, ("; OFF - " + Q["off"]) if Q["off"] else "", ("; " + Q["loud"]) if Q.get("loud") else "")
def mvp_state(regs, look, reset=False, files=None, day=None):
    """Fill MVP - the option code M0004's own small ledger, per clinician - from the same import registers quality_state read (this stamp's own
    register too), oldest first: each register's "mvp_gate" first, then its rows. files = what quality_files read (held visits, insurance-check
    holds, the lines the inspector step or the insurance check took off). look=False (a dry run) reads nothing in AdvancedMD. reset = MVP_CODE=reset.
    day = the calendar day of this run. See the OPTION CODE comment above for every state. Nothing here can stop the import: the caller turns any
    error into 'no M0004 line this run'."""
    day = day or run_day(); today = _fmt_day(day); files = files if isinstance(files, dict) else {}
    m = _mvp_fresh(); notes = []; S = {"off": "", "wrong": "", "answer": {}}
    _d = lambda k: files.get(k) if isinstance(files.get(k), dict) else {}
    held = _d("held"); chold = _d("check_holds"); rem = {k: list(v) for k, v in _d("removed").items() if isinstance(v, list)}
    billed = set(); void = set(); left = set(); billed_on = {}; lon = {}; lseen = {}; late = {}; late_rows = []; swaps = {}; lines = []; era = [0]
    base = lambda name: _os.path.basename(str(name)); num = lambda x: re.sub(r"\D", "", str(x or ""))
    cof = lambda M: swaps.get(M["charge"], M["charge"])           # the M0004 line's charge number, a swap corrected (8.5)
    def restart(): S.update(off="", wrong=""); era[0] = len(lines)      # MVP_CODE=reset: what switched M0004 off no longer counts; a line that exists still counts for its clinician's year
    def created_row(name, r):
        pid = r.get("pid") if isinstance(r.get("pid"), str) else ""; vis = r.get("visit") if isinstance(r.get("visit"), str) else ""; who = "chart %s, visit %s, %s" % (pid or "?", vis or "?", base(name))
        if r.get("mvp_refused"): S["off"] = S["off"] or "AdvancedMD refused a visit that carried M0004 and took it with the 1123F line only - no second try (%s)" % who
        if r.get("mvp_not_stored"): S["off"] = S["off"] or "AdvancedMD stored a visit without its M0004 line - William looks (%s)" % who
        mc = r.get("mvp_codes") if isinstance(r.get("mvp_codes"), list) else []; mid = r.get("mvp_charge") if isinstance(r.get("mvp_charge"), str) else ""
        if mc and mid:
            lines.append({"reg": base(name), "chart": pid, "visit": vis, "charge": mid, "prof": r.get("mvp_prof") if isinstance(r.get("mvp_prof"), str) else "",
                          "dos": str(r.get("mvp_dos") or r.get("quality_dos") or r.get("dos") or ""), "q": r.get("quality_charge") if isinstance(r.get("quality_charge"), str) else "",
                          "charges": [c for c in (r.get("charges") if isinstance(r.get("charges"), list) else []) if isinstance(c, str)]})
    def failed_row(name, r):          # a visit that carried M0004 was refused and nobody knows what AdvancedMD kept (unless the 1123F-only form was refused too: then M0004 is not blamed)
        info = r.get("info") if isinstance(r.get("info"), dict) else {}
        if info.get("mvp_tried") and not info.get("mvp_form_refused") and (r.get("stored") or r.get("quality_unknown")):
            S["off"] = S["off"] or ("the run was cut while a call that carried M0004 was out; nobody knows what AdvancedMD kept of that visit - William looks (chart %s, visit %s, %s)" if r.get("provisional") else
                                    "AdvancedMD answered a visit that carried M0004 with a fault or an error and nobody knows what it kept of it - William looks (chart %s, visit %s, %s)") % (r.get("pid") if isinstance(r.get("pid"), str) else "?", r.get("empty_visit") or "?", base(name))
    def removal(regname, e):
        """An M0004 line the inspector step or the insurance check TOOK OFF a held visit (11.6): void and final. released (the visit went through
        without it) = M0004 is OFF until William restarts it - no second try; it does not count against 1123F (the 1123F line's own entry does, when
        it was taken off with it). Not released = the line is just void: its clinician may get it again. A void that failed = OFF until restarted.
        "with": "1123F" = it came off only because its 1123F line came off (M0004 never rides without 1123F, 8.2; confirm review NH2-1): just void,
        nothing switched off - that clinician may get M0004 again. Still listed for the edit about the line after the void (the re-save failed, or
        AdvancedMD did not inspect the visit again; NH2-2) = OFF until William has looked."""
        c_ = num(e.get("charge"))
        M = next((M for M in reversed(lines) if num(cof(M)) == c_), None)
        if M is None:      # the row recorded it as its 1123F line (the two were swapped): it is this row's M0004 line
            M = next((M for M in reversed(lines) if M["q"] and num(M["q"]) == c_), None)
            if M is not None: swaps[M["charge"]] = M["q"]
        if M is None: notes.append("%s names M0004 charge %s, which no import register row carries - passed over" % (regname, e.get("charge"))); return
        M["removed"] = dict(e, register=regname)
        if e.get("void_ok") is not True:
            S["off"] = S["off"] or "the Claim Inspector holds visit %s and the routine could not take its M0004 line off (%s: \"%s\") - William looks" % (M["visit"], regname, str(e.get("why") or "")[:140]); return
        void.add(cof(M))
        if e.get("with") == QUALITY_CODE: notes.append("the M0004 line of visit %s came off with its 1123F line - %s may get M0004 again" % (M["visit"], M["prof"] or "its clinician")); return
        if e.get("released") is not True and (e.get("still_named") is True or e.get("resave_ok") is False):
            S["off"] = S["off"] or "the routine took the M0004 line off held visit %s, but the visit is still listed for the edit about the line (%s: \"%s\") - William looks; one re-save of the visit should release it" % (M["visit"], regname, str(e.get("why") or "")[:140]); return
        if e.get("released") is True: S["off"] = S["off"] or "the routine took the M0004 line off held visit %s and the visit went through without it - no second try (%s: \"%s\")" % (M["visit"], regname, str(e.get("why") or "")[:140])
    def rows(fn, name, rs):          # row by row: an odd row is passed over, the rows after it are still read
        for r in rs:
            try:
                if isinstance(r, dict): fn(name, r)
            except Exception: continue
    is_mvp = lambda e: isinstance(e, dict) and str(e.get("code") or "").strip().upper() == MVP_CODE
    for name, reg in sorted(regs, key=lambda x: str(x[0])):
        try:
            if not isinstance(reg, dict): continue
            g = reg.get("mvp_gate") if isinstance(reg.get("mvp_gate"), dict) else {}
            cr = reg.get("created") if isinstance(reg.get("created"), list) else []; fl = reg.get("failed") if isinstance(reg.get("failed"), list) else []
            cut = [0, 0]
            if g.get("reset") is True:      # M0004 was started again in that run; rows an earlier start under the same stamp had written stay before the restart
                ra = g.get("reset_after")
                if isinstance(ra, list) and len(ra) == 2 and all(isinstance(x, int) and not isinstance(x, bool) and x >= 0 for x in ra): cut = ra
                rows(created_row, name, cr[:cut[0]]); rows(failed_row, name, fl[:cut[1]]); restart()
            if isinstance(g.get("off_until_reset"), str) and g["off_until_reset"].strip(): S["off"] = g["off_until_reset"].strip()
            for k, s in (("billed_lines", billed), ("void_lines", void), ("left_off_lines", left)):      # what earlier runs read as final is never read for its outcome again
                s.update(x for x in (g.get(k) if isinstance(g.get(k), list) else []) if isinstance(x, str))
            for k, d_ in (("billed_on", billed_on), ("left_off_seen", lseen), ("left_off_on", lon), ("late_billed", late), ("swaps", swaps)):
                if isinstance(g.get(k), dict): d_.update((a, b) for a, b in g[k].items() if isinstance(a, str) and isinstance(b, (str, dict)))
            if isinstance(g.get("wrong_code_text"), str) and g["wrong_code_text"]: S["wrong"] = g["wrong_code_text"]
            for p_, a_ in (g.get("answer").items() if isinstance(g.get("answer"), dict) else ()):      # the first answer found for a clinician stays
                if isinstance(p_, str) and isinstance(a_, dict) and a_.get("charge"): S["answer"].setdefault(p_, dict(a_))
            rows(created_row, name, cr[cut[0]:]); rows(failed_row, name, fl[cut[1]:])
            for regname, e in [x for x in rem.pop(re.sub(r"^feed_import_|\.json$", "", base(name)), []) if is_mvp(x[1])]:      # the M0004 lines that batch's inspector step / insurance check took off
                try: removal(regname, e)
                except Exception: continue
        except Exception: continue
    for st in sorted(rem):      # removals of a batch whose import register is not here: still void, after everything else
        for regname, e in [x for x in rem[st] if is_mvp(x[1])]:
            try: removal(regname, e)
            except Exception: continue
    if reset:
        if S["off"]: restart(); m["reset"] = True; notes.append("the option code M0004 was started again in this run (MVP_CODE=reset)")
        else: m["loud"] = "NOTHING TO RESTART - MVP_CODE=reset was ignored (M0004 is not switched off; take the switch out of the routine)"; notes.append(m["loud"])
    # HELD VISITS that carry the M0004 line (entered since the last restart) and whose line could NOT be taken off (no removal recorded): a Claim
    # Inspector hold whose words name M0004, or an insurance check that could not set the visit's order -> OFF until William restarts it
    for M in lines[era[0]:]:
        if M.get("removed") or not num(M["visit"]): continue
        for regname, why, _marked in held.get(num(M["visit"])) or ():
            if not S["off"] and names_lines(why, M["q"], cof(M))[1]:
                S["off"] = "the Claim Inspector holds visit %s, which carries the M0004 line, for words that name it (%s: \"%s\") - William looks" % (M["visit"], regname, str(why)[:140])
        for regname, words in chold.get(num(M["visit"])) or ():
            for why in words:
                named = set(re.findall(r"vst\d+", why))
                if not S["off"] and re.search(r"insorder not applied|resave FAULT|detail read mismatch", why) and (not named or M["visit"] in named):
                    S["off"] = "the insurance check could not set the order of visit %s, which carries the M0004 line (%s: \"%s\") - William looks" % (M["visit"], regname, why[:140])
    left -= billed; left -= void      # ONE state per line, its newest reading (as for 1123F): billed and void win over an older gate's "left off"
    final = lambda M: "billed" if cof(M) in billed else "void" if cof(M) in void else "left" if cof(M) in left else ""
    looks = [MVP_LOOKS]
    def own_of(M): return next((c for c in M["charges"] if c not in (M["q"], cof(M))), "")      # the visit's own first charge (the row lists the visit's own charges first)
    def read(M):
        """One read of an M0004 line and, where the outcome needs it, of its visit's own first charge - or of the visit's other recorded charges when
        the charge recorded for the line shows another procedure (the answer named no procedures: 8.5)."""
        looks[0] -= 1; M["seen"] = True; sn = {}
        st, what = _line(cof(M), MVP_PCODE, MVP_CODE, sn)
        if st == "unknown" and not sn.get("wrong") and what and what[0].startswith("AdvancedMD shows another procedure for it") and M["charge"] not in swaps:
            for c in [M["q"]] + [x for x in M["charges"] if x not in (M["q"], M["charge"])]:
                if not c or looks[0] <= 0: continue
                looks[0] -= 1; sn2 = {}; st2, what2 = _line(c, MVP_PCODE, MVP_CODE, sn2)
                if sn2.get("wrong"): sn, st, what = sn2, st2, what2; break
                if st2 in ("billed", "open", "void"):
                    swaps[M["charge"]] = c; notes.append("the M0004 line of visit %s is %s, not %s as its register row says (the answer named no procedures) - corrected" % (M["visit"], c, M["charge"])); st, what = st2, what2; break
        if sn.get("wrong"):      # AdvancedMD's id for the line is not M0004: nothing is built on it
            S["wrong"] = sn["wrong"]; S["off"] = S["off"] or "AdvancedMD stores procedure id %s as %s, not %s - William looks" % (MVP_PCODE, sn["wrong"], MVP_CODE); return
        c_ = cof(M); who = M["prof"] or "its clinician"
        if st == "billed": billed.add(c_); billed_on[c_] = what[0]; return
        if st == "void": void.add(c_); notes.append("the M0004 line of visit %s is void - %s may get it again" % (M["visit"], who)); return
        if st == "unknown": notes.append("the M0004 line of visit %s (%s) is not decided: %s - no second M0004 line for %s; William looks if this stays" % (M["visit"], c_, what[0], who)); return
        o = own_of(M); own, owhat = _line(o) if o else ("none", [])
        if own == "billed":      # LEFT OFF needs time (13.1): the newest billed date of the visit's own charge, else the day this import first saw it billed
            bday = max([d_ for d_ in map(_any_day, owhat) if d_] or [None])
            if bday is None: lseen.setdefault(c_, today); bday = _mdy_day(lseen[c_]) or day
            if (day - bday).days >= QUALITY_LEFT_OFF_DAYS:
                left.add(c_); lon[c_] = {"on": today, "billed": _fmt_day(bday)}
                notes.append("visit %s was billed %s without its M0004 line, and the line is still not billed %d days later - left off the claim; %s gets it once more" % (M["visit"], _fmt_day(bday), (day - bday).days, who))
            else: notes.append("visit %s was billed %s; its M0004 line is not billed yet - not decided before %s" % (M["visit"], _fmt_day(bday), _fmt_day(bday + datetime.timedelta(days=QUALITY_LEFT_OFF_DAYS))))
        elif own == "void": notes.append("the own charge of visit %s is void while its M0004 line is still live - not decided; William looks" % M["visit"])
    for M in lines:      # every M0004 line not decided yet, oldest first (whatever the restarts: whether a clinician is done for the year does not depend on them)
        if not look or looks[0] <= 0: break
        if final(M) or M.get("seen"): continue
        read(M)
    for M in lines:      # a line read as LEFT OFF is read again until QUALITY_LEFT_OFF_REREAD days after its visit was billed (13.1b): billed after all = its clinician is done
        if not look or looks[0] <= 0: break
        c_ = cof(M); w = lon.get(c_) if isinstance(lon.get(c_), dict) else {}; b = _mdy_day(str(w.get("billed") or ""))
        if final(M) != "left" or M.get("seen") or b is None or (day - b).days > QUALITY_LEFT_OFF_REREAD: continue
        looks[0] -= 1; M["seen"] = True; sn = {}; st, what = _line(c_, MVP_PCODE, MVP_CODE, sn)
        if sn.get("wrong"): S["wrong"] = sn["wrong"]; S["off"] = S["off"] or "AdvancedMD stores procedure id %s as %s, not %s - William looks" % (MVP_PCODE, sn["wrong"], MVP_CODE); continue
        if st == "billed":
            left.discard(c_); billed.add(c_); billed_on[c_] = what[0]; late[c_] = today
            again = [N["visit"] for N in lines if N is not M and N["prof"] == M["prof"] and N["dos"][-4:] == M["dos"][-4:] and final(N) == "billed"]      # "two billed lines" only when the later one IS billed
            late_rows.append([M["prof"], M["chart"], M["visit"], c_, str(w.get("on") or ""), again[0] if again else "", M["dos"][-4:]])
            notes.append("the M0004 line of visit %s, read as left off its claim on %s, was billed later (%s): %s counts as done" % (M["visit"], w.get("on") or "?", what[0], M["prof"] or "its clinician"))
        elif st == "void": left.discard(c_); void.add(c_); notes.append("the M0004 line of visit %s, read as left off its claim, is void now" % M["visit"])
    lo = [M for M in lines[era[0]:] if final(M) == "left"]
    if len(lo) >= MVP_LEFT_OFF_MAX and not S["off"]:
        S["off"] = "AdvancedMD left the M0004 line off %d claims since the option code was last started (visits %s) - William looks" % (len(lo), ", ".join(M["visit"] for M in lo[:4]))
    alooks = [MVP_LOOKS]      # MEDICARE'S ANSWER for M0004, per clinician (11.6): a live Medicare Part B payment line posted on a billed M0004 line
    for M in sorted([M for M in lines if final(M) == "billed"], key=lambda M: (_any_day(billed_on.get(cof(M))) or datetime.date.min, cof(M))):
        if not look or alooks[0] <= 0: break
        if not M["prof"] or M["prof"] in S["answer"]: continue
        alooks[0] -= 1
        try: pays = _payments(cof(M))
        except Exception as e: notes.append("Medicare's answer: the payment lines of the M0004 line of visit %s could not be read (%s)" % (M["visit"], type(e).__name__)); continue
        hit = next((p for p in pays if str(p.get("void") or "0") != "1" and re.sub(r"\D", "", str(p.get("carrierfid") or "")) == re.sub(r"\D", "", MEDICARE_B)), None)
        if hit:
            S["answer"][M["prof"]] = {"charge": cof(M), "visit": M["visit"], "date": str(hit.get("date") or ""), "amount": str(hit.get("amount") or ""), "register": M["reg"]}
            notes.append("Medicare's remittance shows the M0004 line for %s on visit %s: a Medicare payment line of $%s posted %s" % (M["prof"], M["visit"], S["answer"][M["prof"]]["amount"], S["answer"][M["prof"]]["date"]))
    for M in lines:      # once per clinician per year: billed = done, not decided = no second line; left off or void = that clinician is due again
        if not M["prof"] or len(M["dos"]) < 4: continue
        if final(M) == "billed": m["done"].add((M["prof"], M["dos"][-4:]))
        elif not final(M): m["wait"].add((M["prof"], M["dos"][-4:]))
    yr = max(MVP_YEARS); cl = {}
    for p_ in sorted(set(PROFILE.values())):      # for the report: each clinician's M0004 line of the year it is registered for
        mine = [M for M in lines if M["prof"] == p_ and M["dos"][-4:] == yr]; b_ = [M for M in mine if final(M) == "billed"]; w_ = [M for M in mine if not final(M)]; l_ = [M for M in mine if final(M) == "left"]
        top = (b_ or w_ or l_ or [None])[0]
        cl[p_] = {"state": "billed" if b_ else "waiting" if w_ else "left off" if l_ else "not yet", "year": yr, "visit": top["visit"] if top else "", "charge": cof(top) if top else "",
                  "billed": billed_on.get(cof(top), "") if b_ else "", "since": top["reg"] if top else ""}
    aw = {p_: {"visit": v_["visit"], "billed": v_["billed"], "days": (day - _any_day(v_["billed"])).days if _any_day(v_["billed"]) else None} for p_, v_ in cl.items() if v_["state"] == "billed" and p_ not in S["answer"]}
    m.update(off=S["off"], off_until_reset=S["off"], billed_lines=sorted(billed), void_lines=sorted(void), left_off_lines=sorted(left - billed - void), billed_on={k: v for k, v in billed_on.items() if k in billed},
             left_off_on={k: v for k, v in lon.items() if k in left}, left_off_seen={k: v for k, v in lseen.items() if k not in billed and k not in void and k not in left}, late_billed=dict(late),
             late_rows=late_rows, swaps=dict(swaps), wrong_code_text=S["wrong"], answer=dict(S["answer"]), answer_wait=aw, clinicians=cl, notes=notes[:20], lines=len(lines))
    MVP.clear(); MVP.update(m)
def mvp_gate():
    """What a run writes into its register as "mvp_gate": the option code M0004's own ledger, for the next run and for the digest. off = why no M0004
    line is added in THIS run; off_until_reset = the sentence of an OFF that only MVP_CODE=reset ends (the specification's mvp_off_until_reset);
    clinicians = per clinician (the profile its visits are entered under), for the year it is registered for: billed / waiting / left off / not yet;
    added = the clinicians whose visit got the M0004 line in this run; answer = Medicare's own answer per clinician (answer_wait while none)."""
    M = MVP; cl = {k: dict(v) for k, v in (M.get("clinicians") or {}).items()}      # main() marks a clinician whose visit got the line in this run as waiting
    return {"code": MVP_CODE, "on": bool(MVP_ON), "off": M.get("off") or "", "off_until_reset": M.get("off_until_reset") or "", "reset": bool(M.get("reset")), "reset_after": M.get("reset_after") if M.get("reset") else None,
            "added": list(M.get("added") or []), "clinicians": cl, "billed_lines": list(M.get("billed_lines") or []), "void_lines": list(M.get("void_lines") or []),
            "left_off_lines": list(M.get("left_off_lines") or []), "billed_on": dict(M.get("billed_on") or {}), "left_off_on": dict(M.get("left_off_on") or {}), "left_off_seen": dict(M.get("left_off_seen") or {}),
            "late_billed": dict(M.get("late_billed") or {}), "late_rows": list(M.get("late_rows") or []), "swaps": dict(M.get("swaps") or {}), "wrong_code_text": M.get("wrong_code_text") or "",
            "answer": dict(M.get("answer") or {}), "answer_wait": dict(M.get("answer_wait") or {}), "notes": list(M.get("notes") or [])}
def mvp_log(n, dry):
    """The ONE line a run prints about the option code M0004, right after the QUALITY 1123F line (the runbook reads it by its start)."""
    M = MVP; cl = M.get("clinicians") or {}; added = set(M.get("added") or [])
    who = ", ".join("%s %s" % (p_, "waiting (added now)" if p_ in added and (cl.get(p_) or {}).get("state") != "billed" else (cl.get(p_) or {}).get("state") or "not yet") for p_ in sorted(set(PROFILE.values())))
    words = "off until William restarts it (one run with MVP_CODE=reset)" if M.get("off_until_reset") else "once per clinician, only with the 1123F line once that is proven"
    return "QUALITY M0004: %s x%d visit(s), %s; %s%s%s" % ("would be on" if dry else "on", n, who, words, ("; OFF - " + M["off"]) if M.get("off") else "", ("; " + M["loud"]) if M.get("loud") else "")
def msg_building(msg):
    """The building name of a message for the visit history: its own, else the patient's when the batch shows only one, else ''."""
    try:
        o = msg_agreed(msg)
        if o[0] is not None: return o[0]
        f = FACS.get(msg.get("pid")) or ()
        return next(iter(f)) if len(f) == 1 else ""
    except Exception: return ""
def msg_buildings(msg):
    """Every building name the raw copies of a message carry (11/10/2026, review C1): one for nearly every message; two or more when the feed sent
    the same lines from several buildings - then that day is named under two buildings, and the resident's next visit and that month's CCM read
    it as a move (31), exactly like a day the chart and the feed name under two buildings."""
    try:
        own = MSGOF.get(msg_key(msg.get("pid"), [(c.get("cpt"), c.get("dos")) for c in msg.get("FT1") or []])) or ()
        names = sorted({o[0] for o in own if o[0]})
        return names if len(names) > 1 else [msg_building(msg)]
    except Exception: return [msg_building(msg)]
def visit_lines(msg, buildings):
    """[[code, 'MM/DD/YYYY', building name]] for the nursing, hospital and home visit lines of a message, once per building given."""
    return [[c["cpt"], mdy(c["dos"][:8]), bn] for bn in buildings for c in msg.get("FT1") or []
            if (c.get("cpt") in NF_VISIT or c.get("cpt") in HOSP_VISIT or c.get("cpt") in HOME_VISIT) and len(c.get("dos") or "") >= 8]
def seen_lines(msg):
    """[[code, 'MM/DD/YYYY', building name]]: the nursing, hospital and home visit lines of a message that is NOT entered (a code the table
    does not have, no usable diagnosis, a fault). They go into the register row so a LATER batch still knows the feed showed them - once per
    building its copies name (a visit the feed sent from two buildings stays a day named under two buildings for that later batch too)."""
    try: return visit_lines(msg, msg_buildings(msg))
    except Exception: return []
def count_pos(info, stats):
    """The DONE-line counters for one message that was entered (or would be, in a dry run)."""
    if info.get("msg_own") is False: stats["feed message not matched to its own raw message - where its copies differ: the patient's last-read building / clinician, the admission date of its own last copy"] += 1
    if info.get("prof_default"): stats["clinician id of the feed message is not one of the practice's two - entered under the physician profile"] += 1
    if info.get("prof_feed"): stats["initial nursing-facility visit entered under the physician although the feed named another clinician (William 11/10/2026)"] += 1
    if not info.get("fac"): stats["visit entered with NO facility - its building is not in the facility table"] += 1      # every code, not only CCM / nursing lines
    if info.get("pos_err"):
        stats["POS RULE NOT APPLIED (entered at the feed's place of service)"] += 1; return
    for cpt, p, k in zip(info["cpts"], info["pos_lines"], info.get("pos_kind") or [""] * len(info["cpts"])):
        if info.get("pos_feed") == "31" and not info.get("fac") and (cpt in CCM or cpt in NF_VISIT): stats["POS RULE: building not in the facility table - entered at the feed's 31"] += 1
        elif k == "ccm": stats["POS 32 CCM (nursing building)"] += 1
        elif k == "ccm-skilled-month": stats["POS 31 CCM kept for William (the back end's exception for that month - see pos_why)"] += 1
        elif k == "monthly": stats["POS 32 nursing visit (monthly)"] += 1
        elif k in ("extra", "between"): stats["POS 31 nursing visit (kept at 31: neither pattern shown)"] += 1
        elif k == "moved": stats["POS 31 nursing visit (previous nursing visit in another building)"] += 1
        elif k and k != "with-visit": stats["POS 31 nursing visit (weekly, admission or new stay)"] += 1
# facility per feed message (MSH-4) and provider NPI per message (PV1-7) re-read from the raw files
import glob
FACOF = {}; NPIOF = {}; ADMIT = {}      # per feed PATIENT, the last message read: only the fallback since 11/10/2026 (see msg_own)
def msg_key(pid, pairs):
    """What names ONE feed message inside a batch: the feed patient id and its (code, DOS) lines - the same whether they are read from
    the raw file here or from the parsed file (feed_parse_dft reads FT1-4 and FT1-25 the same way)."""
    return (str(pid or ""), tuple(sorted((str(c or ""), str(d or "")[:8]) for c, d in pairs)))
def msg_own(msg):
    """(building name, clinician NPI, admission date) of ONE parsed message, or None when the raw files do not give exactly one answer
    for it (no such message, or the same lines sent from two buildings / by two clinicians): then the per-patient values are used."""
    try:
        own = MSGOF.get(msg_key(msg.get("pid"), [(c.get("cpt"), c.get("dos")) for c in msg.get("FT1") or []])) or ()
        return next(iter(own)) if len(own) == 1 else None
    except Exception: return None
def msg_agreed(msg):
    """(building, NPI, admission date) of ONE parsed message value by value: what EVERY raw copy of the message says; None for a value the
    copies do not agree on, or when the raw files do not hold the message. A visit sent twice with a corrected admission date keeps its building and clinician."""
    try:
        own = MSGOF.get(msg_key(msg.get("pid"), [(c.get("cpt"), c.get("dos")) for c in msg.get("FT1") or []])) or ()
        return tuple((next(iter({o[i] for o in own})) if len({o[i] for o in own}) == 1 else None) for i in range(3))
    except Exception: return (None, None, None)
for f in sorted(glob.glob((HL7_DIR + "/*.hl7"))):       # sorted: "the last message read" is the same on every machine (the parser sorts too)
    raw = open(f, encoding="utf-8", errors="replace").read().replace("\r\n", "\n").replace("\r", "\n")      # read exactly as feed_parse_dft reads it (11/10/2026: UTF-8 whatever the machine's default, so a patient id with a non-ASCII letter still matches)
    for b in re.split(r"(?m)^(?=MSH\|)", raw):
        if not b.startswith("MSH|"): continue
        msh = b.split("\n")[0].split("|"); fac = msh[3].split("^")[-1] if len(msh) > 3 else ""; pid = None      # a short line never stops the load
        _npi = _adm = ""; _ft = []; _pv1 = False
        for line in b.strip().split("\n"):              # b.strip(): exactly what feed_parse_dft does to a block, so both readers see the same last field
            s = line.split("|")
            if s[0] == "PID": pid = s[3] if len(s) > 3 else ""; FACOF[pid] = fac; FACS.setdefault(pid, set()).add(fac)
            if s[0] == "PV1":                             # wherever it stands in the message (the parser does not care about the order either)
                _pv1 = True; _npi = s[7].split("^")[0] if len(s) > 7 else ""; _adm = s[44] if len(s) > 44 else ""
            if s[0] == "FT1": _ft.append((s[25].split("^")[0] if len(s) > 25 else "", s[4] if len(s) > 4 else ""))
        if pid and _pv1: NPIOF[pid] = _npi; ADMIT[pid] = _adm
        try:
            if pid: MSGOF.setdefault(msg_key(pid, _ft), set()).add((fac, _npi, _adm)); MSGLAST[msg_key(pid, _ft)] = (fac, _npi, _adm)      # ... and the last raw copy of THIS message
        except Exception: pass
# ---- FEED MESSAGES THAT COULD NOT BE READ (11/11/2026) ---------------------------------------------------------------------------------------
# Two readers can find a message they cannot use: the parser (feed_parse_dft_1028.py: no PID segment, no PV1 segment, an FT1 line with fewer
# fields than it reads, anything that fails while the message is read - it writes them to feed_skipped_<stamp>.json and leaves them out of the
# parsed file) and this import (a parsed message with no FT1 line: nothing to enter and nothing to build the visit's key from). Neither stops the
# batch any more: the message is skipped, every other visit of the batch is entered, and the message is named - by its control id (MSH-10), its
# file and its place in the file, never by a name, a date of birth or a member id - in the import register ("skipped_messages"), in a SKIPPED
# MESSAGE line of the import log and at the top of the report (claimocity_report.py). No routine enters such a message: a person looks at the
# feed file. A list that is there but cannot be read is said the same way ("skipped_messages_unread") - never taken as "nothing was skipped".
SKIPPED_FILE = "feed_skipped_%s.json" % STAMP       # the parser's list of the messages it could not read, beside the parsed file
NO_FT1 = "no FT1 line - no charge to enter"
def unreadable(msg):
    """Why this import cannot enter a parsed message at all ("" = it can): main() builds each visit's key from the message's patient id, its first
    FT1 line's date and its codes, and finds the chart by name and date of birth - a record without them is skipped and named, never a stop."""
    if not isinstance(msg, dict): return "not a message record"
    if not (isinstance(msg.get("FT1"), list) and msg["FT1"]): return NO_FT1
    if not all(isinstance(c, dict) and isinstance(c.get("dos"), str) and isinstance(c.get("cpt"), str) for c in msg["FT1"]): return "an FT1 line without a date of service or a code"
    if not all(isinstance(msg.get(k), str) for k in ("pid", "name", "dob")): return "no patient id, name or date of birth in the parsed record"
    return ""
def _skip_row(x, why, by):
    """One register row for a skipped message: control id, file, place in the file, reason, who skipped it - and nothing else of the message."""
    x = x if isinstance(x, dict) else {}
    return {"ctl": re.sub(r"[^A-Za-z0-9._:\-]", "", str(x.get("ctl") or ""))[:40], "file": re.sub(r"[^A-Za-z0-9._\-]", "", str(x.get("file") or ""))[:8],
            "msg": x.get("msg") if isinstance(x.get("msg"), int) and not isinstance(x.get("msg"), bool) else None, "why": re.sub(r"[^A-Za-z0-9 ()\-;,.:]", "", str(why or ""))[:200], "by": by}
def skipped_rows(parsed, path=None):
    """(rows, unread): the messages of this batch that are not entered because they could not be read - the parser's list first, then the parsed
    messages this import cannot key; unread = why the parser's list could not be read ("" when it was read, or when there is none: a parsed file
    written before 11/11/2026 has no list). The same batch gives the same rows at every start, so a re-run names each message once."""
    path = path or SKIPPED_FILE; rows = []; unread = ""
    try:
        if _os.path.exists(path):
            for x in json.load(open(path)): rows.append(_skip_row(x, x.get("why"), "parser"))
    except Exception as e:
        rows = []; unread = "%s could not be read (%s) - read logs/claimocity_%s_parse.log" % (_os.path.basename(path), type(e).__name__, STAMP)
    for msg in parsed:
        w = unreadable(msg)
        if w: rows.append(_skip_row(msg, w, "import"))
    return rows, unread
_ctx = {}
def chart_ctx(pid):
    """episode, respparty, refplan, insorder, live {(cpt,dos)} from the chart's own history/detail."""
    if pid in _ctx: return _ctx[pid]
    num = re.sub(r"\D", "", pid)
    root = txh.fetch(num)
    live = set(); rows = set(); sample = None; newest = ""; qsample = None
    for c in root.iter("charge"):
        a = c.attrib
        if a.get("void") == "1" or (a.get("fee") or "").startswith("-"): continue
        live.add((a.get("proccode"), a.get("dos")))
        if a.get("proccode") in NF_VISIT or a.get("proccode") in HOSP_VISIT or a.get("proccode") in HOME_VISIT: rows.add((a.get("proccode"), a.get("dos"), a.get("facname") or ""))
        if a.get("proccode") in QUALITY_SAME or a.get("proccode") == MVP_CODE: qsample = qsample or a.get("id")      # a no-charge line (1123F, 1124F or the M0004 line, 8.6) is the sample only when the chart has nothing else
        elif (a.get("dos") or "") > newest or sample is None:
            newest = a.get("dos") or ""; sample = a.get("id")
    ctx = {"live": live, "nfrows": rows, "episode": "", "resp": "", "refplan": "", "insorder": ""}   # nfrows: (code, DOS, facility name) of visit charges, for the place-of-service rule
    r = amd.post('<ppmdmsg action="getdemographic" class="demographics" msgtime="%s" patientid="%s" nocookie="1"/>' % (amd._msgtime(), pid))
    p = re.search(r'<patient [^>]*>', r); a = dict(re.findall(r'(\w+)="([^"]*)"', p.group(0))) if p else {}
    ctx["resp"] = a.get("respparty", ""); ctx["insorder"] = a.get("insorder", "") or "1"; ctx["deceased"] = a.get("deceased", "")
    pl = re.findall(r'<insplan id="(ins\d+)" carrier="(car\d+)" begindate="([^"]*)" enddate="([^"]*)"[^>]*sequence="(\d+)"', r)
    ctx["plans"] = pl
    # 11/10/2026 (round 7): the "1" above is only a stand-in when the chart has no plan - AdvancedMD then keeps insorder "1" on the new visit but builds
    # NO insurance-order list, so no claim is made and no work list shows it (84 visits, $18,802). The chart's own order and its open plans at this
    # moment go on every register row (None = the chart could not be read). The create shape stays: a blank insorder on a new visit is unproven.
    _ip = [dict(re.findall(r'(\w+)="([^"]*)"', t)) for t in re.findall(r'<insplan ([^>]*)>', r)]      # attribute order does not matter (as elig_amd.plans)
    ctx["chart_insorder"] = a.get("insorder", "") if p else None
    ctx["open_plan_seqs"] = [x.get("sequence") or "?" for x in _ip if x.get("id") and not (x.get("enddate") or "").strip()] if p else None
    sample = sample or qsample
    if sample:
        d = ET.fromstring(resave.detail(re.sub(r"\D", "", sample)))
        v = d.find(".//visit")
        if v is not None:
            ctx["episode"] = v.get("episode", ""); ctx["refplan"] = v.get("refplan", "")
            if not ctx["resp"]:
                ch = [e for e in d.iter("charge")]
                if ch: ctx["resp"] = ch[0].get("respparty", "")
    _ctx[pid] = ctx
    return ctx
# One face-to-face E/M per patient per day: a charge already on the chart for the same DOS from the same visit family IS this encounter,
# whatever level or new/established code it ended up with (the Claim Inspector swaps a second new-patient code to 99349; coders change
# levels). 10/30/2026: two 9/2 home visits were entered twice because the feed said 99344 and the chart carried 99349.
EM_FAMILY = [set("99341 99342 99344 99345 99347 99348 99349 99350".split()),            # home / ALF visits
             set("99221 99222 99223 99231 99232 99233 99238 99239 99234 99235 99236".split()),   # hospital
             set("99304 99305 99306 99307 99308 99309 99310 99315 99316".split()),      # SNF / NF
             set("99202 99203 99204 99205 99212 99213 99214 99215".split())]            # office
# (CCM 99487 + its add-on 99489 and ACP 99497/99498 legitimately share a DOS - those stay on the exact code + DOS rule)
def same_encounter(cpt, dos, live):
    fam = next((f for f in EM_FAMILY if cpt in f), None)
    if not fam: return False
    return any(lc in fam and ld == dos for lc, ld in live)
def build(msg, ctx):
    fid = msg["pid"]; own = msg_own(msg)             # this message's own (building, clinician NPI, admission date) - None = not readable
    _ag = msg_agreed(msg)                            # value by value: what every copy of the message says; building and clinician fall back to the patient's last-read value only where the copies differ
    _last = MSGLAST.get(msg_key(fid, [(c.get("cpt"), c.get("dos")) for c in msg.get("FT1") or []]))      # the message's own LAST raw copy (None = the raw files do not hold it)
    facname = _ag[0] if _ag[0] is not None else FACOF.get(fid, ""); npi = _ag[1] if _ag[1] is not None else NPIOF.get(fid, "")
    # copies that differ in the admission date (a copy sent again with a corrected date): the message's own LAST copy answers (11/10/2026, review W2) -
    # never another message of the patient; the patient's last-read date only when the raw files do not hold this message at all
    admit = _ag[2] if _ag[2] is not None else (_last[2] if _last else ADMIT.get(fid, ""))
    _fb = [x for x, v in (("building", _ag[0]), ("clinician", _ag[1])) if v is None]      # the values that did NOT come from every copy of the message (said in the register: msg_fallback)
    _fbw = "; ".join(w for w in (("%s: the patient's last-read message" % " and ".join(_fb)) if _fb else "", ("admission date: %s" % ("this message's own last copy" if _last else "the patient's last-read message")) if _ag[2] is None else "") if w)
    fac, pos = FAC.get(facname, ("", "31"))
    nursing = facname in FAC and pos == "31"        # one of the practice's nursing buildings (never the unknown-building default)
    prof = PROFILE.get(npi, "prof13")               # an id that is not one of the practice's two (or none at all) still goes in under the physician - and is said
    initial = any(c.get("cpt") in INITIAL_NF for c in msg.get("FT1") or [])       # INITIAL NURSING-FACILITY VISIT (William 11/10/2026): the whole visit, every line of the message, under the physician
    prof_feed = prof if (initial and prof != PHYSICIAN) else ""                     # what the message's own clinician maps to, kept in the register when the rule changes it
    if initial: prof = PHYSICIAN
    _tb = msg_buildings(msg)                         # every building the message's raw copies name: two or more = a day named under two buildings (review C1), kept in the register for later batches
    lines = []
    for c in msg["FT1"]:
        cpt = c["cpt"]
        if cpt not in PCODE: return None, "unknown CPT %s" % cpt
        if (cpt, mdy(c["dos"][:8])) in ctx["live"]: continue        # dedupe: same code, same DOS
        if same_encounter(cpt, mdy(c["dos"][:8]), ctx["live"]): continue   # dedupe: same E/M family, same DOS (10/30: 99344 vs the inspector's 99349)
        lines.append(c)
    if not lines: return None, "all lines already in AMD"
    dos = mdy(lines[0]["dos"][:8])
    chg = ""
    cpts = [c["cpt"] for c in lines]
    missing_dx = set()
    # place of service per line (11/10/2026 rule); any failure = the feed's place of service for every line, exactly as before the rule
    pos_err = ""; lkind = [""] * len(lines)
    try:
        if nursing and BATCH_NF_ERR[0]:
            raise ValueError("the visits of this batch could not be listed (%s), so nothing shows this resident's pattern - kept at the feed's place of service" % BATCH_NF_ERR[0])
        if _ag[0] is None and len(FACS.get(fid, ())) > 1 and (nursing or any(FAC.get(_n, ("", ""))[1] == "31" for _n in FACS[fid])):
            raise ValueError("this feed patient has messages from %d buildings in this batch and its own building cannot be read - "
                             "facility, clinician and place of service are for William; a routine changes nothing on this visit" % len(FACS[fid]))
        hist = (list(ctx.get("nfrows") or ctx.get("live") or ()) + list(BATCH_NF.get(ctx.get("pid"), ()))) if nursing else ()   # the history is only read for a nursing building
        lpos, lwhy, lkind = pos_lines([(c["cpt"], mdy(c["dos"][:8])) for c in lines], pos, nursing, hist, fac if nursing else None)
        if len(lpos) != len(lines) or any(p not in ("31", "32", pos) for p in lpos): raise ValueError("unexpected place of service %r" % (lpos,))
    except Exception as e:
        lpos = [pos] * len(lines); lwhy = ["rule error"] * len(lines); lkind = [""] * len(lines); pos_err = str(e)[:200] or type(e).__name__
    _qwhy = []                                            # "hospital" when the visit met every condition but its visit lines are hospital lines
    try: qi = quality_due(msg, ctx, lines, lpos, _qwhy)   # the visit line the advance-care-plan quality code rides with (None = no code)
    except Exception: qi = None; _qwhy = []
    qchg = ""
    for _k, (c, cpos) in enumerate(zip(lines, lpos)):
        dcodes = []
        for code in c["dx"].split("^"):
            if DX.get(code): dcodes.append(DX[code])
            elif code: missing_dx.add(code)
        if not dcodes: return None, "no usable dx for %s" % c["cpt"]
        mod = "mcode7" if c["cpt"] in MOD25 and len(cpts) > 1 else ""
        fee = FEE[c["cpt"]]; d = mdy(c["dos"][:8])
        dcodes = dcodes[:12]
        chg += ('<charge id="" respparty="%s" begindate="%s" enddate="%s" diagcodes="%s" modcodes="%s" aging="%s" billins="1" proccode="%s" cobcode="" pos="%s" tos="01" '
                'units="%s" netfee="0" fee="%s" allowed="%s" patportion="0.00" insportion="%s" patbalance="0.00" insbalance="%s" finclasscode="MC" lineitemnote="">'
                '<diagcodelist>%s</diagcodelist></charge>') % (ctx["resp"], d, d, " ".join(dcodes), mod, d, PCODE[c["cpt"]], cpos, c["units"] or "1", fee, fee, fee, fee,
                "".join('<diagcode id="%s"/>' % re.sub(r"\D", "", x) for x in dcodes))
        if _k == qi and str(cpos) not in QUALITY_POS_SKIP:      # same date and place of service as its visit line; no charge; never a modifier; ONE diagnosis, the first of its visit line (CMS: a quality line points to one diagnosis only); never a hospital or emergency-department line (QUALITY_POS_SKIP)
            qchg = ('<charge id="" respparty="%s" begindate="%s" enddate="%s" diagcodes="%s" modcodes="" aging="%s" billins="1" proccode="%s" cobcode="" pos="%s" tos="01" '
                    'units="1" netfee="0" fee="%s" allowed="%s" patportion="0.00" insportion="%s" patbalance="0.00" insbalance="%s" finclasscode="MC" lineitemnote="">'
                    '<diagcodelist>%s</diagcodelist></charge>') % (ctx["resp"], d, d, dcodes[0], d, QUALITY_PCODE, cpos, QUALITY["fee"], QUALITY["fee"], QUALITY["fee"], QUALITY["fee"],
                    '<diagcode id="%s"/>' % re.sub(r"\D", "", dcodes[0]))
    mchg = ""
    if qchg:      # the option code M0004 rides with the 1123F line, once per clinician per year, once that line is proven (mvp_due): the SAME line with M0004's id - same date, place of service, amount, ONE diagnosis, no modifier
        try: _mok = mvp_due(own is not None and npi in PROFILE, prof, re.sub(r"\D", "", str(lines[qi].get("dos") or ""))[:4], lpos[qi])
        except Exception: _mok = False
        if _mok: mchg = qchg.replace('proccode="%s"' % QUALITY_PCODE, 'proccode="%s"' % MVP_PCODE, 1)
    ext = ""
    if any(c in HOSP for c in cpts) and admit:
        ext = '<extins hospitalizationfrom="%s"/>' % mdy(admit[:8])
    onh = "1" if ext else "0"
    # two-step create (proven 10/28/2026 on pat17476917 vst19458732): addvisit <appt> makes the empty visit, then
    # updvisitwithnewcharges on that visit id adds the charges. VISIT_ID is substituted by the caller.
    def _body(charges):
        vis = ('<visit id="%%VISIT%%" date="%s" profile="%s" facility="%s" refplan="%s" insorder="%s" onhcfa="%s" acceptassign="1" forcepaper="0" force="1">'
               '<chargelist>%s</chargelist>%s</visit>') % (dos, prof, fac, ctx["refplan"], ctx["insorder"], onh, charges, ext)
        return amd.msg("updvisitwithnewcharges", "chargeentry",
                       {"patientid": ctx["pid"], "episodeid": ctx["episode"], "approval": "1", "inspectorenabled": "1",
                        "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"}, vis)
    plain = _body(chg)                                     # the visit exactly as before the quality code existed
    body = _body(chg + qchg + mchg) if qchg else plain     # the quality line is LAST in the list - or second to last, followed by the M0004 line
    if qchg:      # once per patient per year: by the chart and by the feed's own patient id
        _qyr = re.sub(r"\D", "", str(lines[qi].get("dos") or ""))[:4]; QUALITY["added"] += 1; QUALITY["done"].add((ctx.get("pid"), _qyr))
        if _feed_mark(fid): QUALITY["done"].add((_feed_mark(fid), _qyr))
        if mchg: MVP["wait"].add((prof, _qyr)); MVP["added"].append(prof)      # once per clinician per year: no second M0004 line for this clinician until this one is decided
    appt = ('<appt id="" patient="%s" episode="%s" date="%s" profile="%s" facility="%s" refplan="%s" insorder="%s" onhcfa="%s" '
            'acceptassign="1" forcepaper="0" isappt="0" note="" billingnote="" referenceid=""/>') % (ctx["pid"], ctx["episode"], dos, prof, fac, ctx["refplan"], ctx["insorder"], onh)
    create = amd.msg("addvisit", "chargeentry", {"patientid": ctx["pid"], "episodeid": ctx["episode"], "approval": "1", "inspectorenabled": "1",
                     "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"}, appt)
    # "pos" stays ONE value for the registers that read it (recon, monitor, the practice database): the first line's; pos_lines has every line
    # dos_lines: every line's own date (a message can carry two); msg_own: False = building / clinician came from the per-patient fallback
    # quality_codes: the reporting code that rides with this visit (never in cpts: the register dedupe keys on the message's own codes); mvp_codes: the
    # option code with it, mvp_prof the clinician profile its once-a-year mark belongs to (the profile the visit is entered under)
    # prof_feed / prof_why: an initial nursing-facility visit entered under the physician although its message named another clinician (William 11/10/2026);
    # msg_fallback: for a message not matched to exactly one raw copy, where each value came from; tie_lines: the visit lines once per building when the
    # feed sent the message from two or more buildings - a later batch reads that day as named under two buildings (review C1)
    return (create, body, plain), {"dos": dos, "dos_lines": [mdy(c["dos"][:8]) for c in lines], "cpts": cpts, "fac": fac, "pos": lpos[0], "pos_feed": pos, "pos_lines": lpos,
                            "pos_why": lwhy, "pos_kind": lkind, "pos_err": pos_err, "prof": prof, "prof_default": npi not in PROFILE and not initial, "msg_own": bool(own), "admit": admit, "missing_dx": sorted(missing_dx),
                            **({"prof_feed": prof_feed, "prof_why": INITIAL_WHY} if prof_feed else {"prof_why": INITIAL_WHY} if (initial and npi not in PROFILE) else {}),
                            **({"msg_fallback": _fbw} if (own is None and _fbw) else {}), **({"tie_lines": visit_lines(msg, _tb)} if len(_tb) > 1 else {}),
                            **({"quality_codes": [QUALITY_CODE], "quality_fee": QUALITY["fee"], "quality_dos": mdy(lines[qi]["dos"][:8]), "quality_pos": lpos[qi]} if qchg else
                               {"quality_skipped": "hospital"} if "hospital" in _qwhy else {}),
                            **({"mvp_codes": [MVP_CODE], "mvp_fee": QUALITY["fee"], "mvp_dos": mdy(lines[qi]["dos"][:8]), "mvp_pos": lpos[qi], "mvp_prof": prof} if mchg else {})}
def main():
    a = sys.argv[1:]; dry = "--dry" in a; one = a[a.index("--one") + 1] if "--one" in a else None
    limit = int(a[a.index("--limit") + 1]) if "--limit" in a else 10 ** 9
    amd.login_cached()
    reg = json.load(open(REG)) if __import__("os").path.exists(REG) else {"created": [], "skipped": [], "failed": []}
    # feed messages that could not be read (11/11/2026): named here, before anything is entered - in the register (written with the first visit and
    # at the end of a live run; a dry run writes nothing), in the log and, by the digest, at the top of the report. The loop below passes them over.
    _skm, _sku = skipped_rows(PARSED)
    for _k, _v in (("skipped_messages", _skm), ("skipped_messages_unread", _sku)):
        if _v: reg[_k] = _v
        else: reg.pop(_k, None)
    for _x in _skm: print("SKIPPED MESSAGE %s (file %s, message %s): %s - not entered; a person must look at the feed file" % (_x["ctl"] or "no control id", _x["file"] or "?", "?" if _x["msg"] is None else _x["msg"], _x["why"]))
    if _sku: print("SKIPPED MESSAGES NOT KNOWN: %s - a person must look at the feed file" % _sku)
    # a feed id is the PATIENT (PID-3), not the message: dedupe on (patient, DOS, CPT set) - the live-charge check is the backstop.
    # EVERY earlier batch register counts (a visit re-dated after its import, e.g. the CCI 24078 re-dates, no longer matches the feed DOS
    # in AMD, so the live check alone would create it again - 10/29/2026 dry run).
    import glob as _glob
    done = set(); prior_seen = []        # prior_seen: (chart, [code, DOS, building]) visit lines earlier batches saw but did not enter
    prior_regs = []                      # (file name, register) of every batch - the register of THIS stamp too when it exists (a second start, --limit, --one): the quality code's state is read from them
    _unread = []                         # import registers that are there but cannot be read: the quality lines they may hold are not known
    for rf in _glob.glob("registers/feed_import_*.json"):
        if rf.endswith("_decisions.json"): continue
        try: prior = json.load(open(rf))
        except Exception: _unread.append(rf); continue
        if isinstance(prior, dict): prior_regs.append((rf, prior))
        done |= {(r["feed_id"], r["dos"], tuple(sorted(r["cpts"]))) for r in prior.get("created", []) if r.get("feed_id")}
        done |= {(r["feed_id"], r["dos_feed"], tuple(sorted(r["cpts"]))) for r in prior.get("created", []) if r.get("feed_id") and r.get("dos_feed")}   # re-dated visits keep their feed DOS here
        if rf == REG: done |= {(r["feed_id"], None, None) for r in prior.get("skipped", [])}
        for _k in ("skipped", "failed", "created"):      # row by row and line by line: an odd row or line is skipped, the rows after it are still read
            _rows = prior.get(_k) if isinstance(prior, dict) else None
            for r in (_rows if isinstance(_rows, list) else []):
                try: _lns = r.get("lines" if _k != "created" else "tie_lines"); _rp = r.get("pid")      # a created row keeps "tie_lines" when the feed sent its message from two buildings (review C1)
                except Exception: continue
                for _ln in (_lns if isinstance(_lns, list) else []):
                    if isinstance(_ln, (list, tuple)): prior_seen.append((_rp, list(_ln)))
    # deceased guard before any write: a DOS after the cached date of death is never entered (William's standing rule)
    _dc = {}
    for _p in [__import__("os").environ.get("DECEASED_CACHE", ""), "deceased_cache_local.json", "registers/deceased_cache.json"]:
        if _p and __import__("os").path.exists(_p):
            try: _dc = json.load(open(_p)); break
            except Exception: pass
    def _dod(pid):
        v = _dc.get(re.sub(r"\D", "", pid)) or {}
        d = v.get("dod") or ""
        return d if re.match(r"\d{4}-\d{2}-\d{2}$", d) else None
    # nursing and hospital visits of THIS batch per chart: the place-of-service rule reads them together with the chart's own history,
    # so the result does not depend on the order the messages are entered in
    try:
        for _m in PARSED:
            if unreadable(_m): continue                              # a message that is not entered (skipped_messages) shows no visit
            _p = MATCH.get(_m["name"].upper().strip() + "|" + _m["dob"][:8], {}).get("resolved")
            if not _p: continue
            for _bn in msg_buildings(_m):                        # the message's own building - every building its copies name (review C1): a visit in another building is then seen as a move
                for _c in _m.get("FT1") or []:
                    if (_c.get("cpt") in NF_VISIT or _c.get("cpt") in HOSP_VISIT or _c.get("cpt") in HOME_VISIT) and len(_c.get("dos") or "") >= 8:
                        BATCH_NF.setdefault(_p, set()).add((_c["cpt"], mdy(_c["dos"][:8]), _bn) if _bn else (_c["cpt"], mdy(_c["dos"][:8])))
        for _p, _ln in prior_seen:      # a visit an earlier batch could not enter still happened: the feed showed it
            try:                        # row by row: an odd row in an old register is skipped, it never switches the rule off
                if isinstance(_p, str) and _p and len(_ln) >= 2 and isinstance(_ln[0], str) and isinstance(_ln[1], str) and (_ln[0] in NF_VISIT or _ln[0] in HOSP_VISIT or _ln[0] in HOME_VISIT):
                    BATCH_NF.setdefault(_p, set()).add((_ln[0], _ln[1], _ln[2]) if len(_ln) > 2 and isinstance(_ln[2], str) and _ln[2] else (_ln[0], _ln[1]))
            except Exception: continue
    except Exception as e:
        BATCH_NF.clear(); BATCH_NF_ERR[0] = str(e)[:120] or type(e).__name__
        print("POS RULE: batch visit list not built (%s) - nursing-building lines stay at the feed's 31 this run (POS RULE NOT APPLIED)" % BATCH_NF_ERR[0])
    _qenv = (__import__("os").environ.get("QUALITY_CODE") or "").strip().lower()      # William's switches: off / stop / reset (the SWITCHES comment above); case and spaces do not matter
    # an import register of THIS year that is there but cannot be read (cut off, empty): the quality lines it holds are not known - no line
    # this run, and the report says so at the top from the second run in a row. A register whose stamp names no date counts as this year's.
    # The visits themselves are imported as always (the visit dedupe above passes such a file over, as it always did).
    _unread = [x for x in _unread if (lambda m: not m or m.group(1) == run_day().strftime("%Y"))(re.match(r"feed_import_(\d{4})-?\d{2}-?\d{2}T", _os.path.basename(x)))]
    _qf = {}; _qbad = ["the registers folder (it could not be read)"]      # until quality_files has read it (the option code M0004 reads the same)
    try:
        _qf = quality_files(STAMP); _qbad = list(_qf.get("problems") or []) + ["%s (not readable)" % x for x in _unread]
        quality_state(prior_regs, look=not dry and not _qbad, reset=(_qenv == "reset"), stop=(_qenv == "stop"), files=_qf)
        QUALITY["verify"] = _qf.get("verify") or {}; QUALITY["exceptions"] = _qf.get("exceptions") or set(); QUALITY["unread"] = sorted(_os.path.basename(x) for x in _unread)
        if _unread: QUALITY["off"] = QUALITY["off"] or "this run: the import register %s cannot be read - the state of the quality code is not known; no line until it is restored from the repository" % ", ".join(QUALITY["unread"])[:200]
        if _qbad: QUALITY["off"] = QUALITY["off"] or "this run: %s cannot be read - a hold, another payer or a patient William took out could be hidden there" % "; ".join(_qbad)[:200]
    except Exception as e:      # the state could not be read: NO line in this run (an unknown state is never treated as a fresh pilot)
        QUALITY.clear(); QUALITY.update(_quality_fresh()); QUALITY["off"] = "this run: the state of the quality code could not be read (%s)" % type(e).__name__
    if _qenv == "off": QUALITY["off"] = QUALITY["off"] or "this run: switched off (QUALITY_CODE=off)"
    elif _qenv not in ("", "stop", "reset"): QUALITY["off"] = QUALITY["off"] or "this run: QUALITY_CODE=%s is not a value the import knows (off, stop, reset) - no line added" % repr(_qenv[:20])
    if QUALITY["off"]: QUALITY["budget"] = 0
    _g0 = reg.get("quality_gate") if isinstance(reg.get("quality_gate"), dict) else {}      # the gate an earlier start under this same stamp wrote: its restart is kept when this run writes the gate again
    if QUALITY.get("reset"): QUALITY["reset_after"] = [len(reg["created"]), len(reg["failed"])]      # rows already in this stamp's register were written BEFORE the restart
    elif _g0.get("reset") is True: QUALITY["reset"] = True; QUALITY["reset_after"] = _g0.get("reset_after")
    # the option code M0004: its own ledger from the same registers, then its switches (MVP_CODE: off / reset; QUALITY_CODE=off / stop stop it too, since it
    # never rides without the 1123F line). Any doubt = no M0004 line in this run; the visits and the 1123F line are never touched by it.
    _menv = (__import__("os").environ.get("MVP_CODE") or "").strip().lower()
    try: mvp_state(prior_regs, look=not dry and not _qbad, reset=(_menv == "reset"), files=_qf)
    except Exception as e: MVP.clear(); MVP.update(_mvp_fresh()); MVP["off"] = "this run: the state of the option code M0004 could not be read (%s)" % type(e).__name__
    if _unread or _qbad: MVP["off"] = MVP["off"] or "this run: %s cannot be read - the state of the option code M0004 is not known" % "; ".join(sorted(set(_qbad + ["%s (not readable)" % x for x in _unread])))[:200]
    if _menv == "off": MVP["off"] = MVP["off"] or "this run: switched off (MVP_CODE=off)"
    elif _menv not in ("", "reset"): MVP["off"] = MVP["off"] or "this run: MVP_CODE=%s is not a value the import knows (off, reset) - no M0004 line added" % repr(_menv[:20])
    if QUALITY["off"]: MVP["off"] = MVP["off"] or "this run: the quality code is off (M0004 rides only with the 1123F line)"
    _mg0 = reg.get("mvp_gate") if isinstance(reg.get("mvp_gate"), dict) else {}      # an earlier start under this same stamp: its M0004 restart is kept
    if MVP.get("reset"): MVP["reset_after"] = [len(reg["created"]), len(reg["failed"])]
    elif _mg0.get("reset") is True: MVP["reset"] = True; MVP["reset_after"] = _mg0.get("reset_after")
    n = 0; stats = collections.Counter()
    if _skm: stats["FEED MESSAGE SKIPPED - could not be read; a person must look at the feed file"] += len(_skm)
    if _sku: stats["FEED MESSAGES SKIPPED NOT KNOWN - the parser's list could not be read"] += 1
    if BATCH_NF_ERR[0]: stats["POS RULE: batch visit list not built - nursing-building lines kept at the feed's 31"] += 1
    # A PROVISIONAL ROW (confirm review F5): before the call that carries the quality line, a failed row {quality_unknown, provisional} is written to
    # the register. When the answer comes and the visit's outcome is recorded, that row goes again (_unprov). When the run is cut while the call is
    # out (or an error stops the visit's handling after it), the row stays: the next start knows a line may exist that no row records - the code is
    # OFF until William has looked at that visit (section 6's own rule for a call nobody saw the end of), so a pilot never holds more than three lines.
    _prov = [None]
    def _unprov():
        if _prov[0] is not None: reg["failed"][:] = [x for x in reg["failed"] if x is not _prov[0]]; _prov[0] = None
    for msg in PARSED:
        _prov[0] = None
        if unreadable(msg): continue      # named above under skipped_messages: nothing of it is entered, and the batch goes on
        fid = msg["pid"]
        if one and fid != one: continue
        mkey = (fid, mdy(msg["FT1"][0]["dos"][:8]), tuple(sorted(c["cpt"] for c in msg["FT1"])))
        if mkey in done or (fid, None, None) in done: stats["already created"] += 1; continue
        k = msg["name"].upper().strip() + "|" + msg["dob"][:8]; pid = MATCH.get(k, {}).get("resolved")
        if not pid: stats["no chart"] += 1; continue
        if n >= limit: break
        try:
            dod = _dod(pid)
            if dod and any(c["dos"][:8] > dod.replace("-", "") for c in msg["FT1"]):
                stats["DOS after date of death - not entered"] += 1; reg["skipped"].append({"feed_id": fid, "pid": pid, "why": "DOS after date of death %s (deceased cache) - never billed" % dod})
                if not dry: json.dump(reg, open(REG, "w"), indent=1)      # a dry run writes nothing (11/10/2026, challenge review): its register would make the live run of the same stamp skip whole patients
                continue
            ctx = chart_ctx(pid); ctx["pid"] = pid
            if ctx.get("deceased"):
                stats["deceased chart - held"] += 1; reg["skipped"].append({"feed_id": fid, "pid": pid, "why": "deceased flag on chart - William"}); continue
            body, info = build(msg, ctx)
            if body is None:
                stats["skip: " + info] += 1
                reg["skipped"].append(dict({"feed_id": fid, "pid": pid, "why": info}, **({} if info == "all lines already in AMD" else {"lines": seen_lines(msg)}))); continue
            n += 1
            if info.get("pos_err"): print("POS RULE NOT APPLIED", pid, info["dos"], info["cpts"], info["pos_err"])
            if info.get("msg_own") is False and not info.get("pos_err"): print("POS CHECK not own message", pid, info["dos"], info["cpts"], "the raw files gave no single answer for this message - where its copies differ: %s; for William" % (info.get("msg_fallback") or "the patient's last-read values"))
            if info.get("prof_default"): print("POS CHECK clinician not known", pid, info["dos"], info["cpts"], "the feed message names no clinician id the profile table has - entered under the physician profile; for William")
            if info.get("prof_feed"): print("INITIAL VISIT under the physician", pid, info["dos"], "- the feed named", info["prof_feed"])      # William 11/10/2026: every initial nursing-facility visit is his
            if not info.get("fac"): print("POS CHECK no facility", pid, info["dos"], info["cpts"], "the message's building is not in the facility table - entered without a facility at the feed's place of service; for William")
            if dry:
                print("DRY", pid, info); stats["dry"] += 1; stats["dry quality"] += 1 if info.get("quality_codes") else 0; stats["dry mvp"] += 1 if info.get("mvp_codes") else 0; count_pos(info, stats)
                if info.get("quality_skipped") == "hospital": stats["quality code not added: hospital visit (hospital visits are not coded in this version)"] += 1
                continue
            create, body, plain = body
            r0 = amd.post(create, timeout=120)
            vm = re.search(r'<visit id="(vst\d+)"', r0)
            if not vm:
                quality_undo(info, pid, fid); mvp_undo(info)
                stats["FAULT create"] += 1; reg["failed"].append({"feed_id": fid, "pid": pid, "info": info, "lines": seen_lines(msg), "err": "addvisit: " + re.sub(r"\s+", " ", r0[:500])})
                print("FAULT addvisit", pid, info["dos"], re.sub(r"\s+", " ", r0[:200])); json.dump(reg, open(REG, "w"), indent=1); continue
            if info.get("quality_codes"):      # the provisional row (see above), written before the call that carries the line
                _prov[0] = {"feed_id": fid, "pid": pid, "info": dict(info, **({"mvp_tried": info.get("mvp_fee") or "0.00"} if info.get("mvp_codes") else {})), "lines": seen_lines(msg),
                            "empty_visit": vm.group(1), "quality_unknown": info.get("quality_fee") or "0.00", "provisional": True,
                            "err": "provisional: the call that carries the quality line was sent; the run ended before its answer was recorded - William looks at that visit"}
                reg["failed"].append(_prov[0]); json.dump(reg, open(REG, "w"), indent=1)
            try: r = amd.post(body.replace("%VISIT%", vm.group(1)), timeout=180)
            except Exception as e:
                if not info.get("quality_codes"): raise
                _unprov()
                # The call that carried the quality line ended in an error (a time-out). Nobody knows whether AdvancedMD kept the visit and the line. So nothing
                # is sent again, no further line is tried in this run, and the code is OFF until William has looked at that visit and restarts it.
                if info.get("mvp_codes"):      # it carried the M0004 line too: M0004 is OFF until William restarts it as well (the failed row says so to the next run)
                    info["mvp_codes"] = []; info["mvp_tried"] = info.get("mvp_fee") or "0.00"; MVP["off"] = MVP["off"] or "this run: a call that carried M0004 ended in an error"
                    MVP["off_until_reset"] = MVP.get("off_until_reset") or "a call that carried M0004 ended in an error; nobody knows what AdvancedMD kept of that visit - William looks (chart %s, visit %s, %s)" % (pid, vm.group(1), __import__("os").path.basename(REG))
                _fee0 = info.get("quality_fee"); _yr = str(info.get("quality_dos") or info["dos"])[-4:]; info["quality_codes"] = []; info["quality_tried"] = _fee0
                QUALITY["refused"].add((pid, _yr)); QUALITY["done"].add((pid, _yr)); QUALITY["off"] = QUALITY["off"] or "this run: a call that carried the code ended in an error (%s)" % type(e).__name__
                QUALITY["off_until_reset"] = QUALITY.get("off_until_reset") or "a call that carried the quality line ended in an error; nobody knows whether AdvancedMD kept that visit - William looks (chart %s, visit %s, %s)" % (pid, vm.group(1), __import__("os").path.basename(REG))
                stats["error"] += 1; stats["QUALITY CODE: a call that carried the line ended in an error - William looks at that visit"] += 1
                reg["failed"].append({"feed_id": fid, "pid": pid, "info": info, "lines": seen_lines(msg), "empty_visit": vm.group(1), "quality_unknown": _fee0, "err": str(e)[:400]}); print("ERR", pid, str(e)[:200])
                json.dump(reg, open(REG, "w"), indent=1); continue
            if ("Fault" in r or 'success="0"' in r) and info.get("mvp_codes"):
                # A visit that carried 1123F AND M0004 was refused (8.4). The visit always goes in: once a fresh read of the chart (three tries) shows nothing
                # of it stored, the SAME visit goes in with the 1123F line only - that form is proven. Accepted: M0004 was the cause - OFF until William
                # restarts it (MVP_CODE=reset), no second try. Refused too: M0004 is not blamed - the block below reads the chart again and enters the
                # visit without the line, and the refusal counts against 1123F. The chart shows part of the visit, or cannot be read: nothing is tried
                # here, the block below leaves that visit for William as it always did, and M0004 is OFF until restarted.
                _mwhy = re.sub(r"\s+", " ", r[:200]); _vid = vm.group(1); _wreg = __import__("os").path.basename(REG)
                _mmine = set(zip(info["cpts"], info.get("dos_lines") or [info["dos"]] * len(info["cpts"]))) | {(QUALITY_CODE, info.get("quality_dos")), (MVP_CODE, info.get("mvp_dos"))}
                mvp_undo(info); info["mvp_codes"] = []; info["mvp_tried"] = info.get("mvp_fee") or "0.00"
                for _try in (1, 2, 3):
                    try: _ms = sorted(chart_lines_now(pid) & _mmine); break
                    except Exception as e:
                        _ms = ["chart not read: %s" % type(e).__name__]
                        if _try < 3: time.sleep(1.0)
                if _ms:
                    MVP["off"] = MVP["off"] or "this run: a visit with M0004 was refused and the chart could not be shown free of it"
                    MVP["off_until_reset"] = MVP.get("off_until_reset") or "AdvancedMD refused a visit that carried M0004 and the chart did not show it free of that visit - William looks (chart %s, visit %s, %s)" % (pid, _vid, _wreg)
                    stats["OPTION CODE M0004: a visit that carried it was refused and the chart shows part of it or could not be read"] += 1
                else:
                    try: r = amd.post(re.sub(r'<charge id=""(?:(?!</charge>).)*proccode="%s"(?:(?!</charge>).)*</charge>' % MVP_PCODE, "", body).replace("%VISIT%", _vid), timeout=180)      # the same request with the M0004 line taken out
                    except Exception as e:      # the 1123F-only form ended in an error (a time-out): as for any call that carried the 1123F line - nothing is sent again, OFF until William has looked
                        _fee0 = info.get("quality_fee"); _yr = str(info.get("quality_dos") or info["dos"])[-4:]; info["quality_codes"] = []; info["quality_tried"] = _fee0
                        QUALITY["refused"].add((pid, _yr)); QUALITY["done"].add((pid, _yr)); QUALITY["off"] = QUALITY["off"] or "this run: a call that carried the code ended in an error (%s)" % type(e).__name__
                        QUALITY["off_until_reset"] = QUALITY.get("off_until_reset") or "a call that carried the quality line ended in an error; nobody knows whether AdvancedMD kept that visit - William looks (chart %s, visit %s, %s)" % (pid, _vid, _wreg)
                        MVP["off"] = MVP["off"] or "this run: a visit with M0004 was refused"
                        MVP["off_until_reset"] = MVP.get("off_until_reset") or "AdvancedMD refused a visit that carried M0004, and the same visit sent with the 1123F line only ended in an error - William looks (chart %s, visit %s, %s)" % (pid, _vid, _wreg)
                        stats["error"] += 1; stats["QUALITY CODE: a call that carried the line ended in an error - William looks at that visit"] += 1
                        _unprov(); reg["failed"].append({"feed_id": fid, "pid": pid, "info": info, "lines": seen_lines(msg), "empty_visit": _vid, "quality_unknown": _fee0, "err": str(e)[:400]}); print("ERR", pid, str(e)[:200])
                        json.dump(reg, open(REG, "w"), indent=1); continue
                    if "Fault" in r or 'success="0"' in r: info["mvp_form_refused"] = True      # refused with the 1123F line only as well: M0004 is not the cause (the block below)
                    else:
                        info["mvp_refused"] = _mwhy; MVP["off"] = MVP["off"] or "this run: AdvancedMD refused a visit that carried M0004"
                        MVP["off_until_reset"] = MVP.get("off_until_reset") or "AdvancedMD refused a visit that carried M0004 and took it with the 1123F line only - no second try (chart %s, visit %s, %s)" % (pid, _vid, _wreg)
                        stats["OPTION CODE M0004 NOT ACCEPTED by AdvancedMD - the visit was entered with the 1123F line only"] += 1; print("OPTION CODE M0004 REFUSED", pid, info["dos"], _mwhy[:160])
            if ("Fault" in r or 'success="0"' in r) and info.get("quality_codes"):
                # A visit that carried the quality line was refused. A reporting code never holds a charge: the SAME visit goes in without the
                # line - but only when a fresh read of the chart shows that nothing of this visit was stored (a second send would double it).
                # The chart is read up to three times: one failed read must not leave a visit un-entered.
                _why = re.sub(r"\s+", " ", r[:200]); _fee0 = info.get("quality_fee"); _mine = set(zip(info["cpts"], info.get("dos_lines") or [info["dos"]] * len(info["cpts"]))) | {(QUALITY_CODE, info.get("quality_dos"))} | ({(MVP_CODE, info.get("mvp_dos"))} if info.get("mvp_tried") else set())
                _yr = str(info.get("quality_dos") or info["dos"])[-4:]
                quality_undo(info, pid, fid); info["quality_codes"] = []; info["quality_tried"] = _fee0
                for _try in (1, 2, 3):
                    try: _stored = sorted(chart_lines_now(pid) & _mine); break
                    except Exception as e:
                        _stored = ["chart not read: %s" % type(e).__name__]
                        if _try < 3: time.sleep(1.0)
                if _stored:      # the fault came, but the chart shows the visit (or cannot be read): NOT sent again. The code is OFF until William has looked at that visit
                    QUALITY["refused"].add((pid, _yr)); QUALITY["done"].add((pid, _yr))
                    QUALITY["off"] = QUALITY["off"] or "this run: a visit with the code was refused and the chart could not be shown free of it"
                    QUALITY["off_until_reset"] = QUALITY.get("off_until_reset") or (("AdvancedMD answered a fault to a visit that carried the quality line and the chart could not be read afterwards - William looks (chart %s, visit %s, %s)"
                        if any(isinstance(x, str) for x in _stored) else "AdvancedMD answered a fault but kept the visit - William looks (chart %s, visit %s, %s)") % (pid, vm.group(1), __import__("os").path.basename(REG)))
                    stats["FAULT"] += 1; stats["QUALITY CODE: visit refused and NOT sent again (the chart shows part of it, or could not be read)"] += 1
                    _unprov(); reg["failed"].append({"feed_id": fid, "pid": pid, "info": info, "lines": seen_lines(msg), "empty_visit": vm.group(1), "stored": [list(x) if isinstance(x, tuple) else x for x in _stored],
                                          "err": "refused with the quality line; not sent again because the chart shows %s - William looks at that visit: %s" % (_stored, _why)})
                    print("FAULT", pid, info["dos"], info["cpts"], "refused with the quality line; chart shows", _stored); json.dump(reg, open(REG, "w"), indent=1); continue
                try: r = amd.post(plain.replace("%VISIT%", vm.group(1)), timeout=180)
                except Exception as e:      # the send WITHOUT the line failed (a time-out): no further line in this run, and the next run counts this like a refusal (quality_sent = the amount that was refused)
                    QUALITY["refused"].add((pid, _yr)); QUALITY["done"].add((pid, _yr)); QUALITY["off"] = QUALITY["off"] or "this run: a visit refused with the code could not be sent without it either (%s)" % type(e).__name__
                    stats["error"] += 1; _unprov(); reg["failed"].append({"feed_id": fid, "pid": pid, "info": info, "lines": seen_lines(msg), "empty_visit": vm.group(1), "quality_sent": _fee0, "err": str(e)[:400]}); print("ERR", pid, str(e)[:200])
                    json.dump(reg, open(REG, "w"), indent=1); continue
                if "Fault" in r or 'success="0"' in r:      # refused without the line as well: the quality code is not the cause
                    QUALITY["twice"] += 1
                    if QUALITY["twice"] >= 2: QUALITY["off"] = QUALITY["off"] or "this run: two visits were refused with and without the code - no further line tried"
                else:
                    info["quality_refused"] = _why; info["quality_refused_fee"] = _fee0; QUALITY["refused"].add((pid, _yr)); QUALITY["done"].add((pid, _yr))      # that patient gets no second try this year
                    QUALITY["off"] = QUALITY["off"] or "this run: AdvancedMD refused a visit that carried the code"
                    stats["QUALITY CODE NOT ACCEPTED by AdvancedMD - the visit was entered without it"] += 1; print("QUALITY CODE REFUSED", pid, info["dos"], _why[:160])
            if "Fault" in r or 'success="0"' in r:
                stats["FAULT"] += 1; _unprov(); reg["failed"].append({"feed_id": fid, "pid": pid, "info": info, "lines": seen_lines(msg), "empty_visit": vm.group(1), "err": re.sub(r"\s+", " ", r[:600])})
                print("FAULT", pid, info["dos"], info["cpts"], re.sub(r"\s+", " ", r[:300]))
            else:
                vid = re.search(r'<visit id="(vst\d+)"', r); cids = re.findall(r'<charge id="(charge\d+)"', r)
                fees = re.findall(r'<charge [^>]* fee="([^"]*)"', r)
                # what AdvancedMD stored: its answer echoes the charges - compare their place of service with what was sent (any order).
                # pos_stored None = the answer did not carry it for every line (then nothing is claimed either way)
                _qidx = None; _midx = None; _ans = []
                try:
                    if info.get("quality_codes"):      # find the quality charge first: the comparison below is about the visit's OWN lines
                        _ans = answer_charges(r)
                        if info.get("mvp_codes"): _qidx, _midx = lines_in_answer(_ans, len(info["cpts"]), info.get("quality_fee"))      # 8.5: the 1123F line AND the M0004 line
                        else: _qidx = quality_in_answer(_ans, len(info["cpts"]), info.get("quality_fee"))
                        _own = [c for i, c in enumerate(_ans) if i != _qidx and i != _midx]; _st = [c[3] for c in _own if c[3]]
                        if len(_st) != len(_own): _st = []
                        if _qidx is not None and _ans[_qidx][3]: info["quality_pos_stored"] = _ans[_qidx][3]
                        if _midx is not None and _ans[_midx][3]: info["mvp_pos_stored"] = _ans[_midx][3]
                    else:
                        _st = re.findall(r'<charge id="charge\d+"[^>]*?\bpos="(\d+)"', r)
                    info["pos_stored"] = _st if len(_st) == len(info["pos_lines"]) else None
                    if (info["pos_stored"] is not None and sorted(_st) != sorted(info["pos_lines"])) or (info.get("quality_pos_stored") and info.get("quality_pos") and info["quality_pos_stored"] != info["quality_pos"]) \
                            or (info.get("mvp_pos_stored") and info.get("mvp_pos") and info["mvp_pos_stored"] != info["mvp_pos"]):
                        stats["ADVANCEDMD DID NOT KEEP THE PLACE OF SERVICE (stored differs from sent)"] += 1
                        print("POS NOT KEPT", pid, info["dos"], info["cpts"], "sent", info["pos_lines"], "stored", _st, (("quality line sent %s stored %s" % (info.get("quality_pos"), info.get("quality_pos_stored"))) if info.get("quality_pos_stored") else "")
                              + ((" M0004 line sent %s stored %s" % (info.get("mvp_pos"), info.get("mvp_pos_stored"))) if info.get("mvp_pos_stored") else ""))
                except Exception: info["pos_stored"] = None
                if info["admit"] and any(c in HOSP for c in info["cpts"]):
                    # the extins child is ignored on create - write the admission date with the proven updextrainsinfo shape
                    for cpt in info["cpts"]:
                        if cpt in HOSP:
                            ext = ('<extins txtChargeCode="%s" hospitalizationfrom="%s" patsignature="1" emergency="0" epsdt="0" payprov="1" employment="0" '
                                   'autoaccident="0" otheraccident="0" pregnant="0" outsidelab="0"/>') % (cpt, mdy(info["admit"][:8]))
                            re_ = amd.post(amd.msg("updextrainsinfo", "chargeentry", {"visitid": vm.group(1), "nocookie": "1"}, ext), timeout=120)
                            info["admit_written"] = "Fault" not in re_ and 'hospitalizationfrom="%s"' % mdy(info["admit"][:8]) in re_
                if info.get("quality_codes") and info.get("mvp_codes"):      # 8.5: the 1123F line and the M0004 line; "charges" = the visit's own charges in the answer's order, THEN the 1123F charge, THEN the M0004 charge
                    _qc = _ans[_qidx][0] if _qidx is not None else ""; _mc = _ans[_midx][0] if _midx is not None else ""; info["quality_charge"] = _qc; info["mvp_charge"] = _mc
                    if not _qc:      # the 1123F line was not shown stored: as for a visit stored without its quality line
                        quality_undo(info, pid, fid); info["quality_not_stored"] = info.get("quality_fee") or "0.00"; info["quality_codes"] = []
                        stats["QUALITY CODE: AdvancedMD stored the visit WITHOUT the line"] += 1
                        QUALITY["off"] = QUALITY["off"] or "this run: AdvancedMD stored a visit without its quality line"
                    if not _mc:      # the M0004 line was not shown stored: OFF until William restarts it (no second try)
                        mvp_undo(info); info["mvp_not_stored"] = info.get("mvp_fee") or "0.00"; info["mvp_codes"] = []; stats["OPTION CODE M0004: AdvancedMD stored the visit WITHOUT the M0004 line"] += 1
                        MVP["off"] = MVP["off"] or "this run: AdvancedMD stored a visit without its M0004 line"
                        MVP["off_until_reset"] = MVP.get("off_until_reset") or "AdvancedMD stored a visit without its M0004 line - William looks (chart %s, visit %s, %s)" % (pid, vid.group(1) if vid else "?", __import__("os").path.basename(REG))
                    elif not _qc:    # the M0004 line stands on a claim without the 1123F line: OFF until William has looked
                        MVP["off"] = MVP["off"] or "this run: AdvancedMD stored the M0004 line of a visit without its 1123F line"
                        MVP["off_until_reset"] = MVP.get("off_until_reset") or "AdvancedMD stored the M0004 line of a visit without its 1123F line - William looks (chart %s, visit %s, %s)" % (pid, vid.group(1) if vid else "?", __import__("os").path.basename(REG))
                    _nc = [x for x in (_qc, _mc) if x]
                    if len(fees) == len(cids): fees = [f_ for c_, f_ in zip(cids, fees) if c_ not in _nc]
                    cids = [c for c in cids if c not in _nc] + _nc
                elif info.get("quality_codes"):
                    info["quality_charge"] = _ans[_qidx][0] if _qidx is not None else ""      # by procedure, else by amount, else the last of an unnamed list
                    if not info["quality_charge"]:      # the visit was stored, the line was not: the next run reads this like a refusal
                        quality_undo(info, pid, fid); info["quality_not_stored"] = info.get("quality_fee") or "0.00"; info["quality_codes"] = []
                        stats["QUALITY CODE: AdvancedMD stored the visit WITHOUT the line"] += 1
                        QUALITY["off"] = QUALITY["off"] or "this run: AdvancedMD stored a visit without its quality line"
                    else:      # "fees" stays one amount per message code; "charges" = the visit's own charge numbers in the answer's order, THEN the quality charge - so charges[0] is always the visit's own charge and the two lists pair in order
                        try:
                            _i = cids.index(info["quality_charge"])
                            if len(fees) == len(cids): fees = fees[:_i] + fees[_i + 1:]
                        except Exception: pass
                        cids = [c for c in cids if c != info["quality_charge"]] + [info["quality_charge"]]
                _ops = ctx.get("open_plan_seqs")      # 11/10/2026 (round 7): the chart's own order and open plans when this visit was entered (None = not read)
                info["chart_insorder"] = ctx.get("chart_insorder"); info["open_plans_at_entry"] = len(_ops) if isinstance(_ops, list) else None; info["open_plan_seqs_at_entry"] = _ops
                _unprov(); reg["created"].append({"feed_id": fid, "pid": pid, "visit": vid.group(1) if vid else "", "charges": cids, "fees": fees, "at": datetime.datetime.utcnow().isoformat(), **info})
                if info["open_plans_at_entry"] == 0 or info["chart_insorder"] == "":
                    stats["NO PLAN AT ENTRY"] += 1
                    print("NO PLAN AT ENTRY", pid, vid.group(1) if vid else "?", info["dos"], "- %s: AdvancedMD built no insurance order for this visit; it bills only after a plan is added AND the visit is saved again (the insurance check does that)" % (
                        "the chart had no open plan" if info["open_plans_at_entry"] == 0 else "the chart had no insurance order"))
                for cpt, _d in zip(info["cpts"], info.get("dos_lines") or [info["dos"]] * len(info["cpts"])): ctx["live"].add((cpt, _d))   # each line under its OWN date
                if info.get("quality_codes") and info.get("quality_charge"):
                    ctx["live"].add((QUALITY_CODE, info.get("quality_dos") or info["dos"])); stats["quality code 1123F added (advance care plan)"] += 1
                if info.get("mvp_codes") and info.get("mvp_charge"):      # that clinician's M0004 line of the year: waiting for its outcome
                    ctx["live"].add((MVP_CODE, info.get("mvp_dos") or info["dos"])); stats["option code M0004 added"] += 1
                    MVP.setdefault("clinicians", {}).setdefault(info.get("mvp_prof") or "?", {}).update(state="waiting", year=str(info.get("mvp_dos") or "")[-4:], visit=vid.group(1) if vid else "", charge=info["mvp_charge"], billed="", since=__import__("os").path.basename(REG))
                if info.get("quality_skipped") == "hospital":      # met every other condition: counted for the report (hospital visits are not coded in this version)
                    QUALITY["skipped_hospital"] = int(QUALITY.get("skipped_hospital") or 0) + 1; stats["quality code not added: hospital visit (hospital visits are not coded in this version)"] += 1
                stats["created"] += 1; stats["charge lines"] += len(cids) - (1 if info.get("quality_charge") else 0) - (1 if info.get("mvp_charge") else 0); count_pos(info, stats)
                print("OK", pid, info["dos"], info["cpts"], vid.group(1) if vid else "?", cids, fees)
            json.dump(reg, open(REG, "w"), indent=1)
            time.sleep(0.6)
        except Exception as e:
            stats["error"] += 1; reg["failed"].append({"feed_id": fid, "pid": pid, "lines": seen_lines(msg), "err": str(e)[:400]}); print("ERR", pid, str(e)[:200])
            if not dry: json.dump(reg, open(REG, "w"), indent=1)      # a dry run writes nothing (see the date-of-death skip above)
        if n % 25 == 0 and n: print("progress", n, dict(stats))
    # 10/29 05:49Z lesson: a live batch whose every line was already in AMD created nothing and so wrote NO import register (verify,
    # inspector, report and the recon then had nothing to read). The register is now always written at the end of a live run, skips included.
    _qn = stats["dry quality"] if dry else stats["quality code 1123F added (advance care plan)"]
    try:      # inside a try: a failure here never loses the register (the next run finds every line again in the rows)
        reg["quality_gate"] = quality_gate(REG, 0 if dry else _qn); json.dumps(reg["quality_gate"])
    except Exception as e:
        reg["quality_gate"] = {"code": QUALITY_CODE, "off": "this run: the state of the quality code could not be written (%s)" % type(e).__name__, "reset": bool(QUALITY.get("reset")), "notes": []}
    _mn = stats["dry mvp"] if dry else stats["option code M0004 added"]
    try:      # the option code M0004's own gate, the same way (a failure never loses the register: the next run finds every M0004 line again in the rows)
        reg["mvp_gate"] = mvp_gate(); json.dumps(reg["mvp_gate"])
    except Exception as e:
        reg["mvp_gate"] = {"code": MVP_CODE, "off": "this run: the state of the option code M0004 could not be written (%s)" % type(e).__name__, "reset": bool(MVP.get("reset")), "notes": []}
    if not dry: json.dump(reg, open(REG, "w"), indent=1)
    try: print(quality_log(_qn, dry))
    except Exception as e: print("QUALITY 1123F: this line could not be built (%s) - read quality_gate in the import register" % type(e).__name__)
    try: print(mvp_log(_mn, dry))
    except Exception as e: print("QUALITY M0004: this line could not be built (%s) - read mvp_gate in the import register" % type(e).__name__)
    _pk = lambda w: sum(v for k, v in stats.items() if k.startswith(w))
    if _pk("ADVANCEDMD DID NOT KEEP") or _pk("feed message not matched") or _pk("clinician id of the feed message") or _pk("visit entered with NO facility"):
        # one SHORT line, like the next one (90 characters with one-digit counts, 110 with six-digit counts in all four places)
        print("POS CHECK: stored another POS x%d; not own message x%d; clinician unknown x%d; no facility x%d" % (
            _pk("ADVANCEDMD DID NOT KEEP"), _pk("feed message not matched"), _pk("clinician id of the feed message"), _pk("visit entered with NO facility")))
    # one SHORT line (the ingest shows 110 characters of each of the last three log lines): 91 characters with one-digit counts
    print("POS RULE: CCM 32 x%d, CCM 31 x%d, visits 32 x%d, visits 31 x%d, not applied x%d, unknown bldg x%d" % (
        _pk("POS 32 CCM"), _pk("POS 31 CCM"), _pk("POS 32 nursing"), _pk("POS 31 nursing"), _pk("POS RULE NOT APPLIED"), _pk("POS RULE: building")))
    print("DONE", dict(stats))
if __name__ == "__main__": main()
