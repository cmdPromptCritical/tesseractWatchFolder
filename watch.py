import time, os
import cv2
import pytesseract
from wand.image import Image
from wand.display import display
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
from PyPDF2 import PdfFileMerger, PdfFileReader
import ntpath, shutil
#### CONFIG
GRAYSCALE = True # recommended. enables to grayscale (can be used with THRESHOLD)
THRESHHOLD = True # recommended. enables conversion to binary B/W
BLUR = False # recommended. enables slight bluring (removes salt/pepper noise)

IMG_RES = 300 # recommend 300. Sets the resolution of the TIFF image to be OCR'd
# TESSERACT LOCATION:
pytesseract.pytesseract.tesseract_cmd = r"C:\Users\Richard\AppData\Local\Tesseract-OCR\tesseract.exe"

def remove(path):
    """ param <path> could either be relative or absolute. """
    if os.path.isfile(path) or os.path.islink(path):
        os.remove(path)  # remove the file
    elif os.path.isdir(path):
        shutil.rmtree(path)  # remove dir and all contains
    else:
        raise ValueError("file {} is not a file or dir.".format(path))

def on_created(event):
    if event.src_path[-4:] == '.pdf' or event.src_path[-4:] == '.PDF':
        ocrPdf(event.src_path)


def on_deleted(event):
    print(f"what the h**k! Someone deleted {event.src_path}!")

def on_modified(event):
    print(f"hey buddy, {event.src_path} has been modified")

def on_moved(event):
    print(f"ok ok ok, someone moved {event.src_path} to {event.dest_path}")

def ocrPdf(src_path):
    filePathEnding = src_path.rfind('\\', )
    filename = src_path[filePathEnding+1:] # filename only miight be needed
    filePath = src_path[:filePathEnding] # filename only miight be needed
    filenameWoExt = filename[0:-4]

    # excludes matches in the temp and exported folders
    # note: current setup will also exclude any other folder starting with 'tmp' and 'exported'
    print(f'checking if it\'s a tmp filepath: {filePath[:5]}')
    if filePath[:6] == '.\\tmp\\':
        print(f'skipping {src_path}: it\'s a temp file')
        return f'skipping {src_path}: it\'s a temp file'
    if filePath[:10] == '.\\exported':
        print(f'skipping {src_path}: it\'s an exported file')
        return f'skipping {src_path}: it\'s an exported file'
    
    print(f"hey, {src_path} has been created!")

    tmpDir = f'.\\tmp\\{filenameWoExt}'

    if not os.path.exists(tmpDir):
        os.mkdir(tmpDir)

    tiffFiles = shredPdf(src_path, tmpDir)
    if len(tiffFiles) > 0: # confirms there were no errors shredding
        # pre-process image
        tmpPdfFiles = []
        for img_path in tiffFiles:
            processedImg = preProcess(img_path)

            # OCR it! psm = 1 will recognize 2-column layouts.
            pdf = pytesseract.image_to_pdf_or_hocr(processedImg, extension='pdf', config='--psm 1')
            # save pdf to temp path
            tmpSaveDir = f'{img_path[:-5]}.pdf'
            with open(tmpSaveDir, 'w+b') as f:
                f.write(pdf) # pdf type is bytes by default
                print(f'saved temp pdf: {tmpSaveDir}')
                tmpPdfFiles.append(tmpSaveDir)
        mergePdfs(tmpPdfFiles)

        remove(os.path.dirname(tiffFiles[0]))
        # save to pdf
        saveDir = f'.\\exported\\{filePath[6:]}\\{filenameWoExt}.pdf'


def shredPdf(src_path, destDir):
    # shreds pdfs into single-paged images
    # src_path = pdf to be shredded w/file location (currently using relative)
    # destDir = destimation to throw pdfs, inside a folder insdie tmp
    tiffFiles = [] # holds all the files which will be produced by the shredding
    time.sleep(0.015) # needed so the file can be 'unlocked' for reading/editing. Could go lower
    try:
        with Image(filename=src_path, resolution=IMG_RES) as img:
            #print(img.size)
            images = img.sequence
            pages = len(images)
            for i in range(pages):
                #i.type = 'bilevel' # helps OCR
                saveFilename = f'{destDir}/{src_path[2:-4]}_{i}.tiff'
                Image(images[i]).save(filename=saveFilename) # this will force overwrite
                tiffFiles.append(saveFilename)
    except:
        print('something went wrong when shredding PDF. Maybe not enough space? Maybe file locked?')

    #print(f'done shredding {src_path}!')
    return tiffFiles


    # make 

def preProcess(img_path):
    # loads image into cv2
    image = cv2.imread(img_path)
    # confirm that image is in grayscale
    if GRAYSCALE == True:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    # if you want to covert to binary
    if THRESHHOLD == True:
        gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]

    # helps get rid of salt and pepper noise in images
    if BLUR == True:
        gray = cv2.medianBlur(gray, 3)
    
    return gray

def mergePdfs(pdfFiles):
    # merges an array of pdfs into one file, saves it to exported folder
    #filePathEnding = pdfFiles[0].rfind('\\', )
    filename = ntpath.basename(pdfFiles[0]) # filename only miight be needed
    output = PdfFileMerger()
    
    for pdf in pdfFiles:
        with open(pdf, 'rb') as f:
            output.append(PdfFileReader(f))
    
    output.write(f'.\\exported\\{filename[:-6]}.pdf')
    output.close()
    print(f'saved ' + f'\\exported\\{filename[:-6]}.pdf')

if __name__ == "__main__":
    patterns = ["*.pdf", "*.tiff"]
    ignore_patterns = ""
    ignore_directories = True
    case_sensitive = True
    my_event_handler = PatternMatchingEventHandler(patterns, ignore_patterns, ignore_directories, case_sensitive)
    my_event_handler.on_created = on_created
    my_event_handler.on_deleted = on_deleted
    my_event_handler.on_modified = on_modified
    my_event_handler.on_moved = on_moved

    # create observer
    path = "."
    go_recursively = True
    my_observer = Observer()
    my_observer.schedule(my_event_handler, path, recursive=go_recursively)

    my_observer.start()
    # prevents script from exiting:
    try:
        while True:
            time.sleep(2)
    except KeyboardInterrupt:
        my_observer.stop()
        my_observer.join()