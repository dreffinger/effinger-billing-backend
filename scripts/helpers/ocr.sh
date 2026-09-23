#!/bin/bash
# OCR each page of each PDF into ocr/<stem>/pNNN.txt
for f in raw/*.pdf; do s=$(basename "$f" .pdf); mkdir -p ocr/$s/img
  [ -f ocr/$s/.done ] && continue
  pdftoppm -r 300 -gray -png "$f" ocr/$s/img/p
  ls ocr/$s/img/*.png | xargs -P 8 -I{} sh -c 'b=$(basename {} .png); tesseract {} ocr/'$s'/$b --psm 6 >/dev/null 2>&1'
  touch ocr/$s/.done; echo done $s
done
