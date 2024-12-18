import requests
from flask import Response, Flask
import numpy as np
import cv2
import urllib.request
import threading

#可能要在不同台電腦上跑才能獲取影像
INTERVAL_TIME = 2



url = 'http://127.0.0.1:5000'


app = Flask(__name__)

def generateFrame():
    cap = cv2.VideoCapture(0)
    while True:
        success, img = cap.read()

        ret, buffer = cv2.imencode('.jpg',img)
        img = buffer.tobytes()
        yield(b'--frame\r\n'b'Content-Type: image/jpeg\r\n\r\n'+img+b'\r\n')

@app.route('/')
def video_feed():
    return Response(generateFrame(),mimetype='multipart/x-mixed-replace; boundary=frame')

def fetch_mjpeg_stream(url):
    stream = urllib.request.urlopen(url)
    byte_data = b''
    while True:
        data = stream.read(1024)
        if not data:
            break
        byte_data += data
        start_index = byte_data.find(b'\xff\xd8')
        end_index = byte_data.find(b'\xff\xd9')

        if start_index != -1 and end_index != -1:
            jpg_data = byte_data[start_index:end_index+2]
            byte_data = byte_data[end_index+2]
            np_array = np.frombuffer(jpg_data, dtype=np.uint8)
            img = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
            cv2.imshow("img", img)
            if cv2.waitKey(INTERVAL_TIME) == 'q':
                break

def runapp():
    if __name__ == '__main__':
        app.run(host = '0.0.0.0', port = 5000)


t1 = threading.Thread(target = runapp)
t2 = threading.Thread(target = fetch_mjpeg_stream, args=[url])
t1.start()
t2.start()