# Battlegrounds Log Grabber
A hacky screen grabber which does its best to parse Player Unknown's Battlegrounds kill feed via OCR
## Installation
* Download and install tesseract:
  * https://github.com/tesseract-ocr/tesseract/wiki/Downloads
  * You may need to add tesseract to your system PATH
* Install required packages
  * `pip install -r requirements.txt`

## Usage guide
* `python main.py` will begin capturing the session.
  * For best results: start the program before or during the lobby.
  * End session with CTRL-C
  * If you're using a weak computer: try `python main.py --delay-processing` which will process all games at the end of your session.
* A CSV output file will be written to `outputs/` and debug logs will be written to `logs/`
  * New games will be automatically detected and new log and output files will be saved.
* When you're finished playing, simply press CTRL-C and any remaining images will be processed.
## Planned
* Better duplicate filtering and improved OCR
* Data visualization
  * Web interface
  * Track individual and global statistics
* Location detection
