#!/usr/bin/env python3
# PLAIN ENGLISH (ERA input - read a truncated or xref-less scan PDF anyway)
# Decides: Nothing about billing. When a ScanSnap batch arrives cut short (a missing byte range, no trailer / xref - pdftoppm renders
#          0 pages), it pulls every embedded JPEG page image straight out of the bytes, in file order = page order, and OCRs them with
#          the same tesseract --psm 6 the normal ocr.sh uses, so classify.py / extract.py see the usual ocr/<batch>/p-NN.txt files.
# Rules it uses: a page whose JPEG was cut by the truncation is still OCR'd (libjpeg decodes the part that exists); the register notes
#          which pages are partial. Never touches: anything but ocr/<batch>/.
# ---
"""Usage: python3 pdf_salvage.py raw/<batch>.pdf [--jobs 4]   (SCANS_DIR default /home/claude/scans)"""
import sys, os, re, subprocess, json
os.environ["OMP_THREAD_LIMIT"] = "1"   # tesseract 5 spawns 4 threads per process otherwise
from concurrent.futures import ThreadPoolExecutor
D = os.environ.get("SCANS_DIR", "/home/claude/scans")
src = sys.argv[1]; stem = os.path.basename(src)[:-4]; jobs = int(sys.argv[sys.argv.index("--jobs") + 1]) if "--jobs" in sys.argv else 4
out = os.path.join(D, "ocr", stem); img = os.path.join(out, "img"); os.makedirs(img, exist_ok=True)
data = open(src, "rb").read()
# every "<< ... /DCTDecode ... >> stream" block: the JPEG runs from the SOI marker to "endstream" (or EOF when the file was cut)
pages = []
for m in re.finditer(rb"/Filter\s*/DCTDecode.*?>>\s*stream\r?\n", data, re.S):
    start = m.end(); soi = data.find(b"\xff\xd8", start, start + 64)
    if soi < 0: continue
    end = data.find(b"endstream", soi); cut = end < 0
    jpg = data[soi:(end if end > 0 else len(data))].rstrip(b"\r\n")
    pages.append((soi, jpg, cut))
pages.sort(); width = max(2, len(str(len(pages))))
meta = []
for i, (pos, jpg, cut) in enumerate(pages, 1):
    name = "p-%0*d" % (width, i); open(os.path.join(img, name + ".jpg"), "wb").write(jpg); meta.append({"page": i, "bytes": len(jpg), "offset": pos, "partial": cut})
def ocr(name):
    r = subprocess.run(["tesseract", os.path.join(img, name + ".jpg"), os.path.join(out, name), "--psm", "6"], capture_output=True, text=True)
    return name, r.returncode
with ThreadPoolExecutor(jobs) as ex:
    for name, rc in ex.map(ocr, ["p-%0*d" % (width, i) for i in range(1, len(pages) + 1)]): pass
json.dump(meta, open(os.path.join(out, "salvage.json"), "w"), indent=1)
open(os.path.join(out, ".done"), "w").write("salvaged %d pages (%d partial)\n" % (len(pages), sum(1 for p in meta if p["partial"])))
print("salvaged", len(pages), "pages;", sum(1 for p in meta if p["partial"]), "partial;", sum(1 for p in meta if p["bytes"] < 20000), "tiny")
