import re
from pytesseract import image_to_string
from difflib import SequenceMatcher
import logging
from PIL import Image, ImageGrab
import time
import numpy as np

ALIVE = []
DEAD = []
# Global lists
WEAPONS = ["punch", "Crowbar", "Machete", "Pan", "Sickle",
           "S12K", "S686", "S1897",
           "UMP9", "Micro-UZI", "Vector", "Tommy Gun",
           "AKM", "M16A4", "SCAR-L", "M416",
           "SKS", "M249",
           "AWM", "M24", "Kar98k", "VSS",
           "P1911", "P92", "R1895",
           "Frag Grenade", "Molotov Cocktail",
           "Crossbow"]
# TODO Fill this in for all supported resolutions
RES_MAP = {
    (1920, 1080):{
        "FEED": (0, 725, 550, 930),
        "LOBBY": (1817, 30, 1890, 70),
        "MATCH_TIMER": (940, 710, 990, 760)
    },
    (1440, 900): {
        "FEED": (30, 1200, 850, 1450),
        "LOBBY": (2727, 140, 2840, 200),
        "MATCH_TIMER": (1410, 1150, 1465, 1240)
    },

}

def get_lobby_countdown(boundary_box):
    '''Attempt to take a screen shot of the lobby countdown timer'''
    img = ImageGrab.grab(bbox=boundary_box)
    # TODO Move this to RES_MAP
    txt = image_to_string(scale_image(img))
    if txt.isdigit():
        countdown = int(txt)
        return countdown
    else:
        logging.warning("Lobby countdown not found (perhaps it hasn't loaded yet)")
        # REVIEW Current (imperfect) logic relies on this returning some number
        # for the countdown
        return 20


def is_similar(a, b, threshold=0.7, echo=False):
    '''Return the similarity score [0, 1] between two strings'''
    rate = SequenceMatcher(None, a, b).ratio()
    if echo:
        print(a, b, rate)
    if rate >= threshold:
        return True
    else:
        return False


# Attempt to resolve inputted name to existing name
def resolve_name(p_name, threshold=0.6, dead=False):
    '''Attempt to resolve a poorly read string into an already seen one.

    Unfortunately, bad readings of names beat out better readings that are seen later.
    Perhaps introduce a way to 'score' strings based on how likely they are to be actual
    player names.
    '''
    # Check targetted list for player name
    name = re.sub('[\[\]\.<>?/;:,\"\'\\()+=|~`]', '',
                  p_name)  # Remove dumb characters
    if name == '':
        logging.warning("Before: " + p_name + "\nAfter: " + name)
    # Remove "##*left" string if it exists
    name = re.sub('(-)?([0-9])?[0-9](.)?[Il]eft$', '', name)
    # name = re.sub('(\wkilled$)|(\wwith$)|(\wknocked$)|')
    if name == "":
        logging.warning("Empty name after filtering original: " + p_name)
        return None
    # Choose list to alter
    if dead:
        target_list = DEAD
    else:
        target_list = ALIVE
    results = []
    # Resolve name
    for x in DEAD:
        if is_similar(name, x, threshold):
            results.append(x)
    for x in ALIVE:
        if is_similar(name, x, threshold):
            # Player should now be dead
            if dead is True:
                ALIVE.remove(x)

            results.append(x)
    # Check results
    if len(results) > 1:
        logging.error(
            "More than 1 possible name resolution (defaulting to first for now): "
            + name + ", " + str(results))
        return results[0]
    elif len(results) == 0:
        logging.debug("No possible name resolution, adding to list: " + name)
        target_list.append(name)
        return name
    else:
        if p_name != results[0]:
            logging.debug("Resolving " + name + " to " + results[0])
        return results[0]


def resolve_wep(wep, threshold=0.7):
    '''Attempt to resolve an invalid weapon string'''
    results = []
    s = wep.replace("-", " ")  # Remove dashes to get rid of "players left"
    s = s.split(" ")[0]
    # Check string similarity for each possible item
    for x in WEAPONS:
        if is_similar(s, x, threshold):
            results.append(x)
    if len(results) > 1:
        logging.error(
            "More than 1 possible weapon resolution! (defaulting to 1st): "
            + s + "," + str(results))
    elif len(results) == 0:
        logging.warning("No possible resolution:" + s)
        return None
    else:
        logging.debug("Resolving " + s + " to " + results[0])
    return results[0]


def process_event(event):
    ''' Attempt to process an event string into an event object

    LOG FORMAT CASES
    1) Knockout
    VILLAIN knocked out VICTIM with WEAPON
    VILLAIN knocked out VICTIM by headshot with WEAPON
    2) Kill
    VILLAIN killed VICTIM with WEAPON
    VILLAIN finally killed VICTIM
    VILLAIN killed VICTIM by headshot with WEAPON
    TODO 3) Other
    VICTIM died outside playzone
    VICTIM died from falling
    VILLAIN ran over VICTIM with a vehicle
    '''
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
                return {
                    "villain": villain,
                    "victim": victim,
                    "weapon": weapon,
                    "type": e_type
                }
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
                return {
                    "villain": villain,
                    "victim": victim,
                    "weapon": weapon,
                    "type": e_type
                }
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
                return {
                    "villain": villain,
                    "victim": victim,
                    "type": e_type
                }

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
                return {
                    "villain": villain,
                    "victim": victim,
                    "weapon": weapon,
                    "type": e_type
                }
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
                return {
                    "villain": villain,
                    "victim": victim,
                    "weapon": weapon,
                    "type": e_type
                }
    # TODO Process this as a suicide and add other cases
    elif "died" in event or "outside" in event:
        logging.debug("Someone died outside the playzone")
        return None
    else:
        logging.warning("Trash string")
        return None


def filter_duplicates(events_list, cache_size=15):
    '''Attempt to remove duplicate events from events list'''
    logging.debug("Filtering duplicates with a cache_size= " + str(cache_size))
    event_cache = []
    filtered = []

    for event in events_list:
        dup = False
        for i in range(len(event_cache)):
            vic_match = is_similar(event["victim"], event_cache[i]["victim"])
            typ_match = is_similar(event["type"], event_cache[i]["type"])

            if vic_match and typ_match:
                logging.debug("Caught duplicate: " +
                              str(event) + " : " + str(event_cache[i]))
                dup = True
                break
        if not dup:
            filtered.append(event)
        # Pop back of cache and prepend the current event
        if len(event_cache) == cache_size:
            event_cache = event_cache[:len(event_cache) - 1]
        event_cache.insert(0, event)
    return filtered


def scale_image(im, factor=2.5):
    '''Scale an image by a factor'''
    # REVIEW There is a balance between performance and accuracy here
    img = im.resize(
        (int(im.width * factor), int(im.height * factor)), Image.ANTIALIAS)
    return img


def process_image(im):
    '''Send an image to Tesseract and receive text'''
    img = Image.fromarray(np.uint8(im[0]))
    img = scale_image(img)
    txt = image_to_string(img)
    return (txt, im[1])
