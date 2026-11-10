#!/usr/bin/env python3
# PLAIN ENGLISH (offline self-test of the workspace state bundle, 11/10/2026)
# Decides: nothing. Builds a throwaway folder of invented files, packs it with tools/bootstrap/ws_bundle.py, unpacks the parts into
#   a second throwaway folder and compares every file byte for byte. No AMD, no Drive, no network, no real workspace and no patient
#   data - every file name and every byte here is invented at run time. It proves:
#     - a bundle of MORE THAN 100 parts comes back whole. Until 11/10/2026 unpack joined the part files in text order, where part100
#       sorts between part10 and part11, so the default pack (267 parts that day) could not be restored in a fresh container: unpack
#       refused it with a sha256 mismatch, or stopped on a base64 error, and the run's state silently did not carry over;
#     - the order comes from the NUMBER after ".part" however it is written: two digits with a third when needed (how every bundle
#       before the fix was named), no leading zeros at all, or padded wider than needed;
#     - pack names a set in ONE width (part001 .. part267), so a plain text sort of a new set is also its number order, and a small
#       set keeps the two-digit names it always had (part01 .. part03);
#     - a 3-part bundle still round-trips, and so does a bundle of more than 1,000 parts (four-digit numbers);
#     - a missing part and an altered part are refused: nothing is written, and both are named, in number order; a part that was
#       cut short is refused the same way instead of stopping the script with an error;
#     - a file in the folder that is not a part (a second download of one) is left out and said so, never joined in; one part
#       in the folder twice under two spellings is refused, and the report says the listed parts are intact rather than "unknown";
#     - with two sets in one folder the newer one is restored, whichever of the two is the big one;
#     - the command lines the routine prompts name (pack --out DIR, unpack DIR) do the same with the real part size;
#     - secrets/, the credential, session and lock files and old bundle files never travel.
# Run: python3 tools/selftest/test_ws_bundle.py   (exit 1 on any failure)
import os, sys, io, re, json, glob, shutil, random, hashlib, tempfile, subprocess, contextlib, atexit
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOOL = os.path.join(ROOT, "tools", "bootstrap", "ws_bundle.py")
sys.path.insert(0, os.path.join(ROOT, "tools", "bootstrap")); import ws_bundle
FAILS = []
def check(name, cond, extra=""):
    print(("ok   " if cond else "FAIL ") + name + (("  -> " + str(extra)[:400]) if extra != "" and not cond else ""))
    if not cond: FAILS.append(name)

TMP = tempfile.mkdtemp(prefix="wsbundle_selftest_")
atexit.register(shutil.rmtree, TMP, ignore_errors=True)        # every throwaway folder goes when the test ends, however it ends
SEQ = [0]
def fresh(label):                                              # a new empty throwaway folder
    SEQ[0] += 1; d = os.path.join(TMP, "%02d_%s" % (SEQ[0], label)); os.makedirs(d); return d
RND = random.Random(1110)                                      # the same invented bytes on every run
def junk(n):                                                   # n random bytes: gzip cannot shrink them, so the number of parts is predictable
    return RND.getrandbits(8 * n).to_bytes(n, "big")
def put(d, rel, data):
    p = os.path.join(d, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "wb").write(data if isinstance(data, bytes) else data.encode())

NEVER = ("secrets", ".amd_cred.json", ".session.json", ".amd_login_lock", ".lock", "outbox", ".b64", "__pycache__")
def make_workspace(label, files, size, marker):
    """A folder shaped like the nightly workspace: state files at the top, registers/, patient_db/ (nested), era_details/ and
    tools/ - plus the kinds of file the tool promises to leave behind. Returns (folder, {relative path: sha256} of what must travel)."""
    d = fresh(label)
    put(d, "needs_facesheet_list.md", "# invented needs list - " + marker + "\n")
    put(d, "laterality_flag_log.md", "invented log\n")
    put(d, "precheck_cache.json", json.dumps({"invented": True, "marker": marker}))
    put(d, "helper_one.py", "print('invented helper')\n")
    put(d, "tools/local_tool.sh", "echo invented\n")
    put(d, "era_details/900001.json", json.dumps({"check": "invented", "lines": []}))
    put(d, "patient_db/chart_0001/answer.json", json.dumps({"chart": "invented", "answer": junk(64).hex()}))
    for i in range(files):
        put(d, "registers/register_%03d.json" % i, junk(size))      # the tool carries bytes, whatever the file is called
    travels = {rel: sha for rel, sha in tree(d).items()}
    put(d, "secrets/some.key", "NOT-A-REAL-KEY")                # everything from here down must stay behind
    put(d, ".amd_cred.json", "{}"); put(d, ".session.json", "{}"); put(d, ".amd_login_lock", "")
    put(d, "registers/run.lock", ""); put(d, "outbox/state/old_set.part01.b64", "AAAA")
    put(d, "registers/leftover.part01.b64", "AAAA"); put(d, "tools/__pycache__/x.json", "{}")
    return d, travels

def tree(d):
    out = {}
    for root, _, fs in os.walk(d):
        for f in fs:
            p = os.path.join(root, f); out[os.path.relpath(p, d)] = hashlib.sha256(open(p, "rb").read()).hexdigest()
    return out

def pack(src, out, part_chars=None, **kw):
    """ws_bundle.pack on a throwaway folder. part_chars = a small part size for this one call, so a small folder makes many parts."""
    keep = (ws_bundle.WS, ws_bundle.PART); ws_bundle.WS = src
    if part_chars: ws_bundle.PART = part_chars
    try:
        with contextlib.redirect_stdout(io.StringIO()): return ws_bundle.pack(out, 40, **kw)
    finally: ws_bundle.WS, ws_bundle.PART = keep

def unpack(bundle_dir, dst, force=False):
    """ws_bundle.unpack into a throwaway folder -> (exit code, what it printed); an error inside it is returned, not raised."""
    keep = ws_bundle.WS; ws_bundle.WS = dst; buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            try: rc = ws_bundle.unpack(bundle_dir, force=force)
            except Exception as e: rc = "stopped with %s: %s" % (type(e).__name__, e)
    finally: ws_bundle.WS = keep
    return rc, buf.getvalue()

PART_NAME = re.compile(r"^(workspace_state_.+)\.part(\d+)\.b64$")
def part_names(d): return sorted(os.path.basename(p) for p in glob.glob(os.path.join(d, "workspace_state_*.part*.b64")))
def numbers(names): return [int(PART_NAME.match(n).group(2)) for n in names]
def manifest_of(d): return glob.glob(os.path.join(d, "workspace_state_*.manifest.json"))[0]

def copy_set(src_dir, label, fmt=None, stamp=None, into=None):
    """Copy one packed set (parts + manifest) to another folder, writing each part number with fmt (e.g. "%02d") and, when
    given, under another stamp - the way a set written by an older copy of the tool, or on another day, sits on Drive. The
    part contents are not touched and the manifest names the parts the same way the files are named."""
    dst = into or fresh(label); man = json.load(open(manifest_of(src_dir))); new = {}
    for name in man["parts"]:
        st, num = PART_NAME.match(name).groups()
        new[name] = "%s.part%s.b64" % ("workspace_state_" + stamp if stamp else st, (fmt % int(num)) if fmt else num)
        shutil.copy(os.path.join(src_dir, name), os.path.join(dst, new[name]))
    man["parts"] = [new[n] for n in man["parts"]]; man["part_sha256"] = {new[n]: h for n, h in man["part_sha256"].items()}
    if stamp: man["stamp"] = stamp
    json.dump(man, open(os.path.join(dst, PART_NAME.match(man["parts"][0]).group(1) + ".manifest.json"), "w"), indent=1)
    return dst

def comes_back(label, bundle_dir, travels):
    dst = fresh("restore"); rc, out = unpack(bundle_dir, dst); got = tree(dst)
    why = out.strip() or rc if rc != 0 else "restored %d of %d files; differing: %s" % (
        len(got), len(travels), sorted(set(got) ^ set(travels) | {k for k in got if travels.get(k) != got[k]})[:5])
    check(label, rc == 0 and got == travels, why)
    return got

# ---- the folders: one small, one that makes many parts ------------------------------------------------------------------------
SMALL, SMALL_FILES = make_workspace("small_ws", 4, 3700, "small")       # 15 KB that will not shrink = about 20,000 base64 characters = 3 parts at the real part size
BIG, BIG_FILES = make_workspace("big_ws", 24, 800, "big")                # 19 KB that will not shrink = about 27,000 base64 characters

# ---- A. three parts, real part size --------------------------------------------------------------------------------------------
a_out = fresh("a_three_parts"); a_man = pack(SMALL, a_out)
check("A1 the small folder packs into exactly 3 parts at the real part size", len(a_man["parts"]) == 3, a_man["parts"])
check("A2 a small set keeps its two-digit names (part01 .. part03)", [n.split(".part")[1] for n in part_names(a_out)] == ["01.b64", "02.b64", "03.b64"], part_names(a_out))
a_got = comes_back("A3 a 3-part bundle comes back whole", a_out, SMALL_FILES)
check("A4 secrets/, credential, session and lock files and old bundle files never travel", a_got and not any(any(x in rel for x in NEVER) for rel in a_got), sorted(a_got))
check("A5 the manifest counts the files that travelled", a_man["files"] == len(SMALL_FILES), (a_man["files"], len(SMALL_FILES)))

# ---- B. more than 100 parts ----------------------------------------------------------------------------------------------------
b_out = fresh("b_over_100"); b_man = pack(BIG, b_out, part_chars=200); b_names = part_names(b_out); n_b = len(b_man["parts"])
check("B1 the big folder packs into more than 100 parts (%d)" % n_b, 100 < n_b < 1000 and len(b_names) == n_b)
comes_back("B2 a bundle of more than 100 parts comes back whole", b_out, BIG_FILES)
check("B3 pack names a set in one width, so a text sort of the names is the number order", len({len(n) for n in b_names}) == 1 and numbers(b_names) == list(range(1, n_b + 1)), b_names[:3] + b_names[98:102])
check("B4 the manifest lists the parts in number order", numbers(b_man["parts"]) == list(range(1, n_b + 1)))

# ---- C. the number decides, however it is written ------------------------------------------------------------------------------
c_old = copy_set(b_out, "c_two_digit", "%02d")                           # part01 .. part99, part100 .. - every set packed before the fix
check("C0 (the old naming really is the one a text sort gets wrong)", numbers(part_names(c_old)) != list(range(1, n_b + 1)))
comes_back("C1 a 100+ part set named the old way (part99, part100: two digits, then three) comes back whole", c_old, BIG_FILES)
comes_back("C2 the same set with no leading zeros (part1 .. part%d) comes back whole" % n_b, copy_set(b_out, "c_no_zeros", "%d"), BIG_FILES)
comes_back("C3 the same set padded wider than needed (part000001 ..) comes back whole", copy_set(b_out, "c_wide", "%06d"), BIG_FILES)

# ---- D. more than 1,000 parts --------------------------------------------------------------------------------------------------
d_out = fresh("d_over_1000"); d_man = pack(BIG, d_out, part_chars=24); n_d = len(d_man["parts"])
check("D1 the same folder in tiny parts makes more than 1,000 (%d)" % n_d, n_d > 1000)
comes_back("D2 a bundle of more than 1,000 parts comes back whole", d_out, BIG_FILES)
comes_back("D3 ... and so does that set named the old way (part99, part100, part999, part1000)", copy_set(d_out, "d_two_digit", "%02d"), BIG_FILES)

# ---- E. refusing a damaged set, and naming the damage in number order -----------------------------------------------------------
def part_file(d, n): return [os.path.join(d, x) for x in part_names(d) if PART_NAME.match(x) and int(PART_NAME.match(x).group(2)) == n][0]
def named(out): return [m.group(0) for m in re.finditer(r"workspace_state_[^\s'\",\]]+?\.part\d+\.b64", out.split("bad parts:")[-1].split("\n")[0])]
e_dir = copy_set(b_out, "e_damaged", "%02d"); gone = part_file(e_dir, 20); flipped = part_file(e_dir, 104)
os.remove(gone); t = open(flipped).read(); open(flipped, "w").write(("B" if t[0] != "B" else "C") + t[1:])       # same length, one character changed
e_dst = fresh("restore"); rc, out = unpack(e_dir, e_dst)
check("E1 a set with a missing part and an altered part is refused (exit 2)", rc == 2, (rc, out))
check("E2 ... nothing is written", tree(e_dst) == {}, sorted(tree(e_dst))[:5])
check("E3 ... both parts are named, the lower number first (20 before 104), and no other part", named(out) == [os.path.basename(gone), os.path.basename(flipped)], out)
def cut_short(d, n):                                           # take 1 to 4 characters off part n, so that what is left can never decode as base64
    p = part_file(d, n); t = open(p).read()
    chars = sum(len(open(os.path.join(d, x)).read().replace("\n", "").rstrip("=")) for x in part_names(d))
    open(p, "w").write(t[:-(((chars - 1) % 4) or 4)]); return p
e2_dir = copy_set(b_out, "e_cut_short", "%02d"); cut = cut_short(e2_dir, 57)
e2_dst = fresh("restore"); rc, out = unpack(e2_dir, e2_dst)
check("E4 a part cut short is refused cleanly (exit 2, no error raised), nothing written", rc == 2 and tree(e2_dst) == {}, (rc, out))
check("E5 ... and it is the part that is named", named(out) == [os.path.basename(cut)], out)
e3_dir = copy_set(b_out, "e_stray_copy", "%02d"); shutil.copy(part_file(e3_dir, 7), part_file(e3_dir, 7)[:-4] + " (1).b64")
e3_dst = fresh("restore"); rc, out = unpack(e3_dir, e3_dst)
check("E6 a file that is not a part (a second download of part07) is left out and said so; the set comes back whole", rc == 0 and tree(e3_dst) == BIG_FILES and "(1).b64" in out, (rc, out))
e4_dir = copy_set(b_out, "e_names_differ", "%d"); shutil.copy(manifest_of(c_old), manifest_of(e4_dir))            # files part7, manifest says part07
bent = part_file(e4_dir, 7); t = open(bent).read(); open(bent, "w").write(("B" if t[0] != "B" else "C") + t[1:])
rc, out = unpack(e4_dir, fresh("restore"))
check("E7 the per-part check goes by part number too: files named part7 against a manifest that says part07 - only the altered part is named",
      rc == 2 and named(out) == [os.path.basename(part_file(c_old, 7))], (rc, out))
e5_dir = copy_set(b_out, "e_no_manifest", "%02d"); os.remove(manifest_of(e5_dir)); cut_short(e5_dir, 57)
e5_dst = fresh("restore"); rc, out = unpack(e5_dir, e5_dst)
check("E8 parts that cannot decode and no manifest beside them: refused (exit 2), nothing written", rc == 2 and tree(e5_dst) == {}, (rc, out))
e6_dir = copy_set(b_out, "e_part_twice", "%02d"); shutil.copy(part_file(e6_dir, 7), part_file(e6_dir, 7).replace(".part07.", ".part007."))
e6_dst = fresh("restore"); rc, out = unpack(e6_dir, e6_dst)
check("E9 one part in the folder twice under two spellings (part07 and part007): refused, nothing written, and the report says every listed part is intact",
      rc == 2 and tree(e6_dst) == {} and "none of the %d parts the manifest lists" % n_b in out and "no per-part sha" not in out, (rc, out))

# ---- F. two sets in one folder: the newer stamp wins, whichever one is the big one ---------------------------------------------------
f1 = fresh("f_old_big_new_small"); copy_set(b_out, "", "%02d", "2026-01-05_2301UTC", into=f1); copy_set(a_out, "", None, "2026-01-06_0102UTC", into=f1)
comes_back("F1 an older 100+ part set and a newer 3-part set: the newer one is restored", f1, SMALL_FILES)
f2 = fresh("f_old_small_new_big"); copy_set(a_out, "", None, "2026-01-05_2301UTC", into=f2); copy_set(b_out, "", "%02d", "2026-01-06_0102UTC", into=f2)
comes_back("F2 an older 3-part set and a newer 100+ part set: the newer one is restored", f2, BIG_FILES)

# ---- G. the command lines the routine prompts name, with the real part size -------------------------------------------------------
REAL, REAL_FILES = make_workspace("real_size_ws", 30, 24000, "real size")     # 720 KB that will not shrink -> about 120 parts of 8,000 characters
g_out = fresh("g_cli_out"); g_dst = fresh("g_cli_restore")
def cli(args, ws): return subprocess.run([sys.executable, TOOL] + args, env=dict(os.environ, WS=ws), capture_output=True, text=True)
p = cli(["pack", "--out", g_out], REAL); n_g = len(part_names(g_out))
check("G1 `ws_bundle.py pack --out DIR` at the real part size makes more than 100 parts (%d)" % n_g, p.returncode == 0 and n_g > 100, p.stdout[-300:] + p.stderr[-300:])
u = cli(["unpack", g_out], g_dst)
check("G2 `ws_bundle.py unpack DIR` restores them (exit 0)", u.returncode == 0, (u.returncode, u.stdout[-300:], u.stderr[-300:]))
check("G3 ... every file byte for byte", tree(g_dst) == REAL_FILES, "restored %d of %d" % (len(tree(g_dst)), len(REAL_FILES)))
g_old = copy_set(g_out, "g_cli_old_names", "%02d"); g_dst2 = fresh("g_cli_restore_old"); u = cli(["unpack", g_old], g_dst2)
check("G4 ... and the same set named the old way (the names a 100+ part set already on Drive has)", u.returncode == 0 and tree(g_dst2) == REAL_FILES, (u.returncode, u.stdout[-300:], u.stderr[-300:]))

print("\n%d failure(s)" % len(FAILS) + (" - all guarantees hold" if not FAILS else ": " + "; ".join(FAILS)))
sys.exit(1 if FAILS else 0)
