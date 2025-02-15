from ultralytics.models.yolo.detect.predict import DetectionPredictor
from ultralytics.models.yolo.pose.predict import PosePredictor
import torch

# 全域定義設備
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

_overrides_person_pose = {"task":"pose",
                          "mode":"predict",
                          "model":"yolov8m-pose.pt",
                          "save":False,
                          "verbose":False,
                          "classes":[0],
                          "iou":0.5,
                          "conf":0.3,
                          "device": str(device)
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