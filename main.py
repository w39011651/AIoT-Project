import cv2

HEIGHT_INDEX = 3
WIDTH_INDEX = 4

cap = cv2.VideoCapture(0)
#cap.set(HEIGHT_INDEX ,1280)
#cap.set(WIDTH_INDEX, 720)

while True:
    success, img = cap.read()

    cv2.imshow("Video", img)

    if cv2.waitKey(1) == ord('q'):
        break