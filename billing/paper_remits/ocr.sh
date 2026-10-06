#!/bin/bash
# OCR each page of each raw/*.pdf into ocr/<stem>/p-NN.txt (300 dpi gray, tesseract --psm 6) - the layout classify.py reads.
# 10/5/2026 rewrite: tesseract 5 starts 4 OpenMP threads per process, so 8 processes on a 4-core box = 32+ threads thrashing
# (one page took 13 minutes). Now: OMP_THREAD_LIMIT=1 and exactly $(nproc) processes (~50 s CPU per page -> ~5 pages/min/core);
# near-blank pages (ScanSnap duplex backs: pixel std-dev < 12/255) get an empty .txt without OCR; a PDF pdftoppm cannot open
# (truncated download, no trailer) is handed to billing/era_input/pdf_salvage.py, which OCRs the embedded JPEGs instead.
export OMP_THREAD_LIMIT=1
J=${OCR_JOBS:-$(nproc)}
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
for f in raw/*.pdf; do s=$(basename "$f" .pdf); mkdir -p ocr/$s/img
  [ -f ocr/$s/.done ] && continue
  pdftoppm -r 300 -gray -png "$f" ocr/$s/img/p 2>/dev/null
  if ! ls ocr/$s/img/*.png >/dev/null 2>&1; then
    echo "pdftoppm rendered nothing for $s - salvaging embedded JPEGs"; python3 "$HERE/../era_input/pdf_salvage.py" "$f" --jobs $J; continue
  fi
  ls ocr/$s/img/*.png | xargs -P $J -I{} sh -c 'b=$(basename {} .png); sd=$(identify -format "%[fx:standard_deviation*255]" {} 2>/dev/null | cut -d. -f1); if [ -n "$sd" ] && [ "$sd" -lt 12 ]; then : > ocr/'$s'/$b.txt; else OMP_THREAD_LIMIT=1 tesseract {} ocr/'$s'/$b --psm 6 >/dev/null 2>&1; fi'
  touch ocr/$s/.done; echo "done $s ($(ls ocr/$s/p-*.txt | wc -l) pages, $(find ocr/$s -name 'p-*.txt' -size 0 | wc -l) blank) $(date -u +%H:%M:%S)"
done
