# PLAIN ENGLISH (run outputs for the 3pm ET 9/17/2026 slot - ehpa cloud run 2026-09-17T1910Z)
# Decides: nothing. Reads this run's column scans (scan_0912/summary_before.json + summary_after.json), the inspector register
#   (registers/insp_2026-09-17T1910Z.json), the ERA before/after snapshots, the AET12 verify register and the Pam admit-email
#   findings (inbox/pam/pam_findings.json), then writes:
#   - "_run report 9-17 1910.csv" (per column: cleared / remaining with patient, DOS, carrier, error, action; ERA rows carry
#     check id, payer, visit, amount, action)
#   - board_updates_2026-09-17T1910Z.json (Insurance Refresh Board inbox file: appends keyed by src+when; ONE new row for the
#     ten Pam admit facesheets of 9/17 so the payer data survives the container; no set on status/need of an existing row)
#   - a needs_facesheet_list.md section, the captured_calls additions file and the chat-history digest text (--final)
# Never touches: AMD, the board databases.
import csv, json, os, re, collections, datetime, sys
S = "2026-09-17T1910Z"; SRC = "3pm ET 9/17 columns run (ehpa cloud)"; W = "9/17"
NOW = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
MIRROR = open("mirror_result.txt").read().strip() if os.path.exists("mirror_result.txt") else "pending"
def load(p, d):
    try: return json.load(open(p))
    except Exception: return d
def f(x):
    try: return float(x or 0)
    except Exception: return 0.0
before = load("scan_0912/summary_before.json", {}); after = load("scan_0912/summary_after.json", {})
insp = load("registers/insp_%s.json" % S, {"visits": [], "held": [], "left": []})
eb = load("era_checks_before_%s.json" % S, []); ea = load("era_checks_after_%s.json" % S, [])
nb, ab = len(eb), round(sum(f(c.get("unpostedamount")) for c in eb), 2)
na, aa = len(ea), round(sum(f(c.get("unpostedamount")) for c in ea), 2)
ex = load("registers/aet12_excl_1700202_2026-09-17T0710Z.json", [])
ver = load("registers/aet12_verify_%s.json" % S, [])
aet_bal = round(sum(f(c.get("insbal")) for c in ver), 2); aet_paid = round(sum(f(c.get("paid")) for c in ver), 2)
runs_n = before.get("overview", {}).get("claimrunstatuscount", "?")
pam = load("inbox/pam/pam_findings.json", {"rows": []})
era_txt = open("era_summary.txt").read().strip() if os.path.exists("era_summary.txt") else "ERA chain not run"
insp_before = sum(len(v) for v in before.get("inspector", {}).values()); insp_after = sum(len(v) for v in after.get("inspector", {}).values())
fixed = insp["visits"]; held = insp["held"]; left = insp["left"]
bychart = collections.Counter(r["patientid"] for r in ex)
chart_txt = ", ".join("pat%s x%d" % (p, n) for p, n in bychart.most_common())
adm_src = collections.Counter(("same stay" if "same stay" in s else s.split("(")[-1].rstrip(")")) for v in fixed for s in v["steps"] if s.startswith("admission"))
bell = [v["vid"] for v in fixed if any("Winslow Jr rule" in s for s in v["steps"])]
gate = [(v["vid"], v["pid"], [s for s in v["steps"] if "PRIMARY-DX GATE" in s or "fix_visit" in s]) for v in fixed if any("PRIMARY-DX GATE" in s for s in v["steps"])]
rows = []
def add(col, state, patient="", dos="", carrier="", err="", action="", check="", visit="", amt=""):
    rows.append({"column": col, "state": state, "patient": patient, "dos": dos, "carrier": carrier, "error": err,
                 "action": action, "checkid": check, "visit": visit, "amount": amt})
add("Charge Review", "clear", action="0 visits before, 0 after (getreviewcharges empty; overview chargereviewcount 0)")
add("Claim Inspector", "cleared" if insp_after == 0 else "partly cleared", action="batch 127728: %d visits on 23 charts before -> %d after. All 56 were 'Hospitalization From Date empty' (new HCA hospital visits 9/14-9/16 from the Claimocity feed); %d fixed (admission = own 99223 x%d, most recent 99223 within 45 days x%d, same-stay admission already on an earlier visit x%d - pat17472393 08/27/2026 and pat17472703 09/05/2026), updextrainsinfo hospitalizationfrom only, full-visit resave onhcfa=1; Winslow Jr (pat17472546) x%d: M86.9 put in front of S81.801S per William 9/6 and Pattern 20389 bypassed; primary-dx gate fired on %d visit(s) (%s); %d held; %d left after the bypass pass" % (insp_before, insp_after, len(fixed), adm_src.get("own 99223", 0), adm_src.get("most recent 99223 within 45d", 0), sum(n for k, n in adm_src.items() if k.startswith("same stay")), len(bell), len(gate), "; ".join("v%s pat%s %s" % (g[0], g[1], " | ".join(x[:120] for x in g[2])) for g in gate) or "none", len(held), len(left)))
for v in fixed:
    adm = next((s for s in v["steps"] if s.startswith("admission")), "")
    add("Claim Inspector", "cleared", patient="pat%s" % v["pid"], dos=next((s.split()[1] for s in v["steps"] if s.startswith("dos")), ""), err="Hospitalization From Date empty" + (" + Pattern 20389" if v["vid"] in bell else ""), action=adm + "; " + next((s[:140] for s in v["steps"] if s.startswith("resave")), ""), visit=v["vid"])
for v in held:
    add("Claim Inspector", "held", patient="pat%s" % v["pid"], err="Hospitalization From Date empty", action=v["steps"][-1][:200], visit=v["vid"])
for bid, vid, pid, errs in left:
    add("Claim Inspector", "remaining", patient="pat%s" % pid, err="; ".join(e[1][:80] for e in errs), action="left in batch %s after the bypass pass" % bid, visit=vid)
add("Unbilled", "clear", action="0 rows before and after (getclaimunbillablecharges totalcount 0)")
add("Exclusions", "held", carrier="AET12", err="CH FH PREF0288 INVALID PAYER ID/CPID 814723941 + PREF0264 MISS/INVD PAYER DOC CONTRL NUM (claim run 1700202, 59 exclusions)",
    action="Same 59 AET12 rows as every run since the 1am 9/17 slot; no claim run newer than 1700202 (%s runs listed). gettxhistory on all 15 charts (%s): 68 AET12 charges billdate 09/16/2026, insurance balance $%.2f open, none at $0, no AET12 payment (Medicare paid $%.2f on the same visits). Held - not rebilled, not completed; the carrier record (IDs dialog / Claim Fields / Box 33B REF*EI / AMD 837 case) is still William's fix." % (runs_n, chart_txt, aet_bal, aet_paid), amt="%.2f" % aet_bal)
for r in ex:
    add("Exclusions", "remaining", patient="pat%s" % r["patientid"], carrier="AET12", err="; ".join(sorted(set(r["errs"]))), action="held on claim run 1700202 (carrier-master fix pending)", visit=r["visit"], amt="%.2f" % r["fee"])
add("ERA", "clear" if na == 0 else "held", action="GET /api/era/checks: %d unposted checks / $%.2f before -> %d / $%.2f after. %s" % (nb, ab, na, aa, era_txt))
add("Availity remits", "none new", action="no file in 'bht Optum era downloads', 'treasury payments' or the four facesheet folders modified after 09:00Z 9/17 (Drive search over every folder except chat history / workspace mirror returned only this routine's own artifacts); registers/availity_register.json unchanged; nothing parsed, posted or reconciled")
add("Pam admit emails", "read", action="10 Pam Garland-G admit emails (18:40-18:50Z 9/17, Brynwood x9 + one marked Brentwood, phone photos of the PCC admission record) decoded from the RAW MIME and read; matched to AMD by lookuppatient name + DOB: 5 existing charts verified (pat17477182, pat17469446, pat17472556, pat17477652, pat24039), 5 admits have no AMD chart yet (Claimocity feed pending) - payer data saved to the board row pam-admits-2026-09-17 on Claude's turn so the next Unbilled run has it")
for p in pam.get("rows", []):
    add("Pam admit emails", p.get("state", ""), patient=p.get("pid", "(no chart)"), dos=p.get("admit", ""), carrier=p.get("payer", ""), action=p.get("action", ""))
add("Boards", "none", action="Working Denials queue 0 queued; Insurance Refresh Board 184 rows on Claude's turn (query truncated at 72 by the tool, none carrying a new William note in the readable part), drops 0 new; board inbox: both registries' applied maps list only 9/12-9/15 files, none still in the inbox (board last synced 9/16 03:46Z) - nothing trashed.")
out = "_run report 9-17 1910.csv"
with open(out, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=["column", "state", "patient", "dos", "carrier", "error", "action", "checkid", "visit", "amount"])
    w.writeheader(); w.writerows(rows)
print("wrote", out, len(rows), "rows")

def chk(ok, result, src=SRC): return {"ok": ok, "result": result, "src": src, "when": W}
ops = []
def row(id, checks=None, notes=None, op="update", set_=None):
    o = {"op": op, "collection": "items", "id": id, "append": {}}
    if set_: o["set"] = set_
    if checks: o["append"]["checks"] = checks
    if notes: o["append"]["notes"] = notes
    ops.append(o)
row("aet12-carrier-cpid",
    checks=[chk("no", "3pm ET 9/17: unchanged - the 59 AET12 exclusions of claim run 1700202 (PREF0288 INVALID PAYER ID/CPID 814723941 + PREF0264) are still on the list, no newer claim run (%s listed). 68 AET12 charges on the 15 charts: billdate 09/16/2026, $%.2f insurance balance open, no AET12 payment. Held, not rebilled, not completed." % (runs_n, aet_bal), SRC + " - claim run 1700202")])
row("era-manual-post-0912", checks=[chk("na", "ERA step 5 (%s, run %s): %d unposted checks / $%.2f before -> %d / $%.2f after. %s" % (SRC, S, nb, ab, na, aa, era_txt[:400]), SRC + " - ERA step 5")])
row("availity-remits-backlog", checks=[chk("na", "No Availity PDF or Check/EFT export newer than the registered set in 'bht Optum era downloads' / 'treasury payments' (nothing modified after 09:00Z 9/17 outside this routine's own artifacts) - nothing to parse, post or reconcile; board drops and Working Denials queue: nothing new. Pam Gmail: 10 admit emails 9/17 18:40Z read (see row pam-admits-2026-09-17).", SRC + " - ERA step 5(g)")])
row("winslow-jr-erwin", checks=[chk("ok", "Three new HCA 99233 visits (9/14 vst19454887, 9/15 vst19454929, 9/16 vst19454953) came through the feed with S81.801S as the only dx again; same 9/3 stay -> admission 09/03/2026 written, M86.9 (dcode1034545415) put in front per your 9/6 rule, full-visit resave onhcfa=1, Pattern 20389 bypassed, inspector clear." if len(bell) == 3 else "Winslow Jr inspector visits this run: %s (see the run report)" % bell)])
if pam.get("board_row"):
    ops.append({"op": "upsert", "collection": "items", "id": "pam-admits-2026-09-17", "set": pam["board_row"], "append": {"notes": [{"who": "Claude", "text": pam.get("board_note", ""), "at": NOW}]}})
for extra in pam.get("row_checks", []):
    row(extra["id"], checks=[chk(extra.get("ok", "ok"), extra["result"], SRC + " - Pam admit email 9/17")])
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}, open("board_updates_%s.json" % S, "w"), indent=1)
print("wrote board_updates_%s.json" % S, len(ops), "ops")

sec = """
## 2026-09-17 3 PM ET columns run (ehpa cloud Code Routine, 19:08-%s UTC, run %s)
Bootstrap: repo ATTACHED (origin/main 5eb33d0, session branch claude/pensive-einstein-b77okp, layout 314 helpers), AMD_OK, STEDI_CRED_OK (no key file), ONE amd.login_cached success, no login lock. Drive 'workspace mirror' newest state bundle is still workspace_state_2026-09-15_1836UTC (older than the repo state, not unpacked); registers restored from practices/ehpa/registers/ in the repo (1710Z state); needs_facesheet_list.md rebuilt from the repo's 17 run sections; captured_calls.md = GitHub main docs/captured_calls.md (the Drive copy is a 92,698-byte stub); pseudonyms.json (142 names) from the workspace mirror. Missing required helpers (not rewritten): columns_inspector2_0908.py, era_details_pull.py (era_step_b_0913.py fills the cache instead). Skills loaded: advancedmd-api-reference, billing-hard-task-clearing-unbilled-column, billing-easy-task-charge-review-and-claim-inspector-columns.
Boards: Insurance Refresh Board - 184 rows on Claude's turn (the inline read shows 72 of them; no new William note seen), drops new = 0; Working Denials queue = 0. Board inbox: both registries' applied maps list only 9/12-9/15 files, none still in the inbox (board last synced 9/16 03:46Z) - nothing trashed. Facesheet folders, Optum ERA folder, treasury folder: nothing modified after 09:00Z 9/17 except this routine's own artifacts. PAM GMAIL: 10 admit emails 18:40-18:50Z 9/17 (Brynwood PCC admission-record photos) read visually - see the Pam section.
Columns: Charge Review 0 -> 0 | Claim Inspector %d -> %d (batch 127728, 23 charts, all 'Hospitalization From Date empty' on new HCA visits 9/14-9/16: %d fixed - admission from the visit's own 99223 x%d, the most recent 99223 within 45 days x%d, the same stay's earlier visit x%d (pat17472393 08/27/2026, pat17472703 09/05/2026 - no 99223 anchor in the history); Winslow Jr x%d M86.9 in front of S81.801S + Pattern 20389 bypassed; primary-dx gate: %s; %d held; %d left) | Unbilled 0 -> 0 | Exclusions 59 -> 59 HELD: the same 59 AET12 claims of claim run 1700202 (PREF0288 INVALID PAYER ID/CPID 814723941 + PREF0264), no newer claim run (%s listed). gettxhistory on the 15 charts: 68 AET12 charges billdate 09/16/2026, $%.2f insurance balance open, none at $0, no AET12 payment (Medicare paid $%.2f on those visits). Not rebilled, not completed - carrier-record fix still William's. Nothing released, rebilled or written off in the four columns by this run.
ERA step 5: %d unposted checks / $%.2f before -> %d / $%.2f after. %s Availity 5(g): nothing new. Working Denials: nothing queued, no denials file written.
Pam admit emails (9/17): %s
Calls learned: none (lookuppatient name wildcard, gettxhistory, getchargedetaildataicd10 by charge id, updextrainsinfo hospitalizationfrom, updvisitwithnewcharges full echo, bypassclaimedits, getclaiminspectorbatches/charges, GET /api/era/checks, POST /api/era/locks/release-expired - all captured; Gmail RAW MIME attachment decode is the registered path). Vocabulary entries added: 0.
Mirror: %s
""" % (datetime.datetime.utcnow().strftime("%H:%M"), S, insp_before, insp_after, len(fixed), adm_src.get("own 99223", 0), adm_src.get("most recent 99223 within 45d", 0), sum(n for k, n in adm_src.items() if k.startswith("same stay")), len(bell), "; ".join("v%s pat%s %s" % (g[0], g[1], " | ".join(x[:100] for x in g[2])) for g in gate) or "none fired", len(held), len(left), runs_n, aet_bal, aet_paid, nb, ab, na, aa, era_txt, pam.get("digest", "(none)"), MIRROR)
if "--final" in sys.argv:
    txt = open("needs_facesheet_list.md").read()
    if "run %s)" % S in txt:
        txt = re.sub(r"\n## 2026-09-17 3 PM ET columns run \(ehpa cloud Code Routine.*?(?=\n## |\Z)", "", txt, flags=re.S).rstrip("\n") + "\n"
    open("needs_facesheet_list.md", "w").write(txt + sec)
    open("needs_facesheet_list_section.md", "w").write(sec.lstrip("\n"))
    open("captured_calls_additions_%s-3pmET-ehpa-cloud.md" % S.replace("T", "_").replace("Z", "UTC"), "w").write("## 2026-09-17 3 PM ET columns run (ehpa cloud Code Routine, run %s) - run entry, NO new AMD call shapes\n" % S + sec.strip().split("\n", 1)[1] + "\n")
    os.makedirs("chat_history", exist_ok=True)
    dig = "# %s run digest - backend billing run, 3pm ET 9/17/2026 slot (ehpa cloud)\n" % S.replace("T", "_").replace("Z", "UTC") + sec + "\nRUN COMPLETE\n"
    open("chat_history/%s run digest.md" % S.replace("T", "_").replace("Z", "UTC"), "w").write(dig)
    print("wrote needs_facesheet section, additions file, digest")
print(sec)
