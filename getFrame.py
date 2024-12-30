import requests
from flask import Response
import numpy as np
import cv2
import urllib.request

#可能要在不同台電腦上跑才能獲取影像
INTERVAL_TIME = 2
url = 'http://127.0.0.1:5000'


def fetch_mjpeg_stream(url):
    stream = urllib.request.urlopen(url)
    byte_data = b''
    while True:
        data = stream.read(1024)
        if not data:
            break

        if type(data) != type(byte_data):
            continue

        byte_data += data
        start_index = byte_data.find(b'\xff\xd8')
        end_index = byte_data.find(b'\xff\xd9')

        if start_index != -1 and end_index != -1 and start_index < end_index:
            jpg_data = byte_data[start_index:end_index+2]
            byte_data = byte_data[end_index+2]
            np_array = np.frombuffer(jpg_data, dtype=np.uint8)
            img = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
            cv2.imshow("img", img)

            if cv2.waitKey(INTERVAL_TIME) & 0xFF == 'q':
                break

fetch_mjpeg_stream(url)

