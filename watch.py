import time, os, csv
import cv2
import pytesseract
import logging, traceback
import multiprocessing
from wand.image import Image
from wand.display import display
from wand.color import Color
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
from PyPDF2 import PdfFileMerger, PdfFileReader
import ntpath, shutil

#### CONFIG
GRAYSCALE = False # recommended. enables to grayscale (can be used with THRESHOLD)
THRESHHOLD = False # recommended. enables conversion to binary B/W
BLUR = False # recommended. enables slight bluring (removes salt/pepper noise)

IMG_RES = 300 # recommend 300. Sets the resolution of the TIFF image to be OCR'd
# TESSERACT LOCATION:
pytesseract.pytesseract.tesseract_cmd = r"C:\Users\Richard\AppData\Local\Tesseract-OCR\tesseract.exe"

# LOG FILE DIRECTORY:
logging.basicConfig(filename='converted.log', filemode='w', level=logging.INFO)
# OCR TXT FILE PATH
ocrTxtFilePath = 'ocrTxt.csv' # logs suscessful CORs
ocrErrFilePath = 'ocrErr.csv' # logs failed OCRs

#### END CONFIG 

def ocrTxtListener(q):
    try:
        # listens for messages on q whenever OCR has been made, writes to file
        with open(ocrTxtFilePath, 'a', newline='') as f: # newline='' fixes double space between entries
            w = csv.writer(f)
            while 1:
                m = q.get()
                w.writerow(m)

    except Exception:
        traceback.print_exc()
        print('ERROR: listener failed. OCR text logging will no longer be performed')
    
def dummyFn(x):
    print('starting job')
    try:
        v += 1
    except Exception:
        traceback.print_exc()
    time.sleep(5)
    print(f'job done! Ans: {x}')

def remove(path):
    # removes file or folder recursively when passed an absolute path
    """ param <path> could either be relative or absolute. """
    if os.path.isfile(path) or os.path.islink(path):
        os.remove(path)  # remove the file
    elif os.path.isdir(path):
        shutil.rmtree(path)  # remove dir and all contains
    else:
        raise ValueError(f'Warning: Could not delete. file {path} is not a file or dir.'.format(path))

def on_created(event):
    if event.src_path[-4:] == '.pdf' or event.src_path[-4:] == '.PDF':
        #pool.apply_async(dummyFn, args=(event.src_path,))
        pool.apply_async(ocrPdf, args=(event.src_path, q,))
        
def on_deleted(event):
    #print(f"what the h**k! Someone deleted {event.src_path}!")
    pass

def on_modified(event):
    print(f"hey buddy, {event.src_path} has been modified")
    pass

def on_moved(event):
    #print(f"ok ok ok, someone moved {event.src_path} to {event.dest_path}")
    pass

def ocrPdf(src_path, q):
    # to print out errors when called by apply_async, a try/except needs to be wrapped around entire function
    try:
        filePathEnding = src_path.rfind('\\', )
        filename = src_path[filePathEnding+1:] # filename only miight be needed
        filePath = src_path[:filePathEnding] # filepath only miight be needed
        filenameWoExt = filename[0:-4]
        extracted_text = ' ' # holds OCR output

        # logging
        #errFile = open(ocrErrFilePath, 'a', newline='') # newline='' fixes double space between entries
        #errTxt = csv.writer(errFile) # writes list of failed OCR attempts

        # excludes matches in the temp and exported folders
        # note: current setup will also exclude any other folder starting with 'tmp' and 'exported'
        #print(f'checking if it\'s a tmp filepath: {filePath[:5]}')
        if filePath[:6] == '.\\tmp\\':
            print(f'skipping {src_path}: it\'s a temp file')
            return f'skipping {src_path}: it\'s a temp file'
        if filePath[:10] == '.\\exported':
            print(f'skipping {src_path}: it\'s an exported file')
            return f'skipping {src_path}: it\'s an exported file'
        
        print(f"processing: {src_path}")

        time.sleep(2) # allows for file to be copied completely before editing
        tmpDir = f'.\\tmp\\{filenameWoExt}'
        if not os.path.exists(tmpDir):
            os.mkdir(tmpDir)

        tiffFiles = shredPdf(src_path, tmpDir) # shreds pdf into TIFF files, for OCRing

        if len(tiffFiles) > 0: # confirms there were no errors shredding
            # pre-process image
            tmpPdfFiles = []
            
            for img_path in tiffFiles: # OCR's each image, saves temporary pdf
                processedImg = preProcess(img_path)

                # OCR it! psm = 1 will recognize 2-column layouts.
                pdf = pytesseract.image_to_pdf_or_hocr(processedImg, extension='pdf', config='--psm 1')
                text = pytesseract.image_to_string(processedImg,lang='eng', config='--psm 1')
                # save extracted text to variable
                extracted_text = extracted_text + text
                # save pdf to temp path
                tmpSaveDir = f'{img_path[:-5]}.pdf'
                with open(tmpSaveDir, 'w+b') as f:
                    f.write(pdf) # pdf type is bytes by default
                    print(f'saved temp pdf: {tmpSaveDir}')
                    tmpPdfFiles.append(tmpSaveDir)
            
            # merges temporary pdfs
            mergePdfs(tmpPdfFiles)
            
            # remove temporary tiff files
            remove(os.path.dirname(tiffFiles[0]))

            # save to pdf
            #saveDir = f'.\\exported\\{filePath[6:]}\\{filenameWoExt}.pdf'
            
            # save to text
            q.put([filenameWoExt, extracted_text, ''])

        return 1

    except Exception: # if aaany error pops up, print it and save to file the ocr which failed
        q.put([filenameWoExt, extracted_text, 'OCR_FAILED'])
        traceback.print_exc()
        return 0

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
                with Image(images[i]) as im:
                    im.background_color = Color('white') # Set white background.
                    im.alpha_channel = 'remove'          # Remove transparency and replace with bg.
                    im.save(filename=saveFilename) # this will force overwrite
                tiffFiles.append(saveFilename)
    except Exception as e:
        print(e)
        logging.error(f'Could not open {src_path}. Doc is either locked, storage space ran out, or doc is password protected.')
        print(f'Could not open {src_path}. Doc is either locked, storage space ran out, or doc is password protected.')

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
    # initializes multiprocessing
    cpuCount = multiprocessing.cpu_count() + 1 # adds one for the file-writing listener
    print(f'there are {cpuCount-1} cores on this computer. Using all of them.')
    pool = multiprocessing.Pool(processes=cpuCount)

    # initializes multiprocessing logger
    manager = multiprocessing.Manager()
    q = manager.Queue()
    watcher = pool.apply_async(ocrTxtListener, (q,))
    
    x = 3

    patterns = ["*.pdf", "*.PDF", "*.tiff"]
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