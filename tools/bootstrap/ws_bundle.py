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
"""
import os, sys, io, tarfile, base64, json, time, glob, hashlib

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
    for i in range(0, len(b64), PART):
        fn = os.path.join(out_dir, f'workspace_state_{stamp}.part{len(parts)+1:02d}.b64')
        chunk = b64[i:i + PART]
        # 100-char lines: the Drive connector round-trips wrapped text reliably (9/13/2026)
        open(fn, 'w').write('\n'.join(chunk[j:j + 100] for j in range(0, len(chunk), 100)))
        parts.append(os.path.basename(fn)); part_sha[parts[-1]] = hashlib.sha256(chunk.encode()).hexdigest()
    manifest = {'stamp': stamp, 'files': len(names), 'raw_bytes': total, 'tar_gz_bytes': len(raw),
                'sha256': hashlib.sha256(raw).hexdigest(), 'parts': parts, 'part_sha256': part_sha, 'members': names[:400]}
    mf = os.path.join(out_dir, f'workspace_state_{stamp}.manifest.json')
    json.dump(manifest, open(mf, 'w'), indent=1)
    print(f'packed {len(names)} files ({total/1024:.0f} KB raw -> {len(raw)/1024:.0f} KB gz) into {len(parts)} part(s): {parts[0]} .. {parts[-1]}')
    print('manifest:', mf)
    return manifest


def unpack(src_dir, force=False):
    sets = {}
    for fn in glob.glob(os.path.join(src_dir, 'workspace_state_*.part*.b64')):
        stamp = os.path.basename(fn).split('.part')[0]
        sets.setdefault(stamp, []).append(fn)
    if not sets:
        print('unpack: no workspace_state_*.partNN.b64 files in', src_dir); return 1
    stamp = sorted(sets)[-1]
    parts = sorted(sets[stamp])
    chunks = {os.path.basename(p): open(p).read().replace('\n', '').strip() for p in parts}
    b64 = ''.join(chunks[os.path.basename(p)] for p in parts)
    raw = base64.b64decode(b64)
    mf = os.path.join(src_dir, stamp + '.manifest.json')
    if os.path.exists(mf):
        man = json.load(open(mf)); want = man.get('sha256')
        got = hashlib.sha256(raw).hexdigest()
        if want and want != got:
            bad = [n for n, h in (man.get('part_sha256') or {}).items() if hashlib.sha256(chunks.get(n, '').encode()).hexdigest() != h]
            print('unpack: SHA256 MISMATCH - a part is missing, truncated or altered; refusing to extract. bad parts:', bad or 'unknown (manifest has no per-part sha)')
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
