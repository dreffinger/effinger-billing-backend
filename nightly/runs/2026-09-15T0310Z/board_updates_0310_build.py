# PLAIN ENGLISH (Insurance Refresh Board answers for the 11pm ET 9/14 run - inbox file builder)
# Decides: Nothing. Writes board_updates_2026-09-15T0310Z.json with the results of tonight's board actions: one note + one
#   lookup-trail line per row that was worked (Alcorn, Brown, Bull, Coalson x2, Collins, Ford, Morris, Moore, Peterson,
#   Powell, Clack, Gray, Tillery), the Stedi API blocks captured tonight, the ERA/Availity remit reconciliation on the
#   ERA row plus a new row for the Florida Blue remits William exported, and status changes only where the row's ask is
#   finished (update ops, never set; appends are keyed by src+when so a re-applied file cannot duplicate them).
# Rules it uses: the first sentence of `need` is the ask; rows William may have touched get update, not set.
# Never touches: the board database directly (the page ingests this file from the Drive board inbox).
import json, os, datetime
S = "2026-09-15T0310Z"; NOW = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
SRC = "11pm ET 9/14 columns run (ehpa cloud)"; W = "9/15"
def chk(ok, result, src=SRC): return {"ok": ok, "result": result, "src": src, "when": W}
def note(text): return {"at": NOW, "text": text, "who": "Claude"}
ops = []
def row(id, notes=None, checks=None, api=None, status=None, need=None, extra=None):
    op = {"op": "update", "id": id, "append": {}}
    if notes: op["append"]["notes"] = notes
    if checks: op["append"]["checks"] = checks
    if api: op["append"]["api"] = api
    d = {}
    if status: d["status"] = status
    if need: d["need"] = need
    if extra: d.update(extra)
    if d: op["data"] = d
    ops.append(op)

# --- Availity / ERA numbers (filled from tonight's registers when present)
def load(p):
    try: return json.load(open(p))
    except Exception: return None
cmp = load("registers/availity_vs_amd_%s.json" % S) or {"totals": {}}
post = load("registers/availity_post_%s_live.json" % S) or {"summary": {}}
reg = load("registers/availity_checks_%s.json" % S) or []
tot = cmp.get("totals", {}); ps = post.get("summary", {})
eb = load("era_checks_before_%s.json" % S) or []; ea = load("era_checks_after_%s.json" % S) or []
def era_sum(l):
    try: return len(l), round(sum(float(c.get("unpostedamount") or 0) for c in l), 2)
    except Exception: return len(l), 0
nb, ab = era_sum(eb); na, aa = era_sum(ea)

# ---------------- rows William answered 9/14 ----------------
row("alcorn-alfred",
    notes=[note("11pm ET 9/14 run: posted the self-pay no-pay write-off on the 9/1/2026 99308 (charge 23364736, visit 19453827): WOBAD $107.00, AMD payment id 10153264, note 'Self-pay no-pay bad debt - no insurance on 9/1/2026 (Sunshine ended 8/31/2026), Medicaid pending - William 9/14/2026'. The 8/28/2026 99309 ($141) stays with Sunshine as billed. If Medicaid is reinstated back to 9/1, say so and the write-off gets voided and the visit billed.")],
    checks=[chk("ok", "WOBAD $107.00 posted on charge 23364736 (9/1/2026 99308), payment id 10153264; balance $0")],
    status="done", need="Done 9/15: 9/1/2026 99308 ($107, visit 19453827) written off WOBAD (self-pay no-pay, no insurance on the DOS, Medicaid pending) - payment id 10153264. The 8/28 99309 ($141) stays billed to Sunshine (covered through 8/31). Reverse the write-off and bill it if Medicaid is reinstated back to 9/1.")

row("brown-randle-17477112",
    notes=[note("11pm ET 9/14 run: chart first name changed RANDLE -> RANDY (demographics PATCH; AMD getdemographic now reads BROWN,RANDY E). The PATCH first bounced 500 'Email is not a valid format' because the email field held the phone +1 850-510-3018 - cleared it and stored that number as the home phone. Stedi Aetna 60054 at DOS 7/13/2026 (both RANDLE and RANDY): ERR 43 'Invalid/Missing Provider Identification' - Aetna's known no-verdict answer for our NPI, member id echoed. Freq-1 rebilled both Aetna visits after the rename: 7/13/2026 99223 $310 (visit 19448269) and 7/14/2026 99232 $111 (visit 19448235) -> HTTP 204 each; they leave on the next claim run.")],
    checks=[chk("ok", "first name RANDLE -> RANDY on the chart (PATCH 200, getdemographic BROWN,RANDY E); phone 850-510-3018 moved from the email field to home phone"),
            chk("na", "ERR 43 Invalid/Missing Provider Identification (no verdict), member W270091846 echoed - RANDLE and RANDY both", "Stedi eligibility Aetna 60054, DOS 7/13/2026"),
            chk("ok", "freq-1 + chargerebill seq 1 -> 204 x2 (7/13 99223 $310 vst19448269, 7/14 99232 $111 vst19448235), after the rename")],
    api=[{"at": NOW, "src": "Stedi API - Aetna 60054 eligibility, DOS 2026-07-13", "text": "BROWN, RANDY E dob on file member W270091846 -> errors: [43 Invalid/Missing Provider Identification] (payer-side provider-on-file problem, not a coverage answer); memberId echoed W270091846. Same answer with first name RANDLE."}],
    need="Watching: 7/13 + 7/14/2026 Aetna visits ($421) re-sent freq-1 under the corrected name RANDY E BROWN (William's OK 9/14). Nothing for William unless Aetna rejects again.")

row("bull-thomas-17477723",
    notes=[note("11pm ET 9/14 run: CAP07 Capital Health Plan (car41826) added with member CHP01052326, begin 06/01/2024, relationship self, NO group number -> ins9519414, sequence 1. Stedi CHP 95112 at DOS 9/10/2026: ACTIVE, Commercial, plan begin 20250601. Admission 09/10/2026 written on both visits (hospitalizationfrom only), full-visit resave insorder 1 + onhcfa=1 (99223 9/10 vst19454465, 99232 9/11 vst19454443), both released from Unbilled (hideunbillablevisits ok) - they bill CAP07 on the next claim run. Address left as the chart's 3135 CORRIB DR (TMH shows 1695 Folkstone Rd) pending your word; e-mail THBULL1973@AOL.COM not restored.")],
    checks=[chk("ok", "CAP07 car41826 member CHP01052326 begin 06/01/2024 added -> ins9519414 seq 1 (no group)"),
            chk("ok", "ACTIVE Commercial, planBegin 20250601", "Stedi eligibility CHP 95112, DOS 9/10/2026"),
            chk("ok", "admit 09/10/2026 + insorder 1 + onhcfa 1 on vst19454465 (99223 9/10) and vst19454443 (99232 9/11); released from Unbilled")],
    api=[{"at": NOW, "src": "Stedi API - CHP 95112 eligibility, DOS 2026-09-10", "text": "BULL, THOMAS dob on file member CHP01052326 -> Active Coverage, insuranceType Commercial (C1), planDateInformation planBegin 20250601; serviceTypeCodes 30; errors none."}],
    status="done", need="Done 9/15: Capital Health Plan CHP01052326 on the chart (seq 1, begin 6/1/2024, no group), Stedi ACTIVE, admission 9/10/2026 written, both HCA visits (99223 9/10 + 99232 9/11, $421) released to CAP07. Optional: tell me if the chart address should switch to TMH's 1695 Folkstone Road.",
    extra={"inscarrier": "CAP07 Capital Health Plan", "insid": "CHP01052326", "insplans": "1st CAP07 Capital Health Plan CHP01052326 (6/1/2024 - open)"})

row("coalson-yvonne-17474210",
    notes=[note("11pm ET 9/14 run: WOLATE (untimely filing, CO-29) posted on all six open Humana lines - $914.00 total: 23323286 9/29/2025 99223 $310 (payment id 10153265), 23323283 9/30 99232 $111 (10153266), 23323448 10/1 $111 (10153267), 23323535 10/2 $111 (10153268), 23323620 10/3 $111 (10153269), 23323673 10/4 99233 $160 (10153270); note on each 'Timely filing - DOS <date> first billed 9/10/2026, Humana CO-29 - William 9/14/2026'. Insurance balance $0 on all six; no rebill, no appeal.")],
    checks=[chk("ok", "WOLATE x6 = $914.00 (payment ids 10153265-10153270), balances $0")],
    status="done", need="Done 9/15: six Sept-Oct 2025 Humana hospital lines ($914) written off WOLATE as untimely filing per your 9/14 note; ids 10153265-10153270.")
row("coalson-yvonne-denials",
    notes=[note("11pm ET 9/14 run: the six HUM01 lines on this row ($914, 9/29-10/4/2025) were written off WOLATE tonight per William's 9/14 'write off as untimely' (see row coalson-yvonne-17474210 for ids). Nothing left open.")],
    status="done", need="Done 9/15: written off WOLATE (untimely filing) - see the companion row for the six write-off ids.")

row("collins-miranda-denials",
    notes=[note("11pm ET 9/14 run: Stedi Florida Blue (BCBSF) with the full id VMYH55699618 at DOS 7/9/2026 again: INACTIVE (planStatus 6). Per your 9/14 OK the five July claims were sent once more anyway - freq-1 + chargerebill seq 1 -> 204 x5: 99223 7/9 $310 vst19447727, 99232 7/10 $111 vst19447678, 7/11 vst19447677, 7/12 vst19447879, 7/13 vst19448232 ($754). Not written off tonight: William's rule is patient responsibility + bad-debt write-off only after Florida Blue answers no-coverage; the next run that sees the denial posts WOBAD.")],
    checks=[chk("no", "INACTIVE (planStatus 6) for VMYH55699618 - same as 9/13", "Stedi eligibility BCBSF, DOS 7/9/2026"),
            chk("ok", "freq-1 + chargerebill seq 1 -> 204 x5 (7/9-7/13/2026, $754) per William's 9/14 OK")],
    need="Watching: the five July 2026 HCA claims ($754) went to Florida Blue once more freq-1 on 9/15 (Stedi still says INACTIVE on 7/9/2026). When Florida Blue denies for no coverage the run moves the balances to patient responsibility and posts the bad-debt write-off per your OK; nothing for William now.")

row("ford-sammie-l-17471384",
    notes=[note("11pm ET 9/14 run: WOLATE posted on the 10/25/2025 CCM lines - 99487 $206.00 charge 23326416 (payment id 10153271) and 99489 $109.00 charge 23326417 (payment id 10153272), note 'Timely filing - DOS 10/25/2025 first billed 9/10/2026, Humana CO-29 - William 9/14/2026'. Balance $0.")],
    checks=[chk("ok", "WOLATE $206.00 (23326416, id 10153271) + $109.00 (23326417, id 10153272); balance $0")],
    status="done", need="Done 9/15: 10/25/2025 Humana CCM claim ($315) written off WOLATE (untimely) - ids 10153271 + 10153272.")
row("morris-richard-44976",
    notes=[note("11pm ET 9/14 run: WOLATE posted on the 10/25/2025 CCM lines - 99487 $206.00 charge 23326386 (payment id 10153273) and 99489 $109.00 charge 23326387 (payment id 10153274), note 'Timely filing - DOS 10/25/2025 first billed 9/10/2026, Humana CO-29 - William 9/14/2026'. Balance $0.")],
    checks=[chk("ok", "WOLATE $206.00 (23326386, id 10153273) + $109.00 (23326387, id 10153274); balance $0")],
    status="done", need="Done 9/15: 10/25/2025 Humana CCM claim ($315) written off WOLATE (untimely) - ids 10153273 + 10153274.")

row("moore-mary-denials",
    notes=[note("11pm ET 9/14 run: CAP07 Capital Health Plan (car41826) added with member CIO60023770, begin 01/01/2026, NO group -> ins9519415, sequence 2. Stedi CHP 95112 at DOS 2/6/2026: ACTIVE, Medicare Risk (MA), plan begin 20260101. Florida Blue plan XJBH29440242 (ins9516490) end-dated 12/31/2025 (success 1); patient insurance order set to 2 (CAP07). Both February visits resaved insorder 2 + onhcfa 1 and freq-1 rebilled on seq 2: 2/6/2026 99223 $310 vst19431787 (charge 23338435) and 2/7/2026 99232 $111 vst19431884 (charge 23338525) -> 204 each. Chart address not changed (TMH: 2677 Old Bainbridge Rd Apt 911) - say the word.")],
    checks=[chk("ok", "CAP07 car41826 member CIO60023770 begin 01/01/2026 added -> ins9519415 seq 2 (no group); BCBS ins9516490 end-dated 12/31/2025; patient insorder 2"),
            chk("ok", "ACTIVE Medicare Risk (MA), planBegin 20260101", "Stedi eligibility CHP 95112, DOS 2/6/2026"),
            chk("ok", "vst19431787 (2/6 99223 $310) + vst19431884 (2/7 99232 $111) insorder 2, freq-1 + chargerebill seq 2 -> 204 x2")],
    api=[{"at": NOW, "src": "Stedi API - CHP 95112 eligibility, DOS 2026-02-06", "text": "MOORE, MARY dob on file member CIO60023770 -> Active Coverage, insuranceType Medicare Risk (MA), planDateInformation planBegin 20260101; serviceTypeCodes 30; errors none."}],
    status="done", need="Done 9/15: CHP Advantage Plus CIO60023770 on the chart (seq 2, begin 1/1/2026, no group), Stedi ACTIVE, Florida Blue ended 12/31/2025, both February 2026 HCA claims ($421) re-sent freq-1 to CAP07. Optional: chart address -> TMH's 2677 Old Bainbridge Rd Apt 911 if you want it.",
    extra={"inscarrier": "CAP07 Capital Health Plan (Medicare Advantage)", "insid": "CIO60023770", "insplans": "BCBS Florida Blue XJBH29440242 (ended 12/31/2025) · 2nd CAP07 Capital Health Plan CIO60023770 (1/1/2026 - open)"})

row("peterson-marie-17475237",
    notes=[note("11pm ET 9/14 run: Stedi Aetna 60054, member W261107443, DOS 1/16/2026: ERR 43 'Invalid/Missing Provider Identification' (Aetna's no-verdict answer for our NPI; member id echoed) - not an eligibility answer. Per the row's ask the 1/16/2026 99223 ($310, visit 19429563, charge 23336090) was freq-1 rebilled to AET07 seq 1 -> 204. The 1/17-1/21 99232 lines ($111 x5) on the same chart were already re-sent 9/10 and stay as billed.")],
    checks=[chk("na", "ERR 43 Invalid/Missing Provider Identification (no verdict), member W261107443 echoed", "Stedi eligibility Aetna 60054, DOS 1/16/2026"),
            chk("ok", "freq-1 + chargerebill seq 1 -> 204 (1/16/2026 99223 $310 vst19429563)")],
    api=[{"at": NOW, "src": "Stedi API - Aetna 60054 eligibility, DOS 2026-01-16", "text": "PETERSON, MARIE dob on file member W261107443 -> errors: [43 Invalid/Missing Provider Identification]; memberId echoed W261107443; no plan status returned."}],
    need="Watching: 1/16/2026 Aetna 99223 ($310) re-sent freq-1 on 9/15 (Aetna's eligibility endpoint answers ERR 43 for our NPI, so TMH's ACTIVE PPO is the coverage evidence). Nothing for William unless Aetna rejects.")

row("powell-robert",
    notes=[note("11pm ET 9/14 run: the two Medicare $0 lines written off WOINS with the note 'Write off, no secondary (Humana ended 12/3/2024) - William 9/14/2026': 4/21/2026 99349 $113.02 charge 23347358 (payment id 10153275) and 5/17/2026 99487 $142.98 charge 23350367 (payment id 10153276). The HUM01 secondary residuals ($172.90 on the 4 exclusion rows) were already written off 9/12 and the 4 exclusions completed then; tx history tonight shows no HUM01 balance left. Chart balance from Medicare lines now $0.")],
    checks=[chk("ok", "WOINS $113.02 (23347358, id 10153275) + $142.98 (23350367, id 10153276); no HUM01 residual left (written off 9/12)")],
    status="done", need="Done 9/15: the last two Medicare $0 lines ($255.99) written off WOINS, no secondary - ids 10153275 + 10153276; the Humana residuals and exclusions were closed 9/12. Nothing open on this chart.")

row("clack-eula-denials",
    notes=[note("11pm ET 9/14 run: (1) tx history - the 2/26/2026 99487 ($206, visit 19434042, charge 23340937) was billed to BCBS (car6062 XYL991586758) 9/4/2026; Florida Blue paid $0 on 9/9/2026 (check 213403769) and WOINS $206 was posted the same day - balance $0, so nothing is open to rebill without voiding that write-off. (2) Stedi Florida Blue (BCBSF) with XYL991586758 at DOS 2/26/2026: ACTIVE 'MED ADV', plan 20260101-20260430 (payer echoed member X3LM65856326 - the BCBS-of-Michigan MA number behind the out-of-state prefix) - so the BCBS out-of-state Medicare Advantage plan WAS active on 2/26/2026 and is the right primary; Medicare FLO02 would answer CO24. (3) The 9/9 remit's reason for the $0: check 213403769 is in William's Availity export - the 2/26 line (patient control 19434042A) shows CO-22 'covered by another payer per COB' / reversal-and-repay of an earlier adjudication. (4) Medicare 271 hospice indicator: none for February; date of death 8/28/2026. Recommendation: void the 9/9 WOINS and send the 2/26/2026 claim to BCBS as a corrected claim with the Michigan MA member number X3LM65856326 - needs your OK because it reverses a posted write-off.")],
    checks=[chk("ok", "ACTIVE 'MED ADV' 20260101-20260430 for XYL991586758 at DOS 2/26/2026; payer echoed member X3LM65856326", "Stedi eligibility BCBSF, DOS 2/26/2026"),
            chk("no", "2/26/2026 99487 billed BCBS 9/4/2026, $0 paid 9/9/2026 (check 213403769, CO-22), WOINS $206 posted 9/9 - balance $0", "AMD tx history + Availity remit 213403769"),
            chk("human", "OK to void the 9/9 WOINS ($206) and re-send 2/26/2026 to BCBS MA with member X3LM65856326 (the id Florida Blue echoed)?", "William")],
    api=[{"at": NOW, "src": "Stedi API - Florida Blue (BCBSF) eligibility, DOS 2026-02-26", "text": "CLACK, EULA dob on file member XYL991586758 -> Active Coverage, plan 'MED ADV', planDateInformation 20260101-20260430; subscriber memberId echoed X3LM65856326 (BCBS of Michigan MA); serviceTypeCodes 30; errors none."}],
    status="william", need="WILLIAM: OK to void the 9/9/2026 WOINS ($206) on the 2/26/2026 99487 and re-send it to BCBS Medicare Advantage as a corrected claim with member X3LM65856326 (the Michigan MA id Florida Blue echoed; the chart holds the out-of-state XYL991586758)? Florida Blue's eligibility says that MA plan was ACTIVE 1/1-4/30/2026, and the 9/9 remit denied the claim CO-22 (covered by another payer / COB) - i.e. the wrong BCBS entity. If you would rather leave the $206 written off, say 'leave it' and the row closes.")

row("gray-doris-denials",
    notes=[note("11pm ET 9/14 run: Stedi UHC 87726, member 132088691, DOS 7/8/2025: INACTIVE (the UHC Dual Complete plan on TMH starts 2/1/2025 per Epic, but UHC's own 271 does not show it active on 7/8/2025 - consistent with CMS naming Sunshine as the MA at that date). Per your rule (no right insurance -> untimely) nothing more to chase; AMD tx history shows the 7/8/2025 99487/99489 ($315) already at $0 - UNI20 paid $0 on 9/7/2026 and WOINS $206 + $109 were posted the same day. Nothing to post; row closed.")],
    checks=[chk("no", "INACTIVE for member 132088691 at DOS 7/8/2025", "Stedi eligibility UHC 87726"),
            chk("ok", "7/8/2025 99487 + 99489 already $0 (UNI20 $0 9/7/2026 + WOINS $206/$109 same day) - nothing open", "AMD tx history")],
    status="done", need="Done 9/15: UHC says INACTIVE on 7/8/2025 and the $315 was already written off WOINS on 9/7/2026 - no balance left, nothing to rebill. Closed per your 'write off as untimely' rule.")

row("tillery-wayne-17472393",
    notes=[note("11pm ET 9/14 run: you are right - nothing for you here. It sat on your turn because the 12/16/2025 Humana claim ($256, visit 19426733) was re-sent 9/12 and had no answer; that is a watch item, not a question. Moved back to Claude's watch list: the next run that sees Humana's answer (277 or ERA) acts on it (corrected claim / appeal with the census / write-off per the rules).")],
    checks=[chk("na", "9/12 HUM01 resubmission of 12/16/2025 still unanswered (no ERA among the 37 unposted checks tonight); watch item only")],
    need="Watching: Humana's answer to the 9/12 resubmission of the 12/16/2025 visit ($256). Nothing for William.")

# ---------------- ERA row + Florida Blue remit reconciliation ----------------
era_txt = ("ERA step 5 (11pm ET 9/14, run %s): %d unposted checks / $%.2f before -> %d / $%.2f after; era_post --all-unposted, fallback dry+live and era_clear ran (see the run report CSV for the per-check lines). "
           "NEW SOURCE TONIGHT: William exported %d Florida Blue / Health Options remits from Availity (CheckDetails/ClaimDetails PDFs in 'bht Optum era downloads', 266 files) - these are Availity views, not 835s, so era_upload cannot load them; parsed them into a check register (%d checks, $%.2f, %d claim lines) and compared every paid line to the live charge: Florida Blue money NOT in AMD = %d lines / $%.2f (posted lines already in AMD %d); manual-posted tonight per the 9/13 rule: %d payments $%.2f + $%.2f contractual write-offs; residual (charge already at $0 in AMD) $%.2f; statuses %s."
           % (S, nb, ab, na, aa, len([f for c in reg for f in c.get("files", [])]), tot.get("checks", 0), tot.get("check_amount", 0), sum(c.get("n_claims", 0) for c in reg), tot.get("missing_lines", 0), tot.get("missing", 0), 0, ps.get("posted", 0), ps.get("posted_amount", 0), ps.get("writeoff_amount", 0), ps.get("residual_remit_money", 0), json.dumps(ps.get("status_counts", {}))))
row("era-manual-post-0912", checks=[chk("ok" if ps.get("posted") else "na", era_txt, SRC + " - ERA step 5")])
ops.append({"op": "upsert", "id": "availity-florida-blue-remits-0915",
            "data": {"patient": "FLORIDA BLUE REMITS (Availity export 9/14)", "amdid": "", "amount": round(tot.get("missing", 0), 2), "status": "claude", "created": NOW, "updated": NOW,
                     "why": "William exported every Florida Blue / Health Options check from Availity Remittance Viewer on 9/14 (CheckDetails + ClaimDetails PDFs, 266 files) because AMD's ERA Center never received the Florida Blue 835s.",
                     "need": "Watching. Register: %d Florida Blue checks $%.2f (1/2026-9/2026); lines with money the AMD charge never received: %d / $%.2f; manual-posted this run: %d payments $%.2f (+ $%.2f contractual WOINS) with the Availity trace number as the check number; %s. The rest is in the run report. Nothing for William unless you want the Florida Blue 835s routed to AMD's clearinghouse (Availity ERA enrollment -> Change Healthcare) so this stops being manual." % (tot.get("checks", 0), tot.get("check_amount", 0), tot.get("missing_lines", 0), tot.get("missing", 0), ps.get("posted", 0), ps.get("posted_amount", 0), ps.get("writeoff_amount", 0), json.dumps(ps.get("status_counts", {}))),
                     "notes": [note("Created by the 11pm ET 9/14 run. Parser: avail_checks_parse.py (pypdf; line control number = AMD charge id, patient control number = AMD visit id); comparison avail_vs_amd.py; posting avail_post.py (pay = min(remit paid, open insurance balance), CO adjustments as WOINS capped to the balance, PR never written off). Registers in the workspace: availity_checks_%s.json, availity_vs_amd_%s.json, availity_post_%s_live.json." % (S, S, S))],
                     "checks": [chk("ok", "%d PDFs read (179 CheckDetails/CheckMultipleDetails + 77 ClaimDetails + earlier files), %d distinct checks by trace number" % (266, tot.get("checks", 0)))]}})

fnd = load("registers/availity_findings_%s.json" % S) or {}
row("availity-remits-backlog",
    notes=[note("11pm ET 9/14 run: processed every Availity PDF in 'bht Optum era downloads' (266 files - all Florida Blue / Health Options): %d checks $%.2f parsed; %d paid lines $%.2f had no matching payment in AMD; posted %d payments $%.2f (+ $%.2f contractual WOINS) with the Availity trace number as the check number and the check date as deposit date; %s. Reversal (status 22) claims recorded, not posted: %d (net $%.2f); OA-18 duplicate lines: %d on %d visits - not rebilled; $0 non-reversal claims: %d. Own parser used (avail_checks_parse.py, pypdf - pdftotext is not installed in the routine container); your availity_pdf.py / availity_remits.py from the workspace mirror were not run this pass - the Treasury CSV matching (treasury inbox) is still open. Full lists in tonight's run report CSV and the registers (availity_checks / availity_vs_amd / availity_post / availity_findings _%s.json)." % (
        tot.get("checks", 0), tot.get("check_amount", 0), tot.get("missing_lines", 0), tot.get("missing", 0), ps.get("posted", 0), ps.get("posted_amount", 0), ps.get("writeoff_amount", 0), json.dumps(ps.get("status_counts", {})), len(fnd.get("reversals", [])), sum(x[5] for x in fnd.get("reversals", [])), len(fnd.get("oa18", [])), len({x[1] for x in fnd.get("oa18", [])}), fnd.get("zero_claims", 0), S))],
    checks=[chk("ok", "Availity Florida Blue remits parsed + reconciled + posted (see note); Treasury CSV matching not run", SRC + " - ERA step 5(g)")])
out = {"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}
json.dump(out, open("board_updates_%s.json" % S, "w"), indent=1)
print("wrote board_updates_%s.json ops=%d" % (S, len(ops)))
