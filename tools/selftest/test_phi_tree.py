#!/usr/bin/env python3
# PLAIN ENGLISH (offline self-test of the PHI tree gate, 10/6/2026)
# Decides: nothing. Builds a throwaway git checkout with sample PHI in registers, a digest and code, runs
#   `phi_gate.py tree .` the way mirror.py does before `git add -A`, and asserts: names -> pseudonym or [name],
#   identifiers -> placeholders, a digest / needs section never enters the tree, code keeps its tokens,
#   billing vocabulary (DOS,CPT / LAST,FIRST / WOINS,WOLATE) is left alone. No AMD, no network.
# Run: python3 tools/selftest/test_phi_tree.py   (exit 1 on any failure)
import os, sys, json, subprocess, tempfile, shutil
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GATE = os.path.join(ROOT, "tools", "mirror", "phi_gate.py")
sys.path.insert(0, os.path.join(ROOT, "tools", "mirror")); import phi_gate
FAILS = []
# sample identifiers are assembled at run time so no identifier-shaped literal sits in the repository
MBI_S = "1EG4" + "TE5MK73"; SSN_S = "123-45-" + "6789"; MEM_S = "1234" + "56789"; MCD_S = "7452" + "486960"; DOB_S = "01/02/" + "1950"
def check(name, cond, extra=""):
    print(("ok   " if cond else "FAIL ") + name + (("  " + extra) if extra and not cond else ""))
    if not cond: FAILS.append(name)

names = {"Simcoe": "Simcoe", "Annika": "Annika", "Pignone": "Pellam"}      # a stand-in map (the real one is PHI, Drive only)
fake_map = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False); json.dump({"names": names}, fake_map); fake_map.close()
phi_gate.MAP_CANDIDATES[:] = [fake_map.name]

# --- redact() unit checks ---
r = phi_gate.redact
check("map name -> pseudonym, AMD caps form too", r("Annika Simcoe / SIMCOE,ANNIKA (pat 1)", names) == "Annika Simcoe / SIMCOE,ANNIKA (pat 1)")
check("unknown LAST,FIRST in a data file -> [name]", r('"name": "BLAKELY,NORBERT", note THACKERAY,KENDREW D (pat 77) and [name]%', names, code=False) == '"name": "[name]", note [name] (pat 77) and [name]')
check("billing vocabulary is not a name", r("DOS,CPT WOINS,WOLATE UNI20,BCBS LAST,FIRST FINALIZED,DENIED", names, code=False) == "DOS,CPT WOINS,WOLATE UNI20,BCBS LAST,FIRST FINALIZED,DENIED")
check("code keeps its tokens (content-detected)", r('import os\nx = "SMYTHE,[first]"\n', names) == 'import os\nx = "SMYTHE,[first]"\n')
check("MBI / SSN / member id / DOB -> placeholders", r("MBI %s ssn %s subscribernum=%s DOB %s" % (MBI_S, SSN_S, MEM_S, DOB_S), names, code=False) == "MBI [MBI] ssn [SSN] subscribernum=[member id] DOB [DOB]")
check("board slug from a real name -> [name]-<amdid>, pseudonym slug kept", r("id willoughby-cathleen-17477898 and pellam-[first]-17477892", names, code=False) == "id [name]-17477898 and pellam-[first]-17477892")

# --- tree mode on a throwaway checkout ---
d = tempfile.mkdtemp(prefix="phi_tree_")
def sh(c): return subprocess.run(c, shell=True, cwd=d, capture_output=True, text=True)
sh("git init -q . && git config user.email t@t && git config user.name t")
os.makedirs(os.path.join(d, "practices/ehpa/registers")); os.makedirs(os.path.join(d, "nightly/runs/2026-10-06T0710Z")); os.makedirs(os.path.join(d, "scripts/helpers"))
W = lambda rel, txt: open(os.path.join(d, rel), "w").write(txt)
W("practices/ehpa/registers/old.json", '{"name": "SIMCOE,ANNIKA", "pid": "1"}\n')
sh("git add -A && git commit -qm init")
W("practices/ehpa/registers/old.json", '{"name": "SIMCOE,ANNIKA", "pid": "1", "x": 2}\n')                       # modified, tracked
W("practices/ehpa/registers/new.json", '{"patient": "GARROW,CERYS", "subscribernum": "%s", "pid": "2"}\n' % MCD_S)   # untracked
W("nightly/runs/2026-10-06T0710Z/run digest.md", "# digest\nJONES,ISA (pat 3)\nRUN COMPLETE\n")              # Drive only
W("nightly/runs/2026-10-06T0710Z/needs_facesheet_list_section.md", "needs: WHITBY,EDWIN\n")                 # Drive only
W("nightly/runs/2026-10-06T0710Z/run_report_0710.py", 'import os\nX = "DOS,CPT"\n')                           # code, kept
W("scripts/helpers/h.py", 'import amd\nMBI = "%s"\n' % MBI_S)
r = subprocess.run([sys.executable, GATE, "tree", ".", "--cwd"], cwd=d, capture_output=True, text=True, env=dict(os.environ, PHI_MAP=fake_map.name))
out = r.stdout
check("tree exits 0", r.returncode == 0, r.stderr[-300:])
check("tracked modified register scrubbed (map)", open(os.path.join(d, "practices/ehpa/registers/old.json")).read() == '{"name": "SIMCOE,ANNIKA", "pid": "1", "x": 2}\n')
check("untracked register: unknown name -> [name], member id -> placeholder", open(os.path.join(d, "practices/ehpa/registers/new.json")).read() == '{"patient": "[name]", "subscribernum": "[member id]", "pid": "2"}\n')
check("digest taken out of the tree", not os.path.exists(os.path.join(d, "nightly/runs/2026-10-06T0710Z/run digest.md")) and "DRIVE ONLY" in out)
check("needs section taken out of the tree", not os.path.exists(os.path.join(d, "nightly/runs/2026-10-06T0710Z/needs_facesheet_list_section.md")))
check("run_report .py is code and stays", open(os.path.join(d, "nightly/runs/2026-10-06T0710Z/run_report_0710.py")).read() == 'import os\nX = "DOS,CPT"\n')
check("MBI in a helper -> [MBI]", open(os.path.join(d, "scripts/helpers/h.py")).read() == 'import amd\nMBI = "[MBI]"\n')
st = sh("git status --porcelain").stdout
check("nothing Drive-only left for git add -A", "digest" not in st and "needs_facesheet" not in st, st)
shutil.rmtree(d, ignore_errors=True); os.unlink(fake_map.name)
print("\n%d failure(s)" % len(FAILS) + (" - all guarantees hold" if not FAILS else ": " + ", ".join(FAILS)))
sys.exit(1 if FAILS else 0)
