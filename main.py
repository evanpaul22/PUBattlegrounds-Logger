# encoding=utf8
import sys
from PIL import Image
from PIL import ImageGrab
from pytesseract import image_to_string
from tkinter import Tk, Label, Button
import time
import multiprocessing
import numpy as np
import hashlib
import csv
import logging
from unidecode import unidecode
import BGOCRLG_utils as b_utils
import threading
import argparse
# reload(sys)
# sys.setdefaultencoding('utf8')


class Session:
    '''A PUBG kill feed capture session utilizing Tesseract for OCR

    Too high of a Capture-interval increases processing time and affects
    parsing performance.
    Too high of a listen_interval may slightly affect weaker processors
    '''
    captures = []
    delayed_captures = []
    start_t = 0
    games_counter = 0
    active = False
    listen = True
    ready = False
    processing = False
    OUT_PATH = "outputs/"
    LOG_PATH = "logs/"

    def __init__(self, capture_interval=2.5, listen_interval=4):
        '''Start a capture session with a random file name'''
        # Make a random file name
        hash = hashlib.sha1()
        hash.update(str(time.time()).encode('utf-8'))
        self.OUTPUT_NAME = hash.hexdigest()[:10]

        logging.basicConfig(filename=self.LOG_PATH +
                            self.OUTPUT_NAME + '.log', level=logging.DEBUG)

        self.start_t = time.time()
        self.capture_interval = capture_interval
        self.listen_interval = listen_interval

    def report(self):
        '''Report results of session'''
        print("=" * 50)
        print("Finished gathering data sucessfully")
        print("Capture time:", time.time() - self.start_t)
        print("Total screenshots:", len(self.captures))
        print("# of unique events:", self.num_events)
        print("=" * 50)

    def process_images(self, images_list=None):
        '''Process all images in the captures buffer'''
        if images_list == None:
            images_list = self.captures
        self.processing = True
        # Get number of cores
        cores = multiprocessing.cpu_count()
        if not cores:
            cores = 2
        # REVIEW Test performance at different thread counts
        threads = cores * 2

        print("Processing", len(images_list), "images with", threads, "threads")
        # Parallelize then rejoin
        pool = multiprocessing.Pool(threads)

        results = pool.map(b_utils.process_image, images_list)
        pool.close()
        pool.join()

        feed_results = []
        if not results:
            print("No images were processed successfully!")
            return False
        # Each event is based on one image
        for events in results:
            if not events:
                print("Error: event is None?")
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
                        events[j] = unidecode('' + events[j])
                    except UnicodeDecodeError:
                        bad_indices.append(j)
            # Remove bad events i.e. muddy text that isn't large enough
            events = [q for p, q in enumerate(events) if p not in bad_indices]
            # Process each event within the feed photo
            for event in events:
                feed_res = b_utils.process_event(event)
                # Bad strings are thrown away
                if feed_res:
                    feed_res["time"] = t
                    feed_results.append(feed_res)

        if len(images_list) == 0:
            print("Allow program to capture images before stopping!")
        else:
            unique_events_list = b_utils.filter_duplicates(feed_results)
            self.num_events = len(unique_events_list)
            self.report()
            return unique_events_list
    # Detect if the player is in a lobby

    def check_for_lobby(self):
        img = ImageGrab.grab(bbox=BBOX["LOBBY"])
        if img:
            txt = image_to_string(b_utils.scale_image(img))
        else:
            logging.error("Image capture failed...")
            return False
        a = b_utils.is_similar(txt, "JOINED")
        if a:
            logging.debug("Lobby detected")
        return a

    def capture_loop(self):
        '''Grab screenshots of the kill feed every capture_interval seconds

        Continues self.active is switched.
        Boundary box dimensions are from global resolution map.
        '''
        while True:
            if self.active:
                im = ImageGrab.grab(bbox=BBOX["FEED"])
                # Convert to numpy array (to play nice with multithreading?)
                im_arr = np.asarray(im)
                # Truncate to 2 decimal places
                cur_t = '%.2f' % (time.time() - self.start_t)
                self.captures.append((im_arr, cur_t))

                # Loop every fixed # of seconds
                time.sleep(self.capture_interval)

    def state_listener(self):
        '''Periodically check the state of the session'''
        while True:
            if self.listen:
                in_lobby = self.check_for_lobby()
                logging.debug("in lobby:" + str(in_lobby))
                logging.debug("active:" + str(self.active))
                logging.debug("ready:" + str(self.ready))
                logging.debug("...")

                if in_lobby and not self.active:
                    logging.debug("Ready for a game")
                    print("Currently waiting in lobby, game capture to begin shortly")
                    self.ready = True
                    wait_t = b_utils.get_lobby_countdown(BBOX["MATCH_TIMER"])
                    time.sleep(wait_t)
                elif self.ready and not in_lobby:
                    self.active = True
                    self.ready = False
                    print("Capturing game #" + str(self.games_counter + 1))
                    logging.debug("Capturing game #" + str(self.games_counter + 1))
                # Game is still in progress
                elif not in_lobby and self.active and not self.ready:
                    pass
                elif in_lobby and self.active:
                    self.stop_and_process()

                time.sleep(self.capture_interval * self.listen_interval)

    def export_csv(self, events):
        '''Export events to a CSV file

        .CSV files ==> outputs/[session-id].csv
        Debug logs ==> logs/[session-id].log
        '''
        if events is not list:
            print("What are you doing don't do that")
            return
        csv_f_name = self.OUT_PATH + self.OUTPUT_NAME + ".csv"
        log_f_name = self.LOG_PATH + self.OUTPUT_NAME + ".log"

        if len(events) > 0:
            print("Results =>", csv_f_name)
            print("Debug logs =>", log_f_name)
            with open(csv_f_name, 'w') as f:
                w = csv.DictWriter(f, list(events[0].keys()))
                w.writeheader()
                for e in events:
                    w.writerow(e)
        else:
            print("Nothing to export!")

    def reset(self, listen=True):
        '''Reset state variables to prepare for a new game'''
        self.captures = []
        self.ready = False
        self.active = False
        self.processing = False
        self.num_events = 0
        # Make a new random file name
        hash = hashlib.sha1()
        hash.update(str(time.time()).encode('utf-8'))
        self.OUTPUT_NAME = hash.hexdigest()[:16]
        logging.basicConfig(filename=self.LOG_PATH +
                            self.OUTPUT_NAME + '.log', level=logging.DEBUG)
        b_utils.ALIVE = []
        b_utils.DEAD = []
        if listen:
            logging.debug("Ready for capture of new game!")
            self.games_counter += 1
        self.listen = listen

    def start(self):
        '''Start capturing and listening threads

        Capture thread grabs screenshots at a fixed interval and adds them to
        the IMAGES buffer.
        Listener thread periodically processes separate screenshots to determine
        state changes.
        '''
        capture = threading.Thread(target=self.capture_loop)
        listener = threading.Thread(target=self.state_listener)
        capture.setDaemon(True)
        listener.setDaemon(True)
        capture.start()
        listener.start()
        print("Waiting for game to start...")

    def stop_and_process(self, session_end=False):
        ''' Stop capturing and listening and process images.

        Capture and listener threads are spinlocked while Tesseract works its
        OCR magic. Resultant text is then parsed, filtered, and exported to a
        CSV file of (mostly) unique events.
        '''
        print("Game " + str(self.games_counter + 1) + " has ended!")
        self.listen = False
        self.active = False

        if not args.delay:
            events = self.process_images()
            if events:
                self.export_csv(events)
            else:
                print("Nothing to export")
        else:
            self.delayed_captures.append(self.captures)
            if session_end:
                if len(self.delayed_captures) > 0:
                    for games in self.delayed_captures:
                        events = self.process_images(images_list=games)
                        if events:
                            self.export_csv(events)
                        else:
                            print("Nothing to export")
                        self.reset(listen=False)
                else:
                    print("Nothing to process.")

        self.reset()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    # For slower computers (like mine): use this flag to process at the end of a session
    # rather than at the end of each game. It will take a long time, but it's better than
    # causing frame drops in the next game
    parser.add_argument('--delay-processing', dest="delay", action='store_true')
    args = parser.parse_args()

    # Simple way to get screen dimensions
    root = Tk()
    width = root.winfo_screenwidth()
    height = root.winfo_screenheight()
    root.destroy()

    # Just to be safe; though if RES_MAP is fully updated this shouldn't happen
    if not (width, height) in b_utils.RES_MAP:
        print("Unsupported resolution, defaulting to 1920x1080")
        width = 1920
        height = 1080

    # Get image boundary boxes from resolution map
    BBOX = b_utils.RES_MAP[(width, height)]

    print("Detected resolution:", str(width) + "x" + str(height))
    print("Press CTRL-C to end session and process any remaining images")
    s = Session()
    s.start()

    # TODO: Allow user inputs here to do things such as save a session early
    # without quitting the entire application.
    try:
        while True:
            pass
    # Catch CTRL-C and finish processing any images in the buffer
    except KeyboardInterrupt:
        if not s.processing:
            if args.delay:
                s.stop_and_process(session_end=True)
            else:
                s.stop_and_process(session_end=True)
            sys.exit()
        else:
            print("Please wait for images to finish processing!")
