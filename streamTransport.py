import requests
import cv2
import numpy as np
def stream_image(img):
        ret ,buffer= cv2.imencode('.jpg', img)
        img = buffer.tobytes()
        while chunk := img.read(1024):  # 每次讀取 1024 字節
            yield chunk

url = "http://127.0.0.1:5000/upload"
headers = {"Content-Type": "application/octet-stream"}

cap = cv2.VideoCapture(0)
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break
    response = requests.post(url, data=stream_image(), headers=headers)    
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break
    if response.status_code == 200:
        print("圖片上傳成功")
    else:
        print("圖片上傳失敗", response.text)
