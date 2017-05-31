# encoding=utf8
import sys
reload(sys)
sys.setdefaultencoding('utf8')
from PIL import Image
from PIL import ImageGrab
import pyscreenshot as ps
from Tkinter import Tk, Label, Button
import time
import multiprocessing
import numpy as np
import hashlib
import csv
import logging
from unidecode import unidecode
import BGOCRLG_utils as utils

class Session:
    captures = []
    start_t = 0
    active = False
    OUT_PATH = "outputs/"
    LOG_PATH = "logs/"

    def __init__(self, root):
        # Make a random file name
        self.root = root
        hash = hashlib.sha1()
        hash.update(str(time.time()))
        self.OUTPUT_NAME = hash.hexdigest()[:10]

        logging.basicConfig(filename=self.LOG_PATH + self.OUTPUT_NAME + '.log', level=logging.DEBUG)

        self.capture_interval = 3 # REVIEW
        self.launch_GUI()
    # Report results f session
    def report(self):
        print "=" * 50
        print "Finished gathering data sucessfully"
        print "Capture time:", time.time() - self.start_t
        print "Total screenshots:", len(self.captures)
        print "# of unique events:", self.num_events
        print "=" * 50
    # Process all images in IMAGES list
    def process_images(self):
        # Get number of cores
        cores = multiprocessing.cpu_count()
        if not cores:
            cores = 2
        # REVIEW Test performance at different thread counts
        threads = cores * 2

        print "Processing", len(self.captures), "images with", threads, "threads"
        # Parallelize then rejoin
        pool = multiprocessing.Pool(threads)

        results = pool.map(utils.process_image, self.captures)
        pool.close()
        pool.join()

        feed_results = []
        # Each event is based on one image
        for events in results:
            if len(events[0]) == 0:
                logging.warning("Trash string")
                continue
            t = events[1]

            events = events[0].split('\n')

            bad_indices = []
            # Remove bad indices and coerce to unicode to ASCII as best as possible
            for j in range(len(events)):
                if len(events[j]) < 10:
                    bad_indices.append(j)
                else:
                    try:
                        events[j] = unidecode(u'' + events[j])
                    except UnicodeDecodeError:
                        bad_indices.append(j)
            # Remove bad events i.e. muddy text that isn't large enough
            events = [q for p, q in enumerate(events) if p not in bad_indices]
            # Process each event within the feed photo
            for event in events:
                feed_res = utils.process_event(event)
                # Bad strings are thrown away
                if feed_res:
                    feed_res["time"] = t
                    feed_results.append(feed_res)

        if len(self.captures) == 0:
            print "Allow program to capture images before stopping!"
        else:
            unique_events_list = utils.filter_duplicates(feed_results)
            self.num_events = len(unique_events_list)
            self.report()
            return unique_events_list
    # Grab screenshots until self.active is switched.
    # Note: this only works via multithreading (which Tkinter manages)
    def screenshot_loop(self):
        if self.active:
            # REVIEW Make DIM a member?
            im = ImageGrab.grab(bbox=DIM)
            # Convert to numpy array (to play nice with multithreading?)
            I = np.asarray(im)
            # Truncate to 2 decimal places
            cur_t = '%.2f' % (time.time() - self.start_t)
            self.captures.append((I, cur_t))
        # Loop every fixed # of seconds
        self.root.after(self.capture_interval * 1000, self.screenshot_loop)
    # Export events to csv
    def export_csv(self, events):
        csv_f_name = self.OUT_PATH + self.OUTPUT_NAME + ".csv"
        log_f_name = self.LOG_PATH + self.OUTPUT_NAME + ".log"

        if len(self.captures) > 0 and len(events) > 0:
            print "Results =>", csv_f_name
            print "Debug logs =>",log_f_name
            with open(csv_f_name, 'wb') as f:
                w = csv.DictWriter(f, events[0].keys())
                w.writeheader()
                for e in events:
                    w.writerow(e)
        else:
            print "Nothing to export!"

    def launch_GUI(self):
        self.root = root
        self.root.title("BG LOGGER")

        self.txt = Label(self.root, text="Press start on the plane")
        self.txt.pack()

        self.greet_button = Button(self.root, text="Start capturing", command=self.start)
        self.greet_button.pack()

        self.close_button = Button(root, text="Stop and process", command=self.stop)
        self.close_button.pack()

        # Keep window on top
        self.root.lift()
        self.root.attributes('-topmost',True)
        self.root.after_idle(root.attributes,'-topmost',False)
        self.root.after(1000, self.screenshot_loop())
        self.root.mainloop()

    def reset(self):
        self.captures = []
        # Make a random file name
        hash = hashlib.sha1()
        hash.update(str(time.time()))
        self.OUTPUT_NAME = hash.hexdigest()[:10]
        logging.basicConfig(filename=self.LOG_PATH + self.OUTPUT_NAME + '.log', level=logging.DEBUG)
        utils.ALIVE = []
        utils.DEAD = []
        print "Ready for capture of new game!"

    # Start capturing
    # TODO Make this dynamic so the user only has to press it once! (i.e. 'press this in first lobby; BGOCRLG will detect new games')
    def start(self):
        print "Capturing kill feed..."
        self.start_t = time.time()
        self.active = True

    def stop(self):
        self.active = False
        events = self.process_images()
        self.export_csv(events)
        self.reset()


if __name__ == "__main__":
    # TODO Fill this in for all supported resolutions
    RES_MAP = {
        (1920, 1080): (0, 725, 550, 930),
        (1440, 900): (30, 1200, 850, 1450),
    }

    # Open TKinter window
    root = Tk()
    # Trick to grab screen dimensions
    width = root.winfo_screenwidth()
    height = root.winfo_screenheight()

    if not RES_MAP.has_key((width, height)):
        print "Unsupported resolution, defaulting to 1920x1080"
        width = 1920
        height = 1080

    DIM = RES_MAP[(width, height)]

    print "Resolution:", width, height

    Session(root)
