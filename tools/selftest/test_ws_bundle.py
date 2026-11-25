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
#       set keeps the two-digit names it always had (part01 .. part03); the rule is checked at its edges (99, 100, 999, 1,000 parts);
#     - a 3-part bundle still round-trips, and so does a bundle of more than 1,000 parts (four-digit numbers);
#     - a missing part and an altered part are refused: nothing is written, and both are named, in number order; a part that was
#       cut short is refused the same way instead of stopping the script with an error;
#     - a second download of a part ("part07 (1).b64") is left out and said so when the real part07 is there, and used when it is
#       the only copy; one part number under two spellings is refused, and the report names both files instead of blaming a part
#       that is intact;
#     - with two sets in one folder the newer one is restored, whichever of the two is the big one - and when the newest set cannot
#       be used, unpack refuses: it never restores an older set in its place;
#     - an intact set without its manifest still restores (it cannot be checked - that is unchanged), and so do parts saved with
#       Windows line ends;
#     - the command lines the routine prompts name (pack --out DIR, unpack DIR) do the same with the real part size;
#     - secrets/, the credential, session and lock files and old bundle files never travel, wherever they sit in the folder;
#     - the size cap is never silent, and what travels under it is the NEWEST state (11/25/2026). From 11/24/2026 13:01 UTC every bundle
#       stopped at the 40 MB default: files were skipped without a word, and registers/ - the folder walked last - lost the registers of
#       the run that had just entered the Claimocity feed's visits, so the next fresh container read the same feed file again. Now the
#       newest files are packed first, the pack says how many files and megabytes it left out (and the manifest records it).
# Run: python3 tools/selftest/test_ws_bundle.py   (exit 1 on any failure)
import os, sys, io, re, json, glob, shutil, random, hashlib, tempfile, subprocess, contextlib, atexit
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOOL = os.path.join(ROOT, "tools", "bootstrap", "ws_bundle.py")
sys.dont_write_bytecode = True                                 # leave no __pycache__ beside the tool
sys.path.insert(0, os.path.join(ROOT, "tools", "bootstrap")); import ws_bundle
FAILS = []
def check(name, cond, extra=""):
    print(("ok   " if cond else "FAIL ") + name + (("  -> " + str(extra)[:400]) if extra != "" and not cond else ""))
    if not cond: FAILS.append(name)

TMP = tempfile.mkdtemp(prefix="wsbundle_selftest_")
atexit.register(shutil.rmtree, TMP, ignore_errors=True)        # every throwaway folder goes when the test ends, passed or failed
SEQ = [0]
def fresh(label):                                              # a new empty throwaway folder
    SEQ[0] += 1; d = os.path.join(TMP, "%02d_%s" % (SEQ[0], label)); os.makedirs(d); return d
RND = random.Random(1110)                                      # the same invented bytes on every run
def junk(n):                                                   # n random bytes: gzip cannot shrink them, so the number of parts is predictable
    return RND.getrandbits(8 * n).to_bytes(n, "big")
def put(d, rel, data):
    p = os.path.join(d, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "wb").write(data if isinstance(data, bytes) else data.encode())

NEVER = ("secrets", ".amd_cred.json", ".session.json", ".amd_login_lock", ".lock", "outbox", "chat_history", ".b64", ".bundle", "__pycache__")
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
    # everything from here down must stay behind - at the top of the folder AND inside the folders pack walks
    put(d, "secrets/some.key", "NOT-A-REAL-KEY"); put(d, "tools/secrets/other.key", "NOT-A-REAL-KEY")
    put(d, ".amd_cred.json", "{}"); put(d, ".session.json", "{}"); put(d, ".amd_login_lock", ""); put(d, "registers/.amd_login_lock", "")
    put(d, "registers/run.lock", ""); put(d, "registers/leftover.part01.b64", "AAAA"); put(d, "registers/old.bundle.json", "{}")
    put(d, "outbox/state/old_set.part01.b64", "AAAA"); put(d, "registers/outbox/old.json", "{}")
    put(d, "patient_db/chat_history/x.json", "{}"); put(d, "tools/__pycache__/x.json", "{}")
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
NAMES = ws_bundle._part_names                                  # (stamp, base64 characters, part size) -> the names pack writes
def digits(names): return sorted({len(n.split(".part")[1]) - len(".b64") for n in names})
check("B5 the naming rule at its edges: 1 part and 99 full parts keep two digits (part01 .. part99)",
      NAMES("s", 1, 8000) == ["workspace_state_s.part01.b64"] and len(NAMES("s", 99 * 8000, 8000)) == 99 and digits(NAMES("s", 99 * 8000, 8000)) == [2])
check("B6 ... one character more makes 100 parts, every one three digits (part001 .. part100); 999 parts are three digits too",
      len(NAMES("s", 99 * 8000 + 1, 8000)) == 100 and digits(NAMES("s", 99 * 8000 + 1, 8000)) == [3] and NAMES("s", 99 * 8000 + 1, 8000)[0].endswith(".part001.b64")
      and len(NAMES("s", 999 * 8000, 8000)) == 999 and digits(NAMES("s", 999 * 8000, 8000)) == [3])
check("B7 ... and 1,000 parts are every one four digits (part0001 .. part1000)",
      len(NAMES("s", 999 * 8000 + 1, 8000)) == 1000 and digits(NAMES("s", 999 * 8000 + 1, 8000)) == [4] and NAMES("s", 999 * 8000 + 1, 8000)[-1].endswith(".part1000.b64"))

# ---- C. the number decides, however it is written ------------------------------------------------------------------------------
c_old = copy_set(b_out, "c_two_digit", "%02d")                           # part01 .. part99, part100 .. - every set packed before the fix
check("C0 (the old naming really is the one a text sort gets wrong)", numbers(part_names(c_old)) != list(range(1, n_b + 1)))
comes_back("C1 a 100+ part set named the old way (part99, part100: two digits, then three) comes back whole", c_old, BIG_FILES)
comes_back("C2 the same set with no leading zeros (part1 .. part%d) comes back whole" % n_b, copy_set(b_out, "c_no_zeros", "%d"), BIG_FILES)
comes_back("C3 the same set padded wider than needed (part000001 ..) comes back whole", copy_set(b_out, "c_wide", "%06d"), BIG_FILES)

# ---- D. more than 1,000 parts --------------------------------------------------------------------------------------------------
d_out = fresh("d_over_1000"); d_man = pack(BIG, d_out, part_chars=24); n_d = len(d_man["parts"])
check("D1 the same folder in tiny parts makes more than 1,000 (%d), every name four digits wide" % n_d, n_d > 1000 and digits(part_names(d_out)) == [4])
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
e6_dir = copy_set(b_out, "e_part_twice", "%02d"); real = part_file(e6_dir, 7); twin = real.replace(".part07.", ".part7."); t = open(real).read()
open(twin, "w").write(("B" if t[0] != "B" else "C") + t[1:])       # the same part number under a second spelling, with other content
e6_dst = fresh("restore"); rc, out = unpack(e6_dir, e6_dst)
check("E9 one part number under two spellings (part07 and part7): refused, nothing written; the report does not blame the intact part and names both files",
      rc == 2 and tree(e6_dst) == {} and named(out) == [] and "none of the %d parts the manifest lists" % n_b in out and "no per-part sha" not in out
      and all(os.path.basename(x) in out for x in (real, twin)), (rc, out))

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

os.remove(part_file(g_old, 33)); g_dst3 = fresh("g_cli_refused"); u = cli(["unpack", g_old], g_dst3)
check("G5 the command line answers a damaged set with exit status 2 and writes nothing", u.returncode == 2 and tree(g_dst3) == {} and "SHA256 MISMATCH" in u.stdout, (u.returncode, u.stdout[-300:], u.stderr[-300:]))

# ---- H. copies under decorated names, and never an older set in place of the newest ---------------------------------------------------
h1 = copy_set(b_out, "h_only_decorated", "%02d"); only = part_file(h1, 7); os.rename(only, only[:-4] + " (1).b64")
h1_dst = fresh("restore"); rc, out = unpack(h1, h1_dst)
check("H1 a part that is in the folder ONLY under a decorated name (part07 (1).b64) is used, and said so: the set comes back whole", rc == 0 and tree(h1_dst) == BIG_FILES and "(1).b64' as part 7" in out, (rc, out))
h2 = fresh("h_newest_all_decorated"); copy_set(a_out, "", None, "2026-01-05_2301UTC", into=h2); copy_set(b_out, "", "%02d", "2026-01-06_0102UTC", into=h2)
for x in part_names(h2):
    if "2026-01-06_0102UTC" in x: os.rename(os.path.join(h2, x), os.path.join(h2, x[:-4] + " (1).b64"))
comes_back("H2 every part of the NEWEST set under a decorated name, an older set beside it: the newest is restored, not the older", h2, BIG_FILES)
h3 = fresh("h_newest_unnumbered"); copy_set(a_out, "", None, "2026-01-05_2301UTC", into=h3); put(h3, "workspace_state_2026-01-06_0102UTC.partial.b64", "AAAA")
h3_dst = fresh("restore"); rc, out = unpack(h3, h3_dst)
check("H3 the newest set has no numbered part at all: refused (exit 2) - the older set is NOT restored in its place", rc == 2 and tree(h3_dst) == {}, (rc, out))

# ---- I. what did not change -----------------------------------------------------------------------------------------------------------
i1 = copy_set(b_out, "i_no_manifest", "%02d"); os.remove(manifest_of(i1))
comes_back("I1 an intact set without its manifest still restores (it cannot be checked - unchanged)", i1, BIG_FILES)
i2 = copy_set(b_out, "i_windows_line_ends", "%02d")
for x in part_names(i2):
    t = open(os.path.join(i2, x)).read(); open(os.path.join(i2, x), "wb").write(t.replace("\n", "\r\n").encode() + b"\r\n")
comes_back("I2 parts saved with Windows line ends and a trailing empty line still restore", i2, BIG_FILES)

# ---- J. the size cap (11/25/2026): never silent, and the NEWEST files are the ones that travel -----------------------------------------
J, _j_unused = make_workspace("j_cap_ws", 0, 0, "cap")
for i in range(6): put(J, "era_details/old_%d.json" % i, junk(200000))                       # 1.2 MB of old ERA cache
for i in range(4): put(J, "patient_db/chart_%04d/old.json" % i, junk(200000))                # 0.8 MB of old 271 answers
for i in range(5): put(J, "registers/feed_import_OLD%d.json" % i, junk(100000))              # 0.5 MB of old registers (already on main)
_t = __import__("time"); _old = _t.time() - 5 * 86400
for _root, _dirs, _fs in os.walk(J):
    for _f in _fs: os.utime(os.path.join(_root, _f), (_old, _old))                          # everything so far is five days old
put(J, "registers/feed_import_NEW.json", junk(150000)); put(J, "registers/claimocity_ingest.json", json.dumps({"files": {"invented": 1}}))   # THIS run's registers
J_TRAVELS = {rel for rel in tree(J) if not any(x in rel for x in NEVER)}
def pack_capped(src, out, mb):
    keep = ws_bundle.WS; ws_bundle.WS = src; buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf): m = ws_bundle.pack(out, mb)
    finally: ws_bundle.WS = keep
    return m, buf.getvalue()
j_out = fresh("j_cap_out"); mj, jo = pack_capped(J, j_out, 1)                                # a 1 MB cap: about 2.65 MB of files cannot all travel
check("J1 over the cap the pack SAYS so - how many files and megabytes were left out, by folder, and what to do about it",
      "BUNDLE INCOMPLETE" in jo and "--max-mb" in jo and re.search(r"\d+ file\(s\)", jo) is not None and "MB" in jo, jo[-500:])
lo = mj.get("left_out") or {}
check("J2 ... and the manifest records it (left_out: files, bytes, by folder, the newest file left out and its time)",
      lo.get("files", 0) >= 1 and lo.get("bytes", 0) > 0 and set(lo.get("by_dir") or {"?": 1}) <= {"registers", "patient_db", "era_details", "tools"} and bool(lo.get("newest")) and isinstance(lo.get("names"), list), lo)
j_dst = fresh("j_cap_restore"); rc, out = unpack(j_out, j_dst); got = set(tree(j_dst))
check("J3 the files THIS run wrote travel first: the new feed register and the file register are in the bundle although registers/ is walked last and older files had to stay behind",
      rc == 0 and {"registers/feed_import_NEW.json", "registers/claimocity_ingest.json"} <= got and len(got) < len(J_TRAVELS), (rc, sorted(got)[:14]))
_mt = lambda rel: os.path.getmtime(os.path.join(J, rel))
_capped = lambda rel: rel.split(os.sep)[0] in ("registers", "patient_db", "era_details", "tools")
_left = sorted(J_TRAVELS - got)
check("J4 what stayed behind is the OLDEST: no file left out is newer than a file of the walked folders that travelled, and the count matches the manifest",
      _left and all(_capped(r) for r in _left) and max(_mt(r) for r in _left) <= min(_mt(r) for r in got if _capped(r)) and len(_left) == lo.get("files"), (_left[:6], lo.get("files")))
j_out2 = fresh("j_cap_roomy"); mj2, jo2 = pack_capped(J, j_out2, 40); j_dst2 = fresh("j_cap_roomy_restore"); rc2, _o2 = unpack(j_out2, j_dst2)
check("J5 under the cap nothing is left out, nothing is said and the manifest carries no left_out - every file travels",
      "BUNDLE INCOMPLETE" not in jo2 and "left_out" not in mj2 and rc2 == 0 and set(tree(j_dst2)) == J_TRAVELS, (jo2[-200:], sorted(J_TRAVELS - set(tree(j_dst2)))[:6]))
pj = cli(["pack", "--out", fresh("j_cli_out"), "--max-mb", "1"], J)
check("J6 the command line says it too, and still exits 0 (a bundle that is not complete is better than none - the run reads the line)",
      pj.returncode == 0 and "BUNDLE INCOMPLETE" in pj.stdout, (pj.returncode, pj.stdout[-300:], pj.stderr[-200:]))

print("\n%d failure(s)" % len(FAILS) + (" - all guarantees hold" if not FAILS else ": " + "; ".join(FAILS)))
sys.exit(1 if FAILS else 0)
