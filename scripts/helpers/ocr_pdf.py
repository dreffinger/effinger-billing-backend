#!/usr/bin/env python3
# PLAIN ENGLISH (ocr_pdf.py, added 9/18/2026 - William 9/17: "add the ability back to ocr a pdf"):
#   Turns a facesheet PDF or image into text. Tries the PDF's own text layer first (pdftotext -layout); when that is
#   empty (a scanned/print-to-PDF sheet) it renders every page at 250 dpi (pdftoppm, or PyMuPDF when poppler is
#   missing) and runs tesseract. SSNs are masked as xxx-xx-NNNN before anything is printed or saved.
#   Usage: python3 ocr_pdf.py <file.pdf|file.png|file.jpg> [--out text.txt] [--keep-pages]
#   Getting a Drive file onto disk: the Google Drive connector's download_file_content returns base64 - write it to
#   <name>.b64 and `python3 ocr_pdf.py --b64 <name>.b64 --pdf <name>.pdf` decodes it first (size printed for a check).
# Decides: nothing. Never touches: AMD, Drive, git. Needs: poppler-utils + tesseract-ocr (bootstrap layout installs them).
import os, re, subprocess, sys, tempfile, glob, base64

SSN = re.compile(r'\b(\d{3})-(\d{2})-(\d{4})\b')

def mask(t): return SSN.sub(r'xxx-xx-\3', t)

def sh(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)

def text_layer(pdf):
    r = sh(["pdftotext", "-layout", pdf, "-"])
    return r.stdout if r.returncode == 0 else ""

def render(pdf, outdir, dpi=250):
    r = sh(["pdftoppm", "-r", str(dpi), "-png", pdf, os.path.join(outdir, "page")])
    pages = sorted(glob.glob(os.path.join(outdir, "page*.png")))
    if pages: return pages
    try:
        import pymupdf
        doc = pymupdf.open(pdf)
        for i, pg in enumerate(doc):
            p = os.path.join(outdir, "page-%02d.png" % (i + 1)); pg.get_pixmap(dpi=dpi).save(p)
        return sorted(glob.glob(os.path.join(outdir, "page*.png")))
    except Exception as e:
        sys.stderr.write("render failed: %s\n" % e); return []

def ocr_image(png, psm="6"):
    r = sh(["tesseract", png, "-", "--psm", psm])
    return r.stdout

def ocr(path, keep_pages=False):
    if path.lower().endswith((".png", ".jpg", ".jpeg", ".tif", ".tiff")):
        return mask(ocr_image(path))
    t = text_layer(path)
    if len(t.strip()) > 40:
        return mask(t)
    d = tempfile.mkdtemp(prefix="ocr_") if not keep_pages else os.path.splitext(path)[0] + "_pages"
    os.makedirs(d, exist_ok=True)
    out = []
    for p in render(path, d):
        out.append("===== %s =====\n%s" % (os.path.basename(p), ocr_image(p)))
    return mask("\n".join(out))

if __name__ == "__main__":
    a = sys.argv[1:]
    if "--b64" in a:
        b = a[a.index("--b64") + 1]; pdf = a[a.index("--pdf") + 1]
        raw = base64.b64decode(open(b).read().replace("\n", "").replace(" ", ""))
        open(pdf, "wb").write(raw); print("decoded", pdf, len(raw), "bytes"); a = [pdf] + [x for x in a if x not in ("--b64", b, "--pdf", pdf)]
    src = a[0]; txt = ocr(src, "--keep-pages" in a)
    if "--out" in a:
        open(a[a.index("--out") + 1], "w").write(txt)
    print(txt)
