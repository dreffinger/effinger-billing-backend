#!/usr/bin/env python3
# PLAIN ENGLISH (ehpa Practice Database - William 11/1/2026: "have it include all the data from all the artifacts involved in the
#   billing and credentialing projects and routines").
# Every billing/credentialing page on claude.ai keeps its own small database (Mandatory Approvals cards, the Insurance Refresh
#   Board rows, Working Denials commands, the Credentialing Board ...) or carries its dataset inside the page (Outstanding Claims,
#   Money Ledger, Treasury, Working Denials triage - artifact_embedded.py pulls those out). A database belongs to one page, so the
#   Practice Database keeps COPIES: the sync routine (nightly/practice_db_sync_prompt_v1.txt) lists each source collection with
#   ArtifactData (out_dir -> one JSON file per document) and this script packs those files into snapshot documents:
#     artifact_copies/<slug>-<collection>-<stamp>        {slug, title, url, coll, at, count, docs: {<id>: <document>}}  (split .p2.. >200 KB)
#     artifact_index/<slug>-<stamp>                       {slug, title, url, at, collections: {<coll>: {count, bytes, doc, parts, stamp, changed}}}
#     sync_runs/<stamp>                                   (--sync-summary) one line per board: what changed, what was skipped
#   New ids every time, so no version pinning; the page shows the newest index per page.
# The REGISTER (--register practices/ehpa/registers/practice_db_copies.json, committed to main by the routine) remembers the sha256
#   of every collection as last copied: an unchanged collection is NOT copied again (the index points at the copy already in the
#   database), a board with nothing changed gets no documents at all. That keeps the database from growing by 30 identical
#   documents a day. --prune-plan <days> writes delete batches for copies older than <days> that are not the newest of their
#   collection (every copy is written once, so if_version is 1); --prune-done removes the deleted ids from the register.
# PHI: these are the user's own pages; nothing here leaves his artifacts. Nothing is written to GitHub by this script except the
#   register, which holds ids, counts and hashes only.
# Usage:
#   python3 tools/db/artifact_copy.py --slug mandatory_approvals --title "Mandatory Approvals" --url https://claude.ai/artifact/HuYd2bSm2NxkFgYRqra7wR \
#            --src <out_dir the ArtifactData lists were saved to> --out <dir> [--stamp <UTC stamp>] [--register <file>] [--max-doc-kb 200]
#       <src>/<collection>/<doc_id>.json is what `ArtifactData list ... out_dir=<src>` writes; every sub-folder is one collection
#       (the embedded datasets go to <src>/embedded/snapshot_N.json via artifact_embedded.py). Prints one line; exit 0.
#   python3 tools/db/artifact_copy.py --sync-summary --register <file> --stamp <stamp> --out <dir>     -> writes_sync_1.json (sync_runs/<stamp>)
#   python3 tools/db/artifact_copy.py --prune-plan 30 --register <file> --out <dir>                    -> writes_prune_N.json (delete entries)
#   python3 tools/db/artifact_copy.py --prune-done --register <file> --out <dir>                       (after every prune batch committed)
import os, sys, re, json, hashlib, datetime

a = sys.argv[1:]
def opt(name, default=None): return a[a.index(name) + 1] if name in a else default
NOW = datetime.datetime.now(datetime.timezone.utc); STAMP = re.sub(r"[^0-9TZ]", "", opt("--stamp", NOW.strftime("%Y%m%dT%H%MZ")))
AT = NOW.strftime("%Y-%m-%dT%H:%M:%SZ")
OUT = opt("--out"); REG = opt("--register"); MAXKB = int(opt("--max-doc-kb", "200"))
if not OUT: sys.exit("usage: artifact_copy.py --out <dir> (--slug ... --src ... | --sync-summary | --prune-plan <days> | --prune-done) [--register <file>]")
os.makedirs(os.path.join(OUT, "docs"), exist_ok=True)

reg = {"schema": "practice-db-copies/1", "boards": {}, "copies": [], "runs": {}}
if REG and os.path.exists(REG):
    try: reg = json.load(open(REG))
    except Exception: pass
reg.setdefault("boards", {}); reg.setdefault("copies", []); reg.setdefault("runs", {})
def save_reg():
    if REG:
        os.makedirs(os.path.dirname(os.path.abspath(REG)), exist_ok=True)
        json.dump(reg, open(REG, "w"), indent=0, sort_keys=True)

def dumps(x): return json.dumps(x, separators=(",", ":"), sort_keys=True)
def write_batches(entries, prefix):
    batches, cur, cur_bytes = [], [], 0
    for e, size in entries:
        if cur and (len(cur) >= 50 or cur_bytes + size > 900 * 1024): batches.append(cur); cur, cur_bytes = [], 0
        cur.append(e); cur_bytes += size
    if cur: batches.append(cur)
    for i, b in enumerate(batches): json.dump(b, open(os.path.join(OUT, "writes_%s_%d.json" % (prefix, i + 1)), "w"), indent=0)
    return len(batches)

# ---------------------------------------------------------------- --sync-summary: one sync_runs document from this stamp's register entries
if "--sync-summary" in a:
    run = reg["runs"].get(STAMP) or {}
    boards = {s: v for s, v in run.items()}
    changed = sum(1 for v in boards.values() for c in v.get("changed", []))
    body = {"schema": "practice-sync-run/1", "at": AT, "stamp": STAMP, "boards": boards, "boards_checked": len(boards),
            "collections_changed": changed, "collections_unchanged": sum(len(v.get("unchanged", [])) for v in boards.values()),
            "_source": "tools/db/artifact_copy.py --sync-summary", "_written": AT}
    fn = os.path.join(OUT, "docs", "sync_runs__%s.json" % STAMP); open(fn, "w").write(dumps(body))
    n = write_batches([({"op": "set", "collection": "sync_runs", "doc_id": STAMP, "file_path": fn}, len(dumps(body)))], "sync")
    print("sync-summary %s: %d board(s) checked, %d collection(s) copied, %d unchanged -> %d batch file(s) under %s" % (STAMP, len(boards), changed, body["collections_unchanged"], n, OUT))
    sys.exit(0)

# ---------------------------------------------------------------- --prune-plan <days>: delete copies older than <days>, never the newest of a collection
if "--prune-plan" in a:
    days = int(opt("--prune-plan", "30")); cutoff = (NOW - datetime.timedelta(days=days)).strftime("%Y%m%dT%H%MZ")
    newest = {}
    for c in reg["copies"]:
        k = (c["slug"], c["coll"])
        if k not in newest or c["stamp"] > newest[k]["stamp"]: newest[k] = c
    victims = [c for c in reg["copies"] if c["stamp"] < cutoff and newest[(c["slug"], c["coll"])]["stamp"] != c["stamp"] and not c.get("deleted")]
    entries = []
    for c in victims:
        for did in c["docs"]: entries.append(({"op": "delete", "collection": "artifact_copies", "doc_id": did, "if_version": 1}, 200))
    # old indexes too: keep the newest index per slug
    idx_new = {}
    for c in reg["copies"]:
        if c.get("index") and (c["slug"] not in idx_new or c["stamp"] > idx_new[c["slug"]]): idx_new[c["slug"]] = c["stamp"]
    seen = set()
    for c in victims:
        if c.get("index") and c["stamp"] != idx_new.get(c["slug"]) and c["index"] not in seen:
            seen.add(c["index"]); entries.append(({"op": "delete", "collection": "artifact_index", "doc_id": c["index"], "if_version": 1}, 200))
    for f in os.listdir(OUT):
        if f.startswith("writes_prune_"): os.remove(os.path.join(OUT, f))
    n = write_batches(entries, "prune") if entries else 0
    json.dump([c["stamp"] + "|" + c["slug"] + "|" + c["coll"] for c in victims], open(os.path.join(OUT, "prune_pending.json"), "w"))
    print("prune-plan: %d copy(ies) older than %d days are not the newest of their collection -> %d delete(s) in %d batch file(s) under %s%s" % (
        len(victims), days, len(entries), n, OUT, "" if entries else " (nothing to prune)"))
    sys.exit(0)

if "--prune-done" in a:
    pend = set(json.load(open(os.path.join(OUT, "prune_pending.json")))) if os.path.exists(os.path.join(OUT, "prune_pending.json")) else set()
    n = 0
    for c in reg["copies"]:
        if c["stamp"] + "|" + c["slug"] + "|" + c["coll"] in pend and not c.get("deleted"): c["deleted"] = AT; n += 1
    save_reg(); print("prune-done: %d copy record(s) marked deleted in the register" % n); sys.exit(0)

# ---------------------------------------------------------------- the copy of one board
SLUG = opt("--slug"); TITLE = opt("--title", SLUG); URL = opt("--url", ""); SRC = opt("--src")
if not (SLUG and SRC): sys.exit("usage: artifact_copy.py --slug <slug> --title <t> --url <u> --src <dir> --out <dir> [--register <file>]")
if not re.match(r"^[A-Za-z0-9_\-]+$", SLUG): sys.exit("slug: letters, digits, _ - only")

def explode(items):
    """an item larger than a document (an embedded page dataset with thousands of rows) is split: each big list field becomes
    <id>.<key>.<n> chunk items and the item itself keeps the scalars plus a _split note naming the moved keys"""
    out = {}; budget = MAXKB * 1024 - 4096
    for k, v in items.items():
        if len(dumps(v)) <= budget or not isinstance(v, dict): out[k] = v; continue
        rest = {}; moved = {}
        for fk, fv in v.items():
            if isinstance(fv, list) and len(dumps(fv)) > 20000:
                chunks, cur, size = [], [], 0
                for row in fv:
                    rs = len(dumps(row)) + 1
                    if cur and size + rs > budget: chunks.append(cur); cur, size = [], 0
                    cur.append(row); size += rs
                if cur: chunks.append(cur)
                for i, ch in enumerate(chunks): out["%s.%s.%d" % (k, fk, i + 1)] = ch
                moved[fk] = {"rows": len(fv), "chunks": len(chunks)}
            else: rest[fk] = fv
        rest["_split"] = moved; out[k] = rest
    return out

colls = {}
for root, dirs, files in os.walk(SRC):
    js = [f for f in files if f.endswith(".json")]
    if not js: continue
    rel = os.path.relpath(root, SRC).replace(os.sep, "/")
    if rel == ".": continue
    items = {}
    for f in sorted(js):
        try: items[f[:-5]] = json.load(open(os.path.join(root, f)))
        except Exception: continue
    if items: colls[rel] = explode(items)

board = reg["boards"].setdefault(SLUG, {"title": TITLE, "url": URL, "collections": {}})
board["title"] = TITLE or board.get("title"); board["url"] = URL or board.get("url")
docs = []                      # (coll, id, body)
index_colls = {}; changed = []; unchanged = []; run_copies = []
for coll, items in sorted(colls.items()):
    sha = hashlib.sha256(dumps(items).encode()).hexdigest()
    prev = board["collections"].get(coll)
    s = dumps(items); nbytes = len(s)
    if prev and prev.get("sha") == sha and prev.get("doc"):
        index_colls[coll] = {"count": len(items), "bytes": nbytes, "doc": prev["doc"], "parts": prev.get("parts", 1), "stamp": prev.get("stamp"), "changed": False}
        unchanged.append(coll); continue
    base = {"schema": "practice-artifact-copy/1", "slug": SLUG, "title": TITLE, "url": URL, "coll": coll, "at": AT, "stamp": STAMP, "count": len(items), "_source": "tools/db/artifact_copy.py", "_written": AT}
    did = "%s-%s-%s" % (SLUG, coll.replace("/", "~"), STAMP); ids = []
    body = dict(base, docs=items)
    if len(dumps(body)) <= MAXKB * 1024:
        docs.append(("artifact_copies", did, body)); ids = [did]; parts = 1
    else:
        budget = MAXKB * 1024 - len(dumps(base)) - 200
        chunks, cur, size = [], {}, 0
        for k, v in items.items():
            vs = len(dumps({k: v})) + 1
            if cur and size + vs > budget: chunks.append(cur); cur, size = {}, 0
            cur[k] = v; size += vs
        if cur: chunks.append(cur)
        for i, ch in enumerate(chunks):
            pid = did if i == 0 else "%s.p%d" % (did, i + 1); ids.append(pid)
            docs.append(("artifact_copies", pid, dict(base, docs=ch, part=i + 1, parts=len(chunks))))
        parts = len(chunks)
    index_colls[coll] = {"count": len(items), "bytes": nbytes, "doc": did, "parts": parts, "stamp": STAMP, "changed": True}
    board["collections"][coll] = {"sha": sha, "doc": did, "parts": parts, "stamp": STAMP, "count": len(items), "bytes": nbytes}
    changed.append(coll); run_copies.append({"slug": SLUG, "coll": coll, "stamp": STAMP, "docs": ids, "at": AT})

index_id = None
if changed or not board.get("last_index"):
    index_id = "%s-%s" % (SLUG, STAMP)
    index = {"schema": "practice-artifact-index/1", "slug": SLUG, "title": TITLE, "url": URL, "at": AT, "stamp": STAMP, "collections": index_colls,
             "changed": changed, "unchanged": unchanged, "_source": "tools/db/artifact_copy.py", "_written": AT}
    docs.append(("artifact_index", index_id, index)); board["last_index"] = {"doc": index_id, "stamp": STAMP}
    for c in run_copies: c["index"] = index_id
reg["copies"].extend(run_copies)
reg["runs"].setdefault(STAMP, {})[SLUG] = {"changed": changed, "unchanged": unchanged, "index": index_id, "counts": {c: v["count"] for c, v in index_colls.items()}}
board["last_checked"] = AT
save_reg()

for f in os.listdir(OUT):
    if f.startswith("writes_%s_" % SLUG): os.remove(os.path.join(OUT, f))
entries = []
for coll, did, body in docs:
    fn = os.path.join(OUT, "docs", "%s__%s.json" % (coll, did)); s = dumps(body); open(fn, "w").write(s)
    entries.append(({"op": "set", "collection": coll, "doc_id": did, "file_path": fn}, len(s)))
n = write_batches(entries, SLUG) if entries else 0
print("artifact_copy %s: %d collection(s) [%s] -> %d changed (%s), %d unchanged (%s) -> %d document(s) in %d batch file(s) under %s%s" % (
    SLUG, len(colls), ", ".join("%s %d" % (c, len(v)) for c, v in sorted(colls.items())), len(changed), ", ".join(changed) or "-",
    len(unchanged), ", ".join(unchanged) or "-", len(docs), n, OUT, "" if entries else "  NOTHING TO WRITE for this board"))
