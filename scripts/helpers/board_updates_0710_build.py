# PLAIN ENGLISH (Insurance Refresh Board answers for the 3am ET 9/15 run - inbox file builder)
# Decides: Nothing. Writes board_updates_2026-09-15T0710Z.json with the results of this run's board actions (Greaves
#   corrected claim, AET12 verdict on run 1700193, Unbilled prior-payor re-release, ERA step numbers, Availity status)
#   as update ops (never set) with appends keyed by src+when so a re-applied file cannot duplicate them.
# Never touches: the board database directly (the page ingests this file from the Drive board inbox).
import json, os, datetime
S = "2026-09-15T0710Z"; NOW = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
SRC = "3am ET 9/15 columns run (ehpa cloud)"; W = "9/15"
def chk(ok, result, src=SRC): return {"ok": ok, "result": result, "src": src, "when": W}
def note(text): return {"at": NOW, "text": text, "who": "Claude"}
ops = []
def row(id, notes=None, checks=None, api=None, status=None, need=None, extra=None):
    op = {"op": "update", "collection": "items", "id": id, "append": {}}
    if notes: op["append"]["notes"] = notes
    if checks: op["append"]["checks"] = checks
    if api: op["append"]["api"] = api
    d = {}
    if status: d["status"] = status
    if need: d["need"] = need
    if extra: d.update(extra)
    if d: op["set"] = d
    ops.append(op)
def load(p):
    try: return json.load(open(p))
    except Exception: return None
def f(x):
    try: return float(x or 0)
    except Exception: return 0.0
eb = load("era_checks_before_%s.json" % S) or []; ea = load("era_checks_after_%s.json" % S) or []
nb, ab = len(eb), round(sum(f(c.get("unpostedamount")) for c in eb), 2)
na, aa = len(ea), round(sum(f(c.get("unpostedamount")) for c in ea), 2)
fb = load("registers/era_fallback_%s_live.json" % S) or []
import collections
fo = collections.Counter((r.get("outcome") or "?") for r in fb) if isinstance(fb, list) else {}
fposted = round(sum(f(r.get("pay")) for r in fb if isinstance(fb, list) and r.get("outcome") == "posted"), 2) if isinstance(fb, list) else 0
clear_txt = open("era_chain_0710.log").read() if os.path.exists("era_chain_0710.log") else ""
import re
dism = re.findall(r'dismiss(?:ed)?[^\n]*', clear_txt)
ub = load("registers/unbilled_release_%s.json" % S) or {}
nrel = sum(len(c["visits"]) for c in ub.get("released", [])); nwo = ub.get("writeoffs", [])
cl = load("registers/greaves_fix_%s.json" % S) or {}

# ---------------- Greaves (William 06:52Z 'yes do that') ----------------
row("greaves-patient522-denials",
    notes=[note("3am ET 9/15 run, per your 'yes do that': (1) the 9/9/2026 WOINS $206 (wo22476007) on the 2/26/2026 99487 (charge 23340937, visit 19434042) was voided - the $206 came back on the INSURANCE balance (patient $0); (2) the Florida Blue plan ins9514111 member id changed XYL991586758 -> X3LM65856326 (the Michigan MA number Florida Blue echoed), patient order untouched (Medicare stays the chart default); (3) the claim went out as a CORRECTED claim, frequency 7 with the payer's claim number H100001346973572 (read from the $0 ERA payment AMD posted 9/9 from check 213403769) on sequence 1 -> HTTP 204, readback resubmissioncode 7 / origrefnum set / insbilled 0. It leaves on the next claim run. If Florida Blue answers CO-22 again with this id, the next step is Medicare primary per your note - say the word.")],
    checks=[chk("ok", "WOINS wo22476007 $206 voided; insurance balance 206.00, patient 0.00"),
            chk("ok", "BCBS plan ins9514111 subscribernum [member id] -> X3LM65856326 (updateinsurance success 1, readback ok)"),
            chk("ok", "frequency 7 + origrefnum H100001346973572 (payer ICN from the posted ERA payment) + chargerebill seq 1 -> 204; readback resub 7, insbilled 0, insbalance 206.00")],
    api=[{"at": NOW, "src": "AMD getchargedetaildataicd10 charge 23340937 - posted ERA payment element", "text": "<payment id=\"pay24634581\" paymentcode=\"PE\" date=\"09/09/2026\" amount=\"0.00\" checknumber=\"213403769\" carrierfid=\"6062\" origrefnum=\"H100001346973572\"> - the payer claim control number AMD stored with the $0 denial; used as origrefnum on the frequency-7 resend."}],
    need="Watching: 2/26/2026 99487 ($206) re-sent to Florida Blue 9/15 as a frequency-7 corrected claim with member [member id] and the payer claim number H100001346973572 (write-off voided per your OK). Nothing for William unless Florida Blue denies again - then Medicare primary per your note.")

# ---------------- AET12 verdict ----------------
row("aet12-carrier-cpid",
    notes=[note("3am ET 9/15 run: VERDICT on the AAR01-matched settings = NOT FIXED. getclaimrunstatus now lists claim run 1700193 (dated 2026-09-14 23:08 on AMD's clock, 59 claims sent, $11,756) - the 59 AET12 claims re-sent after you matched the carrier record to AAR01 - and Change Health front-end rejected all 59 again: PREF0288 INVALID PAYER ID/CPID 814723941 (TIN) + PREF0264 MISS/INVD PAYER DOC CONTRL NUM. Charge detail on all 68 AET12 charges: insbilled=1, datebilled 09/14/2026 = transmitted, not queued. Held open on the exclusion list (59 rows), NOT rebilled a 4th time. Your stated next step: suppress the provider loop on the AET12 carrier record and rebill again - say 'rebill' on this row when it is set. Also still unchecked from the 9/14 analysis: the EDI/Other tab's Box 33B supplemental number (qualifier EI = Tax ID prints as the payer id REF*EI), the IDs dialog and Claim Fields; an AMD support case for the 837 of run 1700193 names the segment carrying 814723941 definitively.")],
    checks=[chk("no", "Claim run 1700193 (59 AET12 claims, $11,756) rejected all 59 again: CH FH PREF0288 INVALID PAYER ID/CPID 814723941 + PREF0264 MISS/INVD PAYER DOC CONTRL NUM - the AAR01-matched settings did not change the transmitted payer id. 68 charges insbilled=1 datebilled 9/14/2026 (transmitted). Held, not rebilled.", SRC + " - claim run 1700193")],
    status="william",
    need="WILLIAM: run 1700193 rejected all 59 AET12 claims AGAIN after the AAR01-matched settings (PREF0288 TIN as payer id + PREF0264). Next step you named: suppress the provider loop on the AET12 carrier record, then say 'rebill' here and the next run re-sends all 59 (15 charts, $2,052.25 open). Candidates if that also fails: EDI/Other Box 33B supplemental number qualifier EI (prints the TIN as REF*EI), the IDs dialog, Claim Fields, or an AMD case for the 837 of run 1700193. 59 exclusion rows held open, not completed.")

# ---------------- Unbilled ----------------
row("unbilled-prior-payor-release-0915",
    notes=[note("3am ET 9/15 run: the 'payment from the prior payor is required' rows were back on the Unbilled snapshot at 07:35 UTC - 103 rows on 33 charts (the same charts released ~06:30 UTC; the snapshot regenerates while the primary claim is unanswered). Verified live again with one gettxhistory per chart: 99 rows primary-sent-and-unanswered (case b), 1 row Medicaid-paid 5/26/2026 (window open), 3 rows Medicare-paid 4/2025 crossover leftovers past the secondary window (Waldron 19398435 $33.94 + 19398478 $33.94, Plessy 19399445 $52.73) -> contractual WOINS with a dated note, then released. All 103 released (hideunbullablevisits success=1 x5). Unbilled 114 -> 11 (the 11 unbalanced-posting rows stay held). Expect these rows to re-queue every run until the primaries answer.")],
    checks=[chk("ok", "103 prior-payor rows verified live (33 charts) and released; 3 crossover leftovers written off WOINS ($120.61); Unbilled 114 -> 11")])
row("unbilled-unbalanced-postings-0915",
    checks=[chk("no", "Still 11 rows 'Payment reason codes are missing or do not balance' (Rylance, Kinross, Cogswell, Delmar, Simcoe x4, Rowantree N x2, Carrow) - held, not released; no captured call edits payment reason codes. William: re-post from the remit or say 'release' to hide them.")],
    status="william",
    need="WILLIAM: 11 Unbilled rows (2024 DOS) sit on 'Payment reason codes are missing or do not balance' - a 9/13 payment posted with no CARC on top of a reversed 5/31 write-off. No API call edits payment reason codes; they need the CARCs from the remit re-posted in Payment Entry, or your word to release (hide) them. $2,422.58 total per the 9/15 chat review.")

# ---------------- ERA ----------------
era_line = ("ERA step 5 (%s, run %s): %d unposted checks / $%.2f before -> %d / $%.2f after; era_post --all-unposted posted 0 visits (every money line is a reversal, orphan, procedure-mismatch or already-adjudicated line); manual fallback live outcomes %s, fallback posted $%.2f; era_clear %s; no new 835s in the Optum folder; locks release-expired sent; addpayments faults 0."
            % (SRC, S, nb, ab, na, aa, dict(fo), fposted, ("dismissed " + "; ".join(dism)[:200]) if dism else "0 dismissed, all held (reversal/orphan/unvalidated money lines)"))
row("era-manual-post-0912", checks=[chk("na", era_line, SRC + " - ERA step 5")])

# ---------------- Availity ----------------
row("availity-remits-backlog",
    checks=[chk("na", "No Availity PDF or Check/EFT export newer than the 0310Z pass in 'bht Optum era downloads' / 'treasury payments' (newest PDF 03:30Z, only availity_pdf.py landed after) - nothing new to parse or reconcile. The 0310Z run's Availity registers are in its state bundle (workspace_state_2026-09-15_0452UTC, 26 of 37 parts uploaded at 07:10Z) - this run restored the era_manual_register from GitHub main instead; live 'already posted' checks on the charge remain the double-posting guard.", SRC + " - ERA step 5(g)")])
row("availity-florida-blue-remits-0915",
    checks=[chk("na", "No new Florida Blue Availity files since the 0310Z pass; nothing posted this run. Note for the record: the payer claim number (ICN) of every ERA-posted line is readable from the charge's <payment origrefnum> element - the frequency-7 path for OA-18 duplicates (Denby 19426625/19426661) no longer needs the PDF.", SRC)])
row("denby-shana-duplicate",
    checks=[chk("na", "Not touched this run. The ICN needed for a frequency-7 correction is on the charge itself (getchargedetaildataicd10 <payment origrefnum>), proven on Greaves today - the next run that works this row reads it from the original Florida Blue posting instead of the Availity PDF.", SRC)])

out = {"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}
json.dump(out, open("board_updates_%s.json" % S, "w"), indent=1)
print("wrote board_updates_%s.json" % S, len(ops), "ops")
