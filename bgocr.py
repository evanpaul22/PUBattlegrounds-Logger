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
from difflib import SequenceMatcher
import multiprocessing
from unidecode import unidecode
import numpy as np
import re
import hashlib
import csv
import logging
##############
# Log Levels #
##############
# Debug
# Info
# Warning
# Error
# Critical

# Use this for weapons, players, keywords, etc!
def is_similar(a, b, threshold=0.7, echo=False):
    rate = SequenceMatcher(None, a, b).ratio()
    if echo:
        print a, b, rate
    if rate >= threshold:
        return True
    else:
        return False

# Attempt to resolve invalid weapon to a valid weapon
def resolve_wep(wep, threshold=0.7):
    results = []
    s = wep.replace("-", " ")  # Remove dashes to get rid "players left"
    s = s.split(" ")[0]
    # Check string similarity for each possible item
    for x in WEAPONS:
        if is_similar(s, x, threshold):
            results.append(x)
    if len(results) > 1:
        logging.error(
            "More than 1 possible weapon resolution! (defaulting to first for now): " + s + "," + str(results))
    elif len(results) == 0:
        logging.warning("No possible resolution:" + s)
        return None
    else:
        logging.debug("Resolving " + s + " to " + results[0])
    return results[0]
# Attempt to resolve inputted name to existing name
def resolve_name(p_name, threshold=0.6, dead=False):
    # Check targetted list for player name
    name = re.sub('[\[\]\.<>?/;:,\"\'\\()+=|~`]', '', p_name)  # Remove dumb characters
    logging.debug("Before: " + p_name + "; After: " + name)
    # Remove "##*left" string if it exists
    name = re.sub('(-)?([0-9])?[0-9](.)?[Il]eft$', '', name)
    # name = re.sub('(\wkilled$)|(\wwith$)|(\wknocked$)|')
    if name == "":
        logging.warning("Empty name after filtering original: " + p_name)
        return None
    # Choose list to alter
    if dead:
        target_list = DEAD_PLAYERS
    else:
        target_list = ALIVE_PLAYERS
    results = []
    # Resolve name
    for x in DEAD_PLAYERS:
        if is_similar(name, x, threshold):
            results.append(x)
    for x in ALIVE_PLAYERS:
        if is_similar(name, x, threshold):
            # Player should now be dead
            if dead == True:
                ALIVE_PLAYERS.remove(x)

            results.append(x)
    # Check results
    if len(results) > 1:
        logging.error(
            "More than 1 possible name resolution (defaulting to first for now): " + name + ", " + str(results))
        return results[0]
    elif len(results) == 0:
        logging.debug("No possible name resolution, adding to list: " + name)

        target_list.append(name)
        return name
    else:
        logging.debug("Resolving " + name + " to " + results[0])
        return results[0]


## LOG FORMAT CASES ##
# 1) Knockout
# VILLAIN knocked out VICTIM with WEAPON
# VILLAIN knocked out VICTIM by headshot with WEAPON
# 2) Kill
# VILLAIN killed VICTIM with WEAPON
# VILLAIN finally killed VICTIM
# VILLAIN killed VICTIM by headshot with WEAPON
# 3) Other
# VICTIM died outside playzone
# VICTIM died from falling

# Process feed event
def process_event(event):
    e = event.split(" ")
    if len(e) < 3:
        logging.warning("Trash string")
        return None
    # Knocked out
    if "knocked" in event or "Knocked" in event or "out" in event:
        # VILLAIN knocked out VICTIM by headshot with WEAPON
        e_type = "KO"
        if "by" in event or "headshot" in event:
            if len(e) < 8:
                logging.warning("Malformed: " + str(e))
                return None
            weapon = None
            villain = None
            victim = None
            name_i = 3  # Expected index

            # Find variables
            for k in range(len(e)):
                if is_similar(e[k], "knocked"):
                    villain = ''.join(e[:k])
                    villain = resolve_name(villain)
                elif is_similar(e[k], "out"):
                    name_i = k + 1
                elif is_similar(e[k], "by"):
                    victim = ''.join(e[name_i:k])
                    victim = resolve_name(victim)
                elif is_similar(e[k], "with"):
                    try:
                        weapon = e[k + 1]
                    except IndexError:
                        logging.error("IndexError: " + str(e))
                    break

            # Can't reliably resolve
            if not weapon or not villain or not victim or len(weapon) < 3:
                logging.warning("Trash string")
                return None
            else:
                weapon = resolve_wep(weapon)
                return {"villain": villain, "victim": victim, "weapon": weapon, "type": e_type}
        # VILLAIN knocked out VICTIM with WEAPON
        else:
            if len(e) < 6:
                logging.warning("Malformed: " + str(e))
                return None

            villain = None
            victim = None
            weapon = None
            name_i = 3  # Expected index
            # Find variables
            for l in range(len(e)):
                if is_similar(e[l], "knocked"):
                    villain = ''.join(e[:l])
                    villain = resolve_name(villain)
                elif is_similar(e[l], "out"):
                    name_i = l + 1
                elif is_similar(e[l], "with"):
                    victim = ''.join(e[name_i:l])
                    victim = resolve_name(victim)
                    try:
                        weapon = e[l + 1]
                    except IndexError:
                        logging.error("IndexError: " + str(e))
                    break
            # Can't reliably resolve
            if not weapon or not victim or not villain or len(weapon) < 3:
                logging.warning("Trash string")
                return None
            else:
                weapon = resolve_wep(weapon)
                return {"villain": villain, "victim": victim, "weapon": weapon, "type": e_type}
    # Killed
    elif "killed" in event:
        # VILLAIN finally killed VICTIM
        if "finally" in event:
            if len(e) < 4:
                logging.warning("Malformed: " + str(e))
                return None

            e_type = "EXECUTION"
            villain = None
            victim = None
            # find variables
            for q in range(len(e)):
                if is_similar(e[q], "finally"):
                    villain = ''.join(e[:q])
                    villain = resolve_name(villain)
                elif is_similar(e[q], "killed"):
                    try:
                        victim = e[q + 1]
                        victim = resolve_name(victim, dead=True)
                    except IndexError:
                        logging.error("IndexError: " + str(e))
            # Can't reliably resolve
            if not victim or not villain:
                logging.warning("Trash string")
                return None
            else:
                return {"villain": villain, "victim": victim, "weapon": None, "type": e_type}

        # VILLAIN killed VICTIM by headshot with WEAPON
        elif "by" in event or "headshot" in event:
            if len(e) < 7:
                logging.warning("Malformed: " + str(e))
                return None

            e_type = "KILL"
            villain = None
            victim = None
            weapon = None
            name_i = 2  # Expected index
            # Find variables
            for i in range(len(e)):
                if is_similar(e[i], "killed"):
                    name_i = i + 1
                    villain = "".join(e[:i])
                    villain = resolve_name(villain)
                elif is_similar(e[i], "by"):
                    victim = ''.join(e[name_i:i])
                    victim = resolve_name(victim, dead=True)
                elif is_similar(e[i], "with"):
                    try:
                        weapon = e[i + 1]
                    except IndexError:
                        logging.error("IndexError: " + str(e))
                    break
            # Can't reliably resolve
            if not villain or not victim or not weapon or len(weapon) < 3:
                logging.warning("Trash string")
                return None
            else:
                weapon = resolve_wep(weapon)
                return {"villain": villain, "victim": victim, "weapon": weapon, "type": e_type}
        # VILLAIN killed VICTIM with WEAPON
        else:
            if len(e) < 5:
                logging.warning("Malformed: " + str(e))
                return None

            e_type = "KILL"
            villain = None
            victim = None
            weapon = None
            name_i = 2  # Expected index
            # Find variables
            for j in range(len(e)):
                if is_similar(e[j], "killed"):
                    name_i = j + 1
                    villain = "".join(e[:j])
                    villain = resolve_name(villain)
                elif is_similar(e[j], "with"):
                    victim = "".join(e[name_i:j])
                    victim = resolve_name(victim, dead=True)
                    try:
                        weapon = e[j + 1]
                    except IndexError:
                        logging.error("IndexError: " + str(e))
                    break
            # Can't reliably resolve
            if not victim or not villain or not weapon or len(weapon) < 3:
                logging.warning("Trash string")
                return None
            else:
                weapon = resolve_wep(weapon)
                return {"villain": villain, "victim": victim, "weapon": weapon, "type": e_type}
    # Death outside playzone
    # TODO Do something for this
    elif "died" in event or "outside" in event:
        # print "died outside playzone"
        return None
    else:
        logging.warning("Trash string")
        return None

# Remove duplicate events
def filter_duplicates(source):
    cache = []
    filtered = []

    for datum in source:
        dup = False
        for i in range(len(cache)):
            vic_match = False
            typ_match = False
            # if datum["villain"] == cache[i]["villain"]:
            #     vil_match = True
            if is_similar(datum["victim"], cache[i]["victim"]):
                vic_match = True
            # if datum["weapon"] == cache[i]["weapon"]:
            #     wep_match = True
            if is_similar(datum["type"], cache[i]["type"]):
                typ_match = True
            if vic_match and typ_match:
                logging.debug("Caught duplicate: " +
                              str(datum) + " : " + str(cache[i]))
                dup = True
                break
        if not dup:
            filtered.append(datum)
        # Pop back of cache and prepend the current datum
        if len(cache) == 10:
            cache = cache[:len(cache) - 1]
        cache.insert(0, datum)
    return filtered
# Scale an image
def scale_image(im):
    factor = 3  # REVIEW There is a balance between performance and accuracy here
    img = im.resize(
        (int(im.width * factor), int(im.height * factor)), Image.ANTIALIAS)
    return img
# Process individual image into a string via tesseract
def process_image(im):
    img = Image.fromarray(np.uint8(im[0]))
    img = scale_image(img)
    txt = image_to_string(img)
    return (txt, im[1])

# Process all images in IMAGES list
def process_images():
    # Get number of cores
    cores = multiprocessing.cpu_count()
    if not cores:
        cores = 2
    # REVIEW Test performance at different thread counts
    threads = cores * 2

    print "Processing", len(IMAGES), "images with", threads, "threads"
    # Parallelize then rejoin
    pool = multiprocessing.Pool(threads)

    results = pool.map(process_image, IMAGES)
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
            feed_res = process_event(event)
            # Bad strings are thrown away
            if feed_res:
                feed_res["time"] = t
                feed_results.append(feed_res)

    if len(IMAGES) == 0:
        print "Allow program to capture images before stopping!"
    else:
        root.destroy()
        print "=" * 50
        print "Finished gathering data sucessfully"
        print "Execution time:", time.time() - START_T
        print "Total screenshots:", len(IMAGES)
        unique_events_list = filter_duplicates(feed_results)
        print "# of unique events:", len(unique_events_list)
        print "=" * 50
        logging.debug("LIVING PLAYERS:")
        for player in ALIVE_PLAYERS:
            logging.debug(player)
        logging.debug("DEAD PLAYERS:")
        for ghost in DEAD_PLAYERS:
            logging.debug(ghost)
        return unique_events_list
# Multithreaded imaging test
def images_test():
    num_im = 20
    # Open test images
    for i in range(1, num_im + 1):
        if i > 9:
            fname = test_set1 + "Image 0" + str(i) + ".bmp"
        else:
            fname = test_set1 + "Image 00" + str(i) + ".bmp"
        IMAGES.append(Image.open(fname))
    process_images()
# Simple image scaling test
def scaling_test():
    im = Image.open(test_set1 + "Image 001.bmp")
    im.show()
    im = scale_image(im)
    im.show()
# Grab screenshots until RUN_FLAG is switched.
# Note: this only works via multithreading (which Tkinter manages)
def screenshot_loop(interval=3):
    if RUN_FLAG:
        im = ImageGrab.grab(bbox=DIM)
        # Convert to numpy array (to play nice with multithreading?)
        I = np.asarray(im)
        # Truncate to 2 decimal places
        cur_t = '%.2f' % (time.time() - START_T)
        IMAGES.append((I, cur_t))
    root.after(interval * 1000, screenshot_loop)

# Export events to csv
def export_csv(events):
    f_name = OUT + OUTPUT_NAME + ".csv"
    if len(IMAGES) > 0 and len(events) > 0:
        print "Outputting results to", f_name
        with open(f_name, 'wb') as f:
            w = csv.DictWriter(f, events[0].keys())
            w.writeheader()
            for e in events:
                w.writerow(e)
    else:
        print "Nothing to export!"

# TODO: Move class to its own file
# GUI
class LogGUI:
    def __init__(self, master):
        self.master = master
        master.title("BG LOGGER")

        self.txt = Label(master, text="Press start on the plane")
        self.txt.pack()

        self.greet_button = Button(master, text="Start capturing", command=self.start)
        self.greet_button.pack()

        self.close_button = Button(master, text="Stop and process", command=self.stop)
        self.close_button.pack()

        master.after(1000, screenshot_loop)
        # Keep window on top
        master.lift()
        master.attributes('-topmost',True)
        master.after_idle(root.attributes,'-topmost',False)

        master.mainloop()

    def start(self):
        global RUN_FLAG, START_T
        print "Capturing kill feed..."
        START_T = time.time()
        RUN_FLAG = True

    def stop(self):
        global RUN_FLAG, IMAGE_COUNTER
        RUN_FLAG = False
        IMAGE_COUNTER = len(IMAGES)
        events = process_images()
        export_csv(events)


if __name__ == "__main__":
    # Paths
    im_pre = "test_images/"
    OUT = "outputs/"
    LOGS = "logs/"
    # Make a random file name
    hash = hashlib.sha1()
    hash.update(str(time.time()))
    OUTPUT_NAME = hash.hexdigest()[:10]
    test_set1 = im_pre + "set1/"
    test_set2 = im_pre + "set2/"

    logging.basicConfig(filename=LOGS + OUTPUT_NAME + '.log', level=logging.DEBUG)

    # Global lists
    ALIVE_PLAYERS = []
    DEAD_PLAYERS = []
    WEAPONS = ["punch", "Crowbar", "Machete", "Pan", "Sickle",
               "S12K", "S686", "S1897",
               "UMP9", "Micro-UZI", "Vector", "Tommy Gun",
               "AKM", "M16A4", "SCAR-L", "M416",
               "SKS", "M249",
               "AWM", "M24", "Kar98k", "VSS",
               "P1911", "P92", "R1895",
               "Frag Grenade", "Molotov Cocktail",
               "Crossbow"]
    START_T = 0
    IMAGES = []
    IMAGE_COUNTER = 0
    RUN_FLAG = False
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

    LogGUI(root)
