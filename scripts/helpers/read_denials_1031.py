# PLAIN ENGLISH (read-only): for the 14 Humana denial lines of checks 1053349-1053351 read each chart's plans
# and each visit's live charges (carrier, billdate, balances, payments, diagnosis codes). No writes.
import json, sys
import precheck, payreasons, resave, txh
rows = [(17471793,19459299),(17469512,19459179),(17475713,19458868),(17475713,19458983),(17475713,19458764),
        (17472397,19459066),(17471384,19459295),(17471384,19458751),(46048,19458752),(46048,19459296),
        (17478018,19457333),(20407,19457356),(17473065,19459095),(44953,19458948)]
seen=set()
for pid,vid in rows:
    if pid not in seen:
        seen.add(pid)
        try: print("PLANS", pid, json.dumps(precheck.plans(pid))[:900])
        except Exception as e: print("PLANS", pid, "ERR", e)
    try:
        st = payreasons.visit_state(pid, vid)
        print("VISIT", pid, vid, json.dumps(st, default=str)[:1500])
    except Exception as e: print("VISIT", pid, vid, "ERR", e)
