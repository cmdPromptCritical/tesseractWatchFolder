import os, csv
from tika import parser

#### CONFIG
folder = r'./' # folder to scan for PDFs non-recursively
saveFile = r'ocrTxt2.csv' # file to save text inito (column 1 = filename w/o ext., column 2 = text wrapped in quotes "")

# open csv file
with open(saveFile, 'w', newline='') as f: # newline='' fixes double space between entries
    w = csv.writer(f)

    for root, directories, filenames in os.walk(folder):
        for filenames in filenames:
            print(os.path.join(root,filenames))
            pdfCheck = os.path.join(root,filenames)[-4:]
            if pdfCheck == '.pdf' or pdfCheck == '.PDF':
                raw = parser.from_file(os.path.join(root,filenames))['content']
                raw = raw.replace('\n', '') # remove new lines
                raw = raw.replace('  ', '') # remove double spaces
                print(f'schwoop. root: {root}\t\tfilenames: {filenames}')
                w.writerow([filenames[:-4], raw])