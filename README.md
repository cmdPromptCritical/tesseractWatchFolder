# tesseractWatchFolder
Limitations:
- only reads .pdf as input
- watch folder is currently set same dir as watch.py
- cannot convert pdf files not in the top level directory of watch folder

Configuration:
- Modify variables found in the CONFIG section at the top of watch.py
- Possible settings:
  - Watch folder location
  - Conversion to binary (B/W) images before sending through Tesseract
  - Upscale/Downscale to specified DPI
