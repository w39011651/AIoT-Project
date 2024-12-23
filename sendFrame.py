import cv2
from flask import Flask, Response
import requests


CLOUD_SERVER_URL = 'http://140.138.150.21/G13_api/upload'
app = Flask(__name__)

def generateFrame():
    global cap
    while True:
        success, img = cap.read()

        ret, buffer = cv2.imencode('.jpg',img)
        img = buffer.tobytes()

        # try:
        #     requests.post(CLOUD_SERVER_URL, files = {"frame":img})
        #     print("POST send")
        # except Exception as e:
        #     print(f'POST failed:{e}')

        yield(b'--frame\r\n'b'Content-Type: image/jpeg\r\n\r\n'+img+b'\r\n')

@app.route('/')
def video_feed():
    return Response(generateFrame(),mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    cap = cv2.VideoCapture(0)
    app.run(host = '0.0.0.0', port = 5000)
    #generateFrame()
    #requests.post(CLOUD_SERVER_URL, files = {"test": "POST protocol testing"})