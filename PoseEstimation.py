from ultralytics import YOLO
import cv2
from cvzone.PoseModule import PoseDetector

def draw_plot_box(img, det_res, color=(0,0,255)):
    for i, bbox in enumerate(det_res.boxes.xyxy):
        x1,y1,x2,y2=list(map(int, bbox))
        conf = det_res.boxes.conf[i]
        cls = det_res.boxes.cls[i]
        label = f'{det_res.names[int(cls)]}{float(conf):.2f}'

        cv2.rectangle(img, (x1,y1),(x2,y2),color, 2)
        cv2.putText(img, label, (x1,y1-10),cv2.FONT_HERSHEY_SIMPLEX,0.5,color,2)
    return img

if __name__ == '__main__':
    yolo = YOLO('yolov8n-pose.pt')
    detector = PoseDetector()

    # cap = cv2.VideoCapture(0)
    img = cv2.imread('bus.jpg')
    while True:
        # _, img = cap.read()
        #results = yolo.predict(img)
        img = detector.findPose(img)
        imList, bboxInfo = detector.findPosition(img, bboxWithHands=False)
        if bboxInfo:
            center = bboxInfo["center"]
            cv2.circle(img, center, 5, (0,0,255), cv2.FILLED)
        #img = draw_plot_box(img, results[0])
        cv2.imshow('img',img)
        if cv2.waitKey(0) & 0xFF == ord('q'):
            exit()
