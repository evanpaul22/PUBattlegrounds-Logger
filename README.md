# Battlegrounds Log Grabber
A hacky screen grabber which does its best to parse Player Unknown's Battlegrounds kill feed via OCR
## Installation
* Download and install tesseract:
  * https://github.com/tesseract-ocr/tesseract/wiki/Downloads
  * You may need to add tesseract to your system PATH
* Install required packages
  * `pip install -r requirements.txt`

## How-to
* `python bgocr.py` will open the GUI
* Press "Start Capturing" when you're on the plane
* Press "Stop and Process" once you've got that sweet chicken dinner (or once you're dead)
  * A CSV output file will be written to `outputs/` and debug logs will be written to `logs/`
