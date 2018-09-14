#!/usr/bin/python3.5
# coding: utf-8

import os
import sys
import random
import time
import math

import urllib.request
import base64
import json
import configparser

config = configparser.ConfigParser()
config.read("metrics.ini")

def promq(query):
    # return random.randrange(20, 200)
    url = config['prometheus']['endpoint'] + '/v1/query?' + urllib.parse.urlencode({ 'query': query })

    userpass = config['prometheus']['user'] + ':' + config['prometheus']['pass']
    req = urllib.request.Request(url,  headers={"Authorization": "Basic " + base64.b64encode(userpass.encode('utf-8')).decode('utf-8')})
    try:
        with urllib.request.urlopen(req) as res:
            body = res.read()
            data = json.loads(body.decode("utf-8"))
            return float(data['data']['result'][0]['value'][1])

    except urllib.error.HTTPError as err:
        print(err.code)
        return None
    except urllib.error.URLError as err:
        return None

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
font24 = ImageFont.truetype(font_path, 24)
font32 = ImageFont.truetype(font_path, 32)
font48 = ImageFont.truetype(font_path, 48)

draw.text( (0, 10), "CO2", font=font32, fill=0)
draw.text( (0, 60*1+10), "室内気温", font=font32, fill=0)
draw.text( (0, 60*2+10), "室内湿度", font=font32, fill=0)
draw.text( (0, 60*3+10), "気圧", font=font32, fill=0)
draw.text( (0, 60*4+10), "消費電力", font=font32, fill=0)

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
        self.prev_text = ""

    def update(self, text):
        if text == self.prev_text:
            return

        draw = ImageDraw.Draw(self.image)

        size = draw.textsize(text, font=font48)
        width = math.ceil(size[0] / 8) * 8

        dirty_w = max(self.prev_size[0], width)
        dirty_h = max(self.prev_size[1], size[1])
        draw.rectangle([self.x, self.y, self.x+dirty_w, self.y+dirty_h], fill=1)
        draw.text( (self.x, self.y), text, font=font48, fill=0)

        party = self.y
        if party < 0:
            party = 0
            dirty_h += self.y
        partx = self.x
        if partx < 0:
            partx = 0
            dirty_w += self.x
        part = self.image.crop( (partx, party, self.x+dirty_w, party+dirty_h))
        frame = to_frame_buffer(part)
        self.epd.set_partial_window(frame, partx, party, part.width, part.height, 1)
        self.epd.set_partial_window(frame, partx, party, part.width, part.height, 2)

        self.prev_size = (dirty_w, dirty_h)

ppm_text = PartialText(epd, image, 150, 0-10)
temp_text =  PartialText(epd, image, 150, 60*1+5-10)
hum_text =  PartialText(epd, image, 150, 60*2+5-10)
hpa_text =  PartialText(epd, image, 130, 60*3+5-10)
power_text =  PartialText(epd, image, 150, 60*4+5-10)
while True:
    ppm = promq('mqtt_topic{topic="/home/sensor/co2"}')
    if ppm is not None:
        ppm_text.update("{:.0f}ppm".format(ppm))

    temp = promq('mqtt_topic{topic="/home/sensor/temp"}')
    if temp is not None:
        temp_text.update("{:.1f}℃".format(temp))

    hum = promq('mqtt_topic{topic="/home/sensor/hum"}')
    if hum is not None:
        hum_text.update("{:.0f}%".format(hum))

    hpa = promq('mqtt_topic{topic="/home/sensor/pressure"}')
    hpa_delta = promq('delta(mqtt_topic{topic="/home/sensor/pressure"}[1h])')
    if hpa is not None:
        a = ""
        if hpa_delta > 0:
            a = "↑"
        elif hpa_delta < 0:
            a = "↓"
        else:
            a = "→"
        hpa_text.update("{}{:.0f}hPa".format(a, hpa))

    power = promq('consumed_power')
    if power is not None:
        power_text.update("{:.0f}W".format(power))


    time.sleep(1)

