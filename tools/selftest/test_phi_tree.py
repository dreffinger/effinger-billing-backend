#!/usr/bin/env python3
# PLAIN ENGLISH (offline self-test of the PHI tree gate, 10/6/2026)
# Decides: nothing. Builds a throwaway git checkout with sample PHI in registers, a digest and code, runs
#   `phi_gate.py tree .` the way mirror.py does before `git add -A`, and asserts: names -> pseudonym or [name],
#   identifiers -> placeholders, a digest / needs section never enters the tree, code keeps its tokens and still
#   compiles, billing vocabulary (DOS,CPT / LAST,FIRST / WOINS,WOLATE) is left alone. No AMD, no network.
#   Every sample name here is invented (none is in the practice's map) - the 10/6 afternoon lesson: the first
#   version of this test used real surnames as samples. Every LAST,FIRST sample is assembled at run time (lf)
#   so the tree gate, which scrubs this file like any other before a commit, leaves the test alone.
# Run: python3 tools/selftest/test_phi_tree.py   (exit 1 on any failure)
import os, sys, json, subprocess, tempfile, shutil
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GATE = os.path.join(ROOT, "tools", "mirror", "phi_gate.py")
sys.path.insert(0, os.path.join(ROOT, "tools", "mirror")); import phi_gate
FAILS = []
# sample identifiers are assembled at run time so no identifier-shaped literal sits in the repository
MBI_S = "1EG4" + "TE5MK73"; SSN_S = "123-45-" + "6789"; MEM_S = "1234" + "56789"; MCD_S = "7452" + "486960"; DOB_S = "01/02/" + "1950"
def lf(last, first): return last + "," + first          # AMD's LAST,FIRST form, built so no literal sits here
def check(name, cond, extra=""):
    print(("ok   " if cond else "FAIL ") + name + (("  " + extra) if extra and not cond else ""))
    if not cond: FAILS.append(name)
def compiles(src):
    try: compile(src, "<sample>", "exec"); return True
    except SyntaxError: return False

names = {"Zorbaz": "Simcoe", "Annika": "Annika", "Pignone": "Pellam"}      # a stand-in map (the real one is PHI, Drive only)
fake_map = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False); json.dump({"names": names}, fake_map); fake_map.close()
phi_gate.MAP_CANDIDATES[:] = [fake_map.name]

# --- redact() unit checks ---
r = phi_gate.redact
check("map name -> pseudonym, AMD caps form too", r("Annika Zorbaz / %s (pat 1)" % lf("ZORBAZ", "ANNIKA"), names) == "Annika Simcoe / %s (pat 1)" % lf("SIMCOE", "ANNIKA"))
check("unknown LAST,FIRST in a data file -> [name], the AMD % wildcard stays", r('"name": "%s", note %s D (pat 77) and %s%%' % (lf("VANTABLE", "OTTO"), lf("QUARREL", "KENDREW"), lf("XANTHER", "RUFFORD")), names, code=False) == '"name": "[name]", note [name] (pat 77) and [name]%')
check("billing vocabulary is not a name", r("DOS,CPT WOINS,WOLATE UNI20,BCBS LAST,FIRST FINALIZED,DENIED", names, code=False) == "DOS,CPT WOINS,WOLATE UNI20,BCBS LAST,FIRST FINALIZED,DENIED")
check("code keeps its tokens, string literals and comments are scrubbed", r('import os\nDOS,CPT = 1, 2\nx = "%s"  # %s\n' % (lf("XANTHER", "JOHN"), lf("KIRBY", "ANN")), names) == 'import os\nDOS,CPT = 1, 2\nx = "[name]"  # [name]\n')
check("a hyphenated pseudonym inside a module name becomes underscore", r("import medicaid_quenby_fix\n", {"Quenby": "Garland-G"}) == "import medicaid_garland_g_fix\n")
check("MBI / SSN / member id / DOB -> placeholders", r("MBI %s ssn %s subscribernum=%s DOB %s" % (MBI_S, SSN_S, MEM_S, DOB_S), names, code=False) == "MBI [MBI] ssn [SSN] subscribernum=[member id] DOB [DOB]")
check("board slug from a real name -> [name]-<amdid>, pseudonym slug keeps the surname and hides an unmapped first name", r("id xanther-mira-" + "10000001 and pellam-sue-" + "10000002", names, code=False) == "id [name]-10000001 and pellam-[first]-10000002")

# --- the 10/6 afternoon lessons (what the history rewrite exposed) ---
names2 = {"Quenby": "Garland-G", "Field": "Fenwick", "Vantable": "Lowry"}
src = 'import amd\nQUENBY_RPROV = "x"; QUENBY = "prof15"  # (Quenby) QUENBY\nL("not Quenby")\n'
out = r(src, names2)
check("UPPERCASE hyphenated pseudonym: underscore in identifiers, hyphen in strings and comments", out == 'import amd\nGARLAND_G_RPROV = "x"; GARLAND_G = "prof15"  # (Garland-G) GARLAND-G\nL("not Garland-G")\n', out)
check("...and it compiles", compiles(out))
src = 'import amd\nsh("git rev-parse --field HEAD"); field_list = []; f = "vantable_rebill.py"; k = {"vantable": 1, "field": 2}; t = "Field FIELD"\n'
out = r(src, names2)
check("ordinary-word surname: lowercase stays a word (--field, field_list) except as a whole dict key; Title/CAPS map; other surnames map in slugs and keys", out == 'import amd\nsh("git rev-parse --field HEAD"); field_list = []; f = "lowry_rebill.py"; k = {"lowry": 1, "fenwick": 2}; t = "Fenwick FENWICK"\n', out)
src = "import amd\ntargets={'1':('%s',CUT),'2':('%s',CUT)}\nq='name=\"%s%%%%\"' %% t\n" % (lf("VANTABLE", "MIRA"), lf("XANTHER", "OTTO"), lf("XANTHER", "OTTO"))
out = r(src, names2)
check("LAST,FIRST in a quoted literal keeps its closing quote and the %% format escape", out == "import amd\ntargets={'1':('LOWRY,[first]',CUT),'2':('[name]',CUT)}\nq='name=\"[name]%%\"' % t\n", out)
check("...and it compiles", compiles(out))
check("apostrophe inside a name is kept, a trailing one is not swallowed", r("%s (pat 5); '%s'" % (lf("O'HARE", "MARISA-ANN"), lf("XANTHER", "JOE")), names, code=False) == "[name] (pat 5); '[name]'")
check("a path with a lowercase surname is mapped, underscore-safe", r("scripts/helpers/vantable_check_0510.py nightly/quenby_fix.py", names2, code=False) == "scripts/helpers/lowry_check_0510.py nightly/garland_g_fix.py")

# --- the second round (what the rewrite hunt found) - every sample value is assembled at run time ---
MEM_A = "XJJH" + "12345678"; MEM_H = "H72" + "12345"; POL = "987" + "654321"; MEM_W = "W29" + "1234567"
DOB8 = "1950" + "0102"; ISO = "1950-01-" + "02T00:00:00"; DOD = "2025-08-" + "30"; BORN = "1/2/" + "50"
PH1 = "850-555-" + "0101"; PH2 = "+1 850-555-" + "0102"; PH3 = "(850) 555-" + "0103"
ADDR1 = "768 RED OAK " + "DR"; ADDR2 = "2677 Old Bainbridge " + "Rd Apt 911"
check("JSON name fields: unmapped last -> [name], pseudonym last keeps a pseudonym first and hides another, JR suffix, single-part fields",
      r(('"name": "%s", "patient": "%s", "patientname": "%s B", "responsibleparty": "%s", "first' + 'name": "OTTO", "last' + 'name": "SIMCOE"') % (lf("VANTABLE JR", "OTTO"), lf("SIMCOE", "OTTO"), lf("SIMCOE", "ANNIKA"), lf("SIMCOE JR", "ANNIKA")), names, code=False)
      == ('"name": "[name]", "patient": "SIMCOE,[first]", "patientname": "%s B", "responsibleparty": "%s", "first' + 'name": "[name]", "last' + 'name": "SIMCOE"') % (lf("SIMCOE", "ANNIKA"), lf("SIMCOE JR", "ANNIKA")))
check("bare LAST,FIRST: pseudonym last + unknown first -> LAST,[first] (mixed case too), a suffix, a pat-id form",
      r("note %s (pat 3) and %s D, %s; %s" % (lf("SIMCOE", "Otto"), lf("SIMCOE", "ANNIKA"), lf("XANTHER JR", "OTTO"), lf("SIMCOE", "OTTO")), names, code=False)
      == "note SIMCOE,[first] (pat 3) and %s D, [name]; SIMCOE,[first]" % lf("SIMCOE", "ANNIKA"))
check("board slugs in code strings: unknown last -> [name]-id, pseudonym last + unknown first -> last-[first]-id, an initial is kept",
      r('import x\nrow("xanther-mira-' + '10000001"); row("simcoe-mira-' + '10000002"); row("simcoe-annika-l-' + '10000003")\n', names)
      == 'import x\nrow("[name]-10000001"); row("simcoe-[first]-10000002"); row("simcoe-annika-l-10000003")\n')
check("member / subscriber / policy ids in JSON fields and prose; payer ids untouched",
      r('"subscribernum": "%s", member %s and policy %s, "member": "%s", payer 87726, Medicaid 77027 ACTIVE' % (MEM_A, MEM_H, POL, MEM_W), names, code=False)
      == '"subscribernum": "[member id]", member [member id] and policy [member id], "member": "[member id]", payer 87726, Medicaid 77027 ACTIVE')
check("DOB / DOD in every shape", r('"dob": "%s", "death": "%s", dateOfBirth "%s", dob %s, born %s, "dod": "%s"' % (ISO, DOB8, DOB8, DOB8, BORN, DOD), names, code=False)
      == '"dob": "[DOB]", "death": "[DOB]", dateOfBirth "[DOB]", dob [DOB], born [DOB], "dod": "[DOB]"')
check("a 9-10 character MBI fragment", r("others MB IG:%s MEDICARE" % MBI_S[:10], names, code=False) == "others MB IG:[MBI] MEDICARE")
check("phones: JSON fields and a patient's phone in prose; the practice 'Phone:' line is kept",
      r('"phone": "%s", home phone %s, Phone: %s practice' % (PH1, PH2, PH3), names, code=False) == '"phone": "[phone]", home phone [phone], Phone: %s practice' % PH3)
check("addresses: JSON fields and a street line in prose; '1 visit with Dr' is kept",
      r('"address1": "%s", at %s, 1 visit with Dr Effinger' % (ADDR1, ADDR2), names, code=False) == '"address1": "[address]", at [address], 1 visit with Dr Effinger')
check("pending-admit file names: last_first_yyyymmdd -> [name]_[DOB]; a pseudonym pair keeps its names",
      r("patient_db/pending_admits/xanther_mira_%s.json and simcoe_annika_%s.json" % (DOB8, DOB8), names, code=False)
      == "patient_db/pending_admits/[name]_[DOB].json and simcoe_annika_[DOB].json")
check("an ordinary-word surname as a scanned-sheet file name or helper stem is mapped", r("Omnissa Horizon field.pdf, field_1002.py, --field, a field", names2, code=False) == "Omnissa Horizon fenwick.pdf, fenwick_1002.py, --field, a field")
# a second pass over an already-scrubbed file must change nothing (the tree gate re-scrubs every changed file)
ADM = "07/19/" + "2026"; DOS = "2/20/" + "2026"                                   # dates of service, never a DOB
once = r("dob %s, admitted %s; DOD %s then %s" % (BORN, ADM, DOD, DOS), names, code=False)
check("DOB placeholder stops the rule: the next date on the line survives", once == "dob [DOB], admitted %s; DOD [DOB] then %s" % (ADM, DOS), once)
check("...and a second pass is a no-op", r(once, names, code=False) == once)
names3 = {"Zorbaz": "Simcoe", "Simcoe": "Pellam"}
check("a real name that is also a pseudonym is left alone, so pseudonymized text is stable", r("Zorbaz and Simcoe", names3) == "Simcoe and Simcoe" and r(r("Zorbaz", names3), names3) == "Simcoe")

# --- tree mode on a throwaway checkout ---
d = tempfile.mkdtemp(prefix="phi_tree_")
def sh(c): return subprocess.run(c, shell=True, cwd=d, capture_output=True, text=True)
sh("git init -q . && git config user.email t@t && git config user.name t")
os.makedirs(os.path.join(d, "practices/ehpa/registers")); os.makedirs(os.path.join(d, "nightly/runs/2026-10-06T0710Z")); os.makedirs(os.path.join(d, "scripts/helpers"))
W = lambda rel, txt: open(os.path.join(d, rel), "w").write(txt)
W("practices/ehpa/registers/old.json", '{"name": "%s", "pid": "1"}\n' % lf("ZORBAZ", "ANNIKA"))
sh("git add -A && git commit -qm init")
W("practices/ehpa/registers/old.json", '{"name": "%s", "pid": "1", "x": 2}\n' % lf("ZORBAZ", "ANNIKA"))                       # modified, tracked
W("practices/ehpa/registers/new.json", '{"patient": "%s", "subscribernum": "%s", "pid": "2"}\n' % (lf("PRATCHETT", "CERYS"), MCD_S))   # untracked
W("nightly/runs/2026-10-06T0710Z/run digest.md", "# digest\n%s (pat 3)\nRUN COMPLETE\n" % lf("XANTHER", "ISA"))              # Drive only
W("nightly/runs/2026-10-06T0710Z/needs_facesheet_list_section.md", "needs: %s\n" % lf("UMBERFIELD", "EDWIN"))             # Drive only
W("nightly/runs/2026-10-06T0710Z/run_report_0710.py", 'import os\nX = "DOS,CPT"\n')                           # code, kept
W("scripts/helpers/h.py", 'import amd\nMBI = "%s"\n' % MBI_S)
r = subprocess.run([sys.executable, GATE, "tree", ".", "--cwd"], cwd=d, capture_output=True, text=True, env=dict(os.environ, PHI_MAP=fake_map.name))
out = r.stdout
check("tree exits 0", r.returncode == 0, r.stderr[-300:])
check("tracked modified register scrubbed (map)", open(os.path.join(d, "practices/ehpa/registers/old.json")).read() == '{"name": "%s", "pid": "1", "x": 2}\n' % lf("SIMCOE", "ANNIKA"))
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
