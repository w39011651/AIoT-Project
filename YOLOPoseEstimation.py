import urllib.request
import cv2
import numpy as np
from YOLOPoseutil import predictor_person_pose, predictor_person_detection
import urllib


_CONNECTIONS = ((2,4),(1,3),(10,8),(8,6),(6,5),(5,7),(7,9),(6,12),(12,14),(14,16),(5,11),(11,13),(13,15))


def get_video(video_path, read_from_camera = False):

    if read_from_camera:
        cap = cv2.VideoCapture(0)
    else:
        cap = cv2.VideoCapture(video_path)
    return cap
    
def plot_bbox(image, detection_result, color = (0,0,255)):
    for i, bbox in enumerate(detection_result):
        x1,y1,x2,y2=list(map(int, bbox))
        conf = detection_result.boxes.conf[i]
        cls = detection_result.boxes.cls[i]
        label = f'{detection_result[int(cls[i])]}{float(conf):.2f}'

        cv2.rectangle(image, (x1,y1), (x2,y2), color, 2)
        cv2.putText(image, label, (x1,y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color ,2)
    return image

def plot_keypoints(image, keypoints, line_color=(0,255,0), point_color=(255,0,0)):
    global _CONNECTIONS
    if keypoints is None:
        return None
    for data in keypoints.xy:
        if len(data) == 0:
            continue
        for start_idx, end_idx in _CONNECTIONS:
            start_pt = data[start_idx]
            end_pt = data[end_idx]#找出部位點，連線(骨架部分)

            if (start_pt[0] > 0 or start_pt[1] > 0) and (end_pt[0] > 0 or end_pt[1] > 0):
                cv2.line(image, (int(start_pt[0]),int(start_pt[1]))
                         , (int(end_pt[0]),int(end_pt[1])), line_color, 2)

        for idx, point in enumerate(data):#找出關節點、畫點
            x,y=list(map(int,point[:2]))
            if x > 0 and y > 0:
                cv2.circle(image, (x,y), 5, point_color, -1)
    return image

def show_video(my_video_path, self_camera = False):
    cap = get_video(video_path=my_video_path, read_from_camera=self_camera)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            print('Camera is not opened/video is not exist')
            break
        #img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = frame
        persons_pose = predictor_person_pose(img)[0]
        img = plot_keypoints(img, persons_pose.keypoints)
        
        cv2.imshow("img", img)
        if cv2.waitKey(2) & 0xFF == ord('q'):
            break
    cap.release()
    cv2.destroyAllWindows()

def show_video_from_http(url):
    stream = urllib.request.urlopen(url)
    bytes_data = b''
    while True:
        bytes_data += stream.read(1024)
        start_idx = bytes_data.find(b'\xff\xd8')
        end_idx = bytes_data.find(b'\xff\xd9')
        if start_idx != -1 and end_idx != -1:
            jpg_data = bytes_data[start_idx:end_idx+2]
            bytes_data = bytes_data[end_idx+2:]
            np_array = np.frombuffer(jpg_data, dtype=np.uint8)
            img = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
            #img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            persons_pose = predictor_person_pose(img)[0]
            img = plot_keypoints(img, persons_pose.keypoints)
            
            cv2.imshow("img", img)
            if cv2.waitKey(2) & 0xFF == ord('q'):
                break
    cv2.destroyAllWindows()


if __name__ == '__main__':
    FLASK_URL = 'http://192.168.1.134:5000'
    video_path = 'jntm.mp4'
    #show_video(video_path, True)
    show_video_from_http(FLASK_URL)
