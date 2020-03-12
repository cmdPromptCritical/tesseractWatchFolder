# tesseractWatchFolder
Limitations:
- only reads .pdf as input
- watch folder is currently set same dir as watch.py
- cannot convert pdf files not in the top level directory of watch folder

Installation:
1. Download project
2. Ensure Tesseract and ImageMagick are installed, with Tesseract being located in your PATH variable. Add a variable MAGICK_HOME which points to your ImageMagick installation folder.
3. Modify configuration settings in watch.py as needed
4. run watch.py

Configuration:
- Modify variables found in the CONFIG section at the top of watch.py
- Possible settings:
  - Watch folder location
  - Conversion to binary (B/W) images before sending through Tesseract
  - Upscale/Downscale to specified DPI
