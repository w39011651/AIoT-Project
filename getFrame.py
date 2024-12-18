import requests
from flask import Response
import numpy as np
import cv2

#可能要在不同台電腦上跑才能獲取影像

url = 'http://127.0.0.1:5000'

while True:
    img_res = requests.get(url)
    print(Response.status_code)
    img_arr = np.frombuffer(img_res.content, dtype = np.uint8)
    img = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)
    cv2.imshow('ResponseImage', img)
    if cv2.waitKey(1) == ord('q'):
        break

cv2.destroyAllWindows()