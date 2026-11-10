#!/usr/bin/env python3
"""ws_bundle.py - pack / unpack the nightly workspace STATE as chunked base64 text (Drive-safe).

Why (9/11/2026): every scheduled run starts in a FRESH container. GitHub main restores the toolkit
(when the repo is attached), Drive 'workspace mirror' restores PHI helpers file-by-file, but the
run STATE - needs_facesheet_list.md, laterality_flag_log.md, precheck_cache.json, patient_db/ (the
271 archive), era_details/ (the ERA cache), audit/checkpoint json - was lost between runs. This tool
turns that state into text parts small enough for the Google Drive connector, and back.

  python3 tools/ws_bundle.py pack   [--out DIR] [--max-mb 40] [--state-only] [--phi-only]   # writes DIR/workspace_state_<UTC>.partNN.b64 (+ .manifest.json)
                                                                  #   --phi-only (10/6/2026, William: 'ws_bundle.py needs a --phi-only mode') keeps ONLY what lives nowhere else: patient_db/, era_details/,
                                                                  #   needs_facesheet_list.md, laterality_flag_log.md, precheck_cache.json and this run's registers (last 6 h, under 400 KB) - small enough for the connector
                                                                  #   --state-only skips *.py/*.sh and the registry/vocabulary/carrier files the repo + Drive restore (keeps the bundle small enough to survive the connector)
  python3 tools/ws_bundle.py unpack DIR [--force]                  # reassembles the newest set in DIR and extracts into the workspace
                                                                  #   (existing files that are NEWER than the archived copy are kept unless --force)
Includes: *.py *.sh *.md *.json *.jsonl *.csv *.txt at the top level, tools/, patient_db/, era_details/, registers/.
Excludes: secrets/, .amd_cred.json, .session.json, *.lock, .amd_login_lock, __pycache__, outbox/, chat_history/,
          *.bundle*, *.b64, raw *.xml dumps over 2 MB, and anything over 8 MB. No secret ever enters a bundle.

Part order (11/10/2026): unpack joins the parts by the NUMBER after ".part", never by the text of their names. Until then it sorted
the names as text, where part100 comes between part10 and part11, so any bundle of 100 parts or more - the default pack was 267
parts that day - was refused with "SHA256 MISMATCH ... bad parts: unknown" (or stopped on a base64 error) and the run's state did
not carry over to the next fresh container, whichever mode had packed it. Bundles under 100 parts were never affected. Now:
  - any way of writing the number is read (part07, part7, part007), so a set written by an older copy of this tool (two digits,
    a third only from part100 on) unpacks as well;
  - pack writes one width per set (part01 .. part99, part001 .. part267, part0001 ..), so a text sort of a new set is its number
    order too and an older copy of this tool can still restore it; sets under 100 parts are named exactly as before;
  - the newest set in the folder is the one that is unpacked or refused - never an older set in its place;
  - with the manifest beside the parts, the bad-part report goes by part number as well and lists the parts in number order; a
    part cut short is refused and named instead of ending in an error; when every listed part is intact it says so, and it
    names any part that is in the folder twice;
  - a copy of a part under a decorated name ("...part07 (1).b64", a second download) is left out when the plainly named part is
    there and used when it is the only one; a file with no part number in its name is left out; unpack says each time.
Unchanged: a set WITHOUT its manifest cannot be checked - unpack extracts what it can read, as it always did.
Self-test (offline, throwaway folders, no patient data): python3 tools/selftest/test_ws_bundle.py
"""
import os, sys, io, re, tarfile, base64, json, time, glob, hashlib

WS = os.environ.get("WS", "/home/claude/unbilled")
PART = 8000             # chars per part (80 lines x 100) - the size the Drive connector has round-tripped cleanly; 150k parts did not survive
TOP_EXT = ('.py', '.sh', '.md', '.json', '.jsonl', '.csv', '.txt')
DIRS = ('tools', 'patient_db', 'era_details', 'registers')
EXCLUDE_NAMES = {'.amd_cred.json', '.session.json', '.amd_login_lock', '.columns_run.lock', '.unpaid_audit.lock'}
EXCLUDE_DIRS = {'secrets', '__pycache__', 'outbox', 'chat_history', '.git'}
# --state-only also skips what the attached repo / Drive 'billing agent project files' already hold verbatim
REPO_RESTORED = {'captured_calls.md', 'api_vocabulary.json', 'carriers.json', 'carriers_rich.json', 'facilities.json', 'MIRROR.md', 'rules.md'}


def _want(path, rel):
    base = os.path.basename(rel)
    if base in EXCLUDE_NAMES or base.endswith('.lock') or '.bundle' in base or base.endswith('.b64'):
        return False
    if any(p in EXCLUDE_DIRS for p in rel.split(os.sep)):
        return False
    try:
        sz = os.path.getsize(path)
    except OSError:
        return False
    if sz > 8 * 1024 * 1024:
        return False
    if base.endswith('.xml') and sz > 2 * 1024 * 1024:
        return False
    return True


PHI_TOP = {'needs_facesheet_list.md', 'laterality_flag_log.md', 'precheck_cache.json'}   # --phi-only: the top-level files that live nowhere else


def pack(out_dir, max_mb, state_only=False, phi_only=False):
    stamp = time.strftime('%Y-%m-%d_%H%MUTC', time.gmtime())
    buf = io.BytesIO()
    total = 0
    names = []
    with tarfile.open(fileobj=buf, mode='w:gz') as tar:
        for entry in sorted(os.listdir(WS)):
            p = os.path.join(WS, entry)
            if state_only and (entry.endswith(('.py', '.sh')) or entry in REPO_RESTORED):
                continue
            if phi_only and entry not in PHI_TOP:
                continue
            if os.path.isfile(p) and entry.endswith(TOP_EXT) and _want(p, entry):
                tar.add(p, arcname=entry); names.append(entry); total += os.path.getsize(p)
        for d in DIRS:
            dp = os.path.join(WS, d)
            if not os.path.isdir(dp):
                continue
            if phi_only and d == 'tools':
                continue
            if state_only and d in ('era_details', 'patient_db'):   # 9/14: era_details (6+ MB) is re-pulled by era_step_b_0913.py in a minute; patient_db lookups (0.7 MB of Stedi answers) are already on the board rows
                continue
            for root, dirs, files in os.walk(dp):
                dirs[:] = [x for x in dirs if x not in EXCLUDE_DIRS]
                for f in files:
                    fp = os.path.join(root, f); rel = os.path.relpath(fp, WS)
                    if state_only and (rel.startswith('tools' + os.sep) or f.endswith(('.py', '.sh', '.xml'))):   # .xml = raw 271s under patient_db (the .json summaries carry the answer)
                        continue
                    if phi_only and (f.endswith(('.py', '.sh')) or (d == 'registers' and (time.time() - os.path.getmtime(fp) > 6 * 3600 or os.path.getsize(fp) > 400 * 1024))):   # only this run's registers (the rest are on main), none over 400 KB
                        continue
                    if _want(fp, rel):
                        if total + os.path.getsize(fp) > max_mb * 1024 * 1024:
                            continue
                        tar.add(fp, arcname=rel); names.append(rel); total += os.path.getsize(fp)
    raw = buf.getvalue()
    b64 = base64.b64encode(raw).decode()
    os.makedirs(out_dir, exist_ok=True)
    parts = []; part_sha = {}
    for k, name in enumerate(_part_names(stamp, len(b64))):
        fn = os.path.join(out_dir, name)
        chunk = b64[k * PART:(k + 1) * PART]
        # 100-char lines: the Drive connector round-trips wrapped text reliably (9/13/2026)
        open(fn, 'w').write('\n'.join(chunk[j:j + 100] for j in range(0, len(chunk), 100)))
        parts.append(name); part_sha[name] = hashlib.sha256(chunk.encode()).hexdigest()
    manifest = {'stamp': stamp, 'files': len(names), 'raw_bytes': total, 'tar_gz_bytes': len(raw),
                'sha256': hashlib.sha256(raw).hexdigest(), 'parts': parts, 'part_sha256': part_sha, 'members': names[:400]}
    mf = os.path.join(out_dir, f'workspace_state_{stamp}.manifest.json')
    json.dump(manifest, open(mf, 'w'), indent=1)
    print(f'packed {len(names)} files ({total/1024:.0f} KB raw -> {len(raw)/1024:.0f} KB gz) into {len(parts)} part(s): {parts[0]} .. {parts[-1]}')
    print('manifest:', mf)
    return manifest


def _part_names(stamp, n_chars, part=None):
    """The part file names pack writes for n_chars of base64, in order. 11/10/2026: one width per set - two digits up to 99 parts
    (part01 .. part99, as always), then as many as the last part needs (part001 .. part267, part0001 ..) - so a plain text sort of
    a set is its number order too."""
    part = part or PART
    n = max(1, (n_chars + part - 1) // part)
    width = max(2, len(str(n)))
    return [f'workspace_state_{stamp}.part{i:0{width}d}.b64' for i in range(1, n + 1)]


def _parse(name):
    """(set, part number, plainly named?) of a part file. The set is everything before the first ".part" (workspace_state_<stamp>).
    The number is the digits right after it: part07 -> 7, part7 -> 7, part100 -> 100, part0100 -> 100 - and a decorated copy still
    counts ("...part07 (1).b64" is part 7, not plainly named). None when no number follows ".part"."""
    base = os.path.basename(name); stamp = base.split('.part')[0]
    m = re.match(r'\.part(\d+)(.*)\.b64$', base[len(stamp):], re.S)
    return stamp, (int(m.group(1)) if m else None), bool(m and not m.group(2))


def _part_no(name):
    """11/10/2026: a part is this number, never the text of its name - in text order part100 sorts between part10 and part11, which
    is how a 267-part bundle came back as "SHA256 MISMATCH ... bad parts: unknown"."""
    return _parse(name)[1]


def unpack(src_dir, force=False):
    sets = {}
    for fn in glob.glob(os.path.join(src_dir, 'workspace_state_*.part*.b64')):
        sets.setdefault(_parse(fn)[0], []).append(fn)
    if not sets:
        print('unpack: no workspace_state_*.partNN.b64 files in', src_dir); return 1
    stamp = sorted(sets)[-1]   # always the newest set in the folder (the stamp is fixed-width UTC, YYYY-MM-DD_HHMMUTC: its text order is its time order)
    by_no = {}
    for p in sorted(sets[stamp], key=os.path.basename):
        if _part_no(p) is None:   # cannot be placed, and pack never writes such a name
            print('unpack: left out %r - no part number in its name' % os.path.basename(p)); continue
        by_no.setdefault(_part_no(p), []).append(p)
    parts = []
    for no in sorted(by_no):   # by part NUMBER (11/10/2026), however the number is written
        files = by_no[no]; plain = [p for p in files if _parse(p)[2]]
        if plain and len(plain) < len(files):   # a second download saved as "...part07 (1).b64" beside the real part07
            for p in files:
                if p not in plain:
                    print('unpack: left out %r - part %d is in the folder under its plain name too' % (os.path.basename(p), no))
            files = plain
        elif not plain:   # the only copy of this part carries a decorated name: it is the part
            for p in files:
                print('unpack: using %r as part %d - no plainly named file for it' % (os.path.basename(p), no))
        parts += files
    if not parts:
        print('unpack: the newest set in the folder, %r, has no numbered part file; refusing to extract (an older set is never used in its place)' % stamp); return 2
    texts = [(_part_no(p), os.path.basename(p), open(p).read().replace('\n', '').strip()) for p in parts]
    b64 = ''.join(t for _, _, t in texts)
    try:
        raw = base64.b64decode(b64); broken = ''
    except ValueError as e:   # a part cut short or garbled so far that the text is no longer base64: refuse like any other mismatch
        raw = None; broken = ' (the parts do not even decode as base64: %s)' % e
    mf = os.path.join(src_dir, stamp + '.manifest.json')
    man = json.load(open(mf)) if os.path.exists(mf) else {}
    want = man.get('sha256')
    if raw is None or (want and want != hashlib.sha256(raw).hexdigest()):
        listed = man.get('part_sha256') or {}   # the per-part check goes by part number too, and reports in number order
        have = {}
        for no, name, t in texts:
            have.setdefault(no, {})[name] = hashlib.sha256(t.encode()).hexdigest()
        bad = [n for n in sorted(listed, key=lambda n: (_part_no(n) or 0, n)) if listed[n] not in have.get(_part_no(n), {}).values()]
        twice = [name for no in sorted(have) if len(have[no]) > 1 for name in sorted(have[no])]
        if not bad:
            bad = ('none of the %d parts the manifest lists - each matches its own sha256; look for a part file that does not belong to this set, or a damaged manifest' % len(listed) if listed
                   else 'unknown (manifest has no per-part sha)' if man else 'unknown (no manifest in the folder)')
        print('unpack: SHA256 MISMATCH%s - a part is missing, truncated or altered; refusing to extract. bad parts:' % broken, bad)
        if twice:
            print('        in the folder more than once under one part number (keep one of each):', twice)
        print('        recovery: zlib-decompress up to the CRC error and take the intact tar members (see 9/13/2026 7pm ET run), then overlay the previous sha-clean set')
        return 2
    kept = restored = 0
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as tar:
        for m in tar.getmembers():
            if not m.isfile():
                continue
            if m.name.startswith('/') or '..' in m.name.split('/') or m.name.split('/')[0] in EXCLUDE_DIRS:
                continue
            dst = os.path.join(WS, m.name)
            if os.path.exists(dst) and not force and os.path.getmtime(dst) > m.mtime:
                kept += 1; continue
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with tar.extractfile(m) as f, open(dst, 'wb') as o:
                o.write(f.read())
            os.utime(dst, (m.mtime, m.mtime)); restored += 1
    print(f'unpack: {stamp} -> restored {restored} files, kept {kept} newer local files, into {WS}')
    return 0


if __name__ == '__main__':
    args = sys.argv[1:]
    if not args or args[0] not in ('pack', 'unpack'):
        print(__doc__); sys.exit(2)
    if args[0] == 'pack':
        out = args[args.index('--out') + 1] if '--out' in args else os.path.join(WS, 'outbox')
        mb = int(args[args.index('--max-mb') + 1]) if '--max-mb' in args else 40
        pack(out, mb, state_only='--state-only' in args, phi_only='--phi-only' in args)
    else:
        if len(args) < 2:
            print('unpack needs a directory'); sys.exit(2)
        sys.exit(unpack(args[1], force='--force' in args))
