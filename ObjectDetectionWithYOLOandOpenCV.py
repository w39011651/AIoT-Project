import cv2
from ultralytics import YOLO
import requests
import numpy as np
# Load the model


CLOUD_SERVER_URL = 'http://140.138.150.21/G13_api/upload'

yolo = YOLO('yolov8s.pt')
# Load the video capture
videoCap = cv2.VideoCapture(0)

# Function to get class colors
def getColours(cls_num):
    base_colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
    color_index = cls_num % len(base_colors)
    increments = [(1, -2, 1), (-2, 1, -1), (1, -1, 2)]
    color = [base_colors[color_index][i] + increments[color_index][i] * 
    (cls_num // len(base_colors)) % 256 for i in range(3)]
    return tuple(color)

skip_frame_count = -1
while True:
    skip_frame_count+=1
    if skip_frame_count % 500 != 0:
        continue
    ret, frame = videoCap.read()
    if not ret:
        continue
    results = yolo.track(frame, stream=True)


    for result in results:
        # get the classes names
        classes_names = result.names

        # iterate over each box
        for box in result.boxes:
            # check if confidence is greater than 40 percent
            if box.conf[0] > 0.4:
                # get coordinates
                [x1, y1, x2, y2] = box.xyxy[0]
                # convert to int
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

                # get the class
                cls = int(box.cls[0])

                # get the class name
                class_name = classes_names[cls]

                # get the respective colour
                colour = getColours(cls)

                # draw the rectangle
                cv2.rectangle(frame, (x1, y1), (x2, y2), colour, 2)
                # put the class name and confidence on the image
                cv2.putText(frame, f'{classes_names[int(box.cls[0])]} {box.conf[0]:.2f}', (x1, y1), cv2.FONT_HERSHEY_SIMPLEX, 1, colour, 2)
                
    # show the image
    cv2.imshow('img',frame)
    _,buffer = cv2.imencode('.jpg', frame)
    frame = buffer.tobytes()

    try:
        requests.post(CLOUD_SERVER_URL, files = {"frame":frame})
        print("POST send")
    except Exception as e:
        print(f'POST failed:{e}')

    # break the loop if 'q' is pressed
    if cv2.waitKey(2) & 0xFF == ord('q'):
        break

# release the video capture and destroy all windows
# videoCap.release()
# cv2.destroyAllWindows()
