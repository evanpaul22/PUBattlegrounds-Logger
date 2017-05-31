# encoding=utf8
import sys
reload(sys)
sys.setdefaultencoding('utf8')
from PIL import Image
from PIL import ImageGrab
from pytesseract import image_to_string
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
import threading

class Session:
    captures = []
    start_t = 0
    active = False
    listen = True
    OUT_PATH = "outputs/"
    LOG_PATH = "logs/"
    counter = 0

    def __init__(self):
        # Make a random file name
        hash = hashlib.sha1()
        hash.update(str(time.time()))
        self.OUTPUT_NAME = hash.hexdigest()[:10]

        logging.basicConfig(filename=self.LOG_PATH + self.OUTPUT_NAME + '.log', level=logging.DEBUG)

        self.capture_interval = 2.5 # REVIEW
        self.start_t = time.time()
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
    # Detect if the player is in a lobby
    def check_for_lobby(self):
        img = ImageGrab.grab(bbox=BBOX["LOBBY"])
        txt = image_to_string(utils.scale_image(img))
        a = utils.is_similar(txt, "JOINED")
        return a
    # Grab screenshots until self.active is switched.
    # Note: this only works via multithreading (which Tkinter manages)
    def screenshot_loop(self):
        while self.active:
            if self.counter == 0:
                print "Capturing kill feed!"
            self.counter += 1
            im = ImageGrab.grab(bbox=BBOX["FEED"])
            # Convert to numpy array (to play nice with multithreading?)
            I = np.asarray(im)
            # Truncate to 2 decimal places
            cur_t = '%.2f' % (time.time() - self.start_t)
            self.captures.append((I, cur_t))

            # Loop every fixed # of seconds
            time.sleep(self.capture_interval)
        print "Kill feed capture complete!"
    # Checks the state of the session
    def state_listener():
        while self.listen:
            print "..."
            in_lobby = self.check_for_lobby()

            if not (in_lobby and self.active and self.ready):
                print "Waiting for lobby..."
            elif in_lobby and not self.active:
                print "Ready for a game!"
                self.ready = True
            if self.ready and not in_lobby:
                self.active = True
                self.ready = False
                print "Game has begun!"
            if not in_lobby and self.active and not self.ready:
                print "Game is still in progress!"
            if in_lobby and self.active:
                print "Game has ended!"
                # "Pause" threads during image processing
                self.active = False
                self.listen = False
                events = self.process_images()
                self.export_csv(events)
                self.reset() # This turns listening back on

            time.sleep(self.capture_interval * 4)
        print "Done listening for now!"
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

    # Reset variables to prepare for new game
    def reset(self):
        self.counter = 0
        self.captures = []
        self.ready = False
        self.game_in_progress = False
        self.listen = True
        self.active = False
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
        main = threading.Thread(target=screenshot_loop)
        listener = threading.Thread(target=state_listener)
        main.start()
        listener.start()

    def stop(self):
        self.active = False
        events = self.process_images()
        self.export_csv(events)
        self.reset()


if __name__ == "__main__":
    # TODO Fill this in for all supported resolutions
    RES_MAP = {
        (1920, 1080): {"FEED": (0, 725, 550, 930), "LOBBY": (1817,30,1890,70)},
        # This isn't really 1440x900, but based rather on a test video I use when doing dev on my Macbook
        (1440, 900): {"FEED": (30, 1200, 850, 1450), "LOBBY": (2727,140,2840,200)},
    }

    # Open TKinter window
    root = Tk()
    # Trick to grab screen dimensions
    width = root.winfo_screenwidth()
    height = root.winfo_screenheight()

    root.destroy()
    if not RES_MAP.has_key((width, height)):
        print "Unsupported resolution, defaulting to 1920x1080"
        width = 1920
        height = 1080

    BBOX = RES_MAP[(width, height)]

    print "Resolution:", width, height

    Session()
    check_new_game()
