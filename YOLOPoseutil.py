from ultralytics.models.yolo.detect.predict import DetectionPredictor
from ultralytics.models.yolo.pose.predict import PosePredictor

_overrides_person_pose = {"task":"pose",
                          "mode":"predict",
                          "model":"yolov8s-pose.pt",
                          "save":False,
                          "verbose":False,
                          "classes":[0],
                          "iou":0.5,
                          "conf":0.3
                          }
_overrides_person_detection = {"task":"det",
                               "mode":"predict",
                               "model":"yolov8s.pt",
                               "save":False,
                               "verbose":False,
                               "classes":[0,32],
                               "iou":0.5,
                               "conf":0.3
                               }
predictor_person_pose = PosePredictor(overrides=_overrides_person_pose)
predictor_person_detection = DetectionPredictor(overrides=_overrides_person_detection)

                               