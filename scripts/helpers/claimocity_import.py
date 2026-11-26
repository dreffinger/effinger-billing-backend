# PLAIN ENGLISH (Claimocity backlog import, William 10/28/2026 02:23 ET: "enter all of these encounters into advanced md
#   and bill them out, i dont care if we get duplicates later" - Gregg's pickup paused).
# Decides: for every DFT^P03 message in the 10/16-10/27 SFTP files whose patient has an AMD chart, creates the visit with
#   its charges (updvisitwithnewcharges on a NEW visit: id=""), diagnosis list, admission date on hospital stays, modifier
#   25 on 99497 / 99489 as the practice's existing charges carry it, facility/POS/profile copied from how the feed's own
#   earlier visits look in AMD. Charges enter Charge Review (approval=1, inspector on) like any feed charge.
# Dedupe: a feed line whose patient already has a live (non-void) charge with the same CPT + DOS is skipped.
# Modifier 25 and Humana (William 11/25/2026, "yes try that"): the 99489 add-on of a chart whose first plan in billing order is Humana goes in WITHOUT modifier 25 (Humana denies it
#   with the modifier - CO-4); the row says so (no_mod25). The order read is the chart's OWN: a chart with no billing order is built as before, with the modifier (the "1" its
#   visit is created with is a stand-in, not its first plan). The standing CCM gate's helper (mod25_addon.py) reads the same rule from this file. See NO_MOD25 below.
# Whose chart (11/25/2026, William: a feed patient goes to the chart that patient already has): the match file names a chart for EACH Claimocity id of an entry (by_id - the driver
#   writes it) and a message is entered on its OWN id's chart (chart_of); an id the entry does not name has no chart and is not entered. Until then the chart came from the
#   name-and-date key alone, so two feed patients under one name and one birth date shared a chart.
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
#   99487/99489 -> 32, EVERY line (William 11/25/2026: never the skilled-nursing 31 - also when the chart shows a skilled-looking
#   month, when the rule fails or when the building is not in the facility table); a nursing facility visit -> 32 for the monthly
#   visit, 31 when the resident is seen once or twice a week or the chart shows a new stay; whatever the chart does not show stays 31.
#   ALF / home (13) and hospital (21) lines, and every other line from an unknown building, are entered exactly as before. See NF_KINDS /
#   nf_visit_kind / pos_lines / ccm_never_31 below.
# Inpatient rehab stays (William 11/25/2026, STANDING - practices/ehpa/rules.md): "i now follow patients after dc from the inpatient hospital and admit them to
#   inpatient rehab"; asked whether the rehab visits go on 61: "yes and let us monitor them to make sure they pay and dont deny the ones were already paying with the
#   inpatient hosptial as the place oif service". The feed names the HOSPITAL building for the rehab unit's visits too, so a hospital visit is read for its STAY: a stay
#   starts at each initial hospital visit of ours, and it is a REHAB stay when a feed message of it names the unit's own number in its PV1 line, or when its initial visit
#   is dated 1 or 2 days after the last visit of an acute stay. A visit of a rehab stay goes in at HCA REHAB (fac67) with every charge line at place of service 61.
#   NO LOOK-BACK, NO MIXING: the visits of a stay whose initial visit sits on the chart at 21 keep 21 (pos_kind rehab-stay-kept-21 - the group pos61_monitor.py compares
#   the 61 visits with); a claim already sent is never changed. Any error = the visit goes in as before (fac29 / 21) and pos_err says so. No quality line at 61. The
#   register row of every such hospital visit carries "stay" {kind, initial, sign}. See INPATIENT REHAB STAYS below.
#   11/25/2026 (review): a stay is never 61 beside 21 because its messages came in another order. The initial visit comes AFTER follow-ups that already went in at 21 = the
#   whole stay keeps 21; a follow-up read before an initial visit of the same file that goes in as before = kept at 21 with it. The unit's number is the sign of the message
#   that carries it: on the initial visit it makes the stay a rehab stay, on one follow-up it never moves the admission and the other visits. A hospital code the same-day
#   rule passes over is still read by this rule, in every later run too (the register's "same_day" list), and a stay that began on such a day shows no acute stay. What
#   cannot be prevented is SAID: an initial visit that starts a hospital stay one of whose visits already went in at 61 carries pos_err "PLACE OF SERVICE 61 on <day> ...".
#   11/25/2026 (verification of the pull request): our own nursing-facility and home / assisted-living visits are read too. An initial visit 1 or 2 days after an acute stay is
#   NO admission to the rehab unit when one of them lies between the two (the patient had left the hospital), and a stay holds no follow-up behind such a visit; an initial
#   visit 1 or 2 days behind a hospital visit that no stay holds is entered as before and shows no acute stay; a late initial visit keeps 21 with such visits. A stay that is
#   visibly going on is not cut at its 46th day (STAY_GOES_ON_DAYS). No follow-up goes in at 61 behind an initial visit that was NOT entered (a code the table does not have, a
#   visit AdvancedMD did not take), and the stay's initial visit looks ahead at its follow-ups' messages the way a follow-up looks ahead at the initial visit's. A stay that is
#   no rehab stay but holds visits at HCA REHAB shows no acute stay; a follow-up that goes in at 21 behind such visits SAYS so (pos_err "PLACE OF SERVICE 61 on <days>, 21
#   here: the stay is MIXED ..."). Every pos_err of this rule says what matters in its first 70 characters (the digest shows no more), the row names the days in a list of its
#   own (hospital_at61 / mixed_at61), and a day is named ONCE. The counters go by what AdvancedMD stored where it was read back: a rehab visit stored at 21 is not counted as
#   entered at 61.
#   11/25/2026 (second round, after the independent check of those fixes): one of our nursing-facility or home visits shows that the patient had left the hospital ONLY when its
#   row stands in one of the practice's nursing-facility or home / assisted-living buildings (away_building). A nursing code whose own message names the hospital is entered at the
#   hospital building and says nothing about where the patient was: it is not read - and neither is one with no building (behind such a row a rehab stay had dropped to 21
#   without a word). A stay whose last visit is its DISCHARGE visit is over: a hospital follow-up behind it with no new initial visit of ours is in no stay, inside the first 45
#   days too (REHAB_OVER). And what an ENTERED message noted for the stay rule is not taken back when the same visit comes again in a message the import skips (stay_kept).
# Quality code (William 11/10/2026, STANDING - practices/ehpa/rules.md): the advance-care-plan code 1123F goes on as a no-charge line, once
#   per patient per year, with the next nursing-facility, home or assisted-living visit of every patient 65 or older whose first plan is
#   Medicare Part B and whose last insurance check showed Medicare first (hospital visits are not coded in this version). A pilot first;
#   any doubt means no line; the visit itself always goes in. See QUALITY_* below. Once that pilot is proven, the option code M0004 rides
#   with the 1123F line once per clinician per year (William 11/10/2026: "use it"). See MVP_* below.
# 11/12/2026 (William 11/11/2026: "dont stop this dont let it stop make sure this suceeds"): the code never switches itself off. Where it
#   used to go off it probes - one line a run until one is billed - or pauses for one run; only William's own QUALITY_CODE=stop lasts. See
#   THE CODE NEVER SWITCHES ITSELF OFF below.
# Diagnosis codes (William 11/25/2026, STANDING: "for any diagnosis not in the master file yet change it to i10 and send me an email with the codes
#   needed to be added"): AdvancedMD only takes a diagnosis code that is in the practice's own list (Master Files > Diagnosis Codes; the cache DXCACHE
#   holds each feed code's id there, null = not in the list). A code of a charge line that is not in the list goes in as I10 IN ITS PLACE in the
#   line's order - as long as I10 itself is in the list - and I10 never stands twice on such a line; at most 12 codes a line, as before. The register
#   row still names every such code (missing_dx) and says what stands in its place (dx_instead); claimocity_report.py puts them into the digest and
#   writes the text of William's email. A charge line with NO code at all is still skipped ("no usable dx for <CPT>" - there is nothing to change),
#   and without I10 in the list everything is as before that day: the code is left off, and a line with no usable code skips the visit. See DX_INSTEAD.
# CCM and a patient who has passed away - William's word of 11/25/2026: before a CCM message (99487 / 99489) is entered, Medicare is asked for a date of death (the deceased guard's own
#   check; a kept answer younger than 30 days and asked on or after the CCM date is used as it is). A death before the CCM date = the message is never entered, in the
#   month it is found and in every month after. Until that day only a death an earlier look-up had cached kept a CCM charge out. A look-up that fails keeps nothing out.
# A feed message with no charge line, or with no patient id (11/25/2026): passed over and counted - it never stops the import. Where it has a feed id
#   it leaves ONE skipped row with that plain reason; that row never makes a second start of the same batch pass the patient over.
# William 11/25/2026 ("correct every one that comes to the correct date of birth and insurance and fix them ... where we know the correct dob but claimocity sends the
#   wrong one or the 01011900 default date") - the chart's own birth date: the feed can carry a wrong birth date, or the year-1900 placeholder, for a patient whose
#   chart holds the right one. After the match the chart is the patient. The import keeps the chart's own birth date and name from the chart answer it already reads (no
#   extra call; in memory only - never printed, never written). Every register row says how the feed's birth date compares with it (dob_note: "same", "differs: one
#   digit", "no birth date from Claimocity" ... - fixed words, never a date). The age of the 1123F rule comes from the chart's birth date when that is a real one, else
#   from the feed's as before. The run prints ONE line "BIRTH DATES: ..." with chart ids only, and nothing when every date is the same. See THE CHART'S OWN BIRTH DATE.
#   A chart whose own answer could not be read says "chart not read" (11/25/2026, review) - never "chart has no birth date", which nobody knows then.
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
def chart_of(m):
    """The AdvancedMD chart of ONE feed message - or None (no chart: the message is not entered). 11/25/2026 (William: a feed patient goes to the chart he already has - never a second
    one, never another patient's): the match file is keyed by name and birth date, and until now the chart was taken from that key alone - two feed patients under one name and birth date
    (a namesake, the placeholder date, a second Claimocity id of one person) shared ONE chart. The driver now names a chart per Claimocity id in every entry ("by_id"): the message's OWN id
    decides, and an id the entry does not name has no chart - it is never entered on the other id's chart by the name alone. An entry without by_id (an older match file, the retry's of an
    older driver) is read as before: the key's "resolved". Never raises."""
    try:
        e = MATCH.get(str(m.get("name") or "").upper().strip() + "|" + str(m.get("dob") or "")[:8])
        if not isinstance(e, dict): return None
        if isinstance(e.get("by_id"), dict):
            p_ = e["by_id"].get(m.get("pid"))
            return p_ if isinstance(p_, str) and p_ else None
        return e.get("resolved")
    except Exception: return None
DX = json.load(open(DXCACHE))
DX_INSTEAD = "I10"      # William 11/25/2026 (STANDING): "for any diagnosis not in the master file yet change it to i10 and send me an email with the codes needed to be added" - said right after "Add diagnosis S82.843D in AMD Master Files change this diagnosis to i10". The code build() puts in the place of a feed diagnosis code AdvancedMD's list does not have; claimocity_retry_dx.py carries the same line
REG = ("registers/feed_import_%s.json" % STAMP)
# 11/25/2026 (feed review): why a message that carries nothing to enter is passed over - the counters of the DONE line, and the reason in its skipped row
NO_LINES_WHY = "feed message without a charge line - passed over"
NO_PID_WHY = "feed message without a patient id - passed over"
# 11/25/2026 (the second verification of the death check): the fixed words of a visit that is NOT entered because a date of death is on record for its chart and
# nobody can name the day (the cache copy in this workspace carries the privacy gate's placeholder, and nobody named the day). claimocity_retry_dx.py reads these words
# and hands the visit to the import again - once a run, until a later register shows the visit entered or kept out for good; claimocity_report.py says it in the digest,
# in a line for the top of the report.
DEATH_DAY_WHY = "a date of death is on record for this chart but its day cannot be read - not entered"
def death_day(v):
    """A cached date of death as YYYY-MM-DD when it is a real calendar date in a shape a helper has written it in (YYYY-MM-DD, eight digits, MM/DD/YYYY - the
    first and the last may carry a time behind the day, as AdvancedMD stamps its dates); None for anything else - the placeholder of the repository's copy, a
    text, a date that is none. THE GUARD'S OWN READING, step for step (deceased_guard._iso and _day): this helper must work with no guard module beside it, so
    the reading is written out here - and tools/selftest/test_lookup_rules.py holds it, dg_drive.py's and the guard's together over every shape. (11/25/2026,
    the independent check of the second round, finding 12: a day with a time behind it was a day to the guard and none here - the chart counted as one whose
    day is lost, and every visit of it was held, also one BEFORE the day.)"""
    s = str(v or "").strip()
    if re.match(r"\d{8}$", s): s = "%s-%s-%s" % (s[:4], s[4:6], s[6:])
    else:
        m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)
        s = "%s-%02d-%02d" % (m.group(3), int(m.group(1)), int(m.group(2))) if m else s[:10]
    if not v or not re.match(r"\d{4}-\d{2}-\d{2}$", s): return None
    try: return datetime.date.fromisoformat(s).isoformat()
    except ValueError: return None
DEATH_NO_DAY = "day not known"      # the guard's own NO_DAY: what stands in the day's place for a chart whose own record says deceased while nobody named a day (the self-test holds the two together)
DEATH_WORDS = {"deceased", "dead", "died", "expired", "redacted", "y", "yes"}      # the guard's own DEATH_WORDS: the words that stand for a death with no day in a cache's day place
DEATH_NOTHING = {"none", "null", "n/a", "na", "unknown", "no", "empty"}      # the guard's own NOTHING_WORDS: a bracketed text that is one of these (any letter case) plainly means 'nothing' - no death on record
def death_unread(v):
    """True for a cached dod value that is a death ON RECORD whose day cannot be read: no day, and the guard's 'day not known', a text with at least four digits
    in it (a damaged date), a text in square or angle brackets in any letter case (the privacy gate's placeholder is one) unless it plainly means nothing, a
    masked date (nothing but the letter X and separators, at least four X), or one of DEATH_WORDS as the whole value in any letter case. False for a day and
    for every other value - None, '', blanks, the words None / null / unknown, '0', a number: that is NO dod, and the chart is held for nothing. THE GUARD'S
    OWN READING (deceased_guard._unread), written out here as death_day is; tools/selftest/test_lookup_rules.py holds it, dg_drive.py's and the guard's
    together over every shape. (11/25/2026, the third round: until then ANY value in a dod field that was no day held every visit of the chart - one word in a
    stray file. The fourth round: the bracketed texts, the masked date and the words. The fifth round, 11/26/2026: a bracketed text that is one of
    DEATH_NOTHING - '[none]', '<null>', '[n/a]' - is no death on record: by the fourth round's letter it would have held every visit of a living patient's chart.)"""
    if not isinstance(v, str) or death_day(v) is not None: return False
    s = v.strip(); bracketed = [(a or b).strip().lower() for a, b in re.findall(r"\[([^\[\]]*[A-Za-z][^\[\]]*)\]|<([^<>]*[A-Za-z][^<>]*)>", s)]
    return (s == DEATH_NO_DAY or len(re.findall(r"\d", s)) >= 4 or any(w not in DEATH_NOTHING for w in bracketed)
            or s.lower() in DEATH_WORDS or (bool(re.fullmatch(r"[Xx/. -]+", s)) and len(re.findall(r"[Xx]", s)) >= 4))
def death_read(tables):
    """What the cache files say, read TOGETHER -> ({chart number: its entry, its dod the EARLIEST day any file holds for the chart}, {the charts with a death on
    record whose day is in no file}). tables = what each file holds, in the order the files were read; whatever is no table, and a line that is no entry, is
    passed over. A day (death_day) beats a death on record whose day cannot be read (death_unread); every other value in the day's place is NO dod. Nothing is
    asked and nothing is written here. The guard after its carry comes to the same answer for every set of entries the files can hold for one chart
    (tools/selftest/test_lookup_rules.py holds this function and the guard together over every pair and triple of them).
    (11/26/2026, the fifth round: rounds three and four had each given the owner's word a rule in here - and the fourth a third value, the charts to ask about
    afresh. Both rules are gone: no file's entry outweighs another's but by the two readings above, and the order of the files means nothing.)"""
    days = {}; lost = set()
    for c in tables:
        for k, v in (c.items() if isinstance(c, dict) else ()):
            if not isinstance(v, dict): continue
            k = re.sub(r"\D", "", str(k)); d = death_day(v.get("dod"))
            if d is not None: days.setdefault(k, []).append(dict(v, dod=d))
            elif death_unread(v.get("dod")): lost.add(k)
    out = {k: min(rows, key=lambda r: r["dod"]) for k, rows in days.items()}      # of the days the files hold the EARLIEST counts
    return out, {k for k in lost if k not in out}
# 11/12/2026 (William: "fix everything billable to put them in advanced md"): 99349, the established-patient home / assisted-living visit, was
#   not in these two tables, so three feed visits (9/1, 9/2 and 11/3/2026) were skipped as "unknown CPT 99349". It goes in under pcode65142
#   (the id the 10/15 recode and the 10/20 GV rebill used) at the practice's $198.00 (the fee of every natively entered 99349 on the ERA
#   registers - era_audit, era_dual, era_true_residual, era_denials; a 99344 recoded to 99349 keeps its $300). claimocity_retry_dx.py enters
#   the skipped visits once this file is on main; a visit the chart already carries is answered by the live-charge dedupe below - "already",
#   never a second visit.
PCODE = {"99487": "pcode492676", "99489": "pcode492677", "99223": "pcode65084", "99232": "pcode65089", "99233": "pcode65090",
         "99239": "pcode65095", "99497": "pcode492667", "99498": "pcode492668", "99306": "pcode65116", "99308": "pcode65118",
         "99309": "pcode65119", "99316": "pcode65122", "99344": "pcode601053", "99349": "pcode65142"}
FEE = {"99223": "310.00", "99232": "111.00", "99233": "160.00", "99239": "163.00", "99306": "256.00", "99308": "107.00", "99309": "141.00",
       "99487": "206.00", "99489": "109.00", "99497": "133.00", "99344": "300.00", "99316": "207.00", "99498": "115.00", "99349": "198.00"}
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
       "Oakes Southwood": ("fac1350", "31"), "Pruitt Southwood": ("fac1350", "31"),      # (11/25/2026: the November care-management file names the Southwood building 'Pruitt Southwood' - the same building: 15 visits had gone in with no facility)
       "Azalea Gardens ALF": ("fac37", "13"), "Tapestry Senior Living Lakeshore": ("fac55", "13"),
       "Opal Hermitage Boulevard ALF": ("fac53", "13"), "Capital Square at Tallahassee": ("fac54", "13"), "Canterfield of Tallahassee ALF": ("fac38", "13"),
       "Sodalis Senior Living ALF": ("fac65", "13"), "Allegro Senior Living ALF": ("fac57", "13")}
HOSP = {"99221", "99222", "99223", "99231", "99232", "99233", "99238", "99239"}
MOD25 = {"99497", "99489"}
# NO MODIFIER 25 ON THE 99489 ADD-ON FOR HUMANA (William 11/25/2026, asked "Should I stop putting 25 on 99489 for Humana and re-send the ones still inside the filing limit?":
# "yes try that"). Humana answered CO-4 (the procedure code is inconsistent with the modifier) on 24 care-management add-on lines that carried modifier 25 in 2026 ($2,616 billed,
# nothing paid) and on none of its 43 add-on lines without it (30 paid). A 99489 line of a chart whose FIRST plan in billing order is one of the practice's Humana carrier records
# goes in without the modifier; the row says so (no_mod25). Every other payer, and the 99497 line, as before. A chart whose plans or billing order cannot be read is built as before.
# 11/25/2026 (review): the billing order is the CHART's OWN (chart_insorder). A chart that has plans but no billing order gets its new visit created with the order "1" - a stand-in for
# the create call (chart_ctx). Until this fix that "1" was read as the chart's first plan: when the plan numbered 1 happened to be a Humana record the modifier came off although nothing
# said that Humana is billed first (the insurance check sets that visit's order afterwards, and may lead with Medicare). Such a chart is built as before - with the modifier.
# The standing CCM gate of the scheduled runs follows the SAME rule: its helper mod25_addon.py reads the two lines below from this file (keep each on ONE line, in this shape).
HUMANA = {"car6285", "car302851"}          # HUM01 HUMANA and HUMMA1 HUMANA GOLD PLUS HMO MA PLAN (practices/ehpa/carriers.json)
NO_MOD25 = {"99489": HUMANA}               # code -> the carriers: when one of them is the chart's first plan in billing order the line carries no modifier 25
def first_carrier(ctx):
    """The carrier id of the chart's FIRST plan in billing order - '' when it cannot be told (ctx['chart_insorder'] = the chart's OWN billing order, the sequences in order: empty
    for a chart that has none, None for a chart that could not be read; ctx['plans'] rows: plan id, carrier, begin date, end date, sequence). The order the create call carries
    (ctx['insorder']) is never read here: for a chart without an order it is the stand-in "1". Never raises."""
    try:
        order = ctx.get("chart_insorder"); first = (order.replace(" ", "").split(",") or [""])[0] if isinstance(order, str) else ""
        if not first: return ""
        for row in ctx.get("plans") or ():
            try: _pid, car, _beg, _end, seq = row[:5]
            except Exception: continue
            if str(seq) == first: return car if isinstance(car, str) else ""
    except Exception: pass
    return ""
def mdy(yyyymmdd):
    return "%s/%s/%s" % (yyyymmdd[4:6], yyyymmdd[6:8], yyyymmdd[0:4])
# ---- PLACE OF SERVICE IN THE NURSING BUILDINGS (William 11/10/2026, STANDING - practices/ehpa/rules.md) -------------------------------
# The five nursing buildings arrive from Claimocity as POS 31 whatever the resident's status ("that is the only way we have to do it in
# claimocity"), so the place of service is decided here by William's frequency rule, per charge line, when the charge is entered. It is
# an operating rule read from the chart's visit pattern, not a check of the building's Part A list. How the code reads Medicare's line: 31 is
# what was billed before; 32 is for a resident who is not in a Part A stay, and Medicare can match a 32 line to the facility's Part A claim. So 32 is
# given only where the chart SHOWS the long-term pattern, and everything unclear keeps the feed's 31 - exactly what was billed before.
#   CCM 99487 / 99489          -> 32, EVERY line: "all the ccm services performed in the nursing facility setting by us are done on our long
#                                 term residents that are not being actively skilled" (11/10/2026) and "make sure they bill with the place
#                                 of service ltc which pays more ... not the skilled snf location of service ... for all ccm charges going
#                                 forward" (11/25/2026). ALF / home CCM keeps its home location (13); a CCM line whose own message names
#                                 the hospital keeps 21. A CCM line is NEVER entered at 31. The back end's exception of 11/10/2026 (the
#                                 chart shows the resident seen at skilled frequency, admitted or readmitted in the CCM's own calendar
#                                 month -> the feed's 31) is REMOVED by William's word of 11/25/2026: such a line is 32 like every other
#                                 and its chart is only LISTED for William (pos_kind ccm-skilled-month) - not held, not changed. The same
#                                 when the rule fails for the message (ccm_never_31) and when the building is not in the facility table
#                                 (the old default 31 - pos_kind ccm-unknown-building; the chart goes to the top of the report as before).
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
# Hospital (21), ALF / home (13) and the unknown-building default are entered exactly as before - except
# that a CCM line of an unknown building is 32, not the default 31. Any error in the rule falls back to the feed's place of service for
# the whole message - its CCM lines 32 all the same - and is counted as "POS RULE NOT APPLIED" - the import never stops for this rule.
# 11/25/2026: a hospital visit of an INPATIENT REHAB STAY goes in at HCA REHAB (fac67) with every line at 61 - INPATIENT REHAB STAYS below. (Until that
# day the inspector step moved a nursing-facility code under the hospital building to HCA REHAB at 31; it moves no visit any more.)
POS_RULE_VERSION = "2026-11-25.5"       # change this line with EVERY revision of the rule - mirror.py PROTECTED, the runbook grep (step c) and the ingest guard name it (.3, 11/25/2026: inpatient rehab at 61; the chart's own birth date - dob_note on every row, the 1123F age from the chart, the BIRTH DATES line; the chart of each Claimocity id - chart_of; no modifier 25 on the 99489 add-on of a Humana chart - NO_MOD25; .4 the fixes after the independent verification; .5 the second round: a nursing or home visit counts for the stay rule only in a nursing or home building, a stay is over with its discharge visit, an entered admission is not taken back by a skipped copy)
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
BATCH_NF_ERR = [""]        # why the batch list could not be built (then no nursing VISIT line is 32 in this run; a CCM line is 32 without the list - William 11/25/2026) - reaches the DONE line
FACS = {}                  # feed patient id -> every building name its messages carry in this batch
MSGOF = {}                 # one feed message (see msg_key) -> {(building name, clinician NPI, admission date)} read from the raw files
MSGLAST = {}               # one feed message -> the LAST raw copy read of it: where its copies differ in the admission date, the message's own last copy answers (11/10/2026, review W2) - never another message of the patient
MSGUNIT = {}               # one feed message -> the PV1 facility number of every raw copy of it (the last ^ component of field 2 of its PV1 line); a number of REHAB_UNIT_NUMBERS names the hospital's rehabilitation unit (11/25/2026, INPATIENT REHAB STAYS)
SAME_DAY = {}              # chart -> {(code, 'MM/DD/YYYY')}: hospital visit lines the feed sent for a day that already carried ANOTHER hospital code of ours on the chart, so the same-day rule never entered them - this run's and, from the import registers' "same_day" lists, every earlier run's. Only the stay rule reads them (11/25/2026, review of INPATIENT REHAB STAYS)
SAME_DAY_NEW = {}          # ... the ones THIS run (this batch stamp) passed over: main() writes them into this run's register as "same_day"
SAID_61 = {}               # chart -> {'MM/DD/YYYY'}: the days of visits at HCA REHAB / 61 that a row of an import register has already NAMED for William (its "hospital_at61" or "mixed_at61" list) - main() reads them from every register, build() adds what this run names: each day is said ONCE (11/25/2026, verification)
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
# code; a hold caused by the line would count as a refusal and could set the code back to probing for every setting. For the 2026 score one counted
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
#             it was called left off (November 12, 2026 - fix round 2, K13: the same clock as the block below; it used to count from that billed date)
#             - billed after all, it counts as billed and its patient as coded.
#             November 12, 2026 - fix round 1 (K12): its patient is due again only once the line was called left off QUALITY_LEFT_OFF_REREAD
#             (30) days ago or more - until then AdvancedMD may still bill it, and once per patient and year holds also across a left-off line,
#             whether the code probes or goes. The same for M0004, per clinician.
#   VOID      the line itself says void. If the visit's own charge is still live, a person took the line off: that patient gets no line
#             again this year and the code stays on (before proof it probes). If the visit's own charge is void too, the visit is gone and its place in the round is free. A line
#             the inspector step or the insurance check took off a held visit by itself (registers' "quality_removed") is void too, but
#             the routine's doing, not a person's - see removal() in quality_state. November 12, 2026 - fix round 1 (K10): "a person took
#             the line off" is said only of a line found void with no entry of the routine's on record (an entry that says "listed": false
#             records that the step did nothing); the inspector step writes its entry before the void, so a cut after the void leaves the
#             visit stuck, and the step re-saves it.
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
#     until a restart, also when the $0.00 line turns out billed later. A one-cent line LEFT OFF -> the code probes.
#   - THE CODE NEVER SWITCHES ITSELF OFF (11/12/2026; William 11/11/2026: "dont stop this dont let it stop make sure this suceeds"). Where
#     there used to be one OFF, three things are kept apart. STOPPED = William's own QUALITY_CODE=stop: the only sentence a gate carries in
#     "off_until_reset", ended only by his reset. PAUSED = no line in THIS run, and every run looks again: (a) a visit is STUCK held with
#     its line - the void failed, the visit is still listed for the edit about a line that came off, or the Claim Inspector holds it and no
#     removal is recorded (before proof any hold, after proof a hold whose words name the line; since 11/10/2026 the inspector step takes
#     the line off a held visit by itself: William's decision, quoted in practices/ehpa/rules.md). The gate lists it under "stuck", the
#     inspector step tries the void and the re-save again in every run, and only a NEWER "quality_removed" entry ends the mark - not
#     William's reset and not a probe: a real claim never waits because of this code; (b) AdvancedMD shows another code text than 1123F for
#     the line's id: the charge that showed it is read again first (another line in its place when it can no longer be read as a 1123F
#     charge), and the pause is over when a read shows 1123F. PROBING = what the code does where it used to go off: ONE new line a run
#     (QUALITY_PROBE) on the first eligible visit, none while a line of the round is not decided, none in a retry register (stamp ...R),
#     none when this stamp's own register already holds a try - until a line of the round is BILLED and proves the code as above. A probe
#     begins at: refusals at one cent (below) and the move to one cent itself - the amount only moves there after something stopped a
#     line, so at one cent the code probes from its first line; a one-cent line left off; a line of the round taken off by a person before
#     proof; a round that is full with nothing proven; a fault while the chart shows the visit, a call that ended in an error, or an
#     insurance check that could not set a coded visit's order (its words: insorder not applied, resave FAULT, detail read mismatch) -
#     that visit is for a person; a stuck visit that is free again; and an OLDER register that still says "off until reset" by the code's
#     own doing (William's standing word restarts it, once, and the report says so). A cause that lies in the registers is taken in its
#     place as they are read and sets a proof in place aside (a new round at the same amount); the gates carry the probe ("probe",
#     "probe_kind", "probe_since", "probe_words", "probe_tries") until a gate says confirmed or William restarts.
# LINES TAKEN OFF A HELD VISIT by the routine: the visit went through without it (released) = ONE refusal (below) and no second try for that
# patient that year; the visit stayed held anyway = nothing counts, the place is free and the patient is due again; such a line is never the proof.
# A REGISTER THAT CANNOT BE READ: an import register of this year that is there but cannot be parsed means the state is not known - no line
# in that run (the visits are imported as always), and the report says so at the top from the second run in a row.
# REFUSALS: AdvancedMD answers a fault to a visit that carries the line -> the import reads the chart again (three tries). Nothing of the
# visit stored -> the SAME visit goes in without the line, that patient gets no second try that year, no further line in that run.
# Refusals (or visits stored without their line, or lines taken off a held visit that then went through) in a row at one amount with no
# line stored in between - before proof ONE, after proof
# TWO - move the amount to one cent (a new round); at one cent the code probes. A fault although the chart shows the visit, or
# the chart cannot be read: the visit is NOT sent again - William looks at that visit - and the code probes from the next run.
# November 12, 2026 - fix round 1 (K11): such a visit - and the visit of a call that carried the line and ended in an error, or of a run cut
# while that call was out - stays for a person, its patient gets no line again that year, AND the gate lists it under "stuck" ("fault": true,
# the line's charge number perhaps unknown): no new line while the Claim Inspector holds it, and every run's inspector step looks at it - not
# listed = free, the probe goes on; held = its live 1123F line comes off by the retry sequence; no such line found = for a person, and no new
# line meanwhile. The state line names the visit in every run until it is free.
# November 12, 2026 - fix round 2 (K15, by William's "dont let it stop"): such a visit pauses the code ONLY while it is held WITH its 1123F line and
# the line cannot be taken off. When the step finds no 1123F line on it, or (after the proof) the hold's words do not name the line ("own_reason"),
# the visit is not held because of this code: it stays listed and on the report for a person in every run until it is free, its patient stays
# marked, and the code goes on (no pause). K16: the words say what is known - an entry with void_ok false and no note was written before a void
# that never reported back ("the routine's last try was cut off before it ended; this run's step looks again"), a chart that could not be read
# ("looked": false) says the line could not be looked for, and a probe cause such an entry began is taken back once a newer entry says the visit is free.
# SWITCHES (William's; QUALITY_CODE in the environment of the import and of the retry command; case and spaces do not matter): off = no
# line in this run; stop = OFF until William restarts it, the only lasting OFF there is; reset = a new round at $0.00, honoured ONLY after his stop (left in
# a routine it does nothing); any other value that is not empty = no line in this run, and the log says which value was not understood.
QUALITY_CODE = "1123F"; QUALITY_PCODE = "pcode65441"       # AdvancedMD's own id for 1123F (lookupproccode 11/10/2026 09:43Z, name "ACP DISCUSS/DSCN MKR DOCD" - docs/captured_calls.md)
QUALITY_SAME = {"1123F", "1124F"}                          # either one on the chart in the same year = already reported
QUALITY_PILOT = 3                                            # lines a pilot ROUND may hold before one of them is proven (void lines not counted; never more than twice this in all)
QUALITY_PROBE = 1                                            # lines a RUN may add while the code PROBES (11/12/2026: where it used to go off) - one, on the first eligible visit, across every register of that run
QUALITY_STOP_WORDS = "stopped on William's word"             # how William's own stop begins in a gate's "off_until_reset" - the only lasting OFF there is; any other sentence there was written by the code before 11/12/2026
QUALITY_FAULT_WHAT = {"cut": "the run was cut while the call that carried the line was out", "error": "the call that carried the line ended in an error",      # November 12, 2026 - fix round 1 (K11): how the gate's "stuck"
                      "kept": "AdvancedMD answered a fault but kept the visit", "unread": "AdvancedMD answered a fault and the chart could not be read afterwards"}      # names a visit of a fault run before the inspector step has looked at it
QUALITY_LOOKS = 6                                            # quality lines read per run for their outcome (one read of the line; one of its visit's own charge where the outcome needs it); after proof, as many again for Medicare's answer
QUALITY_DAILY = 10                                           # after proof: lines per run until Medicare's own answer is on file (a payment line read by the import, or QUALITY_N620)
QUALITY_MIN_AGE = 65
QUALITY_YEARS = {"2026"}                                     # dates of service the code list below and William's word were read for (measure 047, 2026); another year gets no line until William renews it
QUALITY_POS_SKIP = {"21", "22", "23", "61"}                  # places of service whose visit lines never carry the line in this version: hospital inpatient, hospital outpatient, emergency department (HOSPITAL VISITS above) - and 61, inpatient rehab (11/25/2026: a visit of a rehab stay is a hospital visit for this rule)
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
#   OFF (its visit billed, the line not, and still so QUALITY_LEFT_OFF_DAYS days after the visit's billed date) = that clinician gets it once more
#   (November 12, 2026 - fix round 1, K12: once the line was called left off QUALITY_LEFT_OFF_REREAD days ago or more - it may still be billed until then);
#   the line is read again until QUALITY_LEFT_OFF_REREAD days after that date (fix round 2, K13; billed after all = done). Open / unknown = no second line for that
#   clinician. The line is known by its code text: the charge detail must name pcode692183 as M0004.
# M0004 NEVER SWITCHES ITSELF OFF EITHER (11/12/2026; William 11/11/2026: "dont stop this dont let it stop make sure this suceeds"; the gate's
#   "off_until_reset" is always empty now). Where M0004 used to go off it PROBES: at most ONE M0004 line a run in all (not one per clinician), on the
#   first visit that carries the 1123F line and whose clinician still needs M0004, none while any M0004 line is not decided, none in a retry register,
#   none when this stamp's own register already holds an M0004 try - until an M0004 line entered after the newest cause is read billed; then each
#   clinician who has none gets one, as before. It probes after: AdvancedMD refused a visit that carried M0004 and took it with the 1123F line only;
#   AdvancedMD stored a visit without its M0004 line, or the M0004 line without its 1123F line; M0004 left off MVP_LEFT_OFF_MAX claims; the routine took
#   the M0004 line off a held visit that then went through; the insurance check could not set such a visit's order; a visit that carried M0004 was
#   refused or ended in an error and nobody knows what AdvancedMD kept of it (that visit is for a person). It PAUSES one run at a time - no new M0004
#   line, the 1123F line goes on - while a visit is STUCK held with its M0004 line (the void failed, still listed for the edit about the line, or a hold
#   whose words name M0004 with no removal recorded: the gate's "stuck"; the inspector step tries again in every run and only a newer entry ends the
#   mark) and while AdvancedMD shows pcode692183 with another code text (read again by every run, as for 1123F). An OLDER register's "off until reset"
#   is read as a pause that has ended: M0004 probes, once said in the report.
# REFUSALS: a visit with 1123F + M0004 that AdvancedMD refuses goes in again with the 1123F line only (that form is proven) once a fresh read of the
#   chart shows nothing of it stored; refused that way too, it goes in plain and the refusal counts against 1123F (REFUSALS above), M0004 is not
#   blamed. MEDICARE'S ANSWER: a billed M0004 line is read for a live Medicare Part B payment line, per clinician (the report shows it).
# SWITCHES: QUALITY_CODE=off / stop stop M0004 too (it never rides without the 1123F line); MVP_CODE=off = no M0004 line in this run; MVP_CODE=reset
#   has nothing left to restart (the log says NOTHING TO RESTART); any other MVP_CODE value = no M0004 line in this run, and the
#   log says which value was not understood.
MVP_CODE = "M0004"; MVP_PCODE = "pcode692183"                # AdvancedMD's own id for M0004 (lookupproccode 11/10/2026 10:24Z, name "QUAL CARE NEUROLOGIC CND MVP" - docs/captured_calls.md)
MVP_YEARS = {"2026"}                                          # the year the group and both clinicians are registered for the option; another year gets no M0004 line until William renews it
MVP_ON = True                                                 # William 11/10/2026, about M0004: "use it"
MVP_LEFT_OFF_MAX = 2                                          # M0004 lines read as left off after which M0004 probes (left off once: that clinician gets it once more; until 11/12/2026 the second switched M0004 off)
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
                              "medicare_answer": None, "medicare_wait": None, "skipped_hospital": 0, "unread": [], "unread_prev": [],
                              # 11/12/2026, the code never switches itself off: probe* = why the code probes (one line a run) and since when; paused = why no line is added in THIS run
                              # (also in "off"); stuck = the visits held with their line (the inspector step tries them again); open_lines = the lines not decided yet
                              "probe": "", "probe_kind": "", "probe_since": "", "probe_words": "", "probe_tries": 0, "paused": "", "stuck": [], "open_lines": [], "standing_restart": None, "taken_lines": [],
                              "wrong_code_charge": "", "n620_seen": "", "left_off_cent": [], "proof_aside": None}
QUALITY = _quality_fresh()
# the option code M0004's state for this run (mvp_state fills it from the registers): done / wait = (clinician profile, year) with an M0004 line that
# is billed / not decided yet - neither gets another line; added = the clinicians whose visit got the line in this run; the rest is its ledger
def _mvp_fresh(): return {"off": "", "off_until_reset": "", "reset": False, "reset_after": None, "loud": "", "done": set(), "wait": set(), "added": [], "notes": [], "lines": 0,
                          "billed_lines": [], "void_lines": [], "left_off_lines": [], "billed_on": {}, "left_off_on": {}, "left_off_seen": {}, "late_billed": {}, "late_rows": [],
                          "swaps": {}, "wrong_code_text": "", "answer": {}, "answer_wait": {}, "clinicians": {},
                          # 11/12/2026: probe* = why M0004 probes (ONE M0004 line a run in all; budget = what this run may add while it probes, None = not probing); paused / stuck / open_lines as for 1123F
                          "probe": "", "probe_since": "", "probe_words": "", "paused": "", "stuck": [], "open_lines": [], "standing_restart": None, "wrong_code_charge": "", "budget": None}
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
# ---- William 11/25/2026 ("correct every one that comes to the correct date of birth and insurance and fix them figure our how to do this for other charts that have the
# same mistake where we know the correct dob but claimocity sends the wrong one or the 01011900 default date") - THE CHART'S OWN BIRTH DATE -----------------------------
# The feed sends some patients with a WRONG birth date (an old one ten days off, a year twenty years off) or with the year-1900 placeholder, although the chart the visit
# goes to holds the right one - corrected from a face sheet. Until that day the import knew only the feed's: the age of the 1123F rule was counted from it (the placeholder
# meant no line at all, a wrong year a line for a patient under 65 or none for one over it), and nothing on main said that the two dates differ. Now chart_ctx keeps the
# chart's own birth date from the chart answer it already reads, build() writes dob_note into the visit's register fields, quality_due counts the age from the chart's date
# when it is a REAL one, and main() prints ONE line (birth_dates_line). Nothing here holds, moves or changes a visit: which chart a feed patient goes to is decided before
# the import (the match step); the import only says what it sees. A register row never carries a date or a name - a slip is named by its kind.
# _real_dob and _slip are the owner's rule as scripts/helpers/feed_identity.py states it (real_dob, slip); they are private copies here - the same text stands in
# claimocity_verify.py and feed_in1_intake.py, and tools/selftest/test_pos_rule.py checks the three read the same. 11/25/2026 (review): they are NOT drop-in equal
# to that module - _slip answers in this helper's own shorter words ("one digit", "two digits swapped"; there "one digit differs", "two neighbouring digits swapped")
# and "far" where slip answers ""; _real_dob answers False for a today that is no date (real_dob raises). dob_note's words are in the registers and in the digest's
# own list, so point these at the module only through that word map.
def _real_dob(d8, today8):
    """True when d8 is a REAL birth date (the owner's rule): 8 digits, a real calendar date, the year 1901 or later, not after today8 and not more than 120 years before
    it. Anything else - empty, the year-1900 placeholder, zeros, a day that does not exist - is NO BIRTH DATE. (The rule of real_dob in feed_identity.py.)"""
    d8 = str(d8 if d8 is not None else ""); today8 = str(today8 if today8 is not None else "")
    if not re.fullmatch(r"[0-9]{8}", d8) or not re.fullmatch(r"[0-9]{8}", today8) or d8[:4] < "1901": return False
    try: __import__("datetime").date(int(d8[:4]), int(d8[4:6]), int(d8[6:8]))
    except ValueError: return False
    return "%04d%s" % (int(today8[:4]) - 120, today8[4:]) <= d8 <= today8
def _slip(a8, b8):
    """How two REAL birth dates differ (the owner's rule) - the kind of slip, the first that fits: "one digit" (one digit differs), "two digits swapped" (two neighbouring
    digits swapped), "month and day swapped" (MMDD read as DDMM), "one day apart"; anything else is "far". "" when the two are the same date. (The rule of slip in
    feed_identity.py, in this helper's own shorter words; there far is the empty answer.)"""
    a8, b8 = str(a8), str(b8)
    if a8 == b8: return ""
    if len(a8) != 8 or len(b8) != 8: return "far"
    diff = [i for i in range(8) if a8[i] != b8[i]]
    if len(diff) == 1: return "one digit"
    if len(diff) == 2 and diff[1] == diff[0] + 1 and a8[diff[0]] == b8[diff[1]] and a8[diff[1]] == b8[diff[0]]: return "two digits swapped"
    if a8[:4] == b8[:4] and a8[4:6] == b8[6:8] and a8[6:8] == b8[4:6]: return "month and day swapped"
    try:
        day = __import__("datetime").date
        if abs((day(int(a8[:4]), int(a8[4:6]), int(a8[6:8])) - day(int(b8[:4]), int(b8[4:6]), int(b8[6:8]))).days) == 1: return "one day apart"
    except ValueError: pass
    return "far"
SLIP_KINDS = ("one digit", "two digits swapped", "month and day swapped", "one day apart", "far")      # what _slip can answer for two different dates, in the rule's own order
def dob_note(feed8, chart8, today8):
    """What a register row says about the two birth dates of its visit ("dob_note") - fixed words, never a date: "same" (both REAL and equal); "no birth date from
    Claimocity" (the chart has a real one, the feed none or the placeholder); "chart has no birth date" (the feed has a real one); "no birth date on either side";
    "differs: " + the kind of slip (one digit / two digits swapped / month and day swapped / one day apart) or "differs: far" for two real dates that are not equal.
    chart8 None = the chart's own answer could not be read (chart_ctx): "chart not read", whatever the feed carries - 11/25/2026 (review): until then such a row said
    "chart has no birth date", which nobody knows of a chart that was not read."""
    if chart8 is None: return "chart not read"
    f = _real_dob(feed8, today8); c = _real_dob(chart8, today8)
    if f and c: return "same" if str(feed8) == str(chart8) else "differs: " + _slip(feed8, chart8)
    return "no birth date from Claimocity" if c else "chart has no birth date" if f else "no birth date on either side"
def death_check_line(g):
    """The run's date-of-death checks in ONE printed line (11/25/2026, William: "is stedi able to do that for free?"): asked free at AdvancedMD, answered free,
    went to the vendor - the deceased guard's own COUNTS (g = the loaded guard module, or None) - and how many checks ended UNVERIFIED (the guard's own LOG lines:
    nobody answered, the charge went on), with ' - TOP OF THE REPORT' when there is one. "" when there is nothing to say: no guard loaded, nothing asked and nothing
    unverified. (The second verification of that day: the line said 'vendor bought' for checks the vendor refused or never answered - the count is the guard's CHECKS
    that went to the vendor; stedi_usage.py has the requests and the dollars - and nothing on the feed's path said that a chart stayed unverified.) Counts only -
    never a chart, a name or a date. It never raises."""
    try:
        c = getattr(g, "COUNTS", None); lg = getattr(g, "LOG", None)
        u = sum(1 for x in lg if isinstance(x, str) and "UNVERIFIED" in x) if isinstance(lg, list) else 0
        tail = ("; date of death UNVERIFIED x%d - TOP OF THE REPORT" % u) if u else ""
        try: fa, fn, pa = [int(c.get(k) or 0) for k in ("free asked", "free answered", "paid asked")] if isinstance(c, dict) else [None] * 3
        except (TypeError, ValueError): fa = fn = pa = None
        if fa is None: return ("DEATH CHECK: checks not counted by this guard" + tail) if u else ""
        if not (fa or pa or u): return ""
        return "DEATH CHECK: AdvancedMD free asked x%d, answered x%d; went to the vendor x%d%s%s" % (fa, fn, pa, "; free check off after 3 failures in a row" if getattr(g, "free_down", lambda: False)() else "", tail)
    except Exception: return ""
def birth_dates_line(seen):
    """The ONE line a run prints about birth dates ("BIRTH DATES: ..."), or "" when there is nothing to say (no visit, or every visit's feed date is its chart's). seen =
    chart id -> the dob_note words of its visits in this run. Chart ids only - never a name, never a date. A chart whose visits differ in two ways is named once, with
    both kinds; a group names its first twelve charts and counts the rest (the rows of the register name every one). The charts whose own answer could not be read
    ("chart not read") are a group of their own, said last."""
    def order(p):
        n = re.sub(r"\D", "", str(p)); return (int(n) if n else 0, str(p))
    def some(items): return ", ".join(items[:12]) + ((" +%d more" % (len(items) - 12)) if len(items) > 12 else "")
    notes = {p: {str(w) for w in (ws or ()) if w} for p, ws in (seen or {}).items()}; charts = sorted(notes, key=order)
    differ = ["%s %s" % (p, " / ".join(k for k in SLIP_KINDS if "differs: " + k in notes[p])) for p in charts if any(w.startswith("differs: ") for w in notes[p])]
    group = lambda words: [str(p) for p in charts if words in notes[p]]
    no_feed, no_chart, neither = group("no birth date from Claimocity"), group("chart has no birth date"), group("no birth date on either side"); unread = group("chart not read")      # 11/25/2026 (review): not read is not 'no birth date'
    parts = (["feed and chart differ on %d chart(s) (%s)" % (len(differ), some(differ))] if differ else []) + (["Claimocity sent no birth date for %d chart(s) (%s)" % (len(no_feed), some(no_feed))] if no_feed else []) \
        + (["%d chart(s) carry no birth date themselves (%s)" % (len(no_chart), some(no_chart))] if no_chart else []) + (["no birth date on either side for %d chart(s) (%s)" % (len(neither), some(neither))] if neither else []) \
        + (["%d chart(s) could not be read (%s)" % (len(unread), some(unread))] if unread else [])
    return ("BIRTH DATES: " + "; ".join(parts)) if parts else ""
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
    entered under) has no M0004 line this year that is billed or not decided yet - an M0004 line added earlier in this run counts as not decided.
    11/12/2026: while M0004 PROBES (MVP['probe'], where it used to go off) at most ONE M0004 line a run in all - none once this run added one, none
    while the run has no room for it (MVP['budget'] 0: an M0004 line is not decided, a retry register, or this stamp's register already holds a try)."""
    if not MVP_ON or MVP.get("off") or QUALITY.get("off") or QUALITY.get("confirmed") is not True: return False
    if MVP.get("probe") and (MVP.get("added") or MVP.get("budget") == 0): return False
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
      3. the date of birth is a real calendar date, not the year-1900 placeholder, and the age on that date of service is 65 to 115. Whose date: the CHART's own
         (ctx['dob'], kept by chart_ctx) when it is a REAL one (_real_dob), else the feed's as before - since William's word of 11/25/2026; until then the feed's only,
         which can be a wrong date or the placeholder for a patient whose chart holds the right one. Neither a real one: no line, as before;
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
    _cdob = re.sub(r"\D", "", str(ctx.get("dob") or ""))[:8]                 # William 11/25/2026: the chart is the patient - its own date, when it is a real one, is the one the age is counted from
    if _real_dob(_cdob, run_day().strftime("%Y%m%d")): dob = _cdob            # (a chart with no date, the placeholder, or a date that cannot be: the feed's, exactly as before)
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
# a visit of one of these kinds in the CCM's month (or one of our hospital or home / assisted-living visits that month) is what LISTS that month's CCM for William
# (pos_kind ccm-skilled-month). Until 11/25/2026 it also kept the line at the feed's 31; since William's word of that day the line is 32 like every CCM line.
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
    month or the buildings disagree). Then the CCM line of that month - 32 like every CCM line since 11/25/2026 - is listed for William; it is not held
    and never moved to 31."""
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
# William 11/25/2026 ("make sure they bill with the place of service ltc ... not the skilled snf location of service ... for all ccm charges going
# forward"): a CCM line is never entered at place of service 31. The reasons below go into the import register (pos_why) and carry no date.
CCM_LISTED_WHY = ("32 by William's order (every CCM line) - listed for him, not held: the chart shows a hospital visit, a home / assisted-living visit, nursing visits "
                  "in this CCM month that the rule reads as weekly, an admission or a new stay, or the resident's nursing visits in another building")
CCM_NEVER_31_WHY = "32 by William's order (every CCM line): a CCM line is never entered at 31"
def ccm_never_31(cpts, lpos, lwhy=None, lkind=None, why=CCM_NEVER_31_WHY, kind="ccm-forced"):
    """William 11/25/2026: wherever a CCM line would go in at 31 - the rule failed for its message, or its building is not in the facility table
    (the old default) - it goes in at 32. cpts = the codes in line order; lpos / lwhy / lkind = the lists build() keeps per line, changed IN PLACE.
    Only a CCM line that stands at 31 is touched: 13, 21 and every other code stay as they are. Returns how many lines were changed."""
    n = 0
    for i, cpt in enumerate(cpts):
        if cpt in CCM and i < len(lpos) and str(lpos[i]) == "31":
            lpos[i] = "32"; n += 1
            if lwhy is not None and i < len(lwhy): lwhy[i] = why
            if lkind is not None and i < len(lkind): lkind[i] = kind
    return n
def pos_lines(cpt_dos, feed_pos, nursing, nf_history, here=None):
    """Place of service for every line of ONE feed message. cpt_dos = [(cpt, 'MM/DD/YYYY')] in line order; nursing = the message comes from
    one of the practice's nursing buildings; here = that building's key. Returns ([pos per line], [why per line], [kind per line]).
    A CCM line is never 31 (William 11/25/2026): 32 in a nursing building whatever the chart shows, and 32 where a building the facility table
    does not know would have given the default 31. A message from the hospital (21) or an ALF / home (13) is not touched."""
    n = len(cpt_dos)
    if not nursing:
        out = [feed_pos] * n; why = [""] * n; kinds = [""] * n
        if str(feed_pos) == "31":      # not one of the practice's nursing buildings and yet 31 = the default of a building the facility table does not know
            ccm_never_31([c for c, _d in cpt_dos], out, why, kinds, CCM_NEVER_31_WHY + " (its building is not in the facility table - William checks the building)", "ccm-unknown-building")
        return out, why, kinds
    hist = []
    for row in nf_history:
        try: hist.append((row[0], row[1], row[2] if len(row) > 2 else None))
        except Exception: continue
    for cpt, d in cpt_dos:
        if cpt in NF_VISIT: hist.append((cpt, d, None))   # the message's own visit lines count as history for each other
    out = []; why = []; kinds = []; by_day = {}
    for cpt, d in cpt_dos:
        if cpt in CCM:      # 32, every line (William 11/25/2026); the chart only decides whether the line is LISTED for him
            if seen_at_skilled_frequency(d, hist, here): p, w, k = "32", CCM_LISTED_WHY, "ccm-skilled-month"
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
# ---- INPATIENT REHAB STAYS AT PLACE OF SERVICE 61 (William 11/25/2026, STANDING - practices/ehpa/rules.md) -----------------------------
# William 11/25/2026, about a 99223 the Claim Inspector had held: "i now follow patients after dc from the inpatient hospital and admit them to
# inpatient rehab ... many times now i will be following a patient like that the day after dc from the inpatient hospital". Asked "Do you want the
# rehab visits on 61?": "yes and let us monitor them to make sure they pay and dont deny the ones were already paying with the inpatient hosptial as
# the place oif service though so we need to monitor that". 10/31/2026 (board card facility-npi-fac67): the AdvancedMD facility HCA REHAB (fac67)
# carries the rehab unit's own NPI. The hospital's rehabilitation unit is a distinct-part unit with its own NPI (the national registry: taxonomy
# "Rehabilitation Unit", the hospital's street address). Medicare's manual pays the hospital visit codes at the same facility rate at 21 and at 61,
# allows a discharge and a new initial hospital visit on DIFFERENT days when a patient moves from the acute hospital to such a unit, and pays one
# hospital visit a day. The feed names the HOSPITAL building for the unit's visits too, so until this rule they went in at fac29 / 21 (FAC). What the
# rule reads is the STAY:
#   A STAY starts at each initial hospital visit of ours (HOSP_INITIAL) and holds every later hospital visit of ours on that chart (HOSP_VISIT - the
#   same-day rule's hospital family) until the next initial visit, as long as the visit is at most STAY_MAX_DAYS after the stay's initial visit - or,
#   past them, at most STAY_GOES_ON_DAYS after the stay's last visit in hand - and none of our own nursing-facility or home / assisted-living visits
#   lies between the stay's last visit in hand and it (11/25/2026, verification - below; second round: a visit in one of the practice's nursing-facility
#   or home / assisted-living buildings - away_building), and the stay's last visit in hand is not its DISCHARGE visit (second round: a stay that has its
#   discharge visit is over). A 99497 / 99498 line rides with the visit of its own message. A visit no stay holds is in no stay: it goes in exactly as before.
#   A stay is a REHAB stay when ONE of these is shown, else it is an ACUTE stay:
#     1. FACILITY NUMBER - the feed message of its INITIAL visit names a number of REHAB_UNIT_NUMBERS in its PV1 line (the last ^ component of field 2
#        of that line: PV1|1|^^^<number>|...), in every raw copy of the message. If the feed never sends it, this never fires. (11/25/2026, review: the
#        initial visit's message, not any message of the stay - a follow-up that names the unit does not re-label the stay; see the review notes below.)
#     2. NEW ADMISSION 1-2 DAYS AFTER AN ACUTE STAY - the stay's initial visit is dated 1 or 2 days after the LAST visit of the stay before it, and
#        that stay is an ACUTE stay. The same day is no rehab admission (the same-day rule keeps one hospital visit a day, and Medicare pays one);
#        3 days or more, or no hospital visit of ours before it, is a new admission to the hospital; a new initial visit 1 or 2 days after the last
#        visit of a REHAB stay is the patient going back to the hospital. The chain is worked from the oldest visit in hand: the first stay is
#        ACUTE, the kinds then follow. (11/25/2026, verification: and NOT when one of our own nursing-facility or home / assisted-living visits is
#        dated from the day of that last visit up to the initial visit's own day - the patient had left the hospital: a hospital admission.)
#   And a stay whose initial visit already sits on the chart at HCA REHAB - or was built at 61 earlier in this run - is the rehab stay it was entered
#   as, also when neither sign shows any more (a visit of the stay before it voided or re-dated since, or no longer among the rows read): its
#   remaining visits follow it, and the stay after it is read against it. Every hospital visit known for the chart is used: the chart's history
#   (nfrows), this batch (BATCH_NF) and the message itself.
# NO LOOK-BACK, NO MIXING: a visit goes in at 61 only when its own stay's initial visit is not on the chart at another place of service. The chart's
#   history names the facility of each visit: an initial visit at HCA REHAB = its follow-ups go in at 61; anywhere else (or with no facility named) =
#   the stay was entered before this rule, or as an acute one, and ALL its remaining visits keep 21 - pos_kind rehab-stay-kept-21, the group
#   pos61_monitor.py compares the 61 visits with. An initial visit that is in this same batch and not on the chart yet: its follow-ups in the batch
#   follow it - at 61, or, when this run built it at 21 (the rule failed for its message), at 21. A follow-up whose own message names the rehab unit
#   while no initial visit of ours is in hand for it keeps 21 too (nothing shows where that stay began). And (11/25/2026, verification) a follow-up
#   whose stay's initial visit is NOT ENTERED - it is not on the chart, and no message of this batch that the import can enter carries it - keeps 21:
#   no visit goes in at HCA REHAB behind an admission nobody entered. A claim already sent is never changed: nothing here touches a visit that is on
#   the chart.
# WHAT IS SENT for a visit of a rehab stay entered under this rule: facility fac67 (HCA REHAB), EVERY charge line of the message at place of service
#   61; the admission date and everything else as for any hospital visit. Register row: fac fac67, pos 61, pos_lines all 61, pos_kind rehab on every
#   line, pos_why "inpatient rehab stay: <the sign>", pos_feed still what the building table gave (21), and "stay" {kind rehab | acute, initial =
#   MM/DD/YYYY of the stay's initial visit or '', sign}. A visit of an acute stay is exactly as before (fac29 / 21, pos_kind '') and carries stay
#   {kind acute}. A row whose pos_err names visits that stand at HCA REHAB carries their days as a list too, 'MM/DD/YYYY' each: hospital_at61 (they
#   belong to the HOSPITAL stay this initial visit starts) or mixed_at61 (this follow-up went in at 21 behind them) - 11/25/2026, verification.
# ONLY a message whose OWN building is the hospital (every raw copy of it names that building; FAC gives fac29 / 21) and that carries a hospital visit
#   line is read. ONE message is ONE visit in AdvancedMD: when its hospital lines belong to different stays and one of them is a rehab stay, it goes
#   in as before and is said (pos_err).
# FAIL SAFE: any error while the stay is worked out - also when the batch's own visits could not be listed - = the visit goes in exactly as before
#   (fac29 / 21) with pos_err saying so. The import never stops for this rule and never guesses 61. The no-charge quality lines never ride at 61
#   (QUALITY_POS_SKIP: a rehab visit is a hospital visit for that rule).
# 11/25/2026 (review of the rule - two findings, each reproduced with a stand-in AdvancedMD that keeps the chart from run to run). The spec is silent on both; where it
#   is, the visit goes in exactly as before (fac29 / 21) and the row or the run says so:
#   THE INITIAL VISIT COMES LATE (4 of the 108 initial hospital visits in the committed registers were entered by a later batch than follow-ups of their own stay): those
#     follow-ups went in at 21 as visits of the stay before; the late initial visit and everything after it then went in at 61 - one stay 61, 21, 21, 61, 61. Now a
#     rehab stay whose initial visit is NOT entered yet while another visit of that stay already is, at another place of service (on the chart, or built so by this run)
#     keeps 21 for the WHOLE stay - its initial visit included: pos_kind rehab-stay-kept-21, the reason in pos_why. Once the initial visit stands on the chart it decides,
#     as before. The mirrored case cannot be prevented: a follow-up of a NEW hospital stay whose initial visit has not reached the feed is, for everything in hand, a
#     visit of the rehab stay before it (61). (The feed's own admission date is no sign for it: in the committed registers it stands LATER than the stay's initial visit
#     on 175 of 246 follow-ups read from their own message, in 34 of 53 stays - a test on it would take most real rehab follow-ups off 61.) When that initial visit
#     comes and starts a hospital stay that holds a visit entered at HCA REHAB, the import SAYS so: the initial visit goes in as a hospital visit, its row carries
#     pos_err (REHAB_MIXED, with the day of the visit at 61) - printed as POS RULE NOT APPLIED and counted, the way such a visit reaches the top of the report - and
#     nothing on the chart is changed: the visit at 61 is William's to correct.
#   A HOSPITAL CODE THE SAME-DAY RULE PASSES OVER (the chart already carries another hospital code of ours for its day; none in 998 chart-days of the real feed so
#     far): it counted as a visit for its own batch and was forgotten by the next - visits flipped between 21 and 61, and a hospital admission after it was read as a
#     rehab admission. Now such a line is KEPT for this rule: SAME_DAY for the rest of the run, the register's "same_day" list (chart -> [[code, DOS]]) for every later
#     run - so every run reads the same stays (the spec: every hospital visit known for the chart). And a stay that began on a day with another hospital code is
#     entered as an acute one (the spec: the same day is no rehab admission) but SHOWS no acute stay: an initial visit 1 or 2 days after ITS last visit is not read as
#     an admission to the rehab unit (it would send a patient back in the hospital to 61 when that same-day admission was the one to rehab). Both say why in pos_why.
#     What is not shown stays not shown: an admission entered as before for this reason shows no acute stay either, along stays that follow each other within 1 or
#     2 days; a break of 3 days or more ends it (hospital_stays: "shown"). The price, taken knowingly: after such a day the rest of a rehab stay keeps 21.
#   Three more findings of the same review (the task text that reached the fixer was cut off behind the two above; these are from the review's own saved result):
#   THE FACILITY NUMBER ON ONE FOLLOW-UP sent the acute admission and the acute follow-ups of its batch to 61 (the stay was a rehab stay as soon as ANY of its messages
#     named the unit; cut into two files the same messages gave 21). The number is the sign of the message that carries it (the spec: "the message's own PV1 facility
#     number"): on the stay's INITIAL visit it makes the stay a rehab stay; a follow-up that names the unit while the stay that holds it is no rehab stay is kept at 21
#     like one with no stay in hand (rehab-stay-kept-21, stay {rehab, '', facility number}) - and a stay that holds such a visit shows no acute stay either.
#   THE ORDER OF THE MESSAGES IN A FILE: a follow-up read BEFORE its stay's initial visit went in at 61 although that initial visit's own message was one the rule
#     steps aside for (hospital lines of two stays in one message; a message whose own building cannot be read) and went in at 21. The batch's own messages that carry
#     an initial visit are read for it now (batch_hospital_messages): such a follow-up is kept at 21 with its initial visit, whichever stands first.
#   (The third is the inspector step's: claimocity_inspector.py reads BOTH Claim Inspector listings for an edit about the place of service of a visit entered at 61.)
# 11/25/2026 (the independent verification of the pull request - each finding reproduced first with a stand-in AdvancedMD that keeps the chart from run to run):
#   OUR OWN NURSING-FACILITY OR HOME VISIT BETWEEN TWO HOSPITAL STAYS: the rule read hospital codes only. An initial hospital visit 1 or 2 days after an acute stay went in
#     at HCA REHAB / 61 although the chart, or the same file, showed one of our own nursing-facility visits (99304-99310, 99315, 99316) or home / assisted-living visits
#     (99341-99350) between the two: that day the patient was NOT in the hospital, so the new initial visit is a hospital admission. And a hospital follow-up with no new
#     initial visit of ours kept following a rehab stay to 61 after our own initial nursing-facility visit had shown that the stay was over. Now such a visit - dated from
#     the day of the acute stay's last visit up to the admission's own day - keeps the admission at the hospital (pos_why says why; that stay SHOWS an acute stay, it is not
#     a withheld sign), and a stay holds a follow-up only while no such visit is dated on or after the stay's last visit in hand and before that follow-up. Two days are
#     read for the stay, not against it: a nursing visit on the stay's own FIRST day (the resident came to the hospital from the nursing building that day), and a hospital
#     visit on the very day of such a visit (the stay's last day: discharged from the unit and admitted to the nursing building on one day) - there the rule reads what it
#     read before, so a follow-up that reaches the feed ahead of its stay's initial visit still keeps that initial visit at 21 with it. The facility number on the initial
#     visit's own message, and an initial visit that already stands at HCA REHAB, still make the stay a rehab stay.
#     A hospital visit that NO stay holds any more is no acute stay in hand: an initial visit 1 or 2 days behind it (the patient not known to have left the hospital since)
#     is entered as before, with words of its own (REHAB_LOOSE) - it may be the admission to the rehab unit - and the stay it starts shows no acute stay: the admission
#     after it is not read as a rehab admission either. An admission kept at the hospital because of such a visit of ours shows an acute stay only when it is SURE that the
#     patient had left the hospital: the visit is dated behind the last hospital visit, or on that very day behind a DISCHARGE visit (99238, 99239). And a LATE initial
#     visit keeps 21 when hospital visits dated behind it already stand on the chart at the hospital behind one of those visits of ours (REHAB_LATE_LET): the stay does not
#     hold them, but nothing shows that they are not its visits. (These points came out of the fixer's own comparison of random feeds with the pull request's head: a
#     visit must not go in at 61 that went in at 21 before unless one of the findings asks for it.)
#   A STAY LONGER THAN 45 DAYS was cut: from its 46th day the visits of a rehab stay at 61 went in at the hospital / 21 without a word. Now a stay that is visibly going on -
#     the visit comes at most STAY_GOES_ON_DAYS after the stay's last visit in hand - holds it past the 45 days. A visit that is past the 45 days AND more than that week
#     after the stay's last visit is in no stay, as before, and pos_why says so when the stay was a rehab stay.
#   THE INITIAL VISIT OF A REHAB STAY AT 61 WAS VOIDED on the chart (a person's void): the stay's follow-ups at HCA REHAB were then read as visits of the acute stay before
#     it. The next follow-up went in at 21 without a word, and a hospital admission the day after went in at 61 ('1-2 days after an acute stay'). Now a stay that is no
#     rehab stay but holds visits at HCA REHAB shows no acute stay - the admission after it goes in as before - and the follow-up that goes in at 21 behind those visits
#     SAYS so: pos_err REHAB_SPLIT, with the days. It is said ONCE: the row carries the days it names (mixed_at61), every run reads the rows of the registers (SAID_61), and
#     a day that was named is not named again.
#   THE SENTENCE ABOUT A HOSPITAL STAY WITH VISITS AT 61 (REHAB_MIXED) listed every day in full: the digest shows the first 70 characters of a pos_err, so from the third
#     visit on the words 'belongs to this HOSPITAL stay' were cut off and from the fifth a day was missing. Now ONE day stands as before; several stand as their first and
#     last day ('08/16-08/20/2026') with every day behind the first 70 characters, and the row carries them as a list (hospital_at61).
#   A REHAB STAY WHOSE INITIAL VISIT THE IMPORT DID NOT ENTER (99221 and 99222 start a stay for this rule but are not in the code table - 'unknown CPT'; or AdvancedMD
#     answered a fault): its follow-ups went in at 61, file after file, and nothing named the stay for William - the digest names a new rehab stay from the row of its
#     initial visit. Now a follow-up goes in at 61 only when its stay's initial visit stands on the chart at HCA REHAB, was built so by this run, or is coming in this batch
#     in a message the import reads and can enter (batch_hospital_messages); else it keeps 21 (rehab-stay-kept-21, pos_why REHAB_NO_INITIAL). main() takes back what build()
#     noted of a visit that was not entered (stay_not_entered). What cannot be prevented is SAID: a follow-up that stood BEFORE its initial visit in the file went in at 61,
#     and then that initial visit failed - the next follow-up goes in as before and says that the stay is mixed (REHAB_NO_ADMISSION), once.
#   THE ORDER OF THE MESSAGES IN A FILE, THE OTHER WAY ROUND: a stay's initial visit read BEFORE a follow-up of it whose own building cannot be read went in at 61, and
#     at 21 when it was read behind it. The initial visit now looks ahead at every hospital message of the batch that carries a line of its stay, as a follow-up does.
#   THE COUNTERS: a rehab visit AdvancedMD stored at 21 was counted and printed as entered at 61 ('rehab 61 x1') while the monitor of the same run said that no visit is at
#     61. count_pos goes by what was stored where it was read back (REHAB_61_LOST); the row keeps what was sent beside what was stored, as before.
# 11/25/2026 (the second round - what the independent check of the verification's fixes found; each point reproduced first against a stand-in AdvancedMD that keeps the chart):
#   THE BUILDING OF A NURSING-FACILITY OR HOME VISIT: the fix above counted EVERY nursing-facility or home visit code of ours as a day the patient was not in the hospital,
#     whatever building its row stands in. A nursing code whose own message names the HOSPITAL is entered at the hospital building (rules.md part 3: such a visit is held with
#     the question which building the patient was in; until 11/25/2026 the inspector step moved it to HCA REHAB at 31) - it says nothing about where the patient was. Behind
#     such a row a rehab stay at 61 dropped to the hospital / 21 without a word ('the patient had left the unit'), a rehab admission behind it was kept at 21, and one inside
#     the ACUTE stay sent the whole rehab stay after it to 21. Now such a visit counts ONLY when its row stands in one of the practice's nursing-facility or home /
#     assisted-living buildings - the buildings the facility table (FAC) enters at 31 or 13 (away_building): a row of the batch by the feed's own name of its building, a row of
#     the chart by the name AdvancedMD's history gives its facility (BUILDING_KEYS, HOME_KEYS). A row under a hospital building (fac29, fac67), in a building the table does not
#     know, or with no building is not read by the stay rule - as before the verification. (A visit from a building the table does not know goes in with NO facility: the run
#     that enters it and every later run, which finds it on the chart without one, read the same stays.)
#   A STAY THAT HAS ITS DISCHARGE VISIT IS OVER: 'a stay that is visibly going on' was judged by the days since its last visit alone - also when that last visit was the stay's
#     discharge visit (99238 / 99239). A hospital follow-up of a later episode, with no initial visit of ours, 4 or 7 days behind the discharge visit of a rehab stay longer than
#     45 days went in at HCA REHAB / 61 (inside the first 45 days it had always done so - the pull request's known limit). Now a stay whose LAST visit in hand is its discharge
#     visit holds no later visit: the follow-up is in no stay and goes in as before (the hospital, 21), with the reason in pos_why when the stay was a rehab stay (REHAB_OVER) -
#     inside the first 45 days too. It is a hospital visit that no stay holds like any other: an initial visit 1 or 2 days behind it is entered as before (REHAB_LOOSE), and it
#     never keeps that stay's late initial visit at 21 (it is not the stay's visit, in whichever order the two reach the feed).
#   AN ADMISSION THAT WAS ENTERED IS NOT FORGOTTEN: when the same admission came again in a message the import skips whole (a code the table does not have beside it), main()
#     took back what the run had noted of the admission it had just entered at 61, and the stay's follow-ups of that run went in at 21 ('its stay's initial visit is not
#     entered'). What an ENTERED message noted now stands for the rest of the run (stay_entered, ctx['stay_kept']); stay_not_entered passes such a line over. (A call that ended
#     in an error is still read as not entered - nobody knows what AdvancedMD kept, and the rest of the stay goes in as before.)
REHAB_UNIT_NUMBERS = {"1083375828"}        # the facility numbers a feed message's PV1 line names the hospital's rehabilitation unit by: the unit's own NPI. ONE constant - a number the feed is seen to send for the unit is added here
REHAB_FAC = "fac67"; REHAB_POS = "61"      # where a visit of a rehab stay goes in: AdvancedMD facility fac67 (HCA REHAB), every charge line at place of service 61 (inpatient rehabilitation facility)
REHAB_NAME = "HCA REHAB"                   # how the chart's history names a visit at fac67 (practices/ehpa/facilities.json: "HCA REHAB (TALLAHASSEE)")
REHAB_HOSPITAL = ("fac29", "21")           # the building whose messages are read: the hospital, as FAC gives it - the feed names it for the rehab unit's visits too
HOSP_INITIAL = {"99221", "99222", "99223"} # an initial hospital visit: a stay starts with it
HOSP_DISCHARGE = {"99238", "99239"}        # a hospital discharge visit: behind it the patient is out of the hospital that very day (11/25/2026, verification)
STAY_MAX_DAYS = 45                         # a stay holds a visit this many days after its initial visit (the window the inspector step and the order sweep use for the admission date)
STAY_GOES_ON_DAYS = 7                      # ... and past them (11/25/2026, verification) still a visit that comes at most this many days after the stay's LAST visit in hand: a stay that is visibly going on is never cut in two
REHAB_GAP_DAYS = (1, 2)                    # a new initial visit this many days after the LAST visit of an ACUTE stay = admitted to the rehabilitation unit
# 11/25/2026 (second round): the buildings in which one of our nursing-facility or home visits shows that the patient had left the hospital - the practice's nursing-facility and
# home / assisted-living buildings, as the facility table (FAC) enters them. HOME_KEYS names the home / assisted-living ones the way the chart's history names a visit there
# (AdvancedMD's own facility name: one word of it per building, the building's facility id beside it), as BUILDING_KEYS does for the nursing buildings.
AWAY_POS = ("31", "13")                    # the places of service the facility table gives a nursing-facility building (31) and a home / assisted-living building (13) of the practice
HOME_KEYS = (("AZALEA GARDENS", "fac37"), ("TAPESTRY", "fac55"), ("HERMITAGE", "fac53"), ("CAPITAL SQUARE", "fac54"), ("CANTERFIELD", "fac38"), ("SODALIS", "fac65"), ("ALLEGRO", "fac57"))
SIGN_NUMBER = "facility number"; SIGN_ADMIT = "new admission 1-2 days after an acute stay"      # the two signs, as the register's stay.sign and pos_why name them
REHAB_KEPT = "rehab-stay-kept-21"          # pos_kind of a visit of a rehab stay that keeps 21 because its stay's initial visit went in at 21 (the monitor's comparison group)
REHAB_WHY = "inpatient rehab stay: %s"     # pos_why of a visit of a rehab stay: the sign that shows the stay (the words carry no date)
# 11/25/2026 (review): the words of the cases the spec is silent on - for pos_why (they carry no date)
REHAB_LATE = " - kept at 21: another visit of this stay is already on the chart at the hospital - it reached the feed before the stay's initial visit - and a stay is never mixed"
REHAB_LATE_LET = (" - kept at 21: a hospital visit dated behind this stay's initial visit is already on the chart at the hospital - it reached the feed before that initial visit, and one of our own nursing-facility or home / assisted-living "
                  "visits is dated between the two, so nothing shows whether it is a visit of this stay - and a stay is never 61 beside 21 because its messages came in another order")      # 11/25/2026 (verification)
REHAB_ASIDE = " - kept at 21: a visit of this stay stands in this batch in a message the rule steps aside for (its own building cannot be read, or it carries hospital lines of another stay too - it goes in as before, at 21), and a stay is never mixed"
REHAB_SAME_DAY = "as before: this day carries another hospital visit code of ours too - the same day is not read as an admission to the rehab unit (one hospital visit a day)"
REHAB_NOT_SHOWN = "as before: by its date this would be an admission to the rehab unit, but nothing shows that the stay before it was an acute stay - it began on a day that carries two hospital visit codes, one of its follow-ups names the rehab unit or stands at HCA REHAB, or it was itself entered as before for this reason"
# 11/25/2026 (verification): five more for pos_why ...
REHAB_AWAY = "as before: by its date this would be an admission to the rehab unit, but one of our own nursing-facility or home / assisted-living visits is dated between the last visit of the hospital stay before it and this visit, or on one of those two days - the patient had left the hospital, so this is a new hospital admission"
REHAB_LEFT = "as before: one of our own nursing-facility or home / assisted-living visits is dated between the last visit of the inpatient rehab stay before it and this visit, or on the day of that last visit - the patient had left the unit, and no initial hospital visit of ours has begun a new stay since: no stay holds this visit"
REHAB_LOOSE = "as before: by its date this would be an admission to the rehab unit, but the hospital visit 1 or 2 days before it belongs to no stay - it came behind one of our own nursing-facility or home / assisted-living visits, behind the discharge visit of the stay before it, past the days of that stay, or with no initial hospital visit of ours in hand - so nothing shows that an acute stay came before it"
REHAB_OVER = "as before: the last visit of the inpatient rehab stay before it is that stay's discharge visit - the stay is over, and no initial hospital visit of ours has begun a new stay since: no stay holds this visit"      # (second round) for pos_why, like the two beside it
REHAB_PAST = "as before: more than %d days after the initial visit of the inpatient rehab stay before it, and more than %d days after that stay's last visit in hand - no stay holds this visit" % (STAY_MAX_DAYS, STAY_GOES_ON_DAYS)
REHAB_NO_INITIAL = (" - kept at 21: its stay's initial visit is not entered - it is not on the chart, and no message of this batch that the import can enter carries it (a code the import's table does not have, "
                    "a visit AdvancedMD did not take, or a message of an earlier batch) - and no visit goes in at HCA REHAB behind an admission that was not entered")
# ... and the three sentences for pos_err: a visit that goes in as before while other visits of the stay in hand stand at HCA REHAB / 61. Each begins 'PLACE OF SERVICE 61 on <days>' and says
# what matters in its FIRST 70 CHARACTERS - the digest shows no more of a pos_err: the days (days_words) and what they are. The first: %s = the days, the days once more in full,
# 'it' / 'they', '' / 's', 'is' / 'are'. The second: the days, in full, 'that visit stands' / 'those visits stand', 'it' / 'them', the day of the stay's initial visit, '' / 's', 'is' / 'are'.
# The third: the days, in full, the day of the stay's initial visit.
REHAB_MIXED = ("PLACE OF SERVICE 61 on %s belongs to this HOSPITAL stay%s - %s went in at HCA REHAB before the stay's initial visit (this one) reached the feed. This visit is entered as before "
               "(fac29 / 21); nothing was changed on the chart - for William: the visit%s at 61 %s his to correct")
REHAB_SPLIT = ("PLACE OF SERVICE 61 on %s, 21 here: the stay is MIXED%s - %s at HCA REHAB, while the initial visit of the stay in hand for %s (%s) stands at the hospital. This visit is entered as before "
               "(fac29 / 21); nothing was changed on the chart - for William: the visit%s at 61 %s his to correct")
REHAB_NO_ADMISSION = ("PLACE OF SERVICE 61 on %s, 21 here: the stay is MIXED%s - the initial visit of this rehab stay (%s) is not entered, and no visit goes in at HCA REHAB behind an admission that was not entered. "
                      "This visit is entered as before (fac29 / 21); nothing was changed on the chart - for William: once the admission is entered, the visits of this stay at 61 or at 21 are his to correct")
# ... and (second round) a fourth, with the same first words: a follow-up behind the DISCHARGE visit of the stay before it (in no stay: the hospital, 21) while other visits behind that
# discharge visit stand at HCA REHAB. %s = the days, in full, 'that visit stands' / 'those visits stand', the day of that discharge visit, '' / 's', 'is' / 'are'.
REHAB_ADRIFT = ("PLACE OF SERVICE 61 on %s, 21 here: the stay is MIXED%s - %s at HCA REHAB with no initial hospital visit of ours in hand: the stay before ended with its discharge visit (%s), and no stay holds a visit behind it. "
                "This visit is entered as before (fac29 / 21); nothing was changed on the chart - for William: the visit%s at 61 %s his to correct")
REHAB_61_LOST = "POS 61 SENT for an inpatient rehab visit - AdvancedMD stored another place of service, so the visit is NOT at 61 (see POS NOT KEPT)"      # (verification) counted INSTEAD of the counter below when the read-back shows no line at 61: the import's numbers go by what was stored, as pos61_monitor.py does
REHAB_61_COUNT = "POS 61 inpatient rehab visit - entered at HCA REHAB (William 11/25/2026)"      # the DONE-line counters of this rule, one per VISIT (count_pos); the short POS RULE line ends with both
REHAB_21_COUNT = "POS 21 visit of an inpatient rehab stay kept at 21 (no look-back, no mixing - see pos_why)"
def at_rehab_unit(facname):
    """True when a facility name the chart's history gives is the hospital's rehabilitation unit (AdvancedMD facility fac67, HCA REHAB)."""
    return REHAB_NAME in " ".join(str(facname or "").upper().split())
def away_building(where):
    """True when `where` names one of the practice's nursing-facility or home / assisted-living buildings - a building the facility table (FAC) enters at 31 or 13. `where` is the
    FEED's own name of a building (a key of FAC: the table itself answers - also that the building is the hospital), or the facility name the CHART's history gives (AdvancedMD's
    own name of the facility: read by the word of its building in BUILDING_KEYS / HOME_KEYS). Anything else is no such building: the hospital under either name, its rehabilitation
    unit (HCA REHAB), a building neither table knows, an empty name, no name at all.
    11/25/2026 (second round): the stay rule reads one of our nursing-facility or home visits as 'that day the patient was NOT in the hospital' only when its row stands in such a
    building. A nursing code whose own message names the hospital is entered at the hospital building, and until 11/25/2026 the inspector step moved it to HCA REHAB at 31: either
    way it says nothing about where the patient was. Pure: no AMD call, no file. Never raises."""
    if not isinstance(where, str) or not where.strip(): return False
    if where in FAC: return FAC[where][1] in AWAY_POS
    n = " ".join(where.upper().split()); ours = {f for f, p in FAC.values() if p in AWAY_POS}
    return not at_rehab_unit(n) and any(word in n and fac in ours for word, fac in BUILDING_KEYS + HOME_KEYS)
def rehab_unit_lines(fid):
    """[(code, 'MM/DD/YYYY')]: the hospital visit lines of this feed patient's messages in the batch's raw files whose PV1 line names the rehab unit - a number of
    REHAB_UNIT_NUMBERS in EVERY raw copy of the message (copies that do not agree on it show nothing). The message being built and the batch's other messages alike."""
    out = []
    for (p, pairs), units in MSGUNIT.items():
        if p != str(fid or "") or not units or not units <= REHAB_UNIT_NUMBERS: continue
        out += [(c, mdy(d)) for c, d in pairs if c in HOSP_VISIT and _d8_day(d) is not None]
    return out
def batch_hospital_messages(fid):
    """[(hospital visit lines [(code, 'MM/DD/YYYY')], readable, enterable)]: every message of this feed patient in the batch's raw files that carries a hospital visit line.
    readable = the rule will read it - every raw copy of it names ONE building, the hospital (build() runs the rule for no other message; any other goes in as before);
    enterable = every code of the message is in the import's code table (a message with a code the table does not have is skipped whole: 'unknown CPT').
    11/25/2026 (review): a follow-up that stands in the file BEFORE its stay's initial visit is read with that message (rehab_visit). 11/25/2026 (verification): the stay's
    INITIAL visit is read with its follow-ups' messages the same way - until then only the messages that carry an initial visit were listed."""
    out = []
    for (p, pairs), own in MSGOF.items():
        if p != str(fid or ""): continue
        hl = [(c, mdy(d)) for c, d in pairs if c in HOSP_VISIT and _d8_day(d) is not None]; names = {o[0] for o in own}
        if hl: out.append((hl, len(names) == 1 and FAC.get(next(iter(names))) == REHAB_HOSPITAL, all(c in PCODE for c, _d in pairs)))
    return out
def days_words(days):
    """(short, full): how the days of some visits stand in a sentence whose FIRST 70 CHARACTERS must carry them (the digest shows no more of a pos_err). ONE day: the day, and ''.
    Several: their first and last day as '08/16-08/20/2026' (both in full when they lie in two years), and every day in brackets for the rest of the sentence:
    ' (5 visits: 08/16/2026, ...)'. days = dates."""
    ds = sorted(set(days))
    if len(ds) < 2: return (_fmt_day(ds[0]) if ds else ""), ""
    return "%s-%s" % (ds[0].strftime("%m/%d") if ds[0].year == ds[-1].year else _fmt_day(ds[0]), _fmt_day(ds[-1])), " (%d visits: %s)" % (len(ds), ", ".join(_fmt_day(x) for x in ds))
def stay_not_entered(ctx, lines):
    """11/25/2026 (verification): lines = [(code, 'MM/DD/YYYY')] of a message the import did NOT enter - a code its table does not have, no usable diagnosis, a fault, a call that
    ended in an error. What build() noted of it for the stay rule is taken back (nothing stands on the chart at that place), and the day of an INITIAL hospital visit among them
    is kept in ctx['stay_gone']: for the rest of this run no follow-up goes in at HCA REHAB behind an admission that was not entered. Never raises.
    11/25/2026 (second round): what an ENTERED message noted is never taken back. A line whose day this run has seen stored (ctx['stay_kept'] - stay_entered) is passed over: the
    same admission sent again in a message the import skips whole (a code the table does not have beside it), or another initial code for a day whose initial visit this run
    entered. Until then the skipped copy made the run forget the admission it had just entered at 61, and the stay's follow-ups of that run went in at 21."""
    try:
        kept = ctx.get("stay_kept") if isinstance(ctx.get("stay_kept"), set) else ()
        for c, d in lines:
            if c not in HOSP_VISIT or (d, c in HOSP_INITIAL) in kept: continue
            if isinstance(ctx.get("stay_sent" if c in HOSP_INITIAL else "stay_sent_fu"), dict): ctx["stay_sent" if c in HOSP_INITIAL else "stay_sent_fu"].pop(d, None)
            if c in HOSP_INITIAL: ctx.setdefault("stay_gone", set()).add(d)
    except Exception: pass
def stay_entered(ctx, lines):
    """11/25/2026 (second round): lines = [(code, 'MM/DD/YYYY')] of a message AdvancedMD STORED in this run (a dry run: that a live run would enter). The day of each hospital visit
    among them is kept in ctx['stay_kept'] - {(day, True for an initial visit)}: what build() noted of it for the stay rule stands for the rest of the run (stay_not_entered passes
    it over). Never raises."""
    try:
        for c, d in lines:
            if c in HOSP_VISIT: ctx.setdefault("stay_kept", set()).add((d, c in HOSP_INITIAL))
    except Exception: pass
def hospital_stays(rows, unit_lines=(), chart_rows=(), sent=None, sent_fu=None):
    """The hospital STAYS of ONE chart, oldest first, and the stay that holds each visit. rows = every hospital visit known for the chart - (code, 'MM/DD/YYYY'[, ...]) from
    the chart's history, this batch, the lines the same-day rule passed over (SAME_DAY) and the message itself (other codes and odd rows are passed over); unit_lines = the
    (code, 'MM/DD/YYYY') lines whose own feed message names the rehab unit; chart_rows = the chart's history rows alone, with their facility names; sent = {'MM/DD/YYYY' of an
    initial visit: the place of service this run built it with}; sent_fu = the same for the other hospital visits this run built.
    -> (stays, holder). stays = [{"initial": day, "last": the day of the last visit it holds, "kind": "acute" | "rehab", "sign": SIGN_NUMBER | SIGN_ADMIT | "" (a rehab stay
    known only by where its initial visit went in), "on_chart": the facility names of the initial visit's rows on the chart, "at_rehab": that visit went in at HCA REHAB (as
    the chart shows it, else as this run built it), "elsewhere" / "at61" (11/25/2026, review): the days of the stay's OTHER visits that are already entered at another place of
    service / at HCA REHAB - on the chart, or built so by this run -, "note": the words for pos_why of an acute stay the spec's plain rule does not explain ('' else)}];
    holder = {(day, True for an initial visit / False for any other hospital visit): the index of the stay that holds it, None = no stay does}. Pure: no AMD call, no file.
    11/25/2026 (verification): rows may hold our own nursing-facility and home / assisted-living visits too (NF_VISIT, HOME_VISIT - build() hands them over with the chart's
    history and the batch): on such a day the patient was NOT in the hospital. (a) A stay holds a follow-up only while no such visit is dated on or after the stay's last visit
    in hand and before that follow-up. Two days are read FOR the stay: a visit on the stay's own first day does not count (the resident came to the hospital from the nursing
    building that day), and a hospital visit on the very day of such a visit is still the stay's - its last day, as the rule read it before. (b) An initial visit 1 or 2 days
    after an acute stay is no admission to the rehab unit when such a visit is dated from the day of that stay's last visit up to the initial visit's own day: the patient had
    left the hospital - a hospital admission, and that stay SHOWS an acute stay. (c) Past STAY_MAX_DAYS a stay still holds a visit that comes at most STAY_GOES_ON_DAYS after its
    last visit in hand. Each stay also carries "out": {the day of a follow-up it does NOT hold for one of these reasons: "away" (a) | "past" (the days ran out)}; a stay that is
    no rehab stay but holds visits at HCA REHAB shows no acute stay; (d) "loose": its initial visit comes 1 or 2 days behind a hospital visit that NO stay holds, and the
    patient is not known to have left the hospital since - nothing shows an acute stay before it: it is entered as before (note REHAB_LOOSE) and shows no acute stay either;
    (e) "left": it is SURE that the patient had left the hospital between the last hospital visit before this stay and its initial visit - such a visit of ours is dated behind
    that day, or on that very day behind a discharge visit (HOSP_DISCHARGE); an admission kept at the hospital under (b) shows an acute stay only then; and (f) "let": the days
    of the visits the stay let go under (a) that already stand on the chart at another place of service - a late initial visit is kept at 21 with them (rehab_visit).
    11/25/2026 (second round): (g) such a visit of ours counts ONLY when its row stands in one of the practice's nursing-facility or home / assisted-living buildings - the third
    element of the row: the feed's own name of the building, or the facility name the chart's history gives (away_building). A row under a hospital building (a nursing code whose
    own message names the hospital; one the inspector step moved to HCA REHAB), in a building the facility table does not know, or with no building says nothing about where the
    patient was and is passed over like any other code. (h) A stay whose LAST visit in hand is its discharge visit (HOSP_DISCHARGE) is over: it holds no later visit - "out" says
    "over" for the follow-up it lets go, inside the first 45 days too. Such a follow-up is a hospital visit that no stay holds, like one let go under (a)."""
    days = {}; names = {}; flagged = set(); away = set(); free = None
    for row in rows:
        try: c, d = row[0], row[1]
        except Exception: continue
        if not isinstance(c, str) or not d or not (c in HOSP_VISIT or c in NF_VISIT or c in HOME_VISIT): continue
        try: dd = _day(d)
        except Exception: continue
        if c in HOSP_VISIT: days.setdefault(dd, set()).add(c); continue
        try: where = row[2] if len(row) > 2 else None      # (second round) the building the row stands in
        except Exception: where = None
        if away_building(where): away.add(dd)      # (verification) one of our own nursing-facility or home / assisted-living visits: that day the patient was not in the hospital - (second round) when its row stands in one of the practice's nursing-facility or home / assisted-living buildings
    for row in chart_rows or ():      # where each hospital visit on the chart stands: (day, initial visit or not) -> the facility names of its rows
        try:
            if row[0] in HOSP_VISIT: names.setdefault((_day(row[1]), row[0] in HOSP_INITIAL), []).append(row[2] if len(row) > 2 else "")
        except Exception: continue
    for row in unit_lines or ():
        try: flagged.add((_day(row[1]), row[0] in HOSP_INITIAL))
        except Exception: continue
    stays = []; holder = {}
    for d in sorted(days):
        ini = bool(days[d] & HOSP_INITIAL); non = bool(days[d] - HOSP_INITIAL); cur = len(stays) - 1
        if non:      # a follow-up or discharge visit: the stay before it holds it for STAY_MAX_DAYS - and past them while the stay is visibly going on; else it belongs to an initial visit of the same day, else to no stay
            s = stays[cur] if cur >= 0 else None
            # (second round) "over": the stay's last visit in hand is its discharge visit - the stay is over and holds no later visit, also inside its first 45 days (until then a
            # hospital follow-up of a later episode a few days behind the discharge visit of a rehab stay went in at 61). Behind one of our nursing or home visits it is "away", as
            # before. The discharge visit must be the stay's OWN (s["over"]): a stay that begins on the very day of the discharge visit of the stay before it is not over by that visit
            out = None if s is None else "away" if any(s["last"] <= x < d and x > s["initial"] for x in away) else "over" if s["over"] else "past" if ((d - s["initial"]).days > STAY_MAX_DAYS and (d - s["last"]).days > STAY_GOES_ON_DAYS) else ""
            if out == "": s["last"] = d; s["over"] = bool(days[d] & HOSP_DISCHARGE); holder[(d, False)] = cur
            else:
                holder[(d, False)] = (cur + 1) if ini else None
                if out and not ini: s["out"][d] = out      # (verification) the stay let this visit go, and why - rehab_visit says it in pos_why
                if not ini: free = d      # (verification) the last hospital visit so far that NO stay holds
        if ini:      # gap: the days since the LAST visit of the stay before (0 = that stay has a visit on this very day); both: this day carries another hospital visit too
            before = free if free is not None else (stays[cur]["last"] if cur >= 0 else None)      # (verification) the day of the last hospital visit before this one - the stay before holds it, or no stay does (free)
            left = before is not None and (any(before < x <= d for x in away) or (before in away and bool(days[before] & HOSP_DISCHARGE)))      # ... and it is SURE that the patient had left the hospital since: one of our nursing or home visits behind that day, or on that very day behind a discharge visit
            stays.append({"initial": d, "last": d, "gap": (d - stays[cur]["last"]).days if cur >= 0 else None, "both": non, "out": {},
                          "over": non and holder.get((d, False)) == cur + 1 and bool(days[d] & HOSP_DISCHARGE),      # over (second round): the stay's last visit in hand is its OWN discharge visit - here: one on the stay's first day that the stay before does not hold
                          "away": cur >= 0 and any(stays[cur]["last"] <= x <= d for x in away),      # away (verification): one of our nursing-facility or home visits from the day of the last visit of the stay before up to this day
                          "left": left, "loose": free is not None and (d - free).days in REHAB_GAP_DAYS and not left})      # loose (verification): a hospital visit that no stay holds 1 or 2 days before this day, and the patient is not known to have left the hospital since
            holder[(d, True)] = cur + 1; free = None
    for k, s in enumerate(stays):      # the kinds, oldest first: each stay is read against the one before it
        # 11/25/2026 (review): the facility number is the sign of the message that carries it. On the stay's INITIAL visit it makes the stay a rehab stay; on a follow-up alone it
        # does not re-label the stay (until then ONE such follow-up sent the acute admission and the acute follow-ups of its batch to 61) - that visit is kept at 21 (rehab_visit)
        number = (s["initial"], True) in flagged
        s["on_chart"] = names.get((s["initial"], True)) or []
        s["at_rehab"] = all(at_rehab_unit(n) for n in s["on_chart"]) if s["on_chart"] else str((sent or {}).get(_fmt_day(s["initial"])) or "") == REHAB_POS
        # 11/25/2026 (review): where the stay's OTHER visits already stand - on the chart (the facility names of their rows) or as this run built them
        fu = sorted(f[0] for f in holder if holder[f] == k and not f[1]); built = lambda d: str((sent_fu or {}).get(_fmt_day(d)) or "")
        s["elsewhere"] = [d for d in fu if any(not at_rehab_unit(n) for n in names.get((d, False), ())) or built(d) not in ("", REHAB_POS)]
        s["at61"] = [d for d in fu if any(at_rehab_unit(n) for n in names.get((d, False), ())) or built(d) == REHAB_POS]
        # ... and (verification) the visits the stay LET GO behind one of our nursing or home visits that already stand on the CHART at another place of service: they reached the
        # feed before the stay's initial visit. The chart alone - what this run builds for a visit that is in no stay must not move the initial visit of the same file
        s["let"] = [d for d in sorted(s["out"]) if s["out"][d] == "away" and any(not at_rehab_unit(n) for n in names.get((d, False), ()))]
        # ... and (second round) the visits the stay let go behind its DISCHARGE visit that stand at HCA REHAB - on the chart, or built so by this run: the initial visit of a
        # rehab stay behind this stay was voided or changed on the chart since, or an import from before the second round entered a visit of a later episode at 61. No stay
        # holds them now, so nothing else would name them: the next follow-up behind that discharge visit goes in at 21 beside them and SAYS so (rehab_visit, REHAB_ADRIFT)
        s["over61"] = [d for d in sorted(s["out"]) if s["out"][d] == "over" and (any(at_rehab_unit(n) for n in names.get((d, False), ())) or built(d) == REHAB_POS)]
        # ... and (review) the stay before it SHOWS an acute stay only when it did not begin on a day that carries another hospital code too: that one is entered as an acute stay
        # (the same day is no rehab admission) but may as well be the admission to rehab the same-day rule did not enter - an initial visit after it is never 61 on that
        # ... nor (review) when one of its follow-ups names the rehab unit while its initial visit does not: the patient was in the unit during that "acute" stay
        s["unit"] = any((d, False) in flagged for d in fu)
        # ... nor when it is itself an admission that was entered as before for this reason: what is not shown stays not shown along stays that follow each other within 1 or
        # 2 days (else the stay AFTER a withheld admission would be read as the rehab admission - and send a patient back in the hospital to 61). A break of 3 days or more ends it.
        # ... (verification) nor when it holds a visit that stands at HCA REHAB although it is no rehab stay: the initial visit of a rehab stay was voided or changed on the chart
        # since, or a visit of this stay went in at 61 before its initial visit came - the admission after it is entered as before
        # ... and (verification) an admission 1 or 2 days after an acute stay is NO rehab admission when one of our nursing-facility or home visits lies between the two (s["away"]):
        # the patient had left the hospital. That is no withheld sign - it is shown - so the stay it starts shows an acute stay like any other
        # ... and (verification) an admission 1 or 2 days behind a hospital visit that NO stay holds (s["loose"]: that visit came behind one of our nursing or home visits, past the
        # days of the stay before it, or with no initial visit of ours before it) is read against no stay: it is entered as before - it may be the admission to the rehab unit behind
        # an acute stay nobody has in hand - and the stay it starts shows no acute stay, like one whose sign was withheld
        near = k > 0 and not s["both"] and not s["loose"] and s["gap"] in REHAB_GAP_DAYS and stays[k - 1]["kind"] == "acute"; admit = near and stays[k - 1]["shown"] and not s["away"]
        s["kind"] = "rehab" if (number or admit or s["at_rehab"]) else "acute"; s["sign"] = SIGN_NUMBER if number else SIGN_ADMIT if admit else ""
        # ... and (verification) an admission that is kept at the hospital because of one of our nursing or home visits (s["away"]) shows an acute stay only when it is SURE that
        # the patient had left the hospital (s["left"]): on the very day of the stay's last visit such a visit shows it only behind a discharge visit
        s["shown"] = s["kind"] == "acute" and not s["both"] and not s["unit"] and not (near and not s["left"]) and not s["loose"] and not s["at61"]      # this stay SHOWS an acute stay (near and still acute while the patient is not known to have left the hospital = its own admission sign was withheld)
        s["note"] = "" if s["kind"] != "acute" else REHAB_AWAY if (near and s["away"]) else REHAB_NOT_SHOWN if near else REHAB_SAME_DAY if (k > 0 and s["both"]) else REHAB_LOOSE if s["loose"] else ""
    return stays, holder
def rehab_visit(lines, chart_rows, batch_rows, unit_lines=(), sent=None, sent_fu=None, messages=None, gone=None, said61=None):
    """ONE feed message from the hospital building -> None when it carries no hospital visit line, else {"to61": True when the visit goes in at HCA REHAB with every line at 61,
    "stay": {"kind", "initial", "sign"} for the register row, "why": the words for pos_why ('' for a visit of an acute stay the plain rule explains)} - and, only when there is
    something to SAY (11/25/2026, review and verification), "said": the words for pos_err of a visit that goes in as before while other visits of the stay in hand stand at HCA
    REHAB, "at61": the days of those visits as 'MM/DD/YYYY', and "at61_kind": "hospital" (they belong to the HOSPITAL stay this initial visit starts) or "mixed" (a follow-up
    that goes in at 21 behind them).
    lines = [(code, 'MM/DD/YYYY')] of EVERY charge line of the message, also the ones already on the chart; chart_rows = the chart's history rows (code, date, facility name);
    batch_rows = this batch's visits of the chart (BATCH_NF - code, date and the FEED's own name of the building) and the lines the same-day rule passed over (SAME_DAY); unit_lines = the lines whose own feed message names the
    rehab unit (rehab_unit_lines); sent / sent_fu = what this run built for the chart's initial / other hospital visits (hospital_stays); messages = the batch's own messages
    that carry a hospital visit line (batch_hospital_messages); gone = the days of initial hospital visits this run could not enter (stay_not_entered); said61 = the days of
    visits at 61 that a row of an import register has already named (SAID_61) - each day is said ONCE.
    Raises when the message's hospital lines belong to different stays and one of them is a rehab stay: one message is one visit - the caller enters it as before and says so.
    Pure: no AMD call, no file."""
    hosp = [(c, d) for c, d in lines if c in HOSP_VISIT]
    if not hosp: return None
    # 11/25/2026 (second round): a row of the BATCH names its building as the feed does, and the facility table alone says which building that is. A name the table does not know
    # is no building here - never read by its words: its visit goes in with NO facility, and that is how every later run finds it on the chart, so both runs read the same stays
    batch = []
    for row in batch_rows or ():
        try: batch.append(row if (len(row) < 3 or (isinstance(row[2], str) and row[2] in FAC)) else (row[0], row[1]))
        except Exception: batch.append(row)      # an odd row: handed on as it is - hospital_stays passes it over
    stays, holder = hospital_stays(list(chart_rows or ()) + batch + hosp, unit_lines, chart_rows, sent, sent_fu)
    named = {(c, d) for c, d in unit_lines or ()}; out = []; said = ""; at61 = []; kind61 = ""
    held = lambda c2, d2: holder.get((_day(d2), c2 in HOSP_INITIAL))
    new61 = lambda s: [x for x in s["at61"] if _fmt_day(x) not in (said61 or ())]      # the visits of a stay that stand at HCA REHAB and that no row has named yet
    for c, d in hosp:
        k = holder.get((_day(d), c in HOSP_INITIAL))
        if k is not None and stays[k]["kind"] != "rehab" and (c, d) in named and c not in HOSP_INITIAL: k = None      # (review) a follow-up that names the rehab unit while the stay that holds it is no rehab stay: its own stay's initial visit is not in hand
        if k is None:      # in no stay: exactly as before - also when its own message names the rehab unit (nothing shows where that stay began: never 61 on a guess)
            let = next((s for s in stays if _day(d) in s["out"] and s["kind"] == "rehab"), None)      # (verification) a rehab stay that let this visit go: the row says why it is not a visit of that stay
            # (second round) a follow-up behind the DISCHARGE visit of the stay before it is in no stay - and when other visits behind that discharge visit stand at HCA REHAB (the initial
            # visit of a rehab stay was voided on the chart since; an earlier import entered a visit of a later episode at 61), this one goes in at 21 beside them: SAID, once
            _ov = next((s for s in stays if s["out"].get(_day(d)) == "over"), None)
            _n = [x for x in (_ov["over61"] if _ov else ()) if x != _day(d) and _fmt_day(x) not in (said61 or ())]
            if _n: said = REHAB_ADRIFT % (days_words(_n)[0], days_words(_n)[1], "those visits stand" if len(_n) > 1 else "that visit stands", _fmt_day(_ov["last"]), "s" if len(_n) > 1 else "", "are" if len(_n) > 1 else "is"); at61 = _n; kind61 = "mixed"
            out.append((None, {"kind": "rehab", "initial": "", "sign": SIGN_NUMBER}, False, REHAB_WHY % SIGN_NUMBER + " - kept at 21: no initial hospital visit of ours that starts a rehab stay is in hand for it (none within %d days before it, or one that does not name the unit), so nothing shows where its stay began" % STAY_MAX_DAYS)
                       if (c, d) in named else (None, {"kind": "acute", "initial": "", "sign": ""}, False, "" if let is None else {"away": REHAB_LEFT, "over": REHAB_OVER}.get(let["out"][_day(d)], REHAB_PAST)))      # (second round) "over": behind that stay's discharge visit
            continue
        s = stays[k]; st = {"kind": s["kind"], "initial": _fmt_day(s["initial"]), "sign": s["sign"]}
        if s["kind"] != "rehab":      # a hospital stay: as before - and SAID, once, when a visit of the stay in hand stands at HCA REHAB
            _n = new61(s); _w = days_words(_n); _pl = len(_n) > 1
            if c in HOSP_INITIAL and _n:      # (review) its INITIAL visit: a follow-up of this stay reached the feed first and went in as a visit of the rehab stay before
                said = REHAB_MIXED % (_w[0], _w[1], "they" if _pl else "it", "s" if _pl else "", "are" if _pl else "is"); at61 = _n; kind61 = "hospital"
            elif c not in HOSP_INITIAL and _n and s["on_chart"]:      # (verification) a FOLLOW-UP of a stay whose initial visit stands on the chart at the hospital, behind visits at HCA REHAB: the initial visit of a rehab stay was voided or changed since. (An initial visit of this stay that is still to be entered says it itself.)
                said = REHAB_SPLIT % (_w[0], _w[1], "those visits stand" if _pl else "that visit stands", "them" if _pl else "it", st["initial"], "s" if _pl else "", "are" if _pl else "is"); at61 = _n; kind61 = "mixed"
            out.append((k, st, False, s["note"])); continue
        entered = bool(s["on_chart"]) or (sent or {}).get(st["initial"]) is not None
        # NO LOOK-BACK, NO MIXING: the visit follows its stay's initial visit - on the chart, else as this run built it. Not entered yet: at 61 - unless
        #   (review) another visit of the stay is already entered at another place of service (it reached the feed before the initial visit): then the WHOLE stay keeps 21, its
        #     initial visit included;
        #   (review, and for the stay's initial visit too since the verification) a visit of the stay stands in this batch in a message the rule steps aside for - one whose own
        #     building cannot be read, or one that carries hospital lines of another stay too: that message goes in as before, at 21, whichever of them is read first (until
        #     then a follow-up read first went in at 61 ahead of such an initial visit, and an initial visit read first went in at 61 ahead of such a follow-up);
        #   (verification) the stay's initial visit is NOT ENTERED and is not coming either - no message of this batch that the import can enter carries it (a code its table does
        #     not have; a visit AdvancedMD did not take; a message of an earlier batch): no follow-up goes in at HCA REHAB behind an admission nobody entered. Where a visit of
        #     the stay already stands at 61 (it was read before the initial visit that then failed), that is SAID once (pos_err).
        mine = [m for m in (messages or ()) if any(held(c2, d2) == k for c2, d2 in m[0])]      # the batch's own messages that carry a hospital line of this stay
        aside = (not entered) and any((not m[1]) or any(held(c2, d2) != k for c2, d2 in m[0]) for m in mine)
        coming = c in HOSP_INITIAL or (st["initial"] not in (gone or ()) and any(m[1] and m[2] and (st["initial"] in [d2 for c2, d2 in m[0] if c2 in HOSP_INITIAL]) and all(held(c2, d2) == k for c2, d2 in m[0]) for m in mine))
        if entered: to61 = s["at_rehab"]; why = REHAB_WHY % (s["sign"] or "its initial visit went in at HCA REHAB") if to61 else REHAB_WHY % s["sign"] + " - kept at 21, where its stay's initial visit went in: a stay is never mixed"
        elif aside: to61 = False; why = REHAB_WHY % s["sign"] + REHAB_ASIDE
        elif not coming:
            to61 = False; why = REHAB_WHY % s["sign"] + REHAB_NO_INITIAL; _n = [] if s["elsewhere"] else new61(s)
            if _n: said = REHAB_NO_ADMISSION % (days_words(_n)[0], days_words(_n)[1], st["initial"]); at61 = _n; kind61 = "mixed"
        elif s["elsewhere"]: to61 = False; why = REHAB_WHY % s["sign"] + REHAB_LATE
        elif s["let"]: to61 = False; why = REHAB_WHY % s["sign"] + REHAB_LATE_LET      # (verification) hospital visits dated behind the initial visit stand on the chart at 21, behind one of our nursing or home visits: the stay does not hold them, but nothing shows that they are not its visits
        else: to61 = True; why = REHAB_WHY % (s["sign"] or "its initial visit went in at HCA REHAB")
        out.append((k, st, to61, why))
    more = dict({"said": said} if said else {}, **({"at61": [_fmt_day(x) for x in sorted(set(at61))], "at61_kind": kind61} if (said and at61) else {}))
    if all(o[1]["kind"] == "acute" for o in out): return dict({"to61": False, "stay": out[0][1], "why": out[0][3]}, **more)
    if len({(o[0], o[2]) for o in out}) > 1: raise ValueError("the hospital lines of this message belong to different stays, one of them an inpatient rehab stay")
    return dict({"to61": out[0][2], "stay": out[0][1], "why": out[0][3]}, **more)
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
def _text_pause(charges, void, wrongc, pcode, code, looks):
    """ANOTHER CODE TEXT is on record for a no-charge line's id (1123F: pcode65441, M0004: pcode692183): THE PAUSE IS WHAT THIS RUN READS (11/12/2026 -
    until then the code switched itself off for it). charges = the line charges of the registers, oldest first; void = the ones known void; wrongc =
    the charge whose detail showed the other text; looks = the run's count of reads. That charge is read again first (one read). When that read
    fails, or the charge is no longer in AdvancedMD's answer or shows no procedure or another one, the newest other line that is not void is read in
    its place (one more read). -> (the other text, the charge that shows it) when a read of this run shows another text for the id: the pause goes
    on; ('', '') when a read shows the id with the text `code` or with no text named - or when no read failed and no line shows the id any more
    (nothing could ever read `code` from them): the pause is over and the code goes on where it stood; None when a read failed and no read showed
    the id at all: nothing is known this run, and the pause goes on as it was."""
    def text(c):      # -> ("wrong", the text) | ("right", "") | ("error", "") the read failed | ("gone", "") not in the answer, no procedure or another one
        sn = {}; looks[0] -= 1; st, w = _line(c, pcode, code, sn)
        if sn.get("wrong"): return "wrong", sn["wrong"]
        if "text" in sn: return "right", ""
        return ("error" if (st == "unknown" and w and str(w[0]).startswith("the read failed")) else "gone"), ""
    r1 = text(wrongc) if (wrongc and wrongc in charges) else ("gone", ""); other = ""; r2 = r1
    if r1[0] in ("error", "gone"):
        other = next((c for c in reversed(charges) if c != wrongc and c not in void), ""); r2 = text(other) if other else ("gone", "")
    if r2[0] == "wrong": return r2[1], (other or wrongc)
    if r2[0] == "right" or (r1[0] == "gone" and r2[0] == "gone"): return "", ""
    return None
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
      n620_seen    what a person wrote in that file as "seen" (40 characters; '' when the file is not there or cannot be read - never a problem file)
      problems     files that are there but cannot be read - then NO line is added in this run (a patient William took out, a hold or
                   another payer could be hidden in them)"""
    import glob as _g
    out = {"verify": {}, "checks": {}, "check_holds": {}, "held": {}, "removed": {}, "exceptions": set(), "n620": _os.path.exists(QUALITY_N620), "n620_seen": "", "problems": []}
    try:      # the report says when a person saw remark N620 (11/12/2026); the file lifts the cap by being there, whatever it holds
        if out["n620"]:
            _seen = json.load(open(QUALITY_N620)); out["n620_seen"] = re.sub(r"\s+", " ", str(_seen.get("seen") or "")).strip()[:40] if isinstance(_seen, dict) else ""
    except Exception: out["n620_seen"] = ""
    def removed(f, st, entries):      # entry by entry: an odd entry is passed over (November 12, 2026 - fix round 1, K11: an entry about a visit of a fault run is known by its visit - its line's charge number may be unknown)
        for e in (entries if isinstance(entries, list) else []):
            if isinstance(e, dict) and ((isinstance(e.get("charge"), str) and re.sub(r"\D", "", e["charge"])) or (e.get("fault") is True and re.sub(r"\D", "", str(e.get("visit") or "")))): out["removed"].setdefault(st, []).append((_os.path.basename(f), e))
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
    for every state. Nothing here can stop the import: the caller turns any error into 'no line this run'.
    11/12/2026 - THE CODE NEVER SWITCHES ITSELF OFF (the comment above): S['off'] holds William's own stop and nothing else. Where the code
    used to go off it probes (probe() below) or pauses for this run (a stuck visit, another code text); QUALITY['off'] is his stop or the
    pause sentence, QUALITY['off_until_reset'] his stop only."""
    day = day or run_day(); today = _fmt_day(day)
    q = _quality_fresh(); notes = []; files = files if isinstance(files, dict) else {}
    _d = lambda k: files.get(k) if isinstance(files.get(k), dict) else {}
    held = _d("held"); chold = _d("check_holds"); checks = _d("checks"); n620 = bool(files.get("n620")); rem = {k: list(v) for k, v in _d("removed").items() if isinstance(v, list)}
    S = {"fee": "0.00", "off": "", "proven": set(), "proof": None, "hist": None, "znb": False, "count": 0, "n": 1, "answer": None, "pwait": None, "wrong": "", "wrongc": "", "unread_prev": [],
         "probe": "", "pkind": "", "psince": "", "pwords": "", "ptries": 0, "standing": None, "own_tries": 0, "aside": None, "at": ""}      # probe ...: why the code probes (the newest cause), its kind, the register the first cause lies in, AdvancedMD's own words, how many causes; standing: an older register's own OFF; own_tries: tries this stamp's register already holds
    billed = set(); void = set(); left = set(); refused = set(); lines = []; era = [0]      # lines: every quality line of the registers, oldest first; era: where the lines entered since the last restart (or since a probe set a proof aside) begin
    took = set()      # carried by the gates: the lines a person took off their visits (that patient gets no line again that year)
    faults = []       # November 12, 2026 - fix round 1 (K11): the visits of a fault run (AdvancedMD answered a fault but kept the visit, the call that carried the line ended in an error, or the run was cut while it was out) - each is for a person AND stuck until the inspector step finds it free
    texts = set(); billed_on = {}; lseen = {}; lon = {}; late = {}; late_rows = []      # carried by the gates: code text read as 1123F, billed dates, when a visit was first seen billed, left-off dates, lines billed late
    base = lambda name: _os.path.basename(str(name)); num = lambda x: re.sub(r"\D", "", str(x or ""))
    st_of = lambda name: re.sub(r"^feed_(?:import|inspector|verify)_|\.json$", "", base(name)); short = lambda w: re.sub(r"\s+", " ", str(w or "")).strip()[:140]
    def stick(L, what, regname, why):      # the visit of line L is STUCK held with its line. Only a newer quality_removed entry ends the mark (removal below)
        L["stuck"] = {"what": what, "register": regname, "why": short(why), "since": (L.get("stuck") or {}).get("since") or regname}
    def mark_stuck():
        """A visit that carries the line, is HELD by the Claim Inspector and has no removal recorded (an older inspector copy, a step that ended in
        an error) is judged HERE, with the proof as it stands here - before proof any hold, after proof a hold whose words name the line. Called
        where the round begins anew (William's restart, a probe that sets a proof aside): neither is a word about that visit, so it stays stuck."""
        pv = S["fee"] in S["proven"]
        for L in lines[era[0]:]:
            if L.get("removed") or L.get("stuck") or not num(L["visit"]): continue
            for regname, why, marked in held.get(num(L["visit"])) or ():
                if not pv or marked or (names_lines(why, L["charge"], L["mvp"])[0] if L.get("mvp") else names_line(why, L["charge"])):
                    stick(L, "the Claim Inspector holds it and the line was not taken off", regname, why); break
    def restart():      # William's word: a new round at $0.00. What was stopped, probed, refused in a row or proven before no longer counts; a line that exists still counts once a year, and a visit that is stuck stays stuck
        mark_stuck()
        S.update(fee="0.00", off="", proof=None, hist=None, znb=False, count=0, pwait=None, wrong="", wrongc="", probe="", pkind="", psince="", pwords="", ptries=0); S["proven"] = set(); S["n"] += 1; era[0] = len(lines)
    def probe(why, name, kind, words=""):
        """A place where the code used to switch itself off: it PROBES instead - one line a run until a line of the round is billed. why = the
        sentence of this cause (the newest cause is the one the gate says), name = the register it lies in, kind = what the report advises on,
        words = AdvancedMD's own words when there are any. The same sentence twice is the same cause (the gate of the run that met it already
        says it): counted once. A proof in place is set aside: the lines entered so far can no longer be it, and the round is new from here."""
        if why == S["probe"]: return
        if not S["probe"]: S["psince"] = base(name); S["ptries"] = 0
        S.update(probe=why, pkind=kind, pwords=short(words)); S["ptries"] += 1
        if S["fee"] in S["proven"]:
            if S["at"] == base(REG): S["aside"] = dict(S["proof"], fee=S["fee"]) if isinstance(S["proof"], dict) else {"fee": S["fee"]}      # in this stamp's own register: the gate this run writes says that a proof was in place here ("proof_aside")
            mark_stuck(); S["proven"].discard(S["fee"]); S["proof"] = None; S["hist"] = None; era[0] = len(lines)
        S["count"] = 0; S["pwait"] = None
    def refusal(f, what, name, kind, words=""):      # one more refusal (or a visit stored without its line) at amount f: before proof ONE is enough, after proof TWO in a row
        if f != S["fee"] or S["off"]: return
        S["count"] += 1
        if S["count"] < (2 if S["fee"] in S["proven"] else 1): return
        if S["fee"] == "0.00":      # the move to one cent is itself a cause: the amount only moves there after something stopped a line, so at one cent the code probes from its first line (11/12/2026)
            S.update(fee="0.01", count=0); S["n"] += 1; w = "AdvancedMD %s at $0.00 (%s) - new lines carry $0.01, one line a run until one is billed" % (what, base(name)); notes.append(w); probe(w, name, kind, words)
        else: probe("AdvancedMD %s with a one-cent charge too (%s) - William looks" % (what, base(name)), name, kind, words)
    def created_row(name, r, gconf):
        qc = r.get("quality_codes") if isinstance(r.get("quality_codes"), list) else []; qid = r.get("quality_charge") if isinstance(r.get("quality_charge"), str) else ""
        pid = r.get("pid") if isinstance(r.get("pid"), str) else ""; d = str(r.get("quality_dos") or r.get("dos") or "")
        if r.get("quality_refused") or r.get("quality_not_stored"):
            f = str(r.get("quality_refused_fee") or r.get("quality_not_stored") or r.get("quality_fee") or "0.00")
            if r.get("quality_refused") and pid and len(d) >= 4: refused.add((pid, d[-4:]))      # the patient of a refused visit gets no second try that year
            if r.get("quality_refused"): refusal(f, "refused a visit that carried the code", name, "refused", r["quality_refused"] if isinstance(r["quality_refused"], str) else "")      # the words: AdvancedMD's own fault text
            else: refusal(f, "stored a visit without its quality line", name, "not_stored")
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
        anyway) = nothing counts, the place in the round is free and the patient is due again. An entry for the visit's M0004 line (code M0004)
        is the option code's own business (mvp_state); an entry whose charge the row recorded as its M0004 line is this row's 1123F line (the
        answer named no procedures, and the two were swapped).
        THE STUCK VISIT (11/12/2026): a void that failed = the visit is held WITH its line; a line that came off while the visit is still listed
        for the edit about it (the re-save after the void failed, or AdvancedMD did not inspect the visit again - confirm review NH2-2) = not the
        visit's own reason. Either way the visit is STUCK: no new line while that is so (a pause), the inspector step tries the void and the
        re-save again in every run, and the code probes afterwards. The entries are read in place, the NEWEST for a line deciding: an entry that
        says "listed": false (the step's retry found the visit no longer listed) is looked at first - it ends the mark and counts nothing more:
        no refusal, the patient is not marked, and the line is not called void by it (it is read in AdvancedMD like any other line). An entry
        that carries "retry_of" (the step tried an earlier visit again) begins a probe when none is running.
        November 12, 2026 - fix round 1: an entry with "fault": true is about a visit of a fault run (K11, fault_entry below) and is found by its visit;
        every entry that is not a "listed": false one says the routine took the line off or tried to (K10: "tried" - such a line found void while its
        visit is still there is the routine's doing, never a person's decision)."""
        if str(e.get("code") or "").strip().upper() == MVP_CODE: return
        if e.get("fault") is True:
            K = next((K for K in reversed(faults) if num(K["visit"]) == num(e.get("visit"))), None)
            if K is None: notes.append("%s names visit %s of a fault run, which no import register row carries - passed over" % (regname, e.get("visit"))); return
            fault_entry(K, regname, e); return
        L = next((L for L in reversed(lines) if num(L["charge"]) == num(e.get("charge"))), None) or next((L for L in reversed(lines) if L.get("mvp") and num(L["mvp"]) == num(e.get("charge"))), None)
        if L is None: notes.append("%s names quality charge %s, which no import register row carries - passed over" % (regname, e.get("charge"))); return
        was = bool(L.get("stuck")); L["removed"] = dict(e, register=regname); w = short(e.get("why"))
        if e.get("listed") is not False: L["tried"] = regname      # K10: the routine's own entry is on record for this line (the register that holds it)
        def freed():      # the step's retry: the visit was held with its line and is free now - from here the code probes (when no probe is running already)
            # November 12, 2026 - fix round 2 (K16): the cause this visit's own earlier entry began is not left behind once a newer entry says the visit is free -
            # the probe that ran before it stands again (or, when none ran, the code probes because the visit was held with its line)
            if S["probe"] and S["probe"] == L.get("pcause"):
                if (L.get("pprev") or {}).get("probe"): S.update(L["pprev"]); return
                S.update(probe="", pkind="", psince="", pwords="", ptries=0); probe("visit %s was held with its quality line until the routine could free it (%s: \"%s\")" % (L["visit"], regname, w), regname, "stuck", w); return
            if e.get("retry_of") and not S["probe"]: probe("visit %s was held with its quality line until the routine could free it (%s: \"%s\")" % (L["visit"], regname, w), regname, "stuck", w)
        if e.get("listed") is False: L["stuck"] = None; freed(); return
        if e.get("void_ok") is not True:
            cut_ = not str(e.get("note") or "").strip()      # K16: an entry with void_ok false and no note was written BEFORE a void that never reported back - the run was cut (K10)
            stick(L, "the routine's last try was cut off before it ended; this run's step looks again" if cut_ else "the routine could not take the line off", regname, w)
            if not was:
                prev_ = {k_: S[k_] for k_ in ("probe", "pkind", "psince", "pwords", "ptries")}
                why_ = (("the routine's last try to take the quality line off held visit %s was cut off before it ended (%s) - this run's inspector step looks again" % (L["visit"], regname)) if cut_ else
                        "the Claim Inspector holds visit %s and the routine could not take its quality line off (%s: \"%s\") - William looks" % (L["visit"], regname, w))
                probe(why_, regname, "stuck", w)
                if S["probe"] == why_: L["pcause"] = why_; L["pprev"] = prev_
            return
        void.add(L["charge"])
        if e.get("released") is not True and (e.get("still_named") is True or e.get("resave_ok") is False):
            stick(L, "the line is off, but the visit is still listed for the edit about it", regname, w)
            if not was: probe("the routine took the quality line off held visit %s, but the visit is still listed for the edit about the line (%s: \"%s\") - William looks; one re-save of the visit should release it" % (L["visit"], regname, w), regname, "stuck", w)
            return
        L["stuck"] = None; freed()
        if e.get("released") is True:
            if len(L["dos"]) >= 4: refused.add((L["chart"], L["dos"][-4:]))
            refusal(L["fee"], "held visit %s because of its quality line (the routine took the line off and the visit went through)" % L["visit"], regname, "claim_check", w)
    def fault_entry(K, regname, e):
        """November 12, 2026 - fix round 1 (K11): what the inspector step's retry pass found about a visit of a fault run - the newest entry decides, as for
        every stuck visit. Not listed = free (the probe goes on). The line came off and the visit went through = free, and ONE refusal at its amount (its
        patient is marked already). The line came off and the visit is held for its own reason = free. Still listed for the edit about the line, or the
        line did not come off (the void failed, or no live 1123F line of that visit was found) = it stays stuck - for a person - and no new line meanwhile."""
        w = short(e.get("why")); nt = short(e.get("note")); since = (K.get("stuck") or {}).get("since") or K["reg"]
        if num(e.get("charge")): K["charge"] = str(e["charge"])      # the line's charge number, found by the step: the next look starts from it
        if e.get("listed") is False: K["stuck"] = None; return
        if e.get("own_reason") is True:      # November 12, 2026 - fix round 2 (K15): held for its own reason - no 1123F line on it, or after the proof words that name no line. It stays on the report for a person until it is free; NOT a pause
            K["stuck"] = {"what": nt or "held for its own reason - a person fixes the visit", "register": regname, "why": w, "since": since, "own": True}; return
        if e.get("void_ok") is not True:      # K16: the words say what is known - the line could not be looked for / it did not come off / the last try was cut off (no note: written before a void that never reported back)
            K["stuck"] = {"what": ("the Claim Inspector holds it and %s" % nt) if (e.get("looked") is False and nt) else ("the Claim Inspector holds it and its line did not come off (%s)" % nt) if nt else
                          "the routine's last try was cut off before it ended; this run's step looks again", "register": regname, "why": w, "since": since}; return
        if e.get("released") is not True and (e.get("still_named") is True or e.get("resave_ok") is False):
            K["stuck"] = {"what": "the line is off, but the visit is still listed for the edit about it", "register": regname, "why": w, "since": since}; return
        K["stuck"] = None
        if e.get("released") is True: refusal(K["fee"], "held visit %s because of its quality line (the routine took the line off and the visit went through)" % K["visit"], regname, "claim_check", w)
    def failed_row(name, r, _gconf):
        info = r.get("info") if isinstance(r.get("info"), dict) else {}; pid = r.get("pid") if isinstance(r.get("pid"), str) else ""
        d = str(info.get("quality_dos") or info.get("dos") or ""); who = "chart %s, visit %s, %s" % (pid or "?", r.get("empty_visit") or "?", base(name))
        if not (r.get("quality_sent") or r.get("quality_unknown") or (r.get("stored") and "quality_tried" in info)): return
        if pid and len(d) >= 4: refused.add((pid, d[-4:]))
        if not r.get("quality_sent") and num(r.get("empty_visit")):      # K11 (November 12, 2026 - fix round 1): that visit may carry the line - it is for a person AND stuck until the inspector step finds it free
            st_ = r.get("stored") if isinstance(r.get("stored"), list) else [r.get("stored")]
            kind_ = "cut" if r.get("provisional") else "error" if r.get("quality_unknown") else "unread" if any(isinstance(x, str) and x.startswith("chart not read") for x in st_) else "kept"
            faults.append({"chart": pid, "visit": str(r["empty_visit"]), "charge": "", "fee": str(r.get("quality_unknown") or info.get("quality_tried") or info.get("quality_fee") or ""), "dos": d, "reg": base(name),
                           "stuck": {"what": QUALITY_FAULT_WHAT[kind_] + " - nobody has seen yet whether the Claim Inspector holds it", "register": base(name), "why": short(r.get("err")), "since": base(name)}})
        if r.get("quality_sent"): refusal(str(r.get("quality_sent")), "refused a visit that carried the code", name, "refused")      # refused with the line, and the send without it failed: counted like a refusal
        elif r.get("quality_unknown"):      # the call that carried the line ended in an error - or the run was cut while it was out (the provisional row main() writes before that call): that visit is for a person; the code probes
            probe(("the run was cut while a call that carried the quality line was out; nobody knows whether AdvancedMD kept that visit and its line - William looks (%s)" if r.get("provisional")
                   else "a call that carried the quality line ended in an error; nobody knows whether AdvancedMD kept that visit - William looks (%s)") % who, name, "fault")
        else:                               # a fault, and the chart shows the visit or could not be read: the visit was not sent again - it is for a person; the code probes
            st = r.get("stored") if isinstance(r.get("stored"), list) else [r.get("stored")]
            probe(("AdvancedMD answered a fault to a visit that carried the quality line and the chart could not be read afterwards - William looks (%s)"
                   if any(isinstance(x, str) and x.startswith("chart not read") for x in st) else "AdvancedMD answered a fault but kept the visit - William looks (%s)") % who, name, "fault")
    def rows(fn, name, rs, gconf):          # row by row: an odd row is passed over, the rows after it are still read
        for r in rs:
            try:
                if isinstance(r, dict): fn(name, r, gconf)
            except Exception: continue
    holds = {}      # batch stamp -> [(visit number, register, the hold's words)]: the visits the insurance check put on HOLD, taken batch by batch as the registers are read (11/12/2026)
    for v_, rows_ in chold.items():
        for regname, words in rows_: holds.setdefault(st_of(regname), []).append((v_, regname, words))
    def hold(v_, regname, words):
        """The insurance check could not set the order of a visit that carries the line (its words: insorder not applied, resave FAULT, detail read
        mismatch): that visit is for a person, and the code probes - taken once, in its place. Only a visit entered since the round last began
        anew is looked at (William's restart, or a probe that set a proof aside, came after the others)."""
        L = next((L for L in reversed(lines[era[0]:]) if num(L["visit"]) == v_), None) if v_ else None
        if L is None: return
        for why in words:
            named = set(re.findall(r"vst\d+", why))
            if re.search(r"insorder not applied|resave FAULT|detail read mismatch", why) and (not named or L["visit"] in named):
                probe("the insurance check could not set the order of visit %s, which carries the quality line (%s: \"%s\") - William looks" % (L["visit"], regname, why[:140]), regname, "order"); return
    for name, reg in sorted(regs, key=lambda x: str(x[0])):
        try:
            if not isinstance(reg, dict): continue
            g = reg.get("quality_gate") if isinstance(reg.get("quality_gate"), dict) else {}
            cr = reg.get("created") if isinstance(reg.get("created"), list) else []; fl = reg.get("failed") if isinstance(reg.get("failed"), list) else []
            gconf = g.get("fee") if (g.get("confirmed") is True and g.get("fee") in ("0.00", "0.01")) else None
            cut = [0, 0]; S["at"] = base(name)
            if g.get("reset") is True:      # the pilot was started again in that run. Rows an earlier start under the same stamp had already written stay in the old round
                ra = g.get("reset_after")
                if isinstance(ra, list) and len(ra) == 2 and all(isinstance(x, int) and not isinstance(x, bool) and x >= 0 for x in ra): cut = ra
                rows(created_row, name, cr[:cut[0]], None); rows(failed_row, name, fl[:cut[1]], None); restart()
            if g.get("fee") == "0.01" and S["fee"] == "0.00": S.update(fee="0.01", count=0); S["n"] += 1      # once at one cent, it stays there until a restart
            if g.get("zero_not_billed") is True and S["fee"] == "0.01": S["znb"] = True
            if isinstance(g.get("round"), dict) and isinstance(g["round"].get("n"), int) and not isinstance(g["round"].get("n"), bool): S["n"] = max(S["n"], g["round"]["n"])
            if gconf is not None and gconf == S["fee"]:
                S["proven"].add(gconf); S["proof"] = g.get("proof") if isinstance(g.get("proof"), dict) else S["proof"]
                if isinstance(g.get("history_shows_line"), bool): S["hist"] = g["history_shows_line"]
                S.update(probe="", pkind="", psince="", pwords="", ptries=0)      # that run had its proof: a probe that began before it has ended
            # "proof_aside": that run HAD a proof in place until a cause in its own place set it aside (a fault while it entered visits - its gate then says "not
            # proven" - or a second start under its stamp that read such a cause). The cause is met again below, with the proof as it stood: the lines entered up
            # to it can no longer be the proof. Without this the old line would prove the code again in the next run, and the cause would be forgotten.
            aside = gconf is None and isinstance(g.get("proof_aside"), dict) and g.get("fee") == S["fee"] and S["fee"] not in S["proven"]
            if aside: S["proven"].add(S["fee"]); S["proof"] = dict(g["proof_aside"]); S.update(probe="", pkind="", psince="", pwords="", ptries=0)
            ou = g["off_until_reset"].strip() if isinstance(g.get("off_until_reset"), str) else ""
            if ou.startswith(QUALITY_STOP_WORDS): S["off"] = ou      # William's own stop: kept and carried, ended only by his reset
            elif ou and not S["probe"]:      # an OLDER register (written before 11/12/2026) whose "off until reset" was the code's own doing: a pause that has ended. Nothing is carried as off; in this place the code probes (William's standing word)
                probe("the code had switched itself off (%s) - William's standing word of November 11, 2026 restarts it" % ou[:200], name, "standing")
            gp = g["probe"].strip() if isinstance(g.get("probe"), str) else ""
            if gp and S["fee"] not in S["proven"]:      # the probe is carried by the gates like every other state, also when what caused it can no longer be read: the gate of that run is the newest word on why (its own rows, removals and holds follow below)
                _n = g.get("probe_tries") if isinstance(g.get("probe_tries"), int) and not isinstance(g.get("probe_tries"), bool) else 0
                S.update(psince=S["psince"] if S["probe"] else (g["probe_since"] if isinstance(g.get("probe_since"), str) and g["probe_since"] else base(name)), ptries=max(S["ptries"] if S["probe"] else 0, _n, 1),
                         probe=gp, pkind=g["probe_kind"] if isinstance(g.get("probe_kind"), str) else "", pwords=short(g["probe_words"]) if isinstance(g.get("probe_words"), str) else "")
            if base(name) != base(REG): S["standing"] = {"was": ou[:300], "register": base(name)} if (ou and not ou.startswith(QUALITY_STOP_WORDS)) else None      # said ONCE, by the run whose newest EARLIER register carries such a sentence
            else:      # this stamp's own register (a second start, --limit, --one): a try it already holds is this run's one probe line
                S["own_tries"] = (sum(1 for r in cr if isinstance(r, dict) and ((r.get("quality_codes") and r.get("quality_charge")) or r.get("quality_refused") or r.get("quality_not_stored")))
                                  + sum(1 for r in fl if isinstance(r, dict) and (r.get("quality_sent") or r.get("quality_unknown") or (r.get("stored") and isinstance(r.get("info"), dict) and "quality_tried" in r["info"]))))
            for k, s in (("billed_lines", billed), ("void_lines", void), ("left_off_lines", left), ("taken_lines", took)):      # what earlier runs read as final is never read again
                s.update(x for x in (g.get(k) if isinstance(g.get(k), list) else []) if isinstance(x, str))
            for x in (g.get("refused_charts") if isinstance(g.get("refused_charts"), list) else []):
                if isinstance(x, list) and len(x) >= 2 and isinstance(x[0], str) and isinstance(x[1], str): refused.add((x[0], x[1]))
            for k, d_ in (("billed_on", billed_on), ("left_off_seen", lseen), ("left_off_on", lon), ("late_billed", late)):
                if isinstance(g.get(k), dict): d_.update((a, b) for a, b in g[k].items() if isinstance(a, str) and isinstance(b, (str, dict)))
            texts.update(x for x in (g.get("code_text_lines") if isinstance(g.get("code_text_lines"), list) else []) if isinstance(x, str))
            if S["answer"] is None and isinstance(g.get("medicare_answer"), dict) and g["medicare_answer"].get("charge"): S["answer"] = dict(g["medicare_answer"])      # the first answer found stays
            if "proof_wait" in g: S["pwait"] = dict(g["proof_wait"]) if isinstance(g.get("proof_wait"), dict) else None
            if "wrong_code_charge" in g:      # a gate of this version says what ITS run read (another code text is a pause that every run reads again); an older gate's text is not carried - the line that showed it is read again in the normal course
                S["wrong"] = g["wrong_code_text"] if isinstance(g.get("wrong_code_text"), str) else ""; S["wrongc"] = g["wrong_code_charge"] if isinstance(g.get("wrong_code_charge"), str) else ""
            if g: S["unread_prev"] = [x for x in (g.get("unread") if isinstance(g.get("unread"), list) else []) if isinstance(x, str)]      # what the run before this one could not read
            rows(created_row, name, cr[cut[0]:], gconf); rows(failed_row, name, fl[cut[1]:], gconf)
            for regname, e in rem.pop(st_of(name), []):      # the lines that batch's inspector step / insurance check took off - after its own rows, in time order
                try: removal(regname, e)
                except Exception: continue
            for h_ in holds.pop(st_of(name), []):      # then that batch's insurance-check HOLDs
                try: hold(*h_)
                except Exception: continue
            if aside and S["fee"] in S["proven"]: probe(gp or "a cause that the registers no longer show set the proof aside (%s)" % base(name), name, g["probe_kind"] if isinstance(g.get("probe_kind"), str) and g["probe_kind"] else "fault")      # nothing in the registers repeated the cause: that run's own word stands
        except Exception: continue
    S["at"] = ""
    for st in sorted(rem):      # removals of a batch whose import register is not here: still void, after everything else
        for regname, e in rem[st]:
            try: removal(regname, e)
            except Exception: continue
    for st in sorted(holds):      # ... and the HOLDs of such a batch
        for h_ in holds[st]:
            try: hold(*h_)
            except Exception: continue
    if stop:
        if S["off"]: notes.append("QUALITY_CODE=stop was given; the code was already off")
        else: S["off"] = "stopped on William's word (QUALITY_CODE=stop) - off until he says to start again"
    if reset:      # honoured only after William's own stop: nothing else is off any more (11/12/2026)
        if S["off"]: restart(); q["reset"] = True; notes.append("the pilot was started again in this run (QUALITY_CODE=reset)")
        else: q["loud"] = "NOTHING TO RESTART - QUALITY_CODE=reset was ignored (the code is not switched off; take the switch out of the routine)"; notes.append(q["loud"])
    # HELD VISITS: a visit that carries the line and was entered since the round last began anew. Since 11/10/2026 the inspector step takes
    # the line off a held visit by itself (removal above): such a hold is the visit's own business, and the rule below is left for a line that
    # could NOT be taken off (no removal recorded - an older inspector copy, a step that ended in an error, or a row without its quality
    # charge). Such a visit is STUCK held with its line (11/12/2026): no new line in this run - a pause - and the inspector step tries it again;
    # no probe starts from the held row itself (it starts when the step's retry records what it did). Judged here with the proof as it stands
    # now, exactly as before: a held row whose words do not name the line stops counting once the code is proven.
    eraL = lines[era[0]:]; proven = S["fee"] in S["proven"]
    for L in eraL:
        L["held"] = False
        for regname, why, marked in (held.get(num(L["visit"])) or ()) if num(L["visit"]) else ():
            L["held"] = True
            if L.get("removed") or L.get("stuck"): continue
            if not proven or marked or (names_lines(why, L["charge"], L["mvp"])[0] if L.get("mvp") else names_line(why, L["charge"])):      # before proof ANY hold; after proof only a hold whose words name the line (beside an M0004 line: words that name only M0004 are M0004's business)
                stick(L, "the Claim Inspector holds it and the line was not taken off", regname, why)
        for regname, words in (chold.get(num(L["visit"])) or ()) if num(L["visit"]) else ():
            L["held"] = True                # any insurance-check HOLD: this visit can never be the proof (an order that could not be set made the code probe in its place - hold() above)
    # a line has ONE state, its newest reading: an older gate still lists a line as left off that a later run read billed (13.1b) or void - billed and void win
    left -= billed; left -= void
    final = lambda L: "billed" if L["charge"] in billed else "void" if L["charge"] in void else "left" if L["charge"] in left else ""
    looks = [QUALITY_LOOKS]
    def read(L):
        """One read of a line and, where the outcome needs it, of its visit's own first charge. A final outcome goes into billed / left / void."""
        looks[0] -= 1; L["seen"] = True; sn = {}
        st, what = _line(L["charge"], QUALITY_PCODE, QUALITY_CODE, sn)
        if sn.get("text", "").upper() == QUALITY_CODE.upper(): texts.add(L["charge"])
        if sn.get("wrong"):      # AdvancedMD shows another code text than 1123F for the line's id: nothing is built on it - a pause while that is so, and every run reads it again (11/12/2026)
            S["wrong"] = sn["wrong"]; S["wrongc"] = L["charge"]; return
        if st == "billed": billed.add(L["charge"]); billed_on[L["charge"]] = what[0]; return
        if st == "unknown": notes.append("the quality line of visit %s (%s) is not decided: %s - the pilot waits; William looks if this stays" % (L["visit"], L["charge"], what[0])); return
        own, owhat = _line(L["own"]) if L["own"] else ("none", [])
        if st == "open":
            if own == "billed":      # LEFT OFF needs time: a line can be billed a day after its visit (second state-machine review). The newest billed date of the visit's own charge counts; when it cannot be read, the day this import first saw the charge billed
                bday = max([d_ for d_ in map(_any_day, owhat) if d_] or [None])
                if bday is None: lseen.setdefault(L["charge"], today); bday = _mdy_day(lseen[L["charge"]]) or day
                if (day - bday).days >= QUALITY_LEFT_OFF_DAYS:
                    left.add(L["charge"]); lon[L["charge"]] = {"on": today, "billed": _fmt_day(bday)}; L["fresh"] = True      # fresh: called left off in THIS run (one more cause while the code probes)
                    notes.append("visit %s was billed %s without its $%s quality line, and the line is still not billed %d days later - left off the claim" % (L["visit"], _fmt_day(bday), L["fee"], (day - bday).days))
                else: notes.append("visit %s was billed %s; its $%s quality line is not billed yet - not decided before %s (a line can be billed a day after its visit)" % (L["visit"], _fmt_day(bday), L["fee"], _fmt_day(bday + datetime.timedelta(days=QUALITY_LEFT_OFF_DAYS))))
            elif own == "void": notes.append("the own charge of visit %s is void while its quality line is still live - not decided; William looks" % L["visit"])
        elif own in ("billed", "open") and L.get("tried"):      # K10 (November 12, 2026 - fix round 1): the routine's own entry for this line is on record - its void, not a person's (a cut right after the void leaves that entry saying void_ok false: the visit stays stuck and the inspector step re-saves it)
            void.add(L["charge"]); notes.append("the quality line of visit %s reads void and the routine's own entry for it is on record (%s) - the routine took it off, not a person" % (L["visit"], L["tried"]))
        elif own in ("billed", "open"):      # a person took the line off: that patient gets no line again this year (a person decided), and the code stays on (11/12/2026) - only when no entry of the routine's is on record for it (K10)
            void.add(L["charge"]); L["taken"] = True; took.add(L["charge"])
            if L["chart"] and len(L["dos"]) >= 4: refused.add((L["chart"], L["dos"][-4:]))
            notes.append("the quality line of visit %s was taken off the visit (void) while the visit itself is still there - a person decided: %s gets no line again this year; the code stays on" % (L["visit"], L["chart"] or "that patient"))
        elif own in ("void", "none"): void.add(L["charge"]); notes.append("visit %s is no longer on the chart (void), its quality line with it" % L["visit"])
        else: notes.append("the quality line of visit %s is void, but the visit's own charge is not decided: %s" % (L["visit"], owhat[0]))
    def proof_ok(L):      # never held, and the insurance check of the line's own batch did not hold the chart or name another payer (no check of that batch is accepted)
        c = (checks.get(re.sub(r"^feed_import_|\.json$", "", L["reg"])) or {}).get(L["chart"])
        return not L.get("held") and (c is None or (c[0] == "RELEASE" and c[1] == MEDICARE_LEAD))
    wait = False; pending = []
    if S["wrong"] and look and not S["off"]:      # another code text was on record (the gate before this run): the pause is what THIS run reads
        _now = _text_pause([L["charge"] for L in lines], void, S["wrongc"], QUALITY_PCODE, QUALITY_CODE, looks)
        if _now is not None: S["wrong"], S["wrongc"] = _now
    for _pass in (0, 1):      # a second pass only when the amount moved to one cent in this run
        fee = S["fee"]; rnd = [L for L in eraL if L["fee"] == fee]
        if S["off"] or fee in S["proven"]: break
        for L in rnd:         # the lines of the round that are not decided, oldest first
            if not final(L) and look and looks[0] > 0: read(L)
        if S["wrong"]: break    # a read of this run shows another code text for the line's id: nothing is judged in this run (a pause)
        taken = [L for L in rnd if L.get("taken")]; good = [L for L in rnd if final(L) == "billed" and proof_ok(L)]
        lo = [L for L in rnd if final(L) == "left"]; undecided = [L for L in rnd if not final(L)]; nonvoid = [L for L in rnd if final(L) != "void"]
        for L in rnd:
            if final(L) == "billed" and not proof_ok(L): notes.append("the quality line of visit %s is billed but cannot be the proof: the visit was held, or the insurance check of its batch did not show Medicare first" % L["visit"])
        if good:      # THE CODE TEXT: a billed line proves the code only when AdvancedMD shows it stored 1123F - its charge detail named the code text, or the chart's history shows a live 1123F on that date
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
                S["proven"].add(fee); S["hist"] = True if by_history else None; S["pwait"] = None; S.update(probe="", pkind="", psince="", pwords="", ptries=0)      # the proof: a probe ends here, and the flow is the normal one again
                S["proof"] = {"register": L["reg"], "chart": L["chart"], "visit": L["visit"], "charge": L["charge"], "billed": billed_on.get(L["charge"]) or "read in an earlier run", "fee": fee}
                if look and not by_history:      # ONE read of that chart's history: does it list a no-charge line at all? If not, a 1123F / 1124F entered by hand is invisible to the import
                    try: S["hist"] = (QUALITY_CODE, L["dos"]) in chart_lines_now(L["chart"])
                    except Exception as e: notes.append("the history of chart %s could not be read after the proof (%s): whether it lists a no-charge line is not known" % (L["chart"], type(e).__name__))
                    if S["hist"] is False: notes.append("the history of chart %s does NOT list the proven quality line: a 1123F or 1124F entered by hand is invisible to the import - William names such patients in %s" % (L["chart"], QUALITY_EXCEPTIONS))
        else:
            # WHAT ADVANCEDMD SHOWS ABOUT THE ROUND, and nothing is proven (11/12/2026: each of these used to switch the code off; now the code probes). Such a
            # cause is met once - in the run that reads it - and the gates carry the probe from then on, also when the line that showed it is void later.
            tk = [L for L in rnd if L["charge"] in took]
            if lo and not any(final(L) == "billed" for L in rnd):
                if fee == "0.00":      # the move to one cent is itself a cause: at one cent the code probes from its first line
                    S.update(fee="0.01", znb=True, count=0); S["n"] += 1
                    w = "new lines carry $0.01: AdvancedMD left the $0.00 line of visit %s off its claim and no $0.00 line of the round is billed" % lo[0]["visit"]; notes.append(w)
                    probe(w + " - one line a run until one is billed", lo[0]["reg"], "left_off"); continue
                if not S["probe"] or any(L.get("fresh") for L in lo):      # a one-cent line left off its claim: AdvancedMD leaves the reporting line off (this needs a setting in AdvancedMD)
                    nl = next((L for L in reversed(lo) if L.get("fresh")), lo[0])
                    probe("AdvancedMD billed visit %s (%s) without its one-cent quality line too - William looks" % (nl["visit"], (lon.get(nl["charge"]) or {}).get("billed") or "read in an earlier run"), nl["reg"], "left_off")
            elif tk and (not S["probe"] or taken):      # a person took a line of the round off before anything was proven: those patients get no line again this year, and the code stays on - one line a run instead of refilling the round
                probe("%d earlier quality line(s) were taken off their visits (void) while the visits are still there (%s) - William looks" % (len(tk), ", ".join(L["visit"] for L in tk[:6])), tk[-1]["reg"], "voided")
            elif not undecided and not S["probe"] and min(QUALITY_PILOT - len(nonvoid), 2 * QUALITY_PILOT - len(rnd)) <= 0:      # the round is full, every line is decided, nothing is proven
                probe(("the pilot's lines keep being voided (%d lines in this round, none billed) - William looks" % len(rnd)) if not nonvoid else (
                       "the pilot round is full (%d lines) and none of them can be the proof - William looks" % len(rnd)), rnd[-1]["reg"], "voided")
            if undecided:      # a line of the round is not decided: no new line in this run - for the pilot and for a probe alike
                wait = True; pending = undecided
                if not look: notes.append("dry run: %d earlier quality line(s) were not looked up - a live run reads them" % len(undecided))
        break
    cur = set(id(L) for L in eraL if L["fee"] == S["fee"])
    for i, L in enumerate(lines):      # then the other lines that were entered before proof and are not decided yet, oldest first (so every $0.00 line is read in the end) - the
        # proven round's own undecided lines too: since a line is called LEFT OFF only three days after its visit was billed, a round can be proven while one of its lines waits.
        # An older line found taken off by a person changes nothing but that patient (read() marks it): the code goes on as it stood (11/12/2026)
        if S["off"] or S["wrong"] or not look or looks[0] <= 0: break
        if (id(L) in cur and S["fee"] not in S["proven"]) or final(L) or not L["pilot"] or L.get("seen"): continue
        read(L)
    for L in lines:      # a line called LEFT OFF is read again, after everything above, until QUALITY_LEFT_OFF_REREAD days after it was CALLED left off: billed after all = it counts as billed
        # November 12, 2026 - fix round 2 (K13): the re-read runs on the K12 block's own clock (the day it was called left off, else its visit's billed date), so a first line billed while its patient is blocked is seen
        if not look or looks[0] <= 0: break
        w = lon.get(L["charge"]) if isinstance(lon.get(L["charge"]), dict) else {}; b = _mdy_day(str(w.get("on") or "")) or _mdy_day(str(w.get("billed") or ""))
        if final(L) != "left" or L.get("seen") or b is None or (day - b).days > QUALITY_LEFT_OFF_REREAD: continue
        looks[0] -= 1; L["seen"] = True; sn = {}
        st, what = _line(L["charge"], QUALITY_PCODE, QUALITY_CODE, sn)
        if sn.get("text", "").upper() == QUALITY_CODE.upper(): texts.add(L["charge"])
        if sn.get("wrong"): S["wrong"] = sn["wrong"]; S["wrongc"] = L["charge"]; continue      # another code text: a pause (see read())
        if st == "billed":      # it went out after all: its patient counts as coded; nothing else changes (the amount stays where it is)
            left.discard(L["charge"]); billed.add(L["charge"]); billed_on[L["charge"]] = what[0]; late[L["charge"]] = today
            again = [M["visit"] for M in lines if M is not L and M["chart"] == L["chart"] and M["dos"][-4:] == L["dos"][-4:] and final(M) == "billed"]      # "two billed lines" only when the later one IS billed
            late_rows.append([L["chart"], L["visit"], L["charge"], str(w.get("on") or ""), again[0] if again else "", L["dos"][-4:]])
            notes.append("the quality line of visit %s, read as left off its claim on %s, was billed later (%s): %s counts as coded" % (L["visit"], w.get("on") or "?", what[0], L["chart"]))
        elif st == "void": left.discard(L["charge"]); void.add(L["charge"]); notes.append("the quality line of visit %s, read as left off its claim, is void now" % L["visit"])
    fee = S["fee"]; proven = fee in S["proven"]; rnd = [L for L in eraL if L["fee"] == fee]; nonvoid = [L for L in rnd if final(L) != "void"]
    if fee == "0.01" and not proven and not S["probe"]:      # at one cent with nothing proven the code always probes (11/12/2026). Here only when no register shows what moved the amount - a gate written before that day, or a register that never arrived
        S.update(probe="new lines carry $0.01 and no one-cent line is seen billed yet - one line a run until one is billed", pkind="left_off" if S["znb"] else "refused", psince=rnd[0]["reg"] if rnd else base(REG), pwords="", ptries=1)
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
    # A PAUSE is THIS run's (11/12/2026): a visit stuck held with its line - a real claim never waits because of this code, so no new line while that is
    # so, and the inspector step of every run tries the void and the re-save again - or another code text for the line's id. Every run looks again.
    stuck = [L for L in lines if L.get("stuck")]; pause = ""; probing = bool(S["probe"]) and not proven
    fstuck = [K for K in faults if K.get("stuck")]      # K11 (November 12, 2026 - fix round 1): a visit of a fault run is stuck too until the inspector step finds it free
    fpause = [K for K in fstuck if not K["stuck"].get("own")]      # K15 (fix round 2): ... and pauses the code only while it is held WITH its line; one held for its own reason stays listed (the step looks again) but pauses nothing
    def item(L, **more): return dict({"chart": L["chart"], "visit": L["visit"], "charge": L["charge"], "own": L["own"], "code": QUALITY_CODE, "fee": L["fee"], "with": L.get("mvp") or ""}, **more)      # what the inspector step needs to find the visit and its line again ("with" = the same visit's M0004 line as the row recorded it)
    def fitem(K): return {"chart": K["chart"], "visit": K["visit"], "charge": K["charge"], "own": "", "code": QUALITY_CODE, "fee": K["fee"], "with": "", "dos": K["dos"], "fault": True,      # what the step knows of a visit of a fault run (K11)
                          "why": K["stuck"]["why"], "register": K["stuck"]["register"], "what": K["stuck"]["what"], "since": K["stuck"]["since"], "own": bool(K["stuck"].get("own"))}
    if stuck or fpause:
        X, isf = (stuck[0], False) if stuck else (fpause[0], True); s0 = X["stuck"]
        pause = "paused this run: visit %s (chart %s) %s - %s (%s: \"%s\")%s; no new line while that is so - every run's inspector step %s" % (      # K16: a fault visit's opening says no more than QUALITY_FAULT_WHAT
            X["visit"], X["chart"], "came from a fault run" if isf else "may still be held with its quality line" if s0["what"].startswith("the routine's last try was cut off") else "is held with its quality line", s0["what"], s0["register"], s0["why"],
            ("; and %d more visit(s)" % (len(stuck) + len(fpause) - 1)) if len(stuck) + len(fpause) > 1 else "", "looks at it again" if isf else "tries the void and the re-save again")
    elif S["wrong"]: pause = "paused this run: AdvancedMD shows procedure id %s as %s, not %s - no line while that is so; every run reads it again" % (QUALITY_PCODE, S["wrong"], QUALITY_CODE)
    for L in lines:      # once per patient per year - from the registers, whatever the chart history shows; by the chart and by the feed's own patient id
        if not L["chart"] or len(L["dos"]) < 4 or final(L) == "void": continue      # a void line was never reported: its patient is due again
        if final(L) == "left":      # left off the claim: dead, its patient is due again - K12 (November 12, 2026 - fix round 1): only once the line was called left off QUALITY_LEFT_OFF_REREAD days ago or more
            q["dead"].add((L["chart"], QUALITY_CODE, L["dos"])); q["dead_rows"].append([L["chart"], L["visit"], L["charge"]])
            w_ = lon.get(L["charge"]) if isinstance(lon.get(L["charge"]), dict) else {}; d_ = _mdy_day(str(w_.get("on") or "")) or _mdy_day(str(w_.get("billed") or ""))
            if d_ is None or (day - d_).days < QUALITY_LEFT_OFF_REREAD:      # AdvancedMD may still bill the first line (it is read again for 30 days): once per patient and year also across a left-off line, probing or going; a date that cannot be read = not shown = no line
                q["done"].add((L["chart"], L["dos"][-4:]))
                if _feed_mark(L.get("feed")): q["done"].add((_feed_mark(L["feed"]), L["dos"][-4:]))
        else:
            q["done"].add((L["chart"], L["dos"][-4:]))
            if _feed_mark(L.get("feed")): q["done"].add((_feed_mark(L["feed"]), L["dos"][-4:]))
    q["done"] |= refused
    pw = dict(S["pwait"], days=(day - (_mdy_day(S["pwait"].get("since")) or day)).days) if (wait and not proven and isinstance(S["pwait"], dict)) else None
    q.update(billed_on={k: v for k, v in billed_on.items() if k in billed}, code_text_lines=sorted(texts), left_off_seen={k: v for k, v in lseen.items() if k not in billed and k not in void and k not in left},
             left_off_on={k: v for k, v in lon.items() if k in left}, late_billed=dict(late), late_rows=late_rows, wrong_code_text=S["wrong"], wrong_code_charge=S["wrongc"] if S["wrong"] else "", proof_wait=pw,
             medicare_answer=S["answer"] if proven else None, medicare_wait=mwait, unread_prev=list(S["unread_prev"]))
    q.update(probe=S["probe"] if probing else "", probe_kind=S["pkind"] if probing else "", probe_since=S["psince"] if probing else "", probe_words=S["pwords"] if probing else "", probe_tries=S["ptries"] if probing else 0,
             paused=pause, stuck=[item(L, why=L["stuck"]["why"], register=L["stuck"]["register"], what=L["stuck"]["what"], since=L["stuck"]["since"]) for L in stuck] + [fitem(K) for K in fstuck],
             open_lines=[item(L, why="", register=L["reg"]) for L in lines if L["pilot"] and not final(L) and not L.get("stuck")],      # entered before proof and not decided: the inspector step looks whether the claim check holds such a visit of an earlier batch
             standing_restart=S["standing"], taken_lines=sorted(took), n620_seen=str(files.get("n620_seen") or "")[:40] if n620 else "", proof_aside=S["aside"] if not proven else None,
             left_off_cent=[L["visit"] for L in lines if final(L) == "left" and L["fee"] == "0.01"])      # the visits whose ONE-CENT line AdvancedMD left off its claim: the report names how many sit unbilled
    # THE BUDGET. William's stop, a pause, a line of the round that is not decided: nothing. Proven: at most ten a run until Medicare's answer is on file. PROBING:
    # ONE line a RUN across its registers - none in a retry register (the run's one line belongs to the ingest), none when this stamp's own register already
    # holds a try. Otherwise the pilot's round of three (a fresh round at $0.00 in which nothing went wrong).
    q.update(fee=fee, confirmed=proven, off=S["off"] or pause, off_until_reset=S["off"], wait=wait, proof=S["proof"] if proven else None, notes=notes[:20], zero_not_billed=bool(S["znb"] and fee == "0.01"),
             budget=0 if (S["off"] or pause or wait) else (None if (n620 or S["answer"]) else QUALITY_DAILY) if proven else (0 if (str(STAMP).endswith("R") or S["own_tries"]) else QUALITY_PROBE) if probing
                    else max(0, min(QUALITY_PILOT - len(nonvoid), 2 * QUALITY_PILOT - len(rnd))),
             billed_lines=sorted(billed), void_lines=sorted(void), left_off_lines=sorted(left - billed - void), refused=refused, n620=n620, history_shows_line=S["hist"] if proven else None,
             pending=[L["visit"] for L in pending], pending_since=pending[0]["reg"] if pending else "",
             round={"n": S["n"], "fee": fee, "since": rnd[0]["reg"] if rnd else "", "lines": len(rnd), "void": len(rnd) - len(nonvoid), "open": len([L for L in rnd if not final(L)])})
    QUALITY.clear(); QUALITY.update(q)
def quality_gate(reg_name="", added=0):
    """What a run writes into its register as "quality_gate": where the code stands, for the next run and for the digest. off = why no line
    is added in THIS run (William's stop, a pause, or a "this run: ..." sentence); off_until_reset = William's own stop and nothing else
    (11/12/2026: the code never switches itself off); round = the round (n, amount, the register it began in, its lines, how many of them
    are void / not decided); budget = what this run was allowed to add (null = no cap). probe = why the code probes (one line a run), the
    newest cause; probe_kind / probe_since / probe_words / probe_tries = what kind of cause, the register the first cause lies in,
    AdvancedMD's own words, how many causes; paused = the pause sentence (also in off); stuck = the visits held with their line, for the
    inspector step's retry; open_lines = the lines not decided yet, for the same step; standing_restart = an older register's own OFF,
    said once; taken_lines = lines a person took off; wrong_code_charge = the charge that showed another code text in this run; proof_aside = the
    proof that was in place in this register when a cause set it aside; left_off_cent = the visits whose one-cent line was left off its claim."""
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
            # 11/12/2026, the code never switches itself off: why it probes, why this run is paused, the visits stuck with their line, the lines not decided yet
            "probe": Q.get("probe") or "", "probe_kind": Q.get("probe_kind") or "", "probe_since": Q.get("probe_since") or "", "probe_words": Q.get("probe_words") or "", "probe_tries": int(Q.get("probe_tries") or 0),
            "paused": Q.get("paused") or "", "stuck": list(Q.get("stuck") or []), "open_lines": list(Q.get("open_lines") or []), "standing_restart": Q.get("standing_restart"), "taken_lines": list(Q.get("taken_lines") or []),
            "wrong_code_charge": Q.get("wrong_code_charge") or "", "n620_seen": Q.get("n620_seen") or "", "left_off_cent": list(Q.get("left_off_cent") or []),
            "proof_aside": Q.get("proof_aside") if isinstance(Q.get("proof_aside"), dict) else None,      # the proof that was in place in THIS register when a cause set it aside (the next run meets that cause with the proof as it stood)
            "notes": list(Q.get("notes") or [])}
def quality_probe_now(why, kind="fault"):
    """What a run finds out WHILE it enters visits (a call that carried the line ended in an error; a fault although the chart shows the visit or it
    cannot be read): that visit is for a person, and the code probes from the next run - nothing is switched off (11/12/2026). The gate this run
    writes already says what the next run reads from the failed row; this run adds no further line (QUALITY['off'] says why)."""
    if QUALITY.get("probe") != why: QUALITY["probe_tries"] = int(QUALITY.get("probe_tries") or 0) + 1
    if QUALITY.get("confirmed") is True: QUALITY["proof_aside"] = dict(QUALITY["proof"], fee=QUALITY["fee"]) if isinstance(QUALITY.get("proof"), dict) else {"fee": QUALITY["fee"]}      # a proof was in place when this happened: the next run sets the lines entered so far aside
    QUALITY.update(probe=why, probe_kind=kind, probe_since=QUALITY.get("probe_since") or _os.path.basename(REG), probe_words="", confirmed=False, proof=None)
def quality_fault_visit(chart, visit, fee, dos, kind, why):
    """November 12, 2026 - fix round 1 (K11): the visit of a fault, a time-out (or a cut run) while the call that carried the line was out is for a person,
    AND it is listed under "stuck" at once - with what the import knows (the line's charge number is not known) - so that THIS run's inspector step
    already looks whether the Claim Inspector holds it. The next run reads the same from the failed row (quality_state)."""
    QUALITY.setdefault("stuck", []).append({"chart": chart, "visit": visit, "charge": "", "own": "", "code": QUALITY_CODE, "fee": str(fee or ""), "with": "", "dos": str(dos or ""), "fault": True,
                                            "why": re.sub(r"\s+", " ", str(why or "")).strip()[:140], "register": _os.path.basename(REG), "what": QUALITY_FAULT_WHAT[kind] + " - nobody has seen yet whether the Claim Inspector holds it",
                                            "since": _os.path.basename(REG)})
def quality_log(n, dry):
    """The ONE line a run prints about the quality code (the runbook reads it by its start). It says 'pilot:' exactly while a pilot round is open,
    'probing:' exactly while the code probes and 'paused:' exactly in a pause (11/12/2026) - the runbook reads those three words. 'off until
    William restarts it' is said only after his own QUALITY_CODE=stop."""
    Q = QUALITY; pause = Q.get("paused") or ""
    words = ("off until William restarts it (one run with QUALITY_CODE=reset)" if Q.get("off_until_reset") else
             "paused: no line in this run" if pause else
             ("no cap (a quality line was seen billed)" if (Q.get("n620") or Q.get("medicare_answer")) else "at most %d a run (a quality line was seen billed; no Medicare payment line is posted yet on the billed lines the import reads - lines added after proof are not read back)" % QUALITY_DAILY) if Q["confirmed"] else
             ("probing: waiting for the outcome of %d earlier line(s) - none added" % len(Q.get("pending") or []) if Q.get("wait") else "probing: one line a run until one is seen billed") if Q.get("probe") else
             "pilot: waiting for the outcome of %d earlier line(s) - none added" % len(Q.get("pending") or []) if Q.get("wait") else "pilot: at most %d visit(s) until one is seen billed" % QUALITY_PILOT)
    tail = ("; PAUSED - " + (pause[len("paused this run: "):] if pause.startswith("paused this run: ") else pause)) if (pause and Q["off"] == pause) else ("; OFF - " + Q["off"]) if Q["off"] else ""
    if Q.get("probe") and not Q.get("off_until_reset") and not pause and not Q["confirmed"]: tail += "; PROBING - " + Q["probe"]
    return "QUALITY 1123F: %s x%d visit(s), line amount $%s, %s%s%s" % ("would be on" if dry else "on", n, Q["fee"], words, tail, ("; " + Q["loud"]) if Q.get("loud") else "")
def mvp_state(regs, look, reset=False, files=None, day=None):
    """Fill MVP - the option code M0004's own small ledger, per clinician - from the same import registers quality_state read (this stamp's own
    register too), oldest first: each register's "mvp_gate" first, then its rows. files = what quality_files read (held visits, insurance-check
    holds, the lines the inspector step or the insurance check took off). look=False (a dry run) reads nothing in AdvancedMD. reset = MVP_CODE=reset.
    day = the calendar day of this run. See the OPTION CODE comment above for every state. Nothing here can stop the import: the caller turns any
    error into 'no M0004 line this run'.
    11/12/2026 - M0004 NEVER SWITCHES ITSELF OFF EITHER (the comment above): where it used to go off it probes (probe() below: ONE M0004 line a run
    in all, until an M0004 line entered after the newest cause is read billed) or pauses for this run (a visit stuck held with its M0004 line,
    another code text for its id). MVP['off'] is the pause sentence or empty; MVP['off_until_reset'] is always empty; MVP_CODE=reset has nothing
    left to restart. The 1123F line is never touched by any of it."""
    day = day or run_day(); today = _fmt_day(day); files = files if isinstance(files, dict) else {}
    m = _mvp_fresh(); notes = []; S = {"wrong": "", "wrongc": "", "answer": {}, "probe": "", "psince": "", "pwords": "", "pfrom": 0, "standing": None, "own_tries": 0}      # probe ...: why M0004 probes (the newest cause), the register the first cause lies in, AdvancedMD's own words, and how many M0004 lines the registers held when the newest cause was met
    _d = lambda k: files.get(k) if isinstance(files.get(k), dict) else {}
    held = _d("held"); chold = _d("check_holds"); rem = {k: list(v) for k, v in _d("removed").items() if isinstance(v, list)}
    billed = set(); void = set(); left = set(); billed_on = {}; lon = {}; lseen = {}; late = {}; late_rows = []; swaps = {}; lines = []; era = [0]
    base = lambda name: _os.path.basename(str(name)); num = lambda x: re.sub(r"\D", "", str(x or ""))
    st_of = lambda name: re.sub(r"^feed_(?:import|inspector|verify)_|\.json$", "", base(name)); short = lambda w: re.sub(r"\s+", " ", str(w or "")).strip()[:140]
    cof = lambda M: swaps.get(M["charge"], M["charge"])           # the M0004 line's charge number, a swap corrected (8.5)
    def restart(): S.update(wrong="", wrongc="", probe="", psince="", pwords="", pfrom=len(lines)); era[0] = len(lines)      # an OLDER register's MVP_CODE=reset, replayed as it was: what stopped M0004 before it no longer counts; a line that exists still counts for its clinician's year
    def probe(why, name, words=""):
        """A place where M0004 used to switch itself off: it PROBES instead - one M0004 line a run in all until an M0004 line entered AFTER this cause
        is read billed. why = the sentence of this cause (the newest cause is the one the gate says), name = the register it lies in, words =
        AdvancedMD's own words when there are any."""
        if not S["probe"]: S["psince"] = base(name)
        S.update(probe=why, pwords=short(words), pfrom=len(lines))
    def over():      # an M0004 line entered after the newest cause is billed: the probe has ended - each clinician who has none gets one, as before
        if S["probe"] and any(cof(M) in billed for M in lines[S["pfrom"]:]): S.update(probe="", psince="", pwords="")
    def stick(M, what, regname, why):      # the visit of M0004 line M is STUCK held with that line. Only a newer quality_removed entry ends the mark (removal below)
        M["stuck"] = {"what": what, "register": regname, "why": short(why), "since": (M.get("stuck") or {}).get("since") or regname}
    def created_row(name, r):
        pid = r.get("pid") if isinstance(r.get("pid"), str) else ""; vis = r.get("visit") if isinstance(r.get("visit"), str) else ""; who = "chart %s, visit %s, %s" % (pid or "?", vis or "?", base(name))
        if r.get("mvp_refused"): probe("AdvancedMD refused a visit that carried M0004 and took it with the 1123F line only (%s)" % who, name, r["mvp_refused"] if isinstance(r["mvp_refused"], str) else "")
        if r.get("mvp_not_stored"): probe("AdvancedMD stored a visit without its M0004 line - William looks (%s)" % who, name)
        mc = r.get("mvp_codes") if isinstance(r.get("mvp_codes"), list) else []; mid = r.get("mvp_charge") if isinstance(r.get("mvp_charge"), str) else ""
        if mc and mid:
            lines.append({"reg": base(name), "chart": pid, "visit": vis, "charge": mid, "prof": r.get("mvp_prof") if isinstance(r.get("mvp_prof"), str) else "",
                          "dos": str(r.get("mvp_dos") or r.get("quality_dos") or r.get("dos") or ""), "q": r.get("quality_charge") if isinstance(r.get("quality_charge"), str) else "",
                          "fee": str(r.get("mvp_fee") or ""), "charges": [c for c in (r.get("charges") if isinstance(r.get("charges"), list) else []) if isinstance(c, str)]})
            if r.get("quality_not_stored"): probe("AdvancedMD stored the M0004 line of a visit without its 1123F line - William looks (%s)" % who, name)      # the row says it (until 11/12/2026 only that run's gate did)
    def failed_row(name, r):          # a visit that carried M0004 was refused and nobody knows what AdvancedMD kept (unless the 1123F-only form was refused too: then M0004 is not blamed): that visit is for a person; M0004 probes
        info = r.get("info") if isinstance(r.get("info"), dict) else {}
        if info.get("mvp_tried") and not info.get("mvp_form_refused") and (r.get("stored") or r.get("quality_unknown")):
            probe(("the run was cut while a call that carried M0004 was out; nobody knows what AdvancedMD kept of that visit - William looks (chart %s, visit %s, %s)" if r.get("provisional") else
                   "AdvancedMD answered a visit that carried M0004 with a fault or an error and nobody knows what it kept of it - William looks (chart %s, visit %s, %s)") % (r.get("pid") if isinstance(r.get("pid"), str) else "?", r.get("empty_visit") or "?", base(name)), name)
    def removal(regname, e):
        """An M0004 line the inspector step or the insurance check TOOK OFF a held visit (11.6): void and final. released (the visit went through
        without it) = M0004 probes; it does not count against 1123F (the 1123F line's own entry does, when it was taken off with it). Not released
        = the line is just void: its clinician may get it again. "with": "1123F" = it came off only because its 1123F line came off (M0004 never
        rides without 1123F, 8.2; confirm review NH2-1): just void, nothing follows for M0004 - that clinician may get M0004 again.
        THE STUCK VISIT (11/12/2026), as for the 1123F line: a void that failed, or the visit still listed for the edit about the line after the
        void (the re-save failed, or AdvancedMD did not inspect the visit again; NH2-2) = the visit is stuck with its M0004 line: no new M0004 line
        while that is so, the inspector step tries again in every run, M0004 probes afterwards. The NEWEST entry for a line decides; an entry that
        says "listed": false ends the mark and counts nothing more; an entry that carries "retry_of" begins a probe when none is running.
        November 12, 2026 - fix round 1 (K11): an entry with "fault": true is about a visit of a fault run - the 1123F ledger reads it (quality_state)."""
        if e.get("fault") is True: return
        c_ = num(e.get("charge"))
        M = next((M for M in reversed(lines) if num(cof(M)) == c_), None)
        if M is None:      # the row recorded it as its 1123F line (the two were swapped): it is this row's M0004 line
            M = next((M for M in reversed(lines) if M["q"] and num(M["q"]) == c_), None)
            if M is not None: swaps[M["charge"]] = M["q"]
        if M is None: notes.append("%s names M0004 charge %s, which no import register row carries - passed over" % (regname, e.get("charge"))); return
        was = bool(M.get("stuck")); M["removed"] = dict(e, register=regname); w = short(e.get("why"))
        def freed():      # the step's retry: the visit was held with its M0004 line and is free now
            if e.get("retry_of") and not S["probe"]: probe("visit %s was held with its M0004 line until the routine could free it (%s: \"%s\")" % (M["visit"], regname, w), regname, w)
        if e.get("listed") is False: M["stuck"] = None; freed(); return
        if e.get("void_ok") is not True:
            stick(M, "the routine could not take the line off", regname, w)
            if not was: probe("the Claim Inspector holds visit %s and the routine could not take its M0004 line off (%s: \"%s\") - William looks" % (M["visit"], regname, w), regname, w)
            return
        void.add(cof(M))
        if e.get("with") == QUALITY_CODE: M["stuck"] = None; notes.append("the M0004 line of visit %s came off with its 1123F line - %s may get M0004 again" % (M["visit"], M["prof"] or "its clinician")); return
        if e.get("released") is not True and (e.get("still_named") is True or e.get("resave_ok") is False):
            stick(M, "the line is off, but the visit is still listed for the edit about it", regname, w)
            if not was: probe("the routine took the M0004 line off held visit %s, but the visit is still listed for the edit about the line (%s: \"%s\") - William looks; one re-save of the visit should release it" % (M["visit"], regname, w), regname, w)
            return
        M["stuck"] = None; freed()
        if e.get("released") is True: probe("the routine took the M0004 line off held visit %s and the visit went through without it (%s: \"%s\")" % (M["visit"], regname, w), regname, w)
    def rows(fn, name, rs):          # row by row: an odd row is passed over, the rows after it are still read
        for r in rs:
            try:
                if isinstance(r, dict): fn(name, r)
            except Exception: continue
    is_mvp = lambda e: isinstance(e, dict) and str(e.get("code") or "").strip().upper() == MVP_CODE
    holds = {}      # batch stamp -> [(visit number, register, the hold's words)]: the visits the insurance check put on HOLD, taken batch by batch (as for 1123F)
    for v_, rows_ in chold.items():
        for regname, words in rows_: holds.setdefault(st_of(regname), []).append((v_, regname, words))
    def hold(v_, regname, words):      # the insurance check could not set the order of a visit that carries the M0004 line: that visit is for a person; M0004 probes - once, in its place
        M = next((M for M in reversed(lines[era[0]:]) if num(M["visit"]) == v_ and not M.get("removed")), None) if v_ else None
        if M is None: return
        for why in words:
            named = set(re.findall(r"vst\d+", why))
            if re.search(r"insorder not applied|resave FAULT|detail read mismatch", why) and (not named or M["visit"] in named):
                probe("the insurance check could not set the order of visit %s, which carries the M0004 line (%s: \"%s\") - William looks" % (M["visit"], regname, why[:140]), regname); return
    for name, reg in sorted(regs, key=lambda x: str(x[0])):
        try:
            if not isinstance(reg, dict): continue
            g = reg.get("mvp_gate") if isinstance(reg.get("mvp_gate"), dict) else {}
            cr = reg.get("created") if isinstance(reg.get("created"), list) else []; fl = reg.get("failed") if isinstance(reg.get("failed"), list) else []
            cut = [0, 0]
            if g.get("reset") is True:      # M0004 was started again in that run (an older register); rows an earlier start under the same stamp had written stay before the restart
                ra = g.get("reset_after")
                if isinstance(ra, list) and len(ra) == 2 and all(isinstance(x, int) and not isinstance(x, bool) and x >= 0 for x in ra): cut = ra
                rows(created_row, name, cr[:cut[0]]); rows(failed_row, name, fl[:cut[1]]); restart()
            for k, s in (("billed_lines", billed), ("void_lines", void), ("left_off_lines", left)):      # what earlier runs read as final is never read for its outcome again
                s.update(x for x in (g.get(k) if isinstance(g.get(k), list) else []) if isinstance(x, str))
            for k, d_ in (("billed_on", billed_on), ("left_off_seen", lseen), ("left_off_on", lon), ("late_billed", late), ("swaps", swaps)):
                if isinstance(g.get(k), dict): d_.update((a, b) for a, b in g[k].items() if isinstance(a, str) and isinstance(b, (str, dict)))
            over()      # with what that run had read billed
            ou = g["off_until_reset"].strip() if isinstance(g.get("off_until_reset"), str) else ""
            if ou and not S["probe"]:      # an OLDER register (written before 11/12/2026) that says "off until reset": every such sentence was the code's own (William has no lasting M0004 stop) - a pause that has ended; in this place M0004 probes
                probe("the option code M0004 had switched itself off (%s) - William's standing word of November 11, 2026 restarts it" % ou[:200], name)
            gp = g["probe"].strip() if isinstance(g.get("probe"), str) else ""
            if gp and not S["probe"]:      # the probe is carried by the gates, also when what caused it can no longer be read (a cause no row records)
                S.update(probe=gp, psince=g["probe_since"] if isinstance(g.get("probe_since"), str) and g["probe_since"] else base(name), pwords=short(g["probe_words"]) if isinstance(g.get("probe_words"), str) else "", pfrom=len(lines))
            if base(name) != base(REG): S["standing"] = {"was": ou[:300], "register": base(name)} if ou else None      # said ONCE, by the run whose newest EARLIER register carries such a sentence
            else:      # this stamp's own register (a second start): an M0004 try it already holds is this run's one M0004 line while M0004 probes
                S["own_tries"] = (sum(1 for r in cr if isinstance(r, dict) and ((r.get("mvp_codes") and r.get("mvp_charge")) or r.get("mvp_refused") or r.get("mvp_not_stored")))
                                  + sum(1 for r in fl if isinstance(r, dict) and isinstance(r.get("info"), dict) and r["info"].get("mvp_tried")))
            if "wrong_code_charge" in g:      # a gate of this version says what ITS run read (a pause that every run reads again); an older gate's text is not carried
                S["wrong"] = g["wrong_code_text"] if isinstance(g.get("wrong_code_text"), str) else ""; S["wrongc"] = g["wrong_code_charge"] if isinstance(g.get("wrong_code_charge"), str) else ""
            for p_, a_ in (g.get("answer").items() if isinstance(g.get("answer"), dict) else ()):      # the first answer found for a clinician stays
                if isinstance(p_, str) and isinstance(a_, dict) and a_.get("charge"): S["answer"].setdefault(p_, dict(a_))
            rows(created_row, name, cr[cut[0]:]); rows(failed_row, name, fl[cut[1]:])
            for regname, e in [x for x in rem.pop(st_of(name), []) if is_mvp(x[1])]:      # the M0004 lines that batch's inspector step / insurance check took off
                try: removal(regname, e)
                except Exception: continue
            for h_ in holds.pop(st_of(name), []):      # then that batch's insurance-check HOLDs
                try: hold(*h_)
                except Exception: continue
        except Exception: continue
    for st in sorted(rem):      # removals of a batch whose import register is not here: still void, after everything else
        for regname, e in [x for x in rem[st] if is_mvp(x[1])]:
            try: removal(regname, e)
            except Exception: continue
    for st in sorted(holds):      # ... and the HOLDs of such a batch
        for h_ in holds[st]:
            try: hold(*h_)
            except Exception: continue
    if reset:      # MVP_CODE=reset has nothing left to restart: M0004 never switches itself off (11/12/2026)
        m["loud"] = "NOTHING TO RESTART - MVP_CODE=reset was ignored (M0004 is not switched off; take the switch out of the routine)"; notes.append(m["loud"])
    # HELD VISITS that carry the M0004 line (entered since the last restart) and whose line could NOT be taken off (no removal recorded): a Claim
    # Inspector hold whose words name M0004 -> the visit is STUCK with its M0004 line (11/12/2026): no new M0004 line in this run, and the
    # inspector step tries it again; no probe starts from the held row itself
    for M in lines[era[0]:]:
        if M.get("removed") or M.get("stuck") or not num(M["visit"]): continue
        for regname, why, _marked in held.get(num(M["visit"])) or ():
            if names_lines(why, M["q"], cof(M))[1]: stick(M, "the Claim Inspector holds it and the line was not taken off", regname, why); break
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
        if sn.get("wrong"):      # AdvancedMD shows another code text than M0004 for the line's id: nothing is built on it - a pause while that is so, and every run reads it again (11/12/2026)
            S["wrong"] = sn["wrong"]; S["wrongc"] = cof(M); return
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
    if S["wrong"] and look:      # another code text was on record (the gate before this run): the pause is what THIS run reads (the rule of the 1123F line, _text_pause)
        _now = _text_pause([cof(M) for M in lines], void, S["wrongc"], MVP_PCODE, MVP_CODE, looks)
        if _now is not None: S["wrong"], S["wrongc"] = _now
    for M in lines:      # every M0004 line not decided yet, oldest first (whatever the restarts: whether a clinician is done for the year does not depend on them)
        if not look or looks[0] <= 0: break
        if final(M) or M.get("seen"): continue
        read(M)
    for M in lines:      # a line read as LEFT OFF is read again until QUALITY_LEFT_OFF_REREAD days after it was CALLED left off (13.1b; fix round 2, K13: the block's own clock): billed after all = its clinician is done
        if not look or looks[0] <= 0: break
        c_ = cof(M); w = lon.get(c_) if isinstance(lon.get(c_), dict) else {}; b = _mdy_day(str(w.get("on") or "")) or _mdy_day(str(w.get("billed") or ""))
        if final(M) != "left" or M.get("seen") or b is None or (day - b).days > QUALITY_LEFT_OFF_REREAD: continue
        looks[0] -= 1; M["seen"] = True; sn = {}; st, what = _line(c_, MVP_PCODE, MVP_CODE, sn)
        if sn.get("wrong"): S["wrong"] = sn["wrong"]; S["wrongc"] = c_; continue      # another code text: a pause (see read())
        if st == "billed":
            left.discard(c_); billed.add(c_); billed_on[c_] = what[0]; late[c_] = today
            again = [N["visit"] for N in lines if N is not M and N["prof"] == M["prof"] and N["dos"][-4:] == M["dos"][-4:] and final(N) == "billed"]      # "two billed lines" only when the later one IS billed
            late_rows.append([M["prof"], M["chart"], M["visit"], c_, str(w.get("on") or ""), again[0] if again else "", M["dos"][-4:]])
            notes.append("the M0004 line of visit %s, read as left off its claim on %s, was billed later (%s): %s counts as done" % (M["visit"], w.get("on") or "?", what[0], M["prof"] or "its clinician"))
        elif st == "void": left.discard(c_); void.add(c_); notes.append("the M0004 line of visit %s, read as left off its claim, is void now" % M["visit"])
    lo = [M for M in lines[era[0]:] if final(M) == "left"]
    if len(lo) >= MVP_LEFT_OFF_MAX:      # AdvancedMD leaves the M0004 line off the claim (this needs a setting in AdvancedMD): M0004 probes - the newest cause is the newest left-off line, so the probe ends when a line entered after it is billed
        k = max(i for i, M in enumerate(lines) if any(M is x for x in lo)) + 1
        if not any(final(M) == "billed" for M in lines[k:]) and (not S["probe"] or S["pfrom"] <= k):
            if not S["probe"]: S["psince"] = lo[-1]["reg"]
            S.update(probe="AdvancedMD left the M0004 line off %d claims since the option code was last started (visits %s) - William looks" % (len(lo), ", ".join(M["visit"] for M in lo[:4])), pwords="", pfrom=k)
    over()      # with what this run read billed
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
        elif final(M) == "left":      # K12 (November 12, 2026 - fix round 1): a left-off M0004 line may still be billed for QUALITY_LEFT_OFF_REREAD days after it was called left off - its clinician gets no new M0004 line until then
            w_ = lon.get(cof(M)) if isinstance(lon.get(cof(M)), dict) else {}; d_ = _mdy_day(str(w_.get("on") or "")) or _mdy_day(str(w_.get("billed") or ""))
            if d_ is None or (day - d_).days < QUALITY_LEFT_OFF_REREAD: m["done"].add((M["prof"], M["dos"][-4:]))
    yr = max(MVP_YEARS); cl = {}
    for p_ in sorted(set(PROFILE.values())):      # for the report: each clinician's M0004 line of the year it is registered for
        mine = [M for M in lines if M["prof"] == p_ and M["dos"][-4:] == yr]; b_ = [M for M in mine if final(M) == "billed"]; w_ = [M for M in mine if not final(M)]; l_ = [M for M in mine if final(M) == "left"]
        top = (b_ or w_ or l_ or [None])[0]
        cl[p_] = {"state": "billed" if b_ else "waiting" if w_ else "left off" if l_ else "not yet", "year": yr, "visit": top["visit"] if top else "", "charge": cof(top) if top else "",
                  "billed": billed_on.get(cof(top), "") if b_ else "", "since": top["reg"] if top else ""}
    aw = {p_: {"visit": v_["visit"], "billed": v_["billed"], "days": (day - _any_day(v_["billed"])).days if _any_day(v_["billed"]) else None} for p_, v_ in cl.items() if v_["state"] == "billed" and p_ not in S["answer"]}
    # A PAUSE is THIS run's (11/12/2026): a visit stuck held with its M0004 line (the inspector step of every run tries the void and the re-save again), or
    # another code text for the line's id. No new M0004 line while that is so; the 1123F line goes on. Every run looks again.
    stuck = [M for M in lines if M.get("stuck")]; pause = ""
    def item(M, **more): return dict({"chart": M["chart"], "visit": M["visit"], "charge": cof(M), "own": own_of(M), "code": MVP_CODE, "fee": M["fee"], "with": M["q"] if M["q"] != cof(M) else M["charge"]}, **more)      # what the inspector step needs to find the visit and its line again ("with" = the same visit's 1123F line; a swap corrected)
    if stuck:
        s0 = stuck[0]["stuck"]
        pause = "paused this run: visit %s (chart %s) is held with its M0004 line - %s (%s: \"%s\")%s; no new M0004 line while that is so - every run's inspector step tries the void and the re-save again" % (
            stuck[0]["visit"], stuck[0]["chart"], s0["what"], s0["register"], s0["why"], ("; and %d more visit(s)" % (len(stuck) - 1)) if len(stuck) > 1 else "")
    elif S["wrong"]: pause = "paused this run: AdvancedMD shows procedure id %s as %s, not %s - no M0004 line while that is so; every run reads it again" % (MVP_PCODE, S["wrong"], MVP_CODE)
    # while M0004 probes: ONE M0004 line a RUN in all - none while an M0004 line is not decided, none in a retry register, none when this stamp's own register already holds an M0004 try
    m.update(off=pause, off_until_reset="", billed_lines=sorted(billed), void_lines=sorted(void), left_off_lines=sorted(left - billed - void), billed_on={k: v for k, v in billed_on.items() if k in billed},
             left_off_on={k: v for k, v in lon.items() if k in left}, left_off_seen={k: v for k, v in lseen.items() if k not in billed and k not in void and k not in left}, late_billed=dict(late),
             late_rows=late_rows, swaps=dict(swaps), wrong_code_text=S["wrong"], wrong_code_charge=S["wrongc"] if S["wrong"] else "", answer=dict(S["answer"]), answer_wait=aw, clinicians=cl, notes=notes[:20], lines=len(lines),
             probe=S["probe"], probe_since=S["psince"] if S["probe"] else "", probe_words=S["pwords"] if S["probe"] else "", paused=pause,
             stuck=[item(M, why=M["stuck"]["why"], register=M["stuck"]["register"], what=M["stuck"]["what"], since=M["stuck"]["since"]) for M in stuck],
             open_lines=[item(M, why="", register=M["reg"]) for M in lines if not final(M) and not M.get("stuck")], standing_restart=S["standing"],
             budget=None if not S["probe"] else (0 if (str(STAMP).endswith("R") or S["own_tries"] or m["wait"]) else 1))
    MVP.clear(); MVP.update(m)
def mvp_gate():
    """What a run writes into its register as "mvp_gate": the option code M0004's own ledger, for the next run and for the digest. off = why no M0004
    line is added in THIS run (a pause, or a "this run: ..." sentence); off_until_reset = always empty since 11/12/2026 (M0004 never switches
    itself off; the key stays for the readers of older registers); clinicians = per clinician (the profile its visits are entered under), for the
    year it is registered for: billed / waiting / left off / not yet; added = the clinicians whose visit got the M0004 line in this run; answer =
    Medicare's own answer per clinician (answer_wait while none). probe = why M0004 probes (one M0004 line a run in all), the newest cause;
    probe_since / probe_words = the register the first cause lies in, AdvancedMD's own words; paused = the pause sentence (also in off); stuck =
    the visits held with their M0004 line, for the inspector step's retry; open_lines = the M0004 lines not decided yet, for the same step;
    standing_restart = an older register's own OFF, said once; wrong_code_charge = the charge that showed another code text in this run."""
    M = MVP; cl = {k: dict(v) for k, v in (M.get("clinicians") or {}).items()}      # main() marks a clinician whose visit got the line in this run as waiting
    return {"code": MVP_CODE, "on": bool(MVP_ON), "off": M.get("off") or "", "off_until_reset": M.get("off_until_reset") or "", "reset": bool(M.get("reset")), "reset_after": M.get("reset_after") if M.get("reset") else None,
            "added": list(M.get("added") or []), "clinicians": cl, "billed_lines": list(M.get("billed_lines") or []), "void_lines": list(M.get("void_lines") or []),
            "left_off_lines": list(M.get("left_off_lines") or []), "billed_on": dict(M.get("billed_on") or {}), "left_off_on": dict(M.get("left_off_on") or {}), "left_off_seen": dict(M.get("left_off_seen") or {}),
            "late_billed": dict(M.get("late_billed") or {}), "late_rows": list(M.get("late_rows") or []), "swaps": dict(M.get("swaps") or {}), "wrong_code_text": M.get("wrong_code_text") or "",
            "answer": dict(M.get("answer") or {}), "answer_wait": dict(M.get("answer_wait") or {}),
            "probe": M.get("probe") or "", "probe_since": M.get("probe_since") or "", "probe_words": M.get("probe_words") or "", "paused": M.get("paused") or "", "stuck": list(M.get("stuck") or []),
            "open_lines": list(M.get("open_lines") or []), "standing_restart": M.get("standing_restart"), "wrong_code_charge": M.get("wrong_code_charge") or "",
            "notes": list(M.get("notes") or [])}
def mvp_probe_now(why, words=""):
    """What a run finds out about M0004 WHILE it enters visits (refused with M0004, stored without it, a call that ended in an error): M0004 probes
    from the next run - nothing is switched off (11/12/2026). The gate this run writes already says so; this run adds no further M0004 line
    (MVP['off'] says why)."""
    MVP.update(probe=why, probe_since=MVP.get("probe_since") or _os.path.basename(REG), probe_words=re.sub(r"\s+", " ", str(words or "")).strip()[:140])
def mvp_log(n, dry):
    """The ONE line a run prints about the option code M0004, right after the QUALITY 1123F line (the runbook reads it by its start). 11/12/2026: it
    says 'probing:' while M0004 probes and 'paused:' in a pause; it never says 'off until William restarts it' any more."""
    M = MVP; cl = M.get("clinicians") or {}; added = set(M.get("added") or []); pause = M.get("paused") or ""
    who = ", ".join("%s %s" % (p_, "waiting (added now)" if p_ in added and (cl.get(p_) or {}).get("state") != "billed" else (cl.get(p_) or {}).get("state") or "not yet") for p_ in sorted(set(PROFILE.values())))
    words = "paused: no M0004 line in this run" if pause else "probing: one M0004 line a run until one is seen billed" if M.get("probe") else "once per clinician, only with the 1123F line once that is proven"
    tail = ("; PAUSED - " + (pause[len("paused this run: "):] if pause.startswith("paused this run: ") else pause)) if (pause and M.get("off") == pause) else ("; OFF - " + M["off"]) if M.get("off") else ""
    if M.get("probe") and not pause: tail += "; PROBING - " + M["probe"]
    return "QUALITY M0004: %s x%d visit(s), %s; %s%s%s" % ("would be on" if dry else "on", n, who, words, tail, ("; " + M["loud"]) if M.get("loud") else "")
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
    the same lines from several buildings - then that day is named under two buildings: the resident's next visit reads it as a move (31), and
    that month's CCM - 32 like every CCM line since 11/25/2026 - is listed for William, exactly like a day the chart and the feed name under two
    buildings."""
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
    if info.get("dx_instead"): stats["diagnosis code not in AdvancedMD's list - visit entered with %s in its place (William 11/25/2026); the digest names the codes for his email" % info["dx_instead"]] += 1
    if not info.get("fac"): stats["visit entered with NO facility - its building is not in the facility table"] += 1      # every code, not only CCM / nursing lines
    # 11/25/2026 (review of the CCM rule): the VALUE is tested first. A CCM line that stands at 31 is counted as not William's rule whatever its kind says and
    # whatever visit it is in - also a visit whose rule failed (pos_err), which used to leave this count before any line was looked at, and a visit with no
    # facility. 'CCM 31 xN' of the short log line is the sum of this counter, so it says what was sent, never how the line was labelled.
    _at31 = [cpt in CCM and str(p) == "31" for cpt, p in zip(info["cpts"], info["pos_lines"])]
    if any(_at31): stats["POS 31 CCM - NOT WILLIAM'S RULE (11/25/2026: every CCM line is 32) - an old copy of the rule ran"] += sum(_at31)
    if info.get("pos_err"):
        stats["POS RULE NOT APPLIED (entered at the feed's place of service; %s)" % ("ITS CCM LINE AT 31, not William's rule" if any(_at31) else "a CCM line at 32")] += 1; return
    _kinds = info.get("pos_kind") if isinstance(info.get("pos_kind"), list) else []      # 11/25/2026 (inpatient rehab stays): counted per VISIT - entered at HCA REHAB / 61, or a visit of a rehab stay kept at 21 (the group the monitor compares with)
    # 11/25/2026 (verification): by what AdvancedMD STORED where the import read it back (pos_stored, one per charge line; a dry run and an answer without it have none - then what was
    # sent counts, as before). A rehab visit whose stored lines hold no 61 was counted and printed as 'entered at HCA REHAB' while the monitor of the same run said that no visit is at 61.
    _stored = info.get("pos_stored") if isinstance(info.get("pos_stored"), list) and info.get("pos_stored") else None
    if "rehab" in _kinds and _stored is not None and REHAB_POS not in [str(x) for x in _stored]: stats[REHAB_61_LOST] += 1
    elif "rehab" in _kinds: stats[REHAB_61_COUNT] += 1
    elif REHAB_KEPT in _kinds: stats[REHAB_21_COUNT] += 1
    for cpt, p, k in zip(info["cpts"], info["pos_lines"], info.get("pos_kind") or [""] * len(info["cpts"])):
        _c31 = cpt in CCM and str(p) == "31"                # counted above, under the value: never again under a kind or under words that say 32
        if info.get("pos_feed") == "31" and not info.get("fac") and (cpt in CCM or cpt in NF_VISIT): stats["POS RULE: building not in the facility table - %s" % ("a CCM line AT 31, not William's rule" if _c31 else "a nursing visit at the default 31, a CCM line at 32")] += 1
        elif _c31: pass
        elif k == "ccm": stats["POS 32 CCM (nursing building)"] += 1
        elif k == "ccm-skilled-month": stats["POS 32 CCM listed for William (the chart shows a skilled-looking month - see pos_why; William 11/25/2026: every CCM line is 32)"] += 1
        elif k == "monthly": stats["POS 32 nursing visit (monthly)"] += 1
        elif k in ("extra", "between"): stats["POS 31 nursing visit (kept at 31: neither pattern shown)"] += 1
        elif k == "moved": stats["POS 31 nursing visit (previous nursing visit in another building)"] += 1
        elif k in ("rehab", REHAB_KEPT): pass               # a line of an inpatient rehab stay's visit: counted above, once per visit - never as a nursing visit
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
        _npi = _adm = _unit = ""; _ft = []; _pv1 = False
        for line in b.strip().split("\n"):              # b.strip(): exactly what feed_parse_dft does to a block, so both readers see the same last field
            s = line.split("|")
            if s[0] == "PID": pid = s[3] if len(s) > 3 else ""; FACOF[pid] = fac; FACS.setdefault(pid, set()).add(fac)
            if s[0] == "PV1":                             # wherever it stands in the message (the parser does not care about the order either)
                _pv1 = True; _npi = s[7].split("^")[0] if len(s) > 7 else ""; _adm = s[44] if len(s) > 44 else ""
                _unit = s[2].split("^")[-1].strip() if len(s) > 2 else ""      # 11/25/2026: the PV1 line's own facility number - the last ^ component of its field 2 (PV1|1|^^^<number>|...); the rehab unit's number names a visit of its stay (REHAB_UNIT_NUMBERS)
            if s[0] == "FT1": _ft.append((s[25].split("^")[0] if len(s) > 25 else "", s[4] if len(s) > 4 else ""))
        if pid and _pv1: NPIOF[pid] = _npi; ADMIT[pid] = _adm
        try:
            if pid: MSGOF.setdefault(msg_key(pid, _ft), set()).add((fac, _npi, _adm)); MSGLAST[msg_key(pid, _ft)] = (fac, _npi, _adm); MSGUNIT.setdefault(msg_key(pid, _ft), set()).add(_unit)      # ... the last raw copy of THIS message, and (11/25/2026) the facility number of every copy
        except Exception: pass
_ctx = {}
def chart_ctx(pid):
    """episode, respparty, refplan, insorder, live {(cpt,dos)} from the chart's own history/detail. Since 11/25/2026 also 'dob' - the chart's own birth date as 8 digits
    ("" when the answer gives none or one that cannot be read; the year-1900 placeholder is kept as written; None when the chart itself could not be read - like
    chart_insorder) - and 'name', both from the getdemographic answer made here anyway. They stay in memory: nothing prints them or writes them to a register."""
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
    # William 11/25/2026 (THE CHART'S OWN BIRTH DATE above): the same answer carries the patient's name and birth date as the chart holds them (name "LAST,FIRST",
    # the date as MM/DD/YYYY) - kept here so the row can say how the feed's date compares and the 1123F age is the chart's. No extra call; in memory only.
    _cd = _any_day(a.get("dob")); ctx["dob"] = ("%04d%02d%02d" % (_cd.year, _cd.month, _cd.day)) if _cd else ("" if p else None); ctx["name"] = __import__("html").unescape(a.get("name", "") or "").strip()
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
    # 11/25/2026 (inpatient rehab stays, review): a hospital visit line passed over just now because the chart carries ANOTHER hospital code of ours for its day (the same-day
    # rule - not the same code sent again) is still a visit the feed showed: where it is an initial visit, a stay began that day. It is kept for the stay rule - SAME_DAY for
    # the rest of this run, this run's register ("same_day") for every later one. Nothing else reads it; what is entered and what is passed over is exactly as before.
    for _c in msg["FT1"]:
        if _c["cpt"] in HOSP_VISIT and _c not in lines and (_c["cpt"], mdy(_c["dos"][:8])) not in ctx["live"]:
            for _m in (SAME_DAY, SAME_DAY_NEW): _m.setdefault(ctx.get("pid"), set()).add((_c["cpt"], mdy(_c["dos"][:8])))
    if not lines: return None, "all lines already in AMD"
    dos = mdy(lines[0]["dos"][:8])
    chg = ""
    cpts = [c["cpt"] for c in lines]
    missing_dx = set()
    # place of service per line (11/10/2026 rule); any failure = the feed's place of service for every line, exactly as before the rule - except a CCM
    # line, which is 32 all the same (William 11/25/2026: never the skilled-nursing 31)
    pos_err = ""; lkind = [""] * len(lines)
    try:
        if nursing and BATCH_NF_ERR[0] and any(c["cpt"] in NF_VISIT for c in lines):      # only a nursing VISIT line needs the pattern; a CCM line is 32 without it (William 11/25/2026)
            raise ValueError("the visits of this batch could not be listed (%s), so nothing shows this resident's pattern - kept at the feed's place of service (a CCM line: 32)" % BATCH_NF_ERR[0])
        if _ag[0] is None and len(FACS.get(fid, ())) > 1 and (nursing or any(FAC.get(_n, ("", ""))[1] == "31" for _n in FACS[fid])):
            raise ValueError("this feed patient has messages from %d buildings in this batch and its own building cannot be read - "
                             "facility, clinician and place of service are for William; a routine changes nothing on this visit" % len(FACS[fid]))
        hist = (list(ctx.get("nfrows") or ctx.get("live") or ()) + list(BATCH_NF.get(ctx.get("pid"), ()))) if nursing else ()   # the history is only read for a nursing building
        lpos, lwhy, lkind = (list(_x) for _x in pos_lines([(c["cpt"], mdy(c["dos"][:8])) for c in lines], pos, nursing, hist, fac if nursing else None))      # three lists of this message's own (the second look below changes them in place)
        if len(lpos) != len(lines) or any(p not in ("31", "32", pos) for p in lpos): raise ValueError("unexpected place of service %r" % (lpos,))
    except Exception as e:
        lpos = [pos] * len(lines); lwhy = ["rule error"] * len(lines); lkind = [""] * len(lines); pos_err = str(e)[:200] or type(e).__name__
        ccm_never_31([c["cpt"] for c in lines], lpos, lwhy, lkind)      # William 11/25/2026: also when the rule fails, a CCM line goes in at 32 - never 31
    # INPATIENT REHAB STAY (William 11/25/2026: the rehab visits go in at place of service 61 - INPATIENT REHAB STAYS above). Only a message whose OWN building is the hospital
    # (every raw copy of it names that building - never the patient's last-read one) and that carries a hospital visit line is read. A visit of a rehab stay entered under the
    # rule: facility fac67, EVERY charge line 61. A visit of a rehab stay whose initial visit went in at 21: as before, pos_kind rehab-stay-kept-21. An acute stay: as before.
    # Any error = exactly as before (fac29 / 21) with pos_err saying so - the import never stops for this rule and never guesses 61.
    _stay = None; _at61 = None
    if not pos_err and (fac, pos) == REHAB_HOSPITAL and _ag[0] is not None and any(c.get("cpt") in HOSP_VISIT for c in msg["FT1"]):
        try:
            if BATCH_NF_ERR[0]: raise ValueError("the visits of this batch could not be listed (%s)" % BATCH_NF_ERR[0])
            _rv = rehab_visit([(c["cpt"], mdy(c["dos"][:8])) for c in msg["FT1"]], ctx["nfrows"] if "nfrows" in ctx else ctx.get("live") or (), list(BATCH_NF.get(ctx.get("pid"), ())) + list(SAME_DAY.get(ctx.get("pid"), ())),
                              rehab_unit_lines(fid), ctx.get("stay_sent"), ctx.get("stay_sent_fu"), batch_hospital_messages(fid), ctx.get("stay_gone"), SAID_61.get(ctx.get("pid")))      # 11/25/2026 (review): with the lines the same-day rule passed over, what this run built for the chart's other hospital visits, and the batch's own hospital messages; (verification) the initial visits this run could not enter, and the days at 61 that were named already
            _st = {_k: str(_rv["stay"][_k]) for _k in ("kind", "initial", "sign")}; _rw = [str(_rv["why"])] * len(lines)
            if _rv["to61"] is True and _st["kind"] != "rehab": raise ValueError("an answer that sends an acute stay's visit to 61")
            if _rv["to61"] is True: fac, lpos, lwhy, lkind = REHAB_FAC, [REHAB_POS] * len(lines), _rw, ["rehab"] * len(lines)
            elif _st["kind"] == "rehab": lwhy, lkind = _rw, [REHAB_KEPT] * len(lines)
            elif _rv["why"]: lwhy = _rw      # (review) a hospital stay the plain rule does not explain: entered as before, with the words why
            _stay = _st
            if _rv.get("said") and _rv["to61"] is not True:      # (review, verification) entered as before - and SAID: other visits of the stay in hand stand at HCA REHAB (REHAB_MIXED / REHAB_SPLIT / REHAB_NO_ADMISSION)
                pos_err = str(_rv["said"]); _d61 = [str(x) for x in (_rv.get("at61") or []) if _mdy_day(x) is not None]
                if _d61:      # the days it names go into the row as a list of their own - and are not named again, by this run or by a later one
                    _at61 = ("hospital_at61" if _rv.get("at61_kind") == "hospital" else "mixed_at61", _d61); SAID_61.setdefault(ctx.get("pid"), set()).update(_d61)
        except Exception as e:      # whatever was set above is taken back: facility, place of service, reason and kind exactly as before the rule
            fac, lpos, lwhy, lkind, _stay, _at61 = REHAB_HOSPITAL[0], [pos] * len(lines), ["rule error"] * len(lines), [""] * len(lines), None, None
            pos_err = "inpatient rehab stay not worked out (%s) - entered as before (fac29 / 21); for William" % (str(e)[:110] or type(e).__name__)
    for _c, _p in zip(lines, lpos):      # what this run built for a hospital visit of the chart - an initial one: its follow-ups later in the run follow it; any other (review): the stay's late initial visit never goes in at another place (a stay is never mixed)
        if _c["cpt"] in HOSP_VISIT: ctx.setdefault("stay_sent" if _c["cpt"] in HOSP_INITIAL else "stay_sent_fu", {})[mdy(_c["dos"][:8])] = _p
    # 11/25/2026 (review of the CCM rule, defence in depth): "a CCM line is never entered at 31" must not rest on what pos_lines answers. Whatever came out
    # above - the rule's own lists or the fallback - is looked at once more: a CCM line that still stands at 31 goes in at 32 (kind ccm-forced, the reason in
    # William's name). Nothing else of the message is touched: 13, 21, every other code and every line that is not at 31 stay as they are.
    ccm_never_31([c["cpt"] for c in lines], lpos, lwhy, lkind)
    _qwhy = []                                            # "hospital" when the visit met every condition but its visit lines are hospital lines
    try: qi = quality_due(msg, ctx, lines, lpos, _qwhy)   # the visit line the advance-care-plan quality code rides with (None = no code)
    except Exception: qi = None; _qwhy = []
    qchg = ""
    # DIAGNOSIS CODES (William 11/25/2026, STANDING: "for any diagnosis not in the master file yet change it to i10 and send me an email with the codes needed to
    # be added"). Until that day a code AdvancedMD's list does not have was left off the charge, and a line with no usable code skipped the whole visit (68 of
    # 1,480 entered visits had a code left off; two 99309 visits waited on S82.843D since 11/13 and 11/22/2026). Now such a code goes in as I10 IN ITS PLACE in
    # the line's own order, as long as I10 itself is in the list; missing_dx still names the code and dx_instead says what stands for it - the digest and
    # William's email are built from them (claimocity_report.py). I10 never stands twice on a line that had a code replaced. A line with no code at all is
    # skipped as before: there is nothing to change. When I10 is not in the list (_instead is empty) every line is built exactly as before 11/25/2026.
    _instead = DX.get(DX_INSTEAD); dx_replaced = False
    _first_car = first_carrier(ctx); no_mod25 = []      # 11/25/2026 (William, Humana): the add-on line of a Humana chart goes in without modifier 25 - NO_MOD25 above
    for _k, (c, cpos) in enumerate(zip(lines, lpos)):
        dcodes = []; _rep = False
        for code in c["dx"].split("^"):
            if _instead: code = code.strip()                  # 11/25/2026: under the rule a code is read as claimocity_dx.py caches it and the retry driver reads it - with a blank around it a code the list HAS would not be found, and would be replaced by I10 and asked for in the email. Without I10 in the list the field is read exactly as before.
            if DX.get(code): dcodes.append(DX[code])
            elif code:
                missing_dx.add(code)
                if _instead: dcodes.append(_instead); _rep = True
        if _rep:                                              # ONCE, at its first position: the feed's own I10 beside a replaced code, or two replaced codes, never give I10 twice
            dcodes = [x for i, x in enumerate(dcodes) if x != _instead or i == dcodes.index(_instead)]; dx_replaced = dx_replaced or _instead in dcodes[:12]      # 11/25/2026 (independent review): said only when I10 really stands on the charge - past the 12 codes a line carries it is cut like any other code, and the row, the DONE counter, the retry's line and William's email must not say 'entered with I10' for it
        if not dcodes: return None, "no usable dx for %s" % c["cpt"]
        mod = "mcode7" if c["cpt"] in MOD25 and len(cpts) > 1 else ""
        if mod and _first_car and _first_car in NO_MOD25.get(c["cpt"], ()): mod = ""; no_mod25.append(c["cpt"])
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
    # missing_dx: the feed's diagnosis codes AdvancedMD's list does not have; dx_instead (11/25/2026): the code that stands in their place on this visit - the
    # key is there only when a code was replaced (a row with missing_dx and no dx_instead had the code left off: an import from before that day, or I10 not in the list)
    # dob_note (William 11/25/2026, THE CHART'S OWN BIRTH DATE): how the feed's date compares with the chart's own - fixed words, never a date ("chart not read" when the
    # chart's answer could not be read). A note that cannot be made is left out; it never keeps a visit from going in
    try: _dn = dob_note(re.sub(r"\D", "", str(msg.get("dob") or ""))[:8], ctx.get("dob"), run_day().strftime("%Y%m%d"))      # None (the chart could not be read) is handed over as it is
    except Exception: _dn = ""
    return (create, body, plain), {"dos": dos, "dos_lines": [mdy(c["dos"][:8]) for c in lines], "cpts": cpts, "fac": fac, "pos": lpos[0], "pos_feed": pos, "pos_lines": lpos,
                            "pos_why": lwhy, "pos_kind": lkind, "pos_err": pos_err, "prof": prof, "prof_default": npi not in PROFILE and not initial, "msg_own": bool(own), "admit": admit, "missing_dx": sorted(missing_dx),
                            **({"dx_instead": DX_INSTEAD} if dx_replaced else {}), **({"dob_note": _dn} if _dn else {}),
                            # feed_building (11/25/2026): the feed's own name of a building the facility table does not know. Until then that name was in no register and no
                            # digest - only in the raw feed files - so nobody could add the building (ten 11/17/2026 visits went in with no facility); the digest names it now
                            **({"feed_building": " ".join(str(facname).split())[:80]} if (not fac and str(facname or "").strip()) else {}),
                            **({"no_mod25": no_mod25} if no_mod25 else {}),      # 11/25/2026 (William, Humana): the codes of this visit left WITHOUT modifier 25 because Humana is the chart's first plan
                            **({"stay": _stay} if _stay else {}),      # 11/25/2026 (inpatient rehab stays): the stay of a hospital visit from the hospital building - kind rehab | acute, the date of its initial visit ('' when none is in hand), the sign that showed a rehab stay
                            # 11/25/2026 (verification): the days its pos_err names, 'MM/DD/YYYY'. hospital_at61 = visits that stand at HCA REHAB / 61 and belong to the HOSPITAL stay this initial
                            # visit starts (pos61_monitor.py takes them out of the rehab visits at 61); mixed_at61 = visits at 61 behind which this follow-up went in at 21. Only on a row that says it
                            **({_at61[0]: _at61[1]} if _at61 else {}),
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
        if rf == REG: done |= {(r["feed_id"], None, None) for r in prior.get("skipped", []) if r.get("why") != NO_LINES_WHY}      # 11/25/2026: the row of a message WITHOUT a charge line names no visit - it never passes the patient's real messages over on a second start
        for _k in ("skipped", "failed", "created"):      # row by row and line by line: an odd row or line is skipped, the rows after it are still read
            _rows = prior.get(_k) if isinstance(prior, dict) else None
            for r in (_rows if isinstance(_rows, list) else []):
                try: _lns = r.get("lines" if _k != "created" else "tie_lines"); _rp = r.get("pid")      # a created row keeps "tie_lines" when the feed sent its message from two buildings (review C1)
                except Exception: continue
                # 11/25/2026 (verification): the days of visits at HCA REHAB / 61 that this row NAMED for William (its pos_err) - no later row names them again. Entry by entry: an odd one is passed over
                for _d in ([x for _f in ("hospital_at61", "mixed_at61") for x in (r.get(_f) if isinstance(r.get(_f), list) else [])] if _k == "created" else []):
                    if isinstance(_rp, str) and _rp and isinstance(_d, str) and _mdy_day(_d) is not None: SAID_61.setdefault(_rp, set()).add(_d)
                for _ln in (_lns if isinstance(_lns, list) else []):
                    if isinstance(_ln, (list, tuple)): prior_seen.append((_rp, list(_ln)))
        # 11/25/2026 (inpatient rehab stays, review): the hospital visit lines that run passed over under the same-day rule (its "same_day": chart -> [[code, DOS]]) are read by
        # the stay rule in every later run (SAME_DAY). Entry by entry: an odd one is passed over, it never stops the import. A second start under this stamp keeps its own list.
        _sdr = prior.get("same_day") if isinstance(prior, dict) else None
        for _rp, _lns in (_sdr.items() if isinstance(_sdr, dict) else ()):
            for _ln in (_lns if isinstance(_lns, list) else ()):
                if isinstance(_rp, str) and _rp and isinstance(_ln, (list, tuple)) and len(_ln) >= 2 and isinstance(_ln[0], str) and isinstance(_ln[1], str) and _ln[0] in HOSP_VISIT:
                    for _m in ((SAME_DAY, SAME_DAY_NEW) if rf == REG else (SAME_DAY,)): _m.setdefault(_rp, set()).add((_ln[0], _ln[1]))
    # deceased guard before any write: a DOS after the cached date of death is never entered (William's standing rule)
    # 11/25/2026 (the second verification of the death check - ONE cache): until then the FIRST cache file found was read and no other, and a day counted only as
    # YYYY-MM-DD. A workspace holds up to three files (the one DECEASED_CACHE names or the guard's own, the feed's file of before, the register): a day only another
    # file held, a day written as eight digits, and a death whose day is the privacy gate's placeholder (the repository's copy) all read as 'no death', and the visit
    # went in. Now EVERY file is read; a chart's EARLIEST day in any of them counts (it keeps more out); a file that cannot be read is passed over; and a chart with a
    # death on record whose day is in no file (_dc_lost) has nothing entered until somebody names the day (_asked_dod below).
    # 11/25/2026 (the independent check of that round, finding 7): 'every file' left one out - the copy at the OLD path, ../practices/ehpa/registers/, where a run's
    # lesson had told runs to put one. The guard carries that copy's days into its cache during this very process, but only at its first answer - and for a chart
    # the import asks nothing about it never answers: both visits of such a chart were ENTERED. So the import reads the files the guard knows: the one the
    # environment names, the guard's own (CACHE), every file on the guard's own list of other cache files (_others - it only looks whether each is a file) when
    # the guard can be loaded, the two relative names of before, and the old path seen from this helper's own folder. Nothing here writes: the guard's _load, which
    # carries, is not called for this - a dry run still writes nothing.
    # 11/25/2026 (the third round): what the files say TOGETHER is worked out by ONE function, death_read (above) - it holds the two readings: which value is a
    # day, and which a death on record whose day cannot be read (death_unread). The order the files are read in means nothing to it.
    _dcf = set(); _osm = __import__("os"); _dcg = ""; _dco = []; _dct = []
    try:
        _dgm = __import__("deceased_guard"); _dcg = getattr(_dgm, "CACHE", "") or ""
        _dco = [_x for _x in (getattr(_dgm, "_others")() or [])] if callable(getattr(_dgm, "_others", None)) else []
    except Exception: pass
    try: _dcold = _osm.path.join(_osm.path.dirname(_osm.path.dirname(_osm.path.abspath(__file__))), "practices", "ehpa", "registers", "deceased_cache.json")
    except Exception: _dcold = ""
    for _p in [_osm.environ.get("DECEASED_CACHE", ""), _dcg] + _dco + ["deceased_cache_local.json", "registers/deceased_cache.json", _dcold]:
        if not isinstance(_p, str) or not _p or not _osm.path.isfile(_p) or _osm.path.realpath(_p) in _dcf: continue
        _dcf.add(_osm.path.realpath(_p))
        try: _dct.append(json.load(open(_p)))
        except Exception: continue
    _dc, _dc_lost = death_read(_dct)
    def _dod(pid):
        return (_dc.get(re.sub(r"\D", "", pid)) or {}).get("dod") or None
    # CCM AND A PATIENT WHO HAS PASSED AWAY - William's word of 11/25/2026: ("run a death check on all ccm charges to make sure there is no date of death prior to billing the ccm charges, there
    # already is a date of death check in the billing runs but verify that no patient dies and a new set of ccm charges go in month after month after the patient has died").
    # The check above reads only the cache: a death an EARLIER look-up found. A patient who died since had the month's CCM entered; the insurance check after the import
    # (claimocity_verify.py) then asked Medicare, found the death and wrote a hold - which stops nothing in AdvancedMD - so the charge went out with the claim run and was
    # written off afterwards (four charts, August 2026: the 'after-death' cards on the board). From 11/25/2026 Medicare is asked BEFORE a CCM message is entered, with the
    # deceased guard's own check (deceased_guard.check as a care-management claim: a fresh Medicare answer when the kept one is older than 30 days or was asked before the
    # CCM date; the answer is kept, so the insurance check after the import pays for no second one). A date of death before the CCM date = the message is not entered,
    # this month and every month after (a death stays in the cache for good). A look-up that fails never keeps a charge out - the guard's rule: only a date of death
    # blocks - the message is entered, the DONE line says so, and the insurance check asks again. A dry run asks nothing new (cache only).
    # 11/25/2026 (the second verification): the guard keeps ONE cache now and the feed's helpers no longer name a file of their own (the import used to point the
    # guard at deceased_cache_local.json here). And a chart with a death ON RECORD whose day nobody can read (lost) is asked about before ANY message of it is
    # entered - as an ordinary claim: the guard asks whatever the payer and the code for such a chart - and is HELD unless a day is named: the guard raises DayLost
    # when neither AdvancedMD nor the vendor names one, and Medicare's 'no death on record' does not undo a death another source put on record. A held message is not
    # entered; its row carries DEATH_DAY_WHY, its codes and its dates of service, and the retry step hands it to the import again - once a run, until a register
    # shows it entered or kept out for good (claimocity_retry_dx.py; the independent check of that round, finding 3).
    # 11/26/2026 (the guard's sixth round - William: "Medicare decides: bill"; "Bill it, flag it"): MEDICARE'S ANSWER DECIDES. A message of such a chart is HELD only
    # when the guard raised DayLost (Medicare could not be asked and no day is known - the one wait left) or the entry still holds a death whose day cannot be read
    # and Medicare did not say 'no death' in this process (the guard's _NONE_SAID; a guard from before has none: held, as before). When Medicare shows no death the
    # message is ENTERED, and the guard's own line for the top of the report ('TOP OF REPORT: pat<chart>: ...') goes into the DONE line's counts, the import's log
    # and the register, from which the digest says it at the top. The same for a chart AdvancedMD marks deceased with no date that the guard named so: its
    # 'deceased' mark no longer holds the message below (_dg_named).
    _ccm_asked = set(); _dd_held = set()
    def _dg_named(pid):
        """(11/26/2026) True when the deceased guard named this chart for the top of the report in this process: Medicare's answer decided for a chart marked
        deceased with no date, or for one whose recorded death has a day that cannot be read (billed), or such a mark could not be put to Medicare (billed,
        flagged). It never raises: what cannot be read is no."""
        try:
            _l = getattr(__import__("sys").modules.get("deceased_guard"), "LOG", None)
            return isinstance(_l, list) and any(isinstance(x, str) and x.startswith("TOP OF REPORT: pat%s: " % re.sub(r"\D", "", pid)) for x in _l)
        except Exception: return False
    def _asked_dod(pid, msg, lost=False):
        """-> (the day or None, held). lost: a death is on record for the chart and its day is in no cache file."""
        num = re.sub(r"\D", "", pid); _ccm = any(c["cpt"] in CCM for c in msg["FT1"])
        try:
            import deceased_guard as _dg
            _d8 = max(c["dos"][:8] for c in msg["FT1"] if lost or c["cpt"] in CCM); _proc = "99487" if _ccm else None
            _lg = getattr(_dg, "LOG", None); _n0 = len(_lg) if isinstance(_lg, list) else 0
            if (num, _d8, _proc) not in _ccm_asked:
                _ccm_asked.add((num, _d8, _proc))
                if _ccm: stats["CCM: date of death looked up before the entry (William 11/25/2026)"] += 1
                _dg.check(num, mdy(_d8), None, _proc, allow_lookup=not dry)
            v = (_dg._load() or {}).get(num); v = v if isinstance(v, dict) else {}
            d = death_day(v.get("dod"))
            if d:
                _dc[num] = dict(v, dod=d); _dc_lost.discard(num); return d, False
            _none = getattr(_dg, "_NONE_SAID", None)      # (11/26/2026) the charts Medicare named no death for in this process
            if (lost or death_unread(v.get("dod"))) and not (isinstance(_none, set) and num in _none): return None, True      # a death on record without a day that can be read, and Medicare did not say 'no death' in this process (death_unread says what such a value is; any other value in the day's place is no dod)
            # the guard answered 'not blocked' and its own log says nobody answered the look-up: the charge goes in (only a date of death keeps one out) and the
            # run SAYS so - until 11/25/2026 (the second verification) only a look-up that raised was counted, and this one went in with no word
            if isinstance(_lg, list) and any(isinstance(x, str) and "UNVERIFIED" in x for x in _lg[_n0:]):
                stats["CCM entered with the date of death UNVERIFIED (nobody answered the look-up) - the insurance check asks again"] += 1
            return None, False
        except Exception as e:
            if lost or type(e).__name__ == "DayLost": return None, True
            stats["CCM death check could not be made before the entry (%s) - entered; the insurance check asks again" % type(e).__name__] += 1
            return None, False
    # nursing and hospital visits of THIS batch per chart: the place-of-service rule reads them together with the chart's own history,
    # so the result does not depend on the order the messages are entered in
    try:
        for _m in PARSED:
            if not isinstance(_m, dict) or _m.get("pid") is None: continue      # 11/25/2026: a message without a patient id (no PID line - no name, no date of birth) is nobody's visit; passed over here too, so it cannot switch the visit rule off for the whole batch
            _p = chart_of(_m)
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
        print("POS RULE: batch visit list not built (%s) - nursing VISIT lines stay at the feed's 31 this run (POS RULE NOT APPLIED); CCM lines are 32 without it" % BATCH_NF_ERR[0])
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
    _dobs = {}      # William 11/25/2026 (THE CHART'S OWN BIRTH DATE): chart -> the dob_note words of the visits this run enters or tries to enter (a dry run: would enter), for the ONE line at the end
    if BATCH_NF_ERR[0]: stats["POS RULE: batch visit list not built - nursing visit lines kept at the feed's 31 (CCM lines 32)"] += 1
    # A PROVISIONAL ROW (confirm review F5): before the call that carries the quality line, a failed row {quality_unknown, provisional} is written to
    # the register. When the answer comes and the visit's outcome is recorded, that row goes again (_unprov). When the run is cut while the call is
    # out (or an error stops the visit's handling after it), the row stays: the next start knows a line may exist that no row records - that visit is
    # for William (section 6's own rule for a call nobody saw the end of), so the run adds no further line; the next run probes (11/12/2026: the code
    # never switches itself off - one line a run until one is billed).
    _prov = [None]
    def _unprov():
        if _prov[0] is not None: reg["failed"][:] = [x for x in reg["failed"] if x is not _prov[0]]; _prov[0] = None
    for msg in PARSED:
        # 11/25/2026 (feed review, finding 6 - older than the CCM change): the parser keeps every MSH block, so a message with no FT1 line arrives with an empty
        # FT1 list and one with no PID line with no patient id at all. Both used to stop the whole import step right here (IndexError / KeyError, outside the
        # per-message guard below): the ingest ended 'STEP FAILED: import', the file was not registered, and every later run read it again and stopped at the same
        # message. There is nothing to enter in such a message: it is passed over and counted, and the messages after it go in. Where a feed id exists ONE skipped
        # row with the plain reason is kept (never twice; never a reason to pass the patient over - see the same-stamp rule above).
        fid = msg.get("pid") if isinstance(msg, dict) else None; _prov[0] = None; _built = None      # _built (verification): the chart and the lines of a visit this run built and has not seen stored yet
        if one and fid != one: continue
        if fid is None: stats[NO_PID_WHY] += 1; continue
        if not msg.get("FT1"):
            stats[NO_LINES_WHY] += 1
            if fid:
                _p0 = chart_of(msg)
                _row = {"feed_id": fid, "pid": _p0 if isinstance(_p0, str) else None, "why": NO_LINES_WHY}
                if _row not in reg["skipped"]: reg["skipped"].append(_row)      # reaches the file with the next write, as every skipped row does (a dry run writes nothing)
            continue
        mkey = (fid, mdy(msg["FT1"][0]["dos"][:8]), tuple(sorted(c["cpt"] for c in msg["FT1"])))
        if mkey in done or (fid, None, None) in done: stats["already created"] += 1; continue
        pid = chart_of(msg)
        if not pid: stats["no chart"] += 1; continue
        if n >= limit: break
        try:
            dod = _dod(pid); _dod_src = "deceased cache"; _lost = re.sub(r"\D", "", pid) in _dc_lost; _held = False
            if not dod and (_lost or any(c["cpt"] in CCM for c in msg["FT1"])):      # a CCM message, or a chart whose day of death is lost: asked before the entry (_asked_dod above)
                dod, _held = _asked_dod(pid, msg, _lost)
                _dod_src = "Medicare, asked because the day on record could not be read" if _lost else "Medicare, asked before this CCM charge was entered - William 11/25/2026"
            # (11/25/2026, the independent check of the second round, finding 3: both rows below name the VISIT - its codes and, under dos_lines, each line's own date of
            #  service as MM/DD/YYYY, the way the created rows do. claimocity_retry_dx.py matches them by that: it hands a held visit over once a run, and leaves it alone
            #  for good once a later register shows the same visit kept out 'DOS after date of death'. The second row used to name the feed patient only.)
            _vis = {"cpts": [c["cpt"] for c in msg["FT1"]], "dos_lines": [mdy(c["dos"][:8]) for c in msg["FT1"]]}
            if _held:
                stats[DEATH_DAY_WHY] += 1; _dd_held.add(pid)
                reg["skipped"].append(dict({"feed_id": fid, "pid": pid, "why": DEATH_DAY_WHY}, **dict(_vis, lines=seen_lines(msg))))
                if not dry: json.dump(reg, open(REG, "w"), indent=1)
                continue
            if dod and any(c["dos"][:8] > dod.replace("-", "") for c in msg["FT1"]):
                stats["DOS after date of death - not entered"] += 1; reg["skipped"].append(dict({"feed_id": fid, "pid": pid, "why": "DOS after date of death %s (%s) - never billed" % (dod, _dod_src)}, **_vis))
                if not dry: json.dump(reg, open(REG, "w"), indent=1)      # a dry run writes nothing (11/10/2026, challenge review): its register would make the live run of the same stamp skip whole patients
                continue
            ctx = chart_ctx(pid); ctx["pid"] = pid
            if ctx.get("deceased") and death_day(ctx.get("deceased")) is None and _dg_named(pid):      # (11/26/2026, William: "Medicare decides: bill") a mark with no date the guard put to Medicare's answer - or could not, "Bill it, flag it" - and named for the top of the report: entered
                stats["deceased mark with no date - Medicare decided, entered (William 11/26/2026)"] += 1
            elif ctx.get("deceased"):
                stats["deceased chart - held"] += 1; reg["skipped"].append({"feed_id": fid, "pid": pid, "why": "deceased flag on chart - William"}); continue
            body, info = build(msg, ctx)
            if body is None:
                stats["skip: " + info] += 1
                if info != "all lines already in AMD": stay_not_entered(ctx, [(c["cpt"], mdy(c["dos"][:8])) for c in msg["FT1"]])      # (verification) an initial hospital visit the import could not build is NOT entered: no follow-up of its stay goes in at 61 behind it
                reg["skipped"].append(dict({"feed_id": fid, "pid": pid, "why": info}, **(_vis if info == "all lines already in AMD" else {"lines": seen_lines(msg)}))); continue      # (11/25/2026, the third round: the 'already' row names the VISIT too - its codes and dates of service, as the two rows above do: claimocity_retry_dx.py ends the retry of a held visit by it, also where the retry's own batch file did not travel)
            n += 1
            if not dry: _built = (ctx, list(zip(info["cpts"], info.get("dos_lines") or [info["dos"]] * len(info["cpts"]))))      # a dry run sends nothing: what it built stands as what a live run would enter
            if info.get("dob_note"): _dobs.setdefault(pid, set()).add(info["dob_note"])      # for the BIRTH DATES line; the row itself carries the words
            if info.get("pos_err"): print("POS RULE NOT APPLIED", pid, info["dos"], info["cpts"], info["pos_err"])
            if info.get("msg_own") is False and not info.get("pos_err"): print("POS CHECK not own message", pid, info["dos"], info["cpts"], "the raw files gave no single answer for this message - where its copies differ: %s; for William" % (info.get("msg_fallback") or "the patient's last-read values"))
            if info.get("prof_default"): print("POS CHECK clinician not known", pid, info["dos"], info["cpts"], "the feed message names no clinician id the profile table has - entered under the physician profile; for William")
            if info.get("prof_feed"): print("INITIAL VISIT under the physician", pid, info["dos"], "- the feed named", info["prof_feed"])      # William 11/10/2026: every initial nursing-facility visit is his
            if not info.get("fac"):      # 11/25/2026 (review): the words follow what was sent - a CCM line of such a message is at 32, not "at the feed's place of service" (the run copies this line to the top of the report)
                _cc = sorted({str(p_) for c_, p_ in zip(info["cpts"], info["pos_lines"]) if c_ in CCM}); _oth = any(c_ not in CCM for c_ in info["cpts"])
                print("POS CHECK no facility", pid, info["dos"], info["cpts"], "the message's building is not in the facility table - entered without a facility%s; for William" % (
                    (": its CCM line(s) at %s (William 11/25/2026: a CCM line is never 31)%s" % ("/".join(_cc), ", every other line at the feed's place of service" if _oth else "")) if _cc else " at the feed's place of service"))
            if dry:
                stay_entered(ctx, list(zip(info["cpts"], info.get("dos_lines") or [info["dos"]] * len(info["cpts"]))))      # (second round) a dry run sends nothing: what it built stands as what a live run would enter - and a skipped copy behind it does not take that back either
                print("DRY", pid, info); stats["dry"] += 1; stats["dry quality"] += 1 if info.get("quality_codes") else 0; stats["dry mvp"] += 1 if info.get("mvp_codes") else 0; count_pos(info, stats)
                if info.get("quality_skipped") == "hospital": stats["quality code not added: hospital visit (hospital visits are not coded in this version)"] += 1
                continue
            create, body, plain = body
            r0 = amd.post(create, timeout=120)
            vm = re.search(r'<visit id="(vst\d+)"', r0)
            if not vm:
                quality_undo(info, pid, fid); mvp_undo(info); stay_not_entered(*_built); _built = None      # (verification) not entered: what build() noted of it for the stay rule is taken back
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
                # is sent again, no further line is tried in this run, and William looks at that visit. The code is NOT off: it probes from the next run (11/12/2026).
                if info.get("mvp_codes"):      # it carried the M0004 line too: M0004 probes from the next run as well (the failed row says so to the next run)
                    info["mvp_codes"] = []; info["mvp_tried"] = info.get("mvp_fee") or "0.00"; MVP["off"] = MVP["off"] or "this run: a call that carried M0004 ended in an error"
                    mvp_probe_now("a call that carried M0004 ended in an error; nobody knows what AdvancedMD kept of that visit - William looks (chart %s, visit %s, %s)" % (pid, vm.group(1), __import__("os").path.basename(REG)))
                _fee0 = info.get("quality_fee"); _yr = str(info.get("quality_dos") or info["dos"])[-4:]; info["quality_codes"] = []; info["quality_tried"] = _fee0
                QUALITY["refused"].add((pid, _yr)); QUALITY["done"].add((pid, _yr)); QUALITY["off"] = QUALITY["off"] or "this run: a call that carried the code ended in an error (%s)" % type(e).__name__
                quality_probe_now("a call that carried the quality line ended in an error; nobody knows whether AdvancedMD kept that visit - William looks (chart %s, visit %s, %s)" % (pid, vm.group(1), __import__("os").path.basename(REG)))
                quality_fault_visit(pid, vm.group(1), _fee0, info.get("quality_dos") or info["dos"], "error", str(e))      # K11: listed as stuck at once - this run's inspector step looks whether the Claim Inspector holds it
                stats["error"] += 1; stats["QUALITY CODE: a call that carried the line ended in an error - William looks at that visit"] += 1
                reg["failed"].append({"feed_id": fid, "pid": pid, "info": info, "lines": seen_lines(msg), "empty_visit": vm.group(1), "quality_unknown": _fee0, "err": str(e)[:400]}); print("ERR", pid, str(e)[:200])
                json.dump(reg, open(REG, "w"), indent=1); continue
            if ("Fault" in r or 'success="0"' in r) and info.get("mvp_codes"):
                # A visit that carried 1123F AND M0004 was refused (8.4). The visit always goes in: once a fresh read of the chart (three tries) shows nothing
                # of it stored, the SAME visit goes in with the 1123F line only - that form is proven. Accepted: M0004 was the cause - M0004 probes
                # (one M0004 line a run in all until one is billed; 11/12/2026). Refused too: M0004 is not blamed - the block below reads the chart again and enters the
                # visit without the line, and the refusal counts against 1123F. The chart shows part of the visit, or cannot be read: nothing is tried
                # here, the block below leaves that visit for William as it always did, and M0004 probes from the next run.
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
                    mvp_probe_now("AdvancedMD refused a visit that carried M0004 and the chart did not show it free of that visit - William looks (chart %s, visit %s, %s)" % (pid, _vid, _wreg))
                    stats["OPTION CODE M0004: a visit that carried it was refused and the chart shows part of it or could not be read"] += 1
                else:
                    try: r = amd.post(re.sub(r'<charge id=""(?:(?!</charge>).)*proccode="%s"(?:(?!</charge>).)*</charge>' % MVP_PCODE, "", body).replace("%VISIT%", _vid), timeout=180)      # the same request with the M0004 line taken out
                    except Exception as e:      # the 1123F-only form ended in an error (a time-out): as for any call that carried the 1123F line - nothing is sent again, William looks at that visit, and both codes probe from the next run
                        _fee0 = info.get("quality_fee"); _yr = str(info.get("quality_dos") or info["dos"])[-4:]; info["quality_codes"] = []; info["quality_tried"] = _fee0
                        QUALITY["refused"].add((pid, _yr)); QUALITY["done"].add((pid, _yr)); QUALITY["off"] = QUALITY["off"] or "this run: a call that carried the code ended in an error (%s)" % type(e).__name__
                        quality_probe_now("a call that carried the quality line ended in an error; nobody knows whether AdvancedMD kept that visit - William looks (chart %s, visit %s, %s)" % (pid, _vid, _wreg))
                        quality_fault_visit(pid, _vid, _fee0, info.get("quality_dos") or info["dos"], "error", str(e))      # K11: listed as stuck at once
                        MVP["off"] = MVP["off"] or "this run: a visit with M0004 was refused"
                        mvp_probe_now("AdvancedMD refused a visit that carried M0004, and the same visit sent with the 1123F line only ended in an error - William looks (chart %s, visit %s, %s)" % (pid, _vid, _wreg))
                        stats["error"] += 1; stats["QUALITY CODE: a call that carried the line ended in an error - William looks at that visit"] += 1
                        _unprov(); reg["failed"].append({"feed_id": fid, "pid": pid, "info": info, "lines": seen_lines(msg), "empty_visit": _vid, "quality_unknown": _fee0, "err": str(e)[:400]}); print("ERR", pid, str(e)[:200])
                        json.dump(reg, open(REG, "w"), indent=1); continue
                    if "Fault" in r or 'success="0"' in r: info["mvp_form_refused"] = True      # refused with the 1123F line only as well: M0004 is not the cause (the block below)
                    else:
                        info["mvp_refused"] = _mwhy; MVP["off"] = MVP["off"] or "this run: AdvancedMD refused a visit that carried M0004"
                        mvp_probe_now("AdvancedMD refused a visit that carried M0004 and took it with the 1123F line only (chart %s, visit %s, %s)" % (pid, _vid, _wreg), _mwhy)
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
                if _stored:      # the fault came, but the chart shows the visit (or cannot be read): NOT sent again - William looks at that visit. The code is not off: it probes from the next run (11/12/2026)
                    QUALITY["refused"].add((pid, _yr)); QUALITY["done"].add((pid, _yr))
                    QUALITY["off"] = QUALITY["off"] or "this run: a visit with the code was refused and the chart could not be shown free of it"
                    quality_probe_now(("AdvancedMD answered a fault to a visit that carried the quality line and the chart could not be read afterwards - William looks (chart %s, visit %s, %s)"
                        if any(isinstance(x, str) for x in _stored) else "AdvancedMD answered a fault but kept the visit - William looks (chart %s, visit %s, %s)") % (pid, vm.group(1), __import__("os").path.basename(REG)))
                    quality_fault_visit(pid, vm.group(1), _fee0, info.get("quality_dos") or info["dos"], "unread" if any(isinstance(x, str) for x in _stored) else "kept",
                                        "refused with the quality line; not sent again because the chart shows %s - William looks at that visit: %s" % (_stored, _why))      # K11: listed as stuck at once
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
                stay_not_entered(*_built); _built = None      # (verification) AdvancedMD did not take the visit: nothing of it stands on the chart - the stay rule of this run no longer counts it as built
                stats["FAULT"] += 1; _unprov(); reg["failed"].append({"feed_id": fid, "pid": pid, "info": info, "lines": seen_lines(msg), "empty_visit": vm.group(1), "err": re.sub(r"\s+", " ", r[:600])})
                print("FAULT", pid, info["dos"], info["cpts"], re.sub(r"\s+", " ", r[:300]))
            else:
                if _built: stay_entered(*_built)      # (second round) ... and stands for the rest of the run: the same visit sent again in a message that is skipped does not take it back
                _built = None      # stored: what build() noted of this visit for the stay rule stands, whatever happens to the calls behind it
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
                    if not _mc:      # the M0004 line was not shown stored: M0004 probes (11/12/2026)
                        mvp_undo(info); info["mvp_not_stored"] = info.get("mvp_fee") or "0.00"; info["mvp_codes"] = []; stats["OPTION CODE M0004: AdvancedMD stored the visit WITHOUT the M0004 line"] += 1
                        MVP["off"] = MVP["off"] or "this run: AdvancedMD stored a visit without its M0004 line"
                        mvp_probe_now("AdvancedMD stored a visit without its M0004 line - William looks (chart %s, visit %s, %s)" % (pid, vid.group(1) if vid else "?", __import__("os").path.basename(REG)))
                    elif not _qc:    # the M0004 line stands on a claim without the 1123F line: William looks at that visit, and M0004 probes
                        MVP["off"] = MVP["off"] or "this run: AdvancedMD stored the M0004 line of a visit without its 1123F line"
                        mvp_probe_now("AdvancedMD stored the M0004 line of a visit without its 1123F line - William looks (chart %s, visit %s, %s)" % (pid, vid.group(1) if vid else "?", __import__("os").path.basename(REG)))
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
            if _built: stay_not_entered(*_built)      # (verification) a call that ended in an error before the visit was seen stored: nobody knows whether AdvancedMD kept it - for the stay rule it is NOT entered (the safe side: the rest of its stay goes in as before)
            stats["error"] += 1; reg["failed"].append({"feed_id": fid, "pid": pid, "lines": seen_lines(msg), "err": str(e)[:400]}); print("ERR", pid, str(e)[:200])
            if not dry: json.dump(reg, open(REG, "w"), indent=1)      # a dry run writes nothing (see the date-of-death skip above)
        if n % 25 == 0 and n: print("progress", n, dict(stats))
    # 11/25/2026 (inpatient rehab stays, review): the hospital lines this run passed over under the same-day rule go into its register - chart ids, codes and dates of service
    # only - so that the stay rule of every later run still reads them. The key is there only when there is such a line
    if SAME_DAY_NEW: reg["same_day"] = {_p: sorted([_c, _d] for _c, _d in _v) for _p, _v in sorted(SAME_DAY_NEW.items(), key=lambda t: str(t[0])) if isinstance(_p, str) and _p}
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
    # 11/26/2026 (the guard's sixth round - William: "Medicare decides: bill", "Bill it, flag it"): the charts the deceased guard named for the top of the report in
    # this run - its own lines, word for word: chart ids and fixed words only. Into the register (the digest says each at the top), into the DONE line's counts and,
    # below, into the import's log. The key is there only when there is such a line.
    try:
        _dtl = getattr(__import__("sys").modules.get("deceased_guard"), "LOG", None)
        _dtop = list(dict.fromkeys(x for x in (_dtl if isinstance(_dtl, list) else []) if isinstance(x, str) and re.fullmatch(r"TOP OF REPORT: pat[0-9]{1,12}: [^\r\n]{1,300}", x)))
    except Exception: _dtop = []
    if _dtop: reg["death_top"] = _dtop; stats["date of death: chart(s) for the TOP OF THE REPORT (Medicare decided, or could not be asked - entered)"] = len(_dtop)
    if not dry: json.dump(reg, open(REG, "w"), indent=1)
    try: print(quality_log(_qn, dry))
    except Exception as e: print("QUALITY 1123F: this line could not be built (%s) - read quality_gate in the import register" % type(e).__name__)
    try: print(mvp_log(_mn, dry))
    except Exception as e: print("QUALITY M0004: this line could not be built (%s) - read mvp_gate in the import register" % type(e).__name__)
    # William 11/25/2026 (THE CHART'S OWN BIRTH DATE): ONE line that names, by chart id only, the charts whose feed date is not the chart's own - nothing when all are
    # the same. It stands BEFORE the place-of-service lines: the ingest shows the last three log lines of this step, and those stay POS CHECK, POS RULE and DONE; a run
    # reads this one by its start (grep '^BIRTH DATES' in the import's log), like the two QUALITY lines above
    try:
        _bl = birth_dates_line(_dobs)
        if _bl: print(_bl)
    except Exception as e: print("BIRTH DATES: this line could not be built (%s) - read dob_note in the rows of the import register" % type(e).__name__)
    # 11/25/2026: the date-of-death checks of this run (the care-management check before the entry) - free at AdvancedMD or sent to the vendor; before the
    # place-of-service lines, like the line above
    _dl = death_check_line(__import__("sys").modules.get("deceased_guard"))
    if _dl: print(_dl)
    # 11/25/2026 (the second verification): the visits kept out because a death is on record for the chart and nobody can name its day - chart ids and counts only.
    # (The independent check of that round, finding 13: the line said 'Medicare named none either' - also when nobody had been asked: a dry run, a workspace with no
    # guard module. 'nobody named the day' is true of every such visit. The third round: it said the retry hands the visit over 'in every later run' - the retry
    # stops once a register shows the visit entered or kept out for good.)
    if _dd_held: print("DEATH DAY UNKNOWN: %d visit(s) on %d chart(s) - %s (nobody named the day) - TOP OF THE REPORT: merge the deceased cache from Drive; the retry step hands each visit to the import again once a run, until a register shows it entered or kept out for good: %s" % (
        stats[DEATH_DAY_WHY], len(_dd_held), DEATH_DAY_WHY, ", ".join(sorted(_dd_held))))
    for _x in _dtop: print(_x)      # 11/26/2026: the guard's own lines for the top of the report, word for word (above)
    _pk = lambda w: sum(v for k, v in stats.items() if k.startswith(w))
    if _pk("ADVANCEDMD DID NOT KEEP") or _pk("feed message not matched") or _pk("clinician id of the feed message") or _pk("visit entered with NO facility"):
        # one SHORTALL line, like the next one (90 characters with one-digit counts, 110 with six-digit counts in all four places)
        print("POS CHECK: stored another POS x%d; not own message x%d; clinician unknown x%d; no facility x%d" % (
            _pk("ADVANCEDMD DID NOT KEEP"), _pk("feed message not matched"), _pk("clinician id of the feed message"), _pk("visit entered with NO facility")))
    # one SHORTALL line (the ingest shows 110 characters of each of the last three log lines): 110 characters with one-digit counts. Its last two numbers (11/25/2026) are
    # the inpatient rehab visits of this run: entered at HCA REHAB / 61, and visits of a rehab stay kept at 21 - with larger counts the DONE line below carries them in full
    print("POS RULE: CCM 32 x%d, CCM 31 x%d, visits 32 x%d, visits 31 x%d, not applied x%d, unknown bldg x%d, rehab 61 x%d/21 x%d" % (
        _pk("POS 32 CCM"), _pk("POS 31 CCM"), _pk("POS 32 nursing"), _pk("POS 31 nursing"), _pk("POS RULE NOT APPLIED"), _pk("POS RULE: building"), stats[REHAB_61_COUNT], stats[REHAB_21_COUNT]))      # "CCM 31" is 0 since 11/25/2026 - anything else is an old copy of the rule
    print("DONE", dict(stats))
if __name__ == "__main__": main()
