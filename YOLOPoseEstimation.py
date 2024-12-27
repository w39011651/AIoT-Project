import urllib.request
import cv2
import numpy as np
import math
from YOLOPoseutil import predictor_person_pose, predictor_person_detection
import urllib
from YOLOPoseConstant import _CONNECTIONS, shoulder_press_joint_index


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

def plot_track(img, keypoints, prev_keypoints, line_color = (0,0,255))->cv2.Mat:
    """
    起始動作: 肩-肘與肘-腕角度為90度
    上推: 不必完全打直、不鎖死(肩-肘-手接近一條直線)
    下放: 手臂平行地面
    穩定: 水平移動不可太多

    函數功能: 劃出軌跡
    實現: 將所有移動過的點紀錄在list中, 在結束動作後畫出動作軌跡圖(可從暗到亮)
    """
    global action_trail

    if prev_keypoints is None:
        return img
    
    for curr_data, prev_data in zip(keypoints.xy, prev_keypoints.xy):
        if len(curr_data) == 0 or len(prev_data) == 0:
            #print(f"len of curr_data:{len(curr_data)} and the len of prev_data:{len(prev_data)}")
            continue
        
        for i, (curr_point, prev_point)  in enumerate(zip(curr_data, prev_data)):
            if i >= 5 and i <= 10:
                curr_x, curr_y = list(map(int, curr_point[:2]))
                prev_x, prev_y = list(map(int, prev_point[:2]))
                if distance((curr_x, curr_y),(prev_x, prev_y)) > HORIZON_MOVE_THRESHOULD:
                    continue
                if i == 10:
                    action_trail.append((prev_x, prev_y))
                if curr_x > 0 and curr_y > 0 and prev_x > 0 and prev_y > 0:
                    cv2.line(img, (prev_x, prev_y), (curr_x, curr_y), line_color, 2)    
    return img

def draw_trail(trail:list, fixed_height, fixed_width):
    back_ground = np.ones((fixed_height, fixed_width), dtype=np.uint8)*255
    trail_size = len(trail)
    for i in range(1, trail_size):
        cv2.line(back_ground, trail[i-1], trail[i], color=(0,0,255), thickness=2)
    cv2.imshow('trail', back_ground)
    if cv2.waitKey(0) & 0xFF == ord('q'):
        cv2.destroyAllWindows()

def distance(point1, point2)->float:
    return math.sqrt((point1[0]- point2[0])**2 + (point1[1] - point2[1])**2)

def show_video(my_video_path, self_camera = False):
    global prev_person_pose, img_height, img_width, action_trail

    cap = get_video(video_path=my_video_path, read_from_camera=self_camera)
    SKIP_FRAME_COUNTING = 500
    skip_frame_counting = -1
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            print('Camera is not opened/video is not exist')
            break
        if img_height is None and img_width is None:
            img_height, img_width = frame.shape[:2]
        #img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        if skip_frame_counting % SKIP_FRAME_COUNTING != 0:
            skip_frame_counting+=1
            continue
        img = frame
        persons_pose = predictor_person_pose(img)[0]
        img = plot_keypoints(img, persons_pose.keypoints)
        if prev_person_pose is not None:
            img = plot_track(img, persons_pose.keypoints, prev_person_pose.keypoints)
        prev_person_pose = persons_pose
        #判定動作品質
        cv2.imshow("img", img)
        if cv2.waitKey(2) & 0xFF == ord('q'):
            break
    cap.release()
    cv2.destroyAllWindows()
    draw_trail(action_trail, img_height, img_width)

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
    print("Person Pose Model Device:", predictor_person_pose.device)
    prev_person_pose = None
    action_trail = list()
    img_height, img_width = (None, None)
    HORIZON_MOVE_THRESHOULD = 10.0
    #print("Person Detection Model Device:", predictor_person_detection.model.device)

    #show_video(video_path, False)
    show_video(video_path, True)
    #show_video_from_http(FLASK_URL)
