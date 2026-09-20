# PLAIN ENGLISH (7am ET 9/20/2026 run 2026-09-20T1110Z): claim run 1700211 rejected the same 11 Florida Blue SECONDARY claims again
#   (CH FH PREF0283 MISSING PAYER DOC CONTROL NUM) after the 1am run re-sent them freq 7 / freq 1. William's standing decision
#   (9/13 04:44Z, board bcbs-secondary-dcn-0910): CROSSOVER-WAIT - complete them off the exclusion list, no rebill; Medicare forwards
#   the Medigap claim to Florida Blue on its own. Every charge re-read live this run (excl_1700211_verify): insurance balance open,
#   Medicare payment posted 9/19 with its ICN, none at $0.
# Decides: hideexclusions run 1700211 for the 11 visit/claim ids, then re-lists the run. Never touches: balances, payments, rebills.
import amd, json, re, time
amd.login_cached()
rows = json.load(open("scan_0912/summary_before.json"))["exclusions"]["1700211"]
xml = amd.call('action="hideexclusions" class="claimsreports" claimrunid="1700211" hide="-1" nocookie="1"',
               "<visitlist>%s</visitlist>" % "".join('<visit id="%s" claimid="%s"/>' % (v["id"], v["claimid"]) for v in rows))
print("hideexclusions x%d -> %s" % (len(rows), re.sub(r"\s+", " ", xml)[:200]), flush=True)
time.sleep(1)
t = amd.post(amd.msg("getclaimexclusioncharges", "claimsreports", {"claimrunid": "1700211", "clearinghouse": "1", "payer": "1", "nocookie": "1"}), timeout=120)
n = len(re.findall(r"<visit ", t)); print("run 1700211 re-listed: %d visit rows" % n)
json.dump({"run": "1700211", "completed": [(v["id"], v["claimid"], v["patientid"]) for v in rows], "relisted": n, "rule": "William 9/13 crossover-wait", "when": "2026-09-20T1110Z"},
          open("registers/excl_1700211_2026-09-20T1110Z.json", "w"), indent=1)
