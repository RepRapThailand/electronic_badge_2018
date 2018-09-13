#!/usr/bin/python3.5
# coding: utf-8

import os
import sys
import random
import time
import math

sys.path.append(os.path.abspath(os.path.dirname(os.path.abspath(__file__)) + '/../lib'))

import epd4in2

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

EPD_WIDTH = 400
EPD_HEIGHT = 300

image = Image.new('1', (EPD_WIDTH, EPD_HEIGHT), 1)
draw = ImageDraw.Draw(image)

epd = epd4in2.EPD()
epd.init()

font_path = '/home/pi/tmp/NotoSansCJKjp-Black.otf'
font32 = ImageFont.truetype(font_path, 32)
font48 = ImageFont.truetype(font_path, 48)

draw.text( (0, 20), "CO2", font=font32, fill=0)
draw.text( (0, 60*1+20), "室内気温", font=font32, fill=0)
draw.text( (0, 60*2+20), "消費電力", font=font32, fill=0)
draw.text( (0, 60*3+20), "電気料金", font=font32, fill=0)

def to_frame_buffer(image):
    image_monocolor = image
    if image.mode != '1':
        image_monocolor = image.convert('1')
    buf = [0] * int(image.width * image.height)
    pixels = image_monocolor.load()
    for y in range(image.height):
        for x in range(image.width):
            # Set the bits for the column of pixels at the current position.
            if pixels[x, y] != 0:
                buf[int((x + y * image.width) / 8)] |= 0x80 >> (x % 8)
    return buf

frame_buffer = epd.get_frame_buffer(image)
epd.display_frame(frame_buffer)

class PartialText:
    def __init__(self, epd, image, x, y):
        self.prev_size = (0, 0)
        self.x = x
        self.y = y
        self.epd = epd
        self.image = image

    def update(self, text):
        draw = ImageDraw.Draw(self.image)

        size = draw.textsize(text, font=font48)
        width = math.ceil(size[0] / 8) * 8

        dirty_w = max(self.prev_size[0], width)
        dirty_h = max(self.prev_size[1], size[1])
        draw.rectangle([self.x, self.y, self.x+dirty_w, self.y+dirty_h], fill=1)
        draw.text( (self.x, self.y), text, font=font48, fill=0)

        part = self.image.crop( (self.x, self.y, self.x+dirty_w, self.y+dirty_h))
        frame = to_frame_buffer(part)
        self.epd.set_partial_window(frame, self.x, self.y, part.width, part.height, 1)
        self.epd.set_partial_window(frame, self.x, self.y, part.width, part.height, 2)

        self.prev_size = (dirty_w, dirty_h)

ppm_text = PartialText(epd, image, 150, 0)
temp_text =  PartialText(epd, image, 150, 60*1+5)
power_text =  PartialText(epd, image, 150, 60*2+5)
kwh_text =  PartialText(epd, image, 150, 60*3+5)
while True:
    ppm_text.update("%d ppm" % random.randrange(400, 1900))
    temp_text.update("%.1f ℃" % random.randrange(10, 35))
    power_text.update("%d W" % random.randrange(200, 1500))
    kwh_text.update("%d 円/日" % random.randrange(200, 500))
    # time.sleep(1)

