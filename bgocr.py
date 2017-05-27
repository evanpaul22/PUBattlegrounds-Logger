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

dead_nodes = []  # root nodes
kill_nodes = []

# Use this for weapons, players, keywords, etc!
def is_similar(a, b, threshold=0.7):
    if SequenceMatcher(None, a, b).ratio() >= threshold:
        return True
    else:
        return False

# Process feed event
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
# Scale an image
# REVIEW how this works
def scale_image(im):
    factor = 3
    img = im.resize((int(im.width * factor), int(im.height * factor)), Image.ANTIALIAS)
    return img
# Process image into a string via tesseract
# There is a balance between performance and accuracy here
def process_image(im, scale=True):
    if scale:
        im = scale_image(im)

    txt = image_to_string(im)
    return txt
# Procses all images in IMAGES list
def process_images():
    if args.verbose:
        print "processing", len(IMAGES), "images"
    for im in IMAGES:
        process_image(im)

# Multithreading test
def images_test():
    num_im = 20
    images = []
    # Open test images
    for i in range(1, num_im + 1):
        if i > 9:
            fname = "test_images/Image 0" + str(i) + ".bmp"
        else:
            fname = "test_images/Image 00" + str(i) + ".bmp"
        if args.verbose:
            print "Opening", fname
        images.append(Image.open(fname))
    # Get number of cores
    cores = multiprocessing.cpu_count()
    if not cores:
        cores = 2
    # Assuming hyperthreading is available this should be efficient...
    threads = cores * 2

    if args.verbose:
        print "processing", num_im, "images with", threads, "threads"

    pool = multiprocessing.Pool(threads)
    results = pool.map(process_image, images)
    pool.close()
    pool.join()
    # Print results
    for txt in results:
        print "==="
        txt = txt.split('\n')
        bad_indices = []
        # Remove bad indices and attempt to convert unicode to ASCII as best as possible
        for j in range(len(txt)):
            if len(txt[j]) < 10:
                bad_indices.append(j)
            else:
                txt[j] = unidecode(u''+txt[j])

        txt = [q for p, q in enumerate(txt) if p not in bad_indices]
        print txt

def scaling_test():
    im = Image.open("test_images/Image 001.bmp")
    im.show()
    im = scale_image(im)
    im.show()
# Grab screenshots until run_flag is switched.
# Note: this only works via multithreading (which Tkinter manages)
def screenshot_loop(interval=3):
    if run_flag:
        # TODO hardcode values
        im = ImageGrab.grab(bbox=(0, 725, 550, height - 150))
        IMAGES.append(im)
    root.after(1000, screenshot_loop)
    # time.sleep(interval)

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

    def start():
        global run_flag
        run_flag = True

    def stop():
        global run_flag
        run_flag = False
        process_images()


if __name__ == "__main__":
    IMAGES = []
    run_flag = False
    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose', action="store_true")
    args = parser.parse_args()
    # Open TKinter window
    # root = Tk()
    # # Trick to grab screen dimensions
    # width = root.winfo_screenwidth()
    # height = root.winfo_screenheight()
    # if args.verbose:
    #     print width, height
    #
    # LogGUI(root)
    #

    images_test()
    # scaling_test()
