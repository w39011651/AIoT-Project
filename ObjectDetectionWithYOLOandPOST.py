import threading
import cv2
import queue
import requests
from ultralytics import YOLO

def getColours(cls_num):
    base_colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
    color_index = cls_num % len(base_colors)
    increments = [(1, -2, 1), (-2, 1, -1), (1, -1, 2)]
    color = [base_colors[color_index][i] + increments[color_index][i] * 
    (cls_num // len(base_colors)) % 256 for i in range(3)]
    return tuple(color)


def object_detection():
    global img
    frame = img
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

def connect():
    global frames_list
    global pic_count
    while True:
        frame = frames_list.get()
        pic_count-=1
        print('Get Frame!')
        print('Resisual Frame in Queue:', pic_count)
        

        try:
            requests.post('http://140.138.150.21/G13_api/upload', files = {"frame":frame})
            print("POST send")
        except Exception as e:
            print(f'POST failed:{e}')


cap = cv2.VideoCapture(0)
threads = []
for _ in range(0,1):
    threads.append(threading.Thread())
frames_list = queue.Queue()
pic_count = 0
yolo = YOLO('yolov8s.pt')
skip_frame_count = -1
#t1.start()
while True:
    skip_frame_count+=1
    if skip_frame_count % 750 != 0:
        continue
    _, img = cap.read()
    object_detection()
    _,buffer = cv2.imencode('.jpg', img)
    frame = buffer.tobytes()
    frames_list.put(frame)
    pic_count+=1
    cv2.imshow('img',img)
    for t in threads:
        if not t.is_alive():
            t = threading.Thread(target = connect,daemon=True)
            t.start()
    if cv2.waitKey(2) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()



