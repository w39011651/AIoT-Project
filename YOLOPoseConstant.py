from enum import Enum

_CONNECTIONS = ((2,4),(1,3),(10,8),(8,6),(6,5),(5,7),(7,9),(6,12),(12,14),(14,16),(5,11),(11,13),(13,15))
    
class shoulder_press_joint_index(Enum):
    left_shoulder = 5
    right_shoulder = 6
    left_elbow = 7
    right_elbow = 8
    left_wrist = 9
    right_wrist = 10