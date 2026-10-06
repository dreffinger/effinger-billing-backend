#!/usr/bin/env python3
# PLAIN ENGLISH (ERA input - get the ScanSnap batches out of Gmail and into the OCR pipeline, whatever their size)
# Decides: Nothing about billing. It turns the connector results a Claude session already holds on disk into raw/<batch>.pdf files,
#          verifies every byte (sha256 / md5 from the connector), and keeps the batch register so no batch is OCR'd or posted twice.
# Rules it uses: three routes, chosen by attachment size (10/5/2026 measurements, Claude cloud session):
#   1. Gmail connector get_message RAW  -> works to ~1 MB of PDF (the MIME JSON is persisted to a tool-results file); the 5-7 MB
#      attachments close the Gmail MCP connection ("message too large").                          -> extract_gmail_raw()
#   2. Zapier Gmail 'Get Attachment by Filename' -> hydrate URL -> Zapier Google Drive 'Upload File' (native hydration, any size)
#      into Drive 'eras scanned' (folder 1Fz90JGLa-s_QTw0RSuUdGnvQznxyGEHO) -> Google Drive connector download_file_content
#      (hard limit 10 MB per file; the base64 JSON is persisted to a tool-results file).          -> extract_drive_download()
#   3. Over 10 MB: the Zapier code action google_drive_get_file_byte_range_base64 (file_id, start, length<=4000000) returns one
#      4 MB slice per call (5.3 MB of JSON, persisted); slices are joined here and the md5 must match Drive's.  -> assemble_chunks()
#   The container proxy refuses zapier.com (CONNECT 403) and drive.google.com; www.googleapis.com answers but needs OAuth - so the
#   bytes only ever travel through connector results. Every Zapier call is one Zapier task (the account ran out on 10/5/2026 with
#   one slice to go - a partial PDF still renders every page whose objects precede the cut).
# Never touches: AMD, Gmail (no sends, no labels), Drive (no writes). Only local files.
# ---
"""Usage:
  python3 fetch_scans.py register <batches.json>          # [{msgid,file,size,sent,subject}] from the Gmail search -> scan_batches register
  python3 fetch_scans.py gmail-raw <tool-result.txt>...   # persisted Gmail RAW results -> raw/<file>.pdf
  python3 fetch_scans.py drive <tool-result.txt>...       # persisted Drive download_file_content results -> raw/<title>
  python3 fetch_scans.py chunks <tool-result.txt>...      # persisted byte-range slices -> raw/<name> (complete files only unless --partial)
  python3 fetch_scans.py status                           # register vs raw/ vs ocr/ - what is still missing
Env: SCANS_DIR (default /home/claude/scans); REGISTER (default <repo>/practices/ehpa/registers/scan_batches.json)."""
import sys, os, json, base64, hashlib, subprocess, glob, datetime, email
from email import policy
D = os.environ.get("SCANS_DIR", "/home/claude/scans"); RAW = os.path.join(D, "raw"); os.makedirs(RAW, exist_ok=True)
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
REG = os.environ.get("REGISTER", os.path.join(ROOT, "practices", "ehpa", "registers", "scan_batches.json"))
def now(): return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
def load_reg(): return json.load(open(REG)) if os.path.exists(REG) else []
def save_reg(r): os.makedirs(os.path.dirname(REG), exist_ok=True); json.dump(r, open(REG, "w"), indent=1)
def pages(p):
    out = subprocess.run(["pdfinfo", p], capture_output=True, text=True).stdout
    for l in out.splitlines():
        if l.startswith("Pages:"): return int(l.split()[1])
    return None
def mark(fname, **kw):
    reg = load_reg(); hit = [b for b in reg if b.get("file") == fname]
    if not hit: hit = [{"file": fname}]; reg.append(hit[0])
    hit[0].update(kw); hit[0]["updated"] = now(); save_reg(reg); return hit[0]
def finish(p, fname, route, expect_md5=None, expect_sha=None):
    data = open(p, "rb").read(); md5 = hashlib.md5(data).hexdigest(); sha = hashlib.sha256(data).hexdigest()
    ok = (expect_md5 is None or md5 == expect_md5) and (expect_sha is None or sha == expect_sha)
    n = pages(p)
    mark(fname, route=route, bytes=len(data), md5=md5, sha256=sha, pages=n, verified=ok, fetched=now())
    print("%s %s %d bytes md5 %s pages %s %s" % (fname, route, len(data), md5[:12], n, "OK" if ok else "CHECKSUM MISMATCH"))
    return ok

def register(path):
    reg = load_reg(); have = {b.get("msgid") for b in reg}
    for b in json.load(open(path)):
        if b.get("msgid") in have: continue
        reg.append({"msgid": b.get("msgid"), "file": b.get("file"), "size": b.get("size"), "sent": b.get("sent"), "subject": b.get("subject"), "registered": now()})
    save_reg(reg); print("register:", len(reg), "batches")

def extract_gmail_raw(src):
    j = json.load(open(src)); raw = j["raw"]
    mime = base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))
    msg = email.message_from_bytes(mime, policy=policy.default)
    for part in msg.walk():
        fn = part.get_filename()
        if fn and fn.lower().endswith(".pdf"):
            p = os.path.join(RAW, fn); open(p, "wb").write(part.get_payload(decode=True)); finish(p, fn, "gmail-raw"); mark(fn, msgid=j.get("id"))

def extract_drive_download(src):
    j = json.load(open(src)); title = j["title"]
    if title.endswith(".pdf.pdf"): title = title[:-4]
    data = base64.b64decode(j["content"]); p = os.path.join(RAW, title); open(p, "wb").write(data); finish(p, title, "drive-connector"); mark(title, drive_id=j.get("id"))

def assemble_chunks(srcs, partial=False):
    files = {}
    for s in srcs:
        try: j = json.load(open(s))
        except Exception as e: print("skip", s, e); continue
        d = (((j.get("results") or {}).get("data") or {}).get("data")) or {}
        if "data" not in d or "start" not in d: continue
        blob = base64.b64decode(d["data"])
        if hashlib.sha256(blob).hexdigest() != d.get("chunk_sha256"): print("CHUNK SHA MISMATCH", d.get("name"), d["start"]); continue
        files.setdefault(d["name"], {"size": d["size"], "md5": d.get("md5Checksum"), "parts": {}})["parts"][int(d["start"])] = blob
    for name, f in files.items():
        parts = f["parts"]; buf = bytearray(); pos = 0; missing = []
        for start in sorted(parts):
            if start != pos: missing.append((pos, start)); buf += b"\0" * (start - pos); pos = start
            buf += parts[start]; pos += len(parts[start])
        if pos < f["size"]: missing.append((pos, f["size"]))
        if missing and not partial: print("%s INCOMPLETE: missing byte ranges %s of %d" % (name, missing, f["size"])); mark(name, route="drive-chunks", missing=missing, verified=False); continue
        p = os.path.join(RAW, name); open(p, "wb").write(bytes(buf))
        ok = finish(p, name, "drive-chunks" + ("-partial" if missing else ""), expect_md5=None if missing else f["md5"])
        if missing: mark(name, missing=missing, verified=False); print("   PARTIAL: %s - pages whose objects sit in the gap will not render" % missing)

def status():
    reg = load_reg()
    for b in sorted(reg, key=lambda b: b.get("file") or ""):
        fn = b.get("file"); p = os.path.join(RAW, fn or "x"); onep = os.path.exists(p)
        ocr = os.path.exists(os.path.join(D, "ocr", (fn or "x")[:-4], ".done"))
        print("%-22s %9s %-22s raw=%s ocr=%s %s" % (fn, b.get("size"), b.get("route", "-"), "yes" if onep else "NO", "done" if ocr else "-", "" if b.get("verified", True) else "UNVERIFIED " + str(b.get("missing", ""))))

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"; args = [a for a in sys.argv[2:] if not a.startswith("--")]
    if cmd == "register": register(args[0])
    elif cmd == "gmail-raw": [extract_gmail_raw(s) for s in args]
    elif cmd == "drive": [extract_drive_download(s) for s in args]
    elif cmd == "chunks": assemble_chunks(args, partial="--partial" in sys.argv)
    else: status()
