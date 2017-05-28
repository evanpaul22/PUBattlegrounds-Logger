# encoding=utf8
import sys

reload(sys)
sys.setdefaultencoding('utf8')
from pytesseract import image_to_string
from PIL import Image
from PIL import ImageGrab
import pyscreenshot as ps
from Tkinter import Tk, Label, Button
import time
import argparse
from difflib import SequenceMatcher
import multiprocessing
from unidecode import unidecode
from event import Node
import numpy as np
DEB = "[DEBUG]"
ERR = "[ERROR]"
test_set1 = "test_images/set1/"
test_set2 = "test_images/set2/"

dead_nodes = []  # root nodes
kill_nodes = []

WEAPONS = ["punch", "Crowbar", "Machete", "Pan", "Sickle",
           "S12K", "S686", "S1897",
           "UMP9", "Micro-UZI", "Vector", "Tommy Gun",
           "AKM", "M16A4", "SCAR-L", "M416",
           "SKS", "M249",
           "AWM", "M24", "Kar98k", "VSS",
           "P1911", "P92", "R1895",
           "Frag Grenade", "Molotov Cocktail",
           "Crossbow"]

# Use this for weapons, players, keywords, etc!
def is_similar(a, b, threshold=0.7):
    rate = SequenceMatcher(None, a, b).ratio()
    if args.verbose:
        print a, b, rate
    if rate >= threshold:
        return True
    else:
        return False

# Attempt to resolve invalid string to a valid string
def resolve_string(s, target_list, threshold=0.7):
    results = []
    s = s.replace("-", " ") # Remove dashes to get rid "players left"
    s = s.split(" ")[0]
    # Check string similarity for each possible item
    for x in target_list:
        if is_similar(s, x, threshold):
            results.append(x)
    if len(results) > 1:
        print ERR, "More than 1 possible resolution!", s, results
        return None
    elif len(results) == 0:
        print ERR, "No possible resolution:", s
        return None
    else:
        print DEB, "Resolving", s, "to", results[0]
    return results[0]

## LOG FORMAT CASES ##
# 1) Knockout
## VILLAIN knocked out VICTIM with WEAPON
## VILLAIN knocked out VICTIM by headshot with WEAPON
# 2) Kill
## VILLAIN killed VICTIM with WEAPON
## VILLAIN finally killed VICTIM
## VILLAIN killed VICTIM by headshot with WEAPON
## REVIEW ??? finally killed by headshot ???
# 3) Other
## VICTIM died outside playzone

# Process feed event
def process_event(event):
    e = event.split(" ")
    # Knocked out
    if "knocked" in event or "Knocked" in event or "out" in event:
        ## VILLAIN knocked out VICTIM by headshot with WEAPON
        if "by" in event or "headshot" in event:
            villain = e[0]
            victim = e[3]
            weapon = None
            # Find weapon
            for k in range(len(k)):
                if e[k] == "with":
                    weapon = e[k+1]
                    break
            # Can't reliably resolve
            if not weapon or len(weapon) < 3:
                print ERR, "Trash string"
                return None
            else:
                weapon = resolve_string(weapon, WEAPONS)
                return weapon
        ## VILLAIN knocked out VICTIM with WEAPON
        else:
            villain = e[0]
            victim = e[3]
            weapon = None
            for l in range(len(e)):
                if e[l] == "with":
                    weapon = e[l+1]
                    break
            # Can't reliably resolve
            if not weapon or len(weapon) < 3:
                print ERR, "Trash string"
                return None
            else:
                weapon = resolve_string(weapon, WEAPONS)
                return weapon
    # Killed
    elif "killed" in event:
        ## VILLAIN finally killed VICTIM
        if "finally" in event:
            villain = e[0]
            victim = e[3]
            return None
            # f_event = Node(victim, villain)
        ## VILLAIN killed VICTIM by headshot with WEAPON
        elif "by" in event or "headshot" in event:
            villain = e[0]
            victim = e[2]
            weapon = None
            # Try to find weapon
            for i in range(len(e)):
                if e[i] == "with":
                    weapon = e[i+1]
                    break
            # Can't reliably resolve
            if not weapon or len(weapon) < 3:
                print ERR, "Trash string"
                return None
            else:
                weapon = resolve_string(weapon, WEAPONS)
                return weapon
        ## VILLAIN killed VICTIM with WEAPON
        else:
            villain = e[0]
            victim = e[2]
            weapon = None
            # Try to find weapon
            for j in range(len(e)):
                if e[j] == "with":
                    weapon = e[j+1]
                    break
            # Can't reliably resolve
            if not weapon or len(weapon) < 3:
                print ERR, "Trash string"
                return None
            else:
                weapon = resolve_string(weapon, WEAPONS)
                return weapon
    # Death outside playzone
    elif "died" in event or "outside" in event:
        print "died outside playzone"
    else:
        print ERR, "Trash string"
# Scale an image
def scale_image(im):
    factor = 3 # REVIEW There is a balance between performance and accuracy here
    img = im.resize((int(im.width * factor), int(im.height * factor)), Image.ANTIALIAS)
    return img
# Process individual mage into a string via tesseract
def process_image(im):
    # global IMAGE_COUNTER
    im = Image.fromarray(np.uint8(im))
    im = scale_image(im)
    if args.dump:
        # im.save("dump/" + str(IMAGE_COUNTER) + ".bmp")
        im.show()
        # IMAGE_COUNTER -= 1
    txt = image_to_string(im)
    return txt

# Process all images in IMAGES list
def process_images():
    # Get number of cores
    print "test"
    cores = multiprocessing.cpu_count()
    if not cores:
        cores = 2
    # Assuming hyperthreading is available this should be efficient...
    threads = cores # * 2

    print "processing", len(IMAGES), "images with", threads, "threads"
    # Parallelize then rejoin
    pool = multiprocessing.Pool(threads)

    results = pool.map(process_image, IMAGES)
    pool.close()
    pool.join()
    # Print results
    feed_results = []
    # Each event is based on one image
    for events in results:
        events = events.split('\n')
        bad_indices = []
        # Remove bad indices and coerce to unicode to ASCII as best as possible
        for j in range(len(events)):
            if len(events[j]) < 10:
                bad_indices.append(j)
            else:
                events[j] = unidecode(u'' + events[j])
        # Remove bad events i.e. muddy text that isn't large enough
        events = [q for p, q in enumerate(events) if p not in bad_indices]
        # Process each event within the feed photo
        for event in events:
            feed_res = process_event(event)
            # Bad strings are thrown away
            if feed_res:
                feed_results.append(feed_res)
    print feed_results
    print DEB, "Finished gracefully"
    root.destroy()

# Multithreaded imaging test
def images_test():
    num_im = 20
    # Open test images
    for i in range(1, num_im + 1):
        if i > 9:
            fname = test_set1 + "Image 0" + str(i) + ".bmp"
        else:
            fname = test_set1 + "Image 00" + str(i) + ".bmp"
        if args.verbose:
            print "Opening", fname
        IMAGES.append(Image.open(fname))
    process_images()
# Simple image scaling test
def scaling_test():
    im = Image.open(test_set1 + "Image 001.bmp")
    im.show()
    im = scale_image(im)
    im.show()
# Grab screenshots until run_flag is switched.
# Note: this only works via multithreading (which Tkinter manages)
def screenshot_loop(interval=3):
    if run_flag:
        screenshot_loop.iterations +=1
        if args.verbose:
            print screenshot_loop.iterations
        # TODO hardcode resolution box values
        im = ImageGrab.grab(bbox=(0, 725, 550, height - 150))
        I = np.asarray(im)
        IMAGES.append(I)
    root.after(interval*1000, screenshot_loop)
screenshot_loop.iterations = 0

# GUI
class LogGUI:
    def __init__(self, master):
        self.master = master
        master.title("BGOCRLG")

        self.label = Label(master, text="Battlegrounds log grabber")
        self.label.pack()

        self.greet_button = Button(master, text="Start", command=self.start)
        self.greet_button.pack()

        self.close_button = Button(master, text="Stop", command=self.stop)
        self.close_button.pack()

        master.after(1000, screenshot_loop)
        master.mainloop()

    def start(self):
        global run_flag
        run_flag = True

    def stop(self):
        global run_flag, IMAGE_COUNTER
        run_flag = False
        IMAGE_COUNTER = len(IMAGES)
        process_images()


if __name__ == "__main__":
    IMAGES = []
    IMAGE_COUNTER = 0
    run_flag = False
    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose', action="store_true")
    parser.add_argument('--dump', action="store_true")
    args = parser.parse_args()
    # Open TKinter window
    root = Tk()
    # Trick to grab screen dimensions
    width = root.winfo_screenwidth()
    height = root.winfo_screenheight()
    if args.verbose:
        print DEB, "resolution:", width, height

    LogGUI(root)

    # images_test()
    # scaling_test()
