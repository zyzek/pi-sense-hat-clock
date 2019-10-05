#!/usr/bin/python3

import json
import math
import time
import datetime
import pytz
from sense_hat import SenseHat

def clamp(x, lower, upper):
    if x < lower:
        return lower
    if x > upper:
        return upper
    return x

def smoothstep(lower, upper, x):
    x = clamp((x - lower) / (upper - lower), 0, 1)
    return x * x * (3 - 2*x)

def col(r, g, b, l=1.0):
    return [int(l*r*255), int(l*g*255), int(l*b*255)]

def dim(p, l):
    return [int(p[0]*l), int(p[1]*l), int(p[2]*l)]

def time_letter(hour):
    if hour == 12:
        return 'c'
    return hex(hour%12)[2:]

def minutes_brightness(mins, x):
    mins_norm = mins / 60
    mins_x = mins_norm * 8

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

def letter_pixel_col(x, y, p, hours, mins):
    mins_bright = minutes_brightness(mins, x)
    color = dim(time_of_day_color(hours, mins), mins_bright)
    return p if p != [0,0,0] else color

def load_letters():
    with open('letters.json', 'r') as letters:
        letters_dict = json.load(letters)
        
        for letter in letters_dict:
            image = letters_dict[letter]
            letters_dict[letter] = [[0]+row+[0,0] for row in image]

        return letters_dict

def quarter_rotation(g):
    return [list(col) for col in zip(*[reversed(row) for row in g])]

def rotate(grid, quarter_turns):
    quarter_turns %= 4
    if quarter_turns == 0:
        return list(grid)
    return rotate(quarter_rotation(grid), quarter_turns-1)



letters_dict = load_letters()

sydney_time = pytz.timezone("Australia/Sydney")
utc_time = pytz.timezone("UTC")

sense = SenseHat()
sense.low_light = True

while True:
    now = utc_time.localize(datetime.datetime.utcnow())
    local_time = now.astimezone(sydney_time)
    hours = time_letter(local_time.hour)
    mins = local_time.minute
    secs = local_time.second
    letter = rotate(letters_dict[hours], -secs)
    letter_pixels = [[128*pixel]*3 for row in letter for pixel in row]
    pixels = [letter_pixel_col(i%8,i//8,p,hours,mins) for i, p in enumerate(letter_pixels)]
    sense.set_pixels(pixels)

    time.sleep(1)

# TODO: differential letter and background dimming
# TODO: colour depending on time of day
# TODO: vertical gradient for time of day transitions
# TODO: background brightness depending on seconds

sense.clear()

