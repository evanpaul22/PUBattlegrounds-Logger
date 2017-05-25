#!/usr/bin/python
from pytesseract import image_to_string
from PIL import Image
import pyscreenshot as ps
import Tkinter
import time
import argparse
from difflib import SequenceMatcher
dead_nodes = [] # root nodes
kill_nodes = []

# Use this for weapons, players, keywords, etc!
def is_similar(a, b, threshold=0.7):
    if SequenceMatcher(None, a, b).ratio() >= threshold:
        return True
    else:
        return False
# x1,y1,x2,y2
# img = ps.grab(bbox=(0,450,700,900))
# img.show()
def process_event(event):
    print event
    e = event.split(" ")
    if "knocked" in event or "Knocked" in event or "out" in event:
        villain = e[0]
        victim = e[3]
        weapon = e[5]
        p_node = Player_node(victim, villain, weapon, kill=False)

    # REVIEW How does this behave if you kill someone with a different weapon you downed them with?
    # Or if someone else kills the downed person. This will be hard to test =/
    elif "finally" in event:
        villain = e[0]
        victim = e[3]

        f_event = Player_node(victim, villain)

    elif "killed" in event:
        villain = e[0]
        victim = e[2]
        weapon = e[4]

        f_event = Player_node(victim, villain, weapon)


    else:
        print "ERROR"

def test():
    img = Image.open('bg_1920.jpg')
    # REVIEW See if this super hacky thing works.
    # probably would be better just to hardcode with all resolutions the game offers
    # unless I can think of something more clever
    w = float(width/4)
    h = float(height-height/6)
    img = img.crop((0, y_offset, w, h))
    # img.show()
    # REVIEW: Messing with this affects quality of OCR. Perhaps filtering or tweaking settings will too
    maxheight = 5000
    ratio = maxheight/h

    img = img.resize((int(img.width*ratio), int(img.height*ratio)), Image.ANTIALIAS)
    # img.show()
    txt = image_to_string(img)

    # Process events
    events = txt.split('\n')
    for e in events:
        process_event(e)


def screenshot_loop(interval=2):
    while True:
        time.sleep(interval - ((time.time() - start) % interval))
        img = ps.grab(bbox=(0, yoff, width - xoff, height - yoff))
        txt = image_to_string(img)
        print txt

if __name__ == "__main__":
    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose', action="store_true")
    args = parser.parse_args()

    # Silly but effective way to get screen size
    root = Tkinter.Tk()
    width = root.winfo_screenwidth()
    height = root.winfo_screenheight()
    root.destroy()
    # width = 1920
    # height = 1080

    if args.verbose:
        print width, height

    #x, y, width, height
    y_offset = height - (height / 3) + height/25
    x_offset = width - (width / 7)

    start = time.time()

    # test()
    screenshot_loop
