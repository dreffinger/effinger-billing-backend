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
NEON_P = "steep-rain-" + "79347575"; NEON_O = "sparkling-silence-" + "16346164"   # the Neon project and org ids, built at run time
check("the Neon project and org ids are kept whole (exact ids, 11/12/2026)", r("projects/%s org-%s" % (NEON_P, NEON_O), {}) == "projects/%s org-%s" % (NEON_P, NEON_O))
check("a board row slug whose name is Rain or Steep is still scrubbed", r("testlast-rain-" + "12345678 steep-testfirst-" + "12345678", {}) == "[name]-12345678 [name]-12345678")
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
shutil.rmtree(d, ignore_errors=True)
# --- 11/26/2026 (the fifth round of the date-of-death check, D2): a file whose NAME carries '.unreadable-' never stays in the tree ---
# dg_drive.py keeps a deceased cache it cannot read under its own name + '.unreadable-<UTC stamp>'. Such a file holds real days of death beside chart numbers.
# Until that day it was kept beside the cache: from the workspace's registers folder the run's own mirror step copied it into the clone, this gate passed it
# over because of its ending ('.unreadable-<stamp>' is no text kind it knows), and `git add -A` staged it for a public repository. Now dg_drive.py keeps it
# outside every registers folder and every checkout, .gitignore names the pattern - and this gate has ONE rule for whatever reaches a tree all the same: the
# file is MOVED out (never deleted, never scrubbed in place) to the folder for such files and named in a line, whatever its ending, with and without --all,
# tracked or not, ignored or not. Every day and name below is invented and put together at run time.
import io, datetime, contextlib, types
DAY1 = (datetime.date.today() - datetime.timedelta(days=33)).isoformat(); DAY2 = (datetime.date.today() - datetime.timedelta(days=71)).strftime("%m/%d/%Y"); MARK = ".unreadable-"
KEPT_LINE = "KEPT OUT OF THE TREE (holds days of death - Drive only): %s -> %s"
def kept_body(n): return '{"95%02d": {"dod": "%s", "name": "%s", "checked": "x"}, "96%02d": {"dod": "%s", "na' % (n, DAY1, lf("ZZTESTLAST", "ZZFIRST"), n, DAY2)      # a cache that was cut off, as dg_drive.py keeps it: two days and a name
def run(args, cwd, **env): return subprocess.run(args, cwd=cwd, capture_output=True, text=True, env=dict(os.environ, PHI_MAP=fake_map.name, **env))
def files_in(root): return sorted(os.path.relpath(os.path.join(a, f), root) for a, _b, fs in os.walk(root) if ".git" not in a.split(os.sep) for f in fs)
def holds_a_day(root): return [f for f in files_in(root) if DAY1 in open(os.path.join(root, f), errors="replace").read() or DAY2 in open(os.path.join(root, f), errors="replace").read()]
def checkout(name, ignore=None):
    """a throwaway git checkout with a scrubbed register committed; ignore = the text of its .gitignore (None = none)"""
    c = os.path.join(BASE, name); os.makedirs(os.path.join(c, "practices", "ehpa", "registers")); os.makedirs(os.path.join(c, "docs"))
    open(os.path.join(c, "practices", "ehpa", "registers", "deceased_cache.json"), "w").write('{\n "9501": {\n  "checked": "x",\n  "dod": "[' + 'DOB]"\n }\n}')
    if ignore is not None: open(os.path.join(c, ".gitignore"), "w").write(ignore)
    subprocess.run("git init -q . && git config user.email t@t && git config user.name t && git add -A && git commit -qm init", shell=True, cwd=c, capture_output=True, text=True)
    return c
BASE = tempfile.mkdtemp(prefix="phi_tree_r5_"); REG = os.path.join("practices", "ehpa", "registers")
for all_flag in ((), ("--all",)):
    tag = "with --all" if all_flag else "without --all"; c = checkout("rule_" + ("all" if all_flag else "changed")); keep = os.path.join(BASE, "kept_" + ("all" if all_flag else "changed"))
    names = {"tracked, as it was committed": os.path.join(REG, "deceased_cache.json" + MARK + "20261101T010101Z"), "tracked, changed since": os.path.join(REG, "deceased_cache.json" + MARK + "20261102T020202Z"),
             "untracked": os.path.join(REG, "deceased_cache.json" + MARK + "20261103T030303Z"), "untracked, with a text ending": os.path.join("docs", "old_cache" + MARK + "20261104T040404Z.json"),
             "untracked, in a folder of its own": os.path.join("nightly", "runs", "x", "deceased_cache_local.json" + MARK + "20261105T050505Z-2")}
    os.makedirs(os.path.join(c, "nightly", "runs", "x"))
    for i, k in enumerate(("tracked, as it was committed", "tracked, changed since")): open(os.path.join(c, names[k]), "w").write(kept_body(i))
    subprocess.run("git add -A && git commit -qm 'a kept file an earlier run let through'", shell=True, cwd=c, capture_output=True, text=True)
    open(os.path.join(c, names["tracked, changed since"]), "w").write(kept_body(1) + " ")
    for i, k in enumerate(("untracked", "untracked, with a text ending", "untracked, in a folder of its own")): open(os.path.join(c, names[k]), "w").write(kept_body(2 + i))
    body = {k: open(os.path.join(c, v)).read() for k, v in names.items()}
    open(os.path.join(c, REG, "feed_unreadable_20261101T0101Z.json"), "w").write('{"note": "a register whose name only holds the word"}\n')      # control: no '.unreadable-' in its name
    r = run([sys.executable, GATE, "tree", ".", "--cwd"] + list(all_flag), c, DG_UNREADABLE_DIR=keep); out = r.stdout
    kept = {k: [l.split(" -> ", 1)[1] for l in out.splitlines() if l.startswith(KEPT_LINE.split("%s")[0] + v + " -> ")] for k, v in names.items()}
    check("unreadable rule (%s): every file whose NAME carries '.unreadable-' is taken OUT of the tree - tracked as it was committed, tracked and changed since, untracked, with a text ending (.json) or none, in a registers folder or anywhere else - and the gate still ends 0" % tag,
          r.returncode == 0 and not any(os.path.exists(os.path.join(c, v)) for v in names.values()) and [f for f in files_in(c) if MARK in f] == [], "%s | %s | %s" % (r.returncode, [f for f in files_in(c) if MARK in f], r.stderr[-300:]))
    check("unreadable rule (%s): ... each is MOVED, never deleted and never rewritten: it lies in the folder for such files byte for byte, under its own name, and ONE line names it - 'KEPT OUT OF THE TREE (holds days of death - Drive only): <its path in the tree> -> <where it lies now>'" % tag,
          all(len(v) == 1 and os.path.dirname(v[0]) == keep and os.path.basename(v[0]).startswith(os.path.basename(names[k])) and open(v[0]).read() == body[k] for k, v in kept.items()) and sorted(os.listdir(keep)) == sorted(os.path.basename(v[0]) for v in kept.values()),
          "%s | %s" % (kept, out[-600:]))
    add = run(["git", "add", "-A", "--dry-run"], c).stdout.splitlines()
    check("unreadable rule (%s): ... `git add -A` would then stage no such file - only the removal of the two an earlier run had let through - no file left in the tree holds a day, and the register whose name merely holds the word 'unreadable' stays where it is" % tag,
          not any(l.startswith("add ") and MARK in l for l in add) and sorted(l for l in add if MARK in l) == sorted("remove '%s'" % names[k] for k in ("tracked, as it was committed", "tracked, changed since"))
          and holds_a_day(c) == [] and os.path.exists(os.path.join(c, REG, "feed_unreadable_20261101T0101Z.json")), "%s | %s" % (add, holds_a_day(c)))
    check("unreadable rule (%s): ... and the summary line counts them among the files kept out of the tree" % tag, ("%d kept out of the tree" % len(names)) in out.splitlines()[-1], str(out.splitlines()[-1:]))
# ... with the pattern in .gitignore git no longer LISTS such a file - the rule holds all the same (the gate looks for the name itself, not only at what git reports)
c = checkout("rule_ignored", "*.json\n!practices/**/*.json\n*" + MARK + "*\n"); keep = os.path.join(BASE, "kept_ignored"); f1 = os.path.join(REG, "deceased_cache.json" + MARK + "20261106T060606Z"); open(os.path.join(c, f1), "w").write(kept_body(7))
st = run(["git", "status", "--porcelain", "--untracked-files=all"], c).stdout; r = run([sys.executable, GATE, "tree", ".", "--cwd"], c, DG_UNREADABLE_DIR=keep)
check("unreadable rule: a file git IGNORES (the pattern '*.unreadable-*' stands in .gitignore, so git status does not list it) is moved out of the tree too - it never lies inside a checkout, staged or not",
      MARK not in st and r.returncode == 0 and not os.path.exists(os.path.join(c, f1)) and [open(os.path.join(keep, n)).read() for n in os.listdir(keep)] == [kept_body(7)] and (KEPT_LINE % (f1, os.path.join(keep, os.path.basename(f1)))) in r.stdout.splitlines(), "%s | %s" % (st, r.stdout[-400:]))
# ... where it goes: the folder the environment names, unless that folder lies inside a git checkout or under a registers folder - then, and when none is named, <the system's temporary folder>/deceased_cache_unreadable
res = {}
for label, folder in (("no folder named", None), ("a folder inside this checkout", "IN"), ("a folder inside another checkout", "OTHER"), ("a registers folder", os.path.join(BASE, "elsewhere", "registers", "kept")), ("a good folder", os.path.join(BASE, "kept_good"))):
    c = checkout("where_%d" % len(res)); f1 = os.path.join(REG, "deceased_cache.json" + MARK + "20261107T070707Z"); open(os.path.join(c, f1), "w").write(kept_body(8)); tmp_ = os.path.join(BASE, "systmp_%d" % len(res)); os.makedirs(tmp_)
    other = checkout("where_other_%d" % len(res)); folder = os.path.join(c, "kept") if folder == "IN" else os.path.join(other, "kept") if folder == "OTHER" else folder
    env = dict(TMPDIR=tmp_, **({"DG_UNREADABLE_DIR": folder} if folder else {})); r = subprocess.run([sys.executable, GATE, "tree", ".", "--cwd"], cwd=c, capture_output=True, text=True, env={k: v for k, v in dict(os.environ, PHI_MAP=fake_map.name, **env).items() if folder or k != "DG_UNREADABLE_DIR"})
    res[label] = (r.returncode, os.path.exists(os.path.join(c, f1)), files_in(os.path.join(tmp_, "deceased_cache_unreadable")) if os.path.isdir(os.path.join(tmp_, "deceased_cache_unreadable")) else [], [f for f in files_in(folder) if MARK in f] if folder and os.path.isdir(folder) else [], [f for f in files_in(other) if MARK in f])
check("unreadable rule (the place): with no folder named the file goes to <the system's temporary folder>/deceased_cache_unreadable/; a folder the environment names inside THIS checkout, inside another checkout or under a registers folder is refused and the temporary folder is used; a good folder is used as named",
      all(res[k][:2] == (0, False) and len(res[k][2]) == 1 and res[k][3] == [] and res[k][4] == [] for k in ("no folder named", "a folder inside this checkout", "a folder inside another checkout", "a registers folder"))
      and res["a good folder"][:3] == (0, False, []) and len(res["a good folder"][3]) == 1, str(res))
# ... and when NO folder can take it: the file is not deleted, not left for a commit unseen - the gate says so and ends non-zero (mirror.py then commits nothing)
c = checkout("stuck"); f1 = os.path.join(REG, "deceased_cache.json" + MARK + "20261108T080808Z"); open(os.path.join(c, f1), "w").write(kept_body(9)); wall = os.path.join(BASE, "a_file_in_the_way"); open(wall, "w").write("a file where a folder would have to be")
def gate_here(root, folder, system_tmp):
    """the gate's tree mode INSIDE this process (the system's temporary folder can only be changed for sure here: a program started with an unusable TMPDIR falls back to /tmp) -> (its exit code, what it printed)"""
    old_tmp, old_env, buf = tempfile.tempdir, os.environ.pop("DG_UNREADABLE_DIR", None), io.StringIO()
    try:
        tempfile.tempdir = system_tmp
        if folder: os.environ["DG_UNREADABLE_DIR"] = folder
        with contextlib.redirect_stdout(buf): rc = phi_gate.tree(["."], root=root)
    except Exception as e: rc = "raised %s: %s" % (type(e).__name__, e)
    finally:
        tempfile.tempdir = old_tmp; os.environ.pop("DG_UNREADABLE_DIR", None)
        if old_env is not None: os.environ["DG_UNREADABLE_DIR"] = old_env
    return rc, buf.getvalue()
rc1, out1 = gate_here(c, os.path.join(wall, "kept"), os.path.join(wall, "tmp")); rc2, out2 = gate_here(c, None, os.path.join(c, "tmp_in_the_tree"))
check("unreadable rule: when no folder outside the tree can take the file - none can be made, or the system's temporary folder itself lies inside the checkout - it is NEVER deleted: it stays byte for byte, nothing is written into the tree, and the gate does not pass in silence: one line 'NOT KEPT OUT OF THE TREE: ...' and a non-zero exit, so the mirror commits nothing",
      rc1 not in (0, None) and rc2 not in (0, None) and isinstance(rc1, int) and isinstance(rc2, int) and open(os.path.join(c, f1)).read() == kept_body(9) and not os.path.exists(os.path.join(c, "tmp_in_the_tree"))
      and all(any(l.startswith("NOT KEPT OUT OF THE TREE: " + f1) for l in o.splitlines()) for o in (out1, out2)), "%s | %s | %s | %s" % (rc1, out1[-300:], rc2, out2[-300:]))
# ---- what the fifth round's own mutation pass let through at first (each now with its check) ----
c = checkout("stuck_text"); f2 = os.path.join(REG, "deceased_cache.json" + MARK + "20261109T090909Z.json"); open(os.path.join(c, f2), "w").write(kept_body(10))
rc3, out3 = gate_here(c, os.path.join(wall, "kept"), os.path.join(wall, "tmp"))
check("unreadable rule: a file that could be moved to no folder is left EXACTLY as it is also when its ending is one the gate knows (.json) - the other rules never get it: it is not scrubbed in place (its days are the only copy there is), and the gate ends non-zero",
      isinstance(rc3, int) and rc3 != 0 and open(os.path.join(c, f2)).read() == kept_body(10) and not any(l.startswith("scrubbed in place: " + f2) for l in out3.splitlines()) and any(l.startswith("NOT KEPT OUT OF THE TREE: " + f2) for l in out3.splitlines()), "%s | %s" % (rc3, out3[-400:]))
c = checkout("same_name"); keep = os.path.join(BASE, "kept_same_name"); n1 = "deceased_cache.json" + MARK + "20261110T101010Z"; os.makedirs(os.path.join(c, "other_place")); os.makedirs(keep)
open(os.path.join(c, REG, n1), "w").write(kept_body(11)); open(os.path.join(c, "other_place", n1), "w").write(kept_body(12)); open(os.path.join(keep, n1), "w").write("kept by an earlier run")
r = run([sys.executable, GATE, "tree", ".", "--cwd"], c, DG_UNREADABLE_DIR=keep); got = {n: open(os.path.join(keep, n)).read() for n in sorted(os.listdir(keep))}
check("unreadable rule: a name that is TAKEN in the folder for such files - by a file an earlier run kept, or by a file of the same name from another folder of the tree - is never written over: each file moved gets a name of its own (name, name-2, name-3), and every file is there byte for byte",
      r.returncode == 0 and got.get(n1) == "kept by an earlier run" and sorted(v for k, v in got.items() if k != n1) == sorted([kept_body(11), kept_body(12)]) and sorted(got) == [n1, n1 + "-2", n1 + "-3"] and not [f for f in files_in(c) if MARK in f], "%s | %s" % (sorted(got), r.stdout[-300:]))
c = checkout("link_place"); other = checkout("link_other"); f3 = os.path.join(REG, "deceased_cache.json" + MARK + "20261111T111111Z"); open(os.path.join(c, f3), "w").write(kept_body(13)); os.makedirs(os.path.join(other, "by_link"))
link = os.path.join(BASE, "a_link_that_looks_harmless"); os.symlink(os.path.join(other, "by_link"), link); tmp_ = os.path.join(BASE, "systmp_link"); os.makedirs(tmp_)
r = run([sys.executable, GATE, "tree", ".", "--cwd"], c, DG_UNREADABLE_DIR=link, TMPDIR=tmp_)
check("unreadable rule (the place): a LINK is judged by where it LEADS - the environment names a link whose own path looks harmless and that points into another checkout: refused, the file goes to the system's temporary folder and nothing is written through the link",
      r.returncode == 0 and not os.path.exists(os.path.join(c, f3)) and files_in(os.path.join(tmp_, "deceased_cache_unreadable")) == [os.path.basename(f3)] and [f for f in files_in(other) if MARK in f] == [], "%s | %s" % (r.stdout[-300:], files_in(other)))
c = checkout("short_copy"); f4 = os.path.join(REG, "deceased_cache.json" + MARK + "20261112T121212Z"); open(os.path.join(c, f4), "w").write(kept_body(14)); keep = os.path.join(BASE, "kept_short"); tmp_ = os.path.join(BASE, "systmp_short"); os.makedirs(tmp_)
class Short:      # a file that takes fewer bytes than it is given and says nothing (a full disk on some file systems, a mount that drops out)
    def __init__(self, fh): self.fh = fh
    def write(self, data): return self.fh.write(data[:len(data) // 2])
    def __enter__(self): return self
    def __exit__(self, *a): self.fh.close()
real_os = phi_gate.os; phi_gate.os = types.SimpleNamespace(**{k: getattr(os, k) for k in dir(os) if not k.startswith("__")})
phi_gate.os.fdopen = lambda fd, mode="r", *a, **k: Short(os.fdopen(fd, mode, *a, **k)) if "b" in mode else os.fdopen(fd, mode, *a, **k)
try: rc4, out4 = gate_here(c, keep, tmp_)
finally: phi_gate.os = real_os
check("unreadable rule: the copy is READ BACK and compared before the file is taken out of the tree - a copy that came out short (the folder took fewer bytes than it was given and said nothing) is no copy: it is taken away again, the file stays in the tree byte for byte, and the gate says so and ends non-zero - never the file gone and half of it kept",
      isinstance(rc4, int) and rc4 != 0 and open(os.path.join(c, f4)).read() == kept_body(14) and files_in(keep) == [] and files_in(os.path.join(tmp_, "deceased_cache_unreadable")) == []
      and any(l.startswith("NOT KEPT OUT OF THE TREE: " + f4) for l in out4.splitlines()), "%s | %s" % (rc4, out4[-300:]))
c = checkout("modes"); f5 = os.path.join(REG, "deceased_cache.json" + MARK + "20261113T131313Z"); open(os.path.join(c, f5), "w").write(kept_body(15)); keep = os.path.join(BASE, "kept_modes")
r = run([sys.executable, GATE, "tree", ".", "--cwd"], c, DG_UNREADABLE_DIR=keep); m_file = os.stat(os.path.join(keep, os.path.basename(f5))).st_mode & 0o777 if os.path.isfile(os.path.join(keep, os.path.basename(f5))) else None
check("unreadable rule: the file moved out holds days of death - only the user the run works as can read it (mode 600), and the folder the gate made for it is that user's alone (mode 700)",
      r.returncode == 0 and m_file == 0o600 and os.stat(keep).st_mode & 0o777 == 0o700, "%s | %s" % (m_file and oct(m_file), r.stdout[-200:]))
# ---- END TO END: step 0c's merge, the Button prompt's own mirror command, this gate, `git add -A` - in a checkout WITHOUT the ignore line and in one WITH it ----
DG = os.path.join(ROOT, "scripts", "helpers", "dg_drive.py"); IGNORE = open(os.path.join(ROOT, ".gitignore")).read()
check("the repository's .gitignore names the pattern '*.unreadable-*' as a line of its own", ("*" + MARK + "*") in IGNORE.splitlines(), IGNORE[-200:])
for label, ignore in (("WITHOUT the ignore line", "\n".join(l for l in IGNORE.splitlines() if MARK not in l) + "\n"), ("WITH the ignore line", "\n".join(l for l in IGNORE.splitlines() if MARK not in l) + "\n*" + MARK + "*\n")):
    n = "e2e_" + label.split()[0].lower(); root = os.path.join(BASE, n); ws = os.path.join(root, "home", "claude", "unbilled"); os.makedirs(os.path.join(ws, "registers")); os.makedirs(os.path.join(ws, "inbox")); tmp_ = os.path.join(root, "tmp"); os.makedirs(tmp_)
    BASE, _base = os.path.join(root, "home", "claude"), BASE; clone = checkout("effinger-billing-backend", ignore); BASE = _base
    full = json.dumps({"9501": {"dod": DAY1, "checked": "x", "src": "stedi-medicare-271", "name": lf("ZZTESTLAST", "ZZFIRST")}, "9502": {"dod": DAY2, "checked": "x", "src": "amd-medicare-271", "name": lf("ZZOTHER", "ZZPERSON")}}, indent=1, sort_keys=True)
    wsc = os.path.join(ws, "registers", "deceased_cache.json"); clc = os.path.join(clone, REG, "deceased_cache.json"); open(wsc, "w").write(full[:-25])      # the workspace's cache: real-looking days, written with indent as the guard writes it - and CUT OFF
    json.dump({"format": "deceased_cache_drive v2", "dated": {"9501": [DAY1, "x"]}, "nodeath": {}, "noday": {}}, open(os.path.join(ws, "inbox", "deceased_cache_drive.json"), "w"))
    env = {k: v for k, v in dict(os.environ, PHI_MAP=fake_map.name, TMPDIR=tmp_).items() if k != "DG_UNREADABLE_DIR"}
    def sh2(args, cwd, shell=False): return subprocess.run(args, cwd=cwd, capture_output=True, text=True, env=env, shell=shell)
    u1 = sh2([sys.executable, DG, "unpack", os.path.join(ws, "inbox", "deceased_cache_drive.json"), wsc, clc], ws)                                  # (1) step 0c's merge, as the prompts write it: into BOTH caches
    _t = open(clc).read(); open(clc, "w").write(_t[:-12]); u2 = sh2([sys.executable, DG, "unpack", os.path.join(ws, "inbox", "deceased_cache_drive.json"), wsc, clc], ws)      # ... the clone's own register is cut off later in the run and merged once more (the clause's ONE second merge)
    old_kept = os.path.join(ws, "registers", "deceased_cache.json" + MARK + "20261120T101010Z"); open(old_kept, "w").write(full[:-25])                 # ... and a file the round before kept BESIDE the cache lies in the workspace still (a state bundle brings it back)
    cp = sh2("cp -pn %s/registers/* %s/" % (ws, REG), clone, shell=True)                                                                              # (2) the Button prompt's own command of the mirror step
    g = sh2([sys.executable, GATE, "tree", "."] + ["--cwd"], clone)                                                                                    # (3) this gate in tree mode, as mirror.py runs it before the commit
    add = sh2(["git", "add", "-A", "--dry-run"], clone).stdout.splitlines()                                                                           # (4) what `git add -A` would stage
    staged = [l.split("'", 1)[1].rstrip("'") for l in add if l.startswith("add ")]; kd = os.path.join(tmp_, "deceased_cache_unreadable"); kept = sorted(os.listdir(kd)) if os.path.isdir(kd) else []
    check("end to end, %s: step 0c's merge on a cut-off workspace cache and - a second time - on the clone's own cut-off register: both are replaced (two lines 'DECEASED CACHE REPLACED: ...', exit 0), and NOTHING that unpack keeps lies in the workspace's registers folder or inside the checkout" % label,
          u1.returncode == 0 and u2.returncode == 0 and len([l for l in (u1.stdout + u2.stdout).splitlines() if l.startswith("DECEASED CACHE REPLACED: ")]) == 2 and sorted(os.listdir(os.path.join(ws, "registers"))) == ["deceased_cache.json", os.path.basename(old_kept)]
          and "Traceback" not in u1.stderr + u2.stderr, "%s %s | %s | %s" % (u1.returncode, u2.returncode, (u1.stdout + u2.stdout)[-500:], (u1.stderr + u2.stderr)[-300:]))
    check("end to end, %s: ... the mirror step's `cp -pn <workspace>/registers/* practices/ehpa/registers/`, then the gate, then `git add -A`: NO file that holds a day of death is staged, and no file with a day or with '.unreadable-' in its name is left anywhere inside the checkout - also not the one the round before had kept beside the cache" % label,
          cp.returncode == 0 and g.returncode == 0 and not any(MARK in s for s in staged) and not any(DAY1 in open(os.path.join(clone, s), errors="replace").read() or DAY2 in open(os.path.join(clone, s), errors="replace").read() for s in staged if os.path.isfile(os.path.join(clone, s)))
          and holds_a_day(clone) == [] and [f for f in files_in(clone) if MARK in f] == [], "%s | %s | %s | %s" % (add, holds_a_day(clone), g.stdout[-400:], g.stderr[-200:]))
    check("end to end, %s: ... every kept file - the two of this merge and the older one the gate took out of the tree - lies under <the system's temporary folder>/deceased_cache_unreadable/, byte for byte; the clone's own register was scrubbed in the same pass, as always" % label,
          len(kept) == 3 and sorted(open(os.path.join(kd, k)).read() for k in kept).count(full[:-25]) == 2 and DAY1 not in open(clc).read() and ("scrubbed in place: " + os.path.join(REG, "deceased_cache.json")) in g.stdout, "%s | %s" % (kept, g.stdout[-400:]))
shutil.rmtree(BASE, ignore_errors=True)
os.unlink(fake_map.name)
print("\n%d failure(s)" % len(FAILS) + (" - all guarantees hold" if not FAILS else ": " + ", ".join(FAILS)))
sys.exit(1 if FAILS else 0)
