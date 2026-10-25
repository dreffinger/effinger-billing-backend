# PLAIN ENGLISH (Mirror prep, nightly cascade 2026-10-25)
# Decides: Nothing. Copies tonight's run scripts and PID-ONLY copies of the registers (patient names stripped) into the
# repository's nightly/runs/<stamp>/ and practices/ehpa/registers/ so mirror.py sync can commit them without PHI.
# Never touches: AMD, Drive, the board.
import json, os, shutil
W = "/home/claude/unbilled"; R = "/home/claude/effinger-billing-backend"; STAMP = "2026-10-25T0535Z"
run = os.path.join(R, "nightly/runs", STAMP); reg = os.path.join(R, "practices/ehpa/registers"); os.makedirs(run, exist_ok=True); os.makedirs(reg, exist_ok=True)
for f in ("sweep_act_1025.py", "build_universe_1025.py", "mirror_prep_1025.py", "nightly_digest_%s.md" % STAMP, "captured_calls_additions_%s.md" % STAMP):
    shutil.copy(os.path.join(W, f), os.path.join(run, f))
def strip(o):
    if isinstance(o, dict): return {k: strip(v) for k, v in o.items() if k not in ("patient", "pays")}
    if isinstance(o, list): return [strip(x) for x in o]
    return o
for f in ("sweep_resend_%s.json" % STAMP, "sweep_denials_%s.json" % STAMP):
    d = strip(json.load(open(os.path.join(W, "registers", f))))
    for dst in (os.path.join(run, f), os.path.join(reg, f)): json.dump(d, open(dst, "w"), indent=1)
for f in ("precheck_20261025.json", "[name]_[DOB].json"):
    shutil.copy(os.path.join(W, f), os.path.join(run, f))
print("mirror prep done:", sorted(os.listdir(run)))
