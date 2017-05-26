#!/usr/bin/python
from pytesseract import image_to_string
from PIL import Image
from PIL import ImageGrab
import pyscreenshot as ps
from Tkinter import Tk, Label, Button
import time
import argparse
from difflib import SequenceMatcher
dead_nodes = [] # root nodes
kill_nodes = []
from multiprocessing.dummy import Pool

# Use this for weapons, players, keywords, etc!
def is_similar(a, b, threshold=0.7):
    if SequenceMatcher(None, a, b).ratio() >= threshold:
        return True
    else:
        return False

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


def process_image(im):
    maxheight = 5000
    h = im.height
    ratio = maxheight/h
    img = im.resize((int(im.width*ratio), int(im.height*ratio)), Image.ANTIALIAS)
    txt = image_to_string(img)

    return txt

def process_images():
    print "processing", len(IMAGES), "images"
    for im in IMAGES:
        process_image(im)

def test():
    num_im = 20
    images = []
    for i in range(1, num_im + 1):
        if i > 9:
            fname = "test_images/Image 0" + str(i) + ".bmp"
        else:
            fname = "test_images/Image 00" + str(i) + ".bmp"
        images.append(Image.open(fname))
    print "processing"
    pool = Pool(4)
    results = pool.map(process_image, images)
    pool.close()
    pool.join()
    print results

def screenshot_loop(interval=3):
    if run_flag:
        im = ImageGrab.grab(bbox=(0, 725, 550, height - 150))
        IMAGES.append(im)
    root.after(1000, screenshot_loop)
    # time.sleep(interval)



class MyFirstGUI:
    def __init__(self, master):
        self.master = master
        master.title("BGOCR")

        self.label = Label(master, text="Battlegrounds log grabber")
        self.label.pack()

        self.greet_button = Button(master, text="Start", command=self.start)
        self.greet_button.pack()

        self.close_button = Button(master, text="Stop", command=self.stop)
        self.close_button.pack()

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

    # root = Tk()
    # # Trick to grab screen dimensions
    # width = root.winfo_screenwidth()
    # height = root.winfo_screenheight()
    # if args.verbose:
    #     print width, height
    #
    # my_gui = MyFirstGUI(root)
    # root.after(1000, screenshot_loop)
    # root.mainloop()


    test()
    # screenshot_loop()
    # #im = ps.grab())
