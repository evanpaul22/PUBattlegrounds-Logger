#!/usr/bin/python
from pytesseract import image_to_string


from PIL import Image
from PIL import ImageGrab
import pyscreenshot as ps
from Tkinter import Tk, Label, Button
import time
import argparse
from difflib import SequenceMatcher
from pynput import keyboard
dead_nodes = [] # root nodes
kill_nodes = []

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

def test():
    img = Image.open('bg_1920.jpg')
    # probably would be better just to hardcode with all resolutions the game offers

    # REVIEW: Messing with this affects quality of OCR. Perhaps filtering or tweaking settings will too


    img = img.resize((int(img.width*ratio), int(img.height*ratio)), Image.ANTIALIAS)
    # img.show()
    txt = image_to_string(img)

    # Process events
    events = txt.split('\n')
    for e in events:
        process_event(e)


def screenshot_loop(interval=3):
    if run_flag:
        im = ImageGrab.grab(bbox=(0, 725, 550, height - 150))
        IMAGES.append(im)
    root.after(1000, screenshot_loop)
    # time.sleep(interval)
def process_images():
        print "processing", len(IMAGES), "images"
        for im in IMAGES:
            maxheight = 5000
            h = im.height
            ratio = maxheight/h
            img = im.resize((int(im.width*ratio), int(im.height*ratio)), Image.ANTIALIAS)
            txt = image_to_string(img)
            if not txt.replace(" ","").isalnum():
                print "[ERROR]", txt
            else:
                print txt


# def on_press(key):
#     try: k = key.char # single-char keys
#     except: k = key.name # other keys
#     if key == keyboard.Key.esc: return False # stop listener
#     if k == '\\': # keys interested
#         FLAG = False
#         print "STOPPING"
#         process_images()




class MyFirstGUI:
    def __init__(self, master):
        self.master = master
        master.title("A simple GUI")

        self.label = Label(master, text="Battlegrounds log grabber")
        self.label.pack()

        self.greet_button = Button(master, text="Start", command=start)
        self.greet_button.pack()

        self.close_button = Button(master, text="Stop", command=stop)
        self.close_button.pack()

    def greet(self):
        print("Greetings!")

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

    # lis = keyboard.Listener(on_press=on_press)
    # lis.start() # start to listen on a separate thread
    # lis.join() # no this if main thread is polling self.keys

    # Doesn't work on Windows...
    root = Tk()
    width = root.winfo_screenwidth()
    height = root.winfo_screenheight()
    root.destroy()
    # width = 1920
    # height = 1080

    if args.verbose:
        print width, height

    root = Tk()
    my_gui = MyFirstGUI(root)
    root.after(1000, screenshot_loop)
    root.mainloop()


    # test()
    # screenshot_loop()
    # #im = ps.grab())
