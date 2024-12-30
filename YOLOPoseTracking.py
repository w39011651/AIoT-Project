from enum import Enum
import time
import threading
from YOLOPoseConstant import shoulder_press_joint_index as sp_idx
import math

class state(Enum):
    ready = 0
    start = 1
    action = 2
    end = 3

class action_state(object):
    __current_state__ = state.ready
    repetition = 0
    action_track = list()
    standard_track = list()
    __time_counter__ = threading.Thread()
    __state_changing_counter__ = 2

    def __init__(self):
        __current_state__ = state.ready
        repetition = 0
        action_track = list()
        standard_track = list()

    def begin(self, keypoints):
        if self.__current_state__ != state.ready:
            return
        is_shoulder_press = self.__is_shoulder_press__(keypoints)
        if (not self.__time_counter__.is_alive() and is_shoulder_press):

            self.__time_counter__ = threading.Thread(target=time.time, args=(1))#倒數1秒
            self.__time_counter__.start()
        elif not is_shoulder_press:
            self.__state_changing_counter__ = 2#重置回2秒
        
        if self.__state_changing_counter__ > 0 and not self.__time_counter__.is_alive():
            self.__state_changing_counter__ -=1

        elif self.__state_changing_counter__ == 0 and not self.__time_counter__.is_alive():
            self = self.__next_state__()
            left_begin_xy = list(map(int,keypoints.xy[sp_idx.left_elbow][:2]))#將肘部關節轉換為整數列表
            left_end_xy = list()

    def working():
        """幫動作計數"""



    def __joint_angle__(self, point1, point2)->float:
        dx = point1[0] - point2[0]
        dy = point1[1] - point2[1]
        angle = math.atan(dy, dx)
        return math.degrees(angle)
    
    def __is_shoulder_press__(self, keypoints)->bool:
        joint_list = list()
        for data in keypoints.xy:
            if len(data) == 0:
                return False#沒有人在畫面中
            
            for _, point in enumerate(data):
                pt_x, pt_y = list(map(int, point[:2]))
                joint_list.append([pt_x, pt_y])#獲取所有關節xy座標

        if (joint_list[sp_idx.left_elbow][1] > joint_list[sp_idx.left_shoulder][1] and 
            joint_list[sp_idx.right_elbow][1] > joint_list[sp_idx.right_shoulder][1] and 
            75 <= self.__joint_angle__(joint_list[sp_idx.right_wrist], joint_list[sp_idx.right_elbow]) <= 105 and 
            75 <= self.__joint_angle__(joint_list[sp_idx.left_wrist], joint_list[sp_idx.left_elbow]) <= 105):
                return True#判斷肘部略低於肩部且腕肘角度接近垂直
        else:
            return False
    
    def __next_state__(self, state)->int:
        return (state+1)%3
                


        

        
