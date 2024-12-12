import cv2
from flask import Flask, Response

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

if __name__ == '__main__':
    app.run(host = '0.0.0.0', port = 5000)