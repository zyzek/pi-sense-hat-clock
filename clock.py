#!/usr/bin/python3

"""
Displays a little clock on the pixel array of a raspberry pi sense hat.
The current hour is indicated with a hexadecimal character, while the 
background of the array fills up with colour from left to right as the
hour elapses.

Designed to be run with, for example: `nohup ./clock.py &` and just left
running forever.

Improvements To Be Made:
    * Differential letter and background dimming.
    * Colour depending on time of day.
    * Vertical gradient for time of day transitions (e.g. orange to blue for dawn or dusk).
    * Background brightness depending on seconds in the minute.
    * Find out how to control the sense hat colours more precisely so that colour transitions aren't so crunchy.
"""

import sys
import signal
import json
import math
import time
import datetime
import pytz
from sense_hat import SenseHat

# The path to the JSON file storing the mapping from letters to images.
LETTERS_FILE_PATH = 'letters.json'

# Replace this with 0, 90, 180, or 270 depending on your pi setup.
ROTATION = 180

# Replace this with your timezone.
TIMEZONE = "Australia/Sydney"

def clamp(x, lower, upper):
    return max(lower, min(x, upper))

def smoothstep(lower, upper, x):
    x = clamp((x - lower) / (upper - lower), 0, 1)
    return x * x * (3 - 2*x)

def col(r, g, b, l=1.0):
    """Converts from colour triples in the range [0,1] to an ordinary 3 byte triplet."""
    return [int(l*r*255), int(l*g*255), int(l*b*255)]

def dim(p, l):
    """p should be a 3 byte triplet"""
    return [int(p[0]*l), int(p[1]*l), int(p[2]*l)]

def time_letter(hour):
    """12-hour time in hex characters, except midday is 'c' and midnight is '0'"""
    if hour == 12:
        return 'c'
    return hex(hour%12)[2:]

def minutes_brightness(mins, x):
    """
    Given an x coordinate from 0 to 7, gives the brightness of that pixel in the range [0, 1].
    The display is supposed to fill up from left to right over an hour, so if it is half past
    the hour, then all the pixels in the left half of the display will be fully lit, and all
    the ones to the right will be blank. If the fraction of the display to be lit does not
    divide pixels evently, then the pixel it falls on will brighten proportionally with the
    fraction of its division which has elapsed.
    """
    mins_x = (mins / 60) * 8
    x_diff = mins_x - x

    if x_diff < 0:
        return 0
    elif x_diff < 1:
        return mins_x % 1
    else:
        return 1

def time_of_day_color(hours, mins):
    midnight = [0,0,128]
    dawn = [200, 150, 70]
    midday = [40, 60, 60]
    dusk = [250, 150, 50]
    return [10,0,100]

def bg_if_blank(col, bg_col):
    """
    Given a colour, returns it unchanged if it is non-zero (is not a background pixel).
    Otherwise, return the provided background colour.
    """
    return col if col != [0,0,0] else bg_col

def letter_pixel_col(x, y, p, hours, mins):
    """
    Given a pixel, return it unchanged if it's background,
    else given its coordinate, and the time, compute the appropriate backgournd colour.
    """
    return bg_if_blank(p, dim(time_of_day_color(hours, mins), minutes_brightness(mins, x)))

def load_letters():
    """
    Loads the letters that can be displayed as a dictionary mapping from the character
    to its pixel layout as a 2d list of binary values indicating whether an individual
    pixel is lit or not.
    The letters are loaded as 5x8 images, but are padded to 8x8 (left-justified) to
    be displayed on the sense hat.

    Letters are drawn this way because the sense hat library function that draws
    letters leads to flickering on redraw when the background is replaced.
    """
    with open(LETTERS_FILE_PATH, 'r') as letters_file:
        letters_dict = json.load(letters_file)
        for letter in letters_dict:
            letters_dict[letter] = [[0]+row+[0,0] for row in letters_dict[letter]] # Pad with blank columns.
        return letters_dict

def quarter_rotation(g):
    """Rotates a list of lists a quarter turn anti-clockwise."""
    return [list(col) for col in zip(*[reversed(row) for row in g])]

def rotate(grid, quarter_turns):
    """
    Rotates a list of lists by several quarter turns anti-clockwise.
    Rotates clockwise if provided a negative argument.
    """
    quarter_turns %= 4
    if quarter_turns == 0:
        return list(grid)
    return rotate(quarter_rotation(grid), quarter_turns-1)

def clear_and_exit(sense):
    """Clears the screen and exits gracefully, in case sigterm or sigint is received."""
    sadface = [[0,0,0,0,0,0,0,0],
               [1,0,1,0,0,1,0,1],
               [0,1,0,0,0,0,1,0],
               [1,0,1,0,0,1,0,1],
               [0,0,0,0,0,0,0,0],
               [0,0,1,1,1,1,0,0],
               [0,1,0,0,0,0,1,0],
               [1,0,0,0,0,0,0,1]]
    
    initial = 0.5
    speed = 2
    increments = [speed * initial/2000, speed * initial/1000, speed * initial/1500]
    min_increment = min(increments)
    power_off_time = int((initial / min_increment) / speed)
    rgb = [initial] * 3
    for _ in range(power_off_time):
        rgb_pix = col(*[pow(clamp(c, 0, 1), 2) for c in rgb])
        pixels = [bg_if_blank(col(*[p*initial]*3),rgb_pix) for row in sadface for p in row]
        sense.set_pixels(pixels)
        rgb = [c - i for c, i in zip(rgb, increments)]
    time.sleep(0.5)
    sense.set_pixels([col(*[p*initial]*3) for row in sadface for p in row])
    time.sleep(0.5)
    sense.clear()
    sys.exit(0)

if __name__ == "__main__":
    # Set up the time properly for the current region.
    sydney_time = pytz.timezone(TIMEZONE)
    utc_time = pytz.timezone("UTC")

    # Load in the letters from the JSON file.
    letters_dict = load_letters()

    # Raspberry pi sense hat setup.
    sense = SenseHat()
    sense.low_light = True
    sense.set_rotation(180)

    # Hanlde keyboard interrupts and SIGTERM signals.
    signal.signal(signal.SIGINT, lambda signum, frame: clear_and_exit(sense))
    signal.signal(signal.SIGTERM, lambda signum, frame: clear_and_exit(sense))

    # Only an interrupt or SIGTERM etc. will halt this.
    while True:
        # Find the current time and extract its components.
        now = utc_time.localize(datetime.datetime.utcnow())
        local_time = now.astimezone(sydney_time)
        hours = time_letter(local_time.hour)
        mins = local_time.minute
        secs = local_time.second

        # Find the right letter for the current hour.
        letter = letters_dict[hours]

        # Rendering at half intensity because 255 is way too bright.
        letter_pixels = [[128*pixel]*3 for row in letter for pixel in row]

        # TODO: inline this into the above.
        # Modulo and integer division by the stride in order to find the x and y coords respectively.
        pixels = [letter_pixel_col(i%8,i//8,p,hours,mins) for i, p in enumerate(letter_pixels)]
        
        # Redraw once per second.
        sense.set_pixels(pixels)
        time.sleep(1)

