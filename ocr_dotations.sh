#!/bin/sh
tesseract "$1" - \
  --psm 6 --oem 0 --tessdata-dir ./tessdata/ \
  -l eng+rus+chi_sim+chi_tra+jpn | grep ' '
