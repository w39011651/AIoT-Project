import requests
from flask import Response
import numpy as np
import cv2
import urllib.request

#可能要在不同台電腦上跑才能獲取影像

class getFrame:
    INTERVAL_TIME = 10
    url = 'http://172.20.10.10:5000'
    def __init__(self):
        pass

    def set_url(self, url):
        self.url = url

    def fetch_mjpeg_stream(self, url)->cv2.Mat:
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

            if start_index != -1 and end_index != -1:
                jpg_data = byte_data[start_index:end_index+2]
                byte_data = byte_data[end_index+2:]
                np_array = np.frombuffer(jpg_data, dtype=np.uint8)
                img = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
                # cv2.imshow('frame', img)
                # if cv2.waitKey(self.INTERVAL_TIME) & 0xFF == ord('q'):
                #     break
                return img
            else:
                print("Cannot find image data")
                #raise Exception("Cannot find image data")
                return None

