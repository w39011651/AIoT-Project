import cv2
import mediapipe as mp

mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(min_detection_confidence=0.5,
                    min_tracking_confidence=0.5)
                    
cap = cv2.VideoCapture(0)
#cap = cv2.VideoCapture('jntm.mp4')

while True:
    _,img=cap.read()
    results = pose.process(img)
    mp_drawing.draw_landmarks(
            img,
            results.pose_landmarks,
            mp_pose.POSE_CONNECTIONS)

    cv2.imshow("MediaPipe Pose", img)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
cv2.destroyAllWindows()
