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
    __ACTION_OFFSET__ = 50 # 動作高點(可能需可變?)

    def __init__(self):
        self.__current_state__ = state.ready
        self.repetition = 0
        self.action_track = list()
        self.standard_track = list()

    def begin(self, keypoints):
        if self.__current_state__ != state.ready:
            return
        is_shoulder_press = self.__is_shoulder_press__(keypoints)
        #print(is_shoulder_press)
        if (not self.__time_counter__.is_alive() and is_shoulder_press):

            self.__time_counter__ = threading.Thread(target=time.time, args=(1))#倒數1秒
            self.__time_counter__.start()
        elif not is_shoulder_press:
            self.__state_changing_counter__ = 2#重置回2秒
            return
        
        if self.__state_changing_counter__ > 0 and not self.__time_counter__.is_alive():
            self.__state_changing_counter__ -=1

        elif self.__state_changing_counter__ == 0 and not self.__time_counter__.is_alive():
            self.__next_state__()

            left_begin_xy = list(map(int,keypoints.xy[sp_idx.left_elbow.value][:2]))#將肘部關節轉換為整數列表
            left_end_xy = [left_begin_xy[0], left_begin_xy[1]+self.__ACTION_OFFSET__]
            right_begin_xy = list(map(int, keypoints.xy[sp_idx.right_elbow.value][:2]))
            right_end_xy = [right_begin_xy[0], right_begin_xy[1]+self.__ACTION_OFFSET__]

            self.standard_track.append([left_begin_xy, left_end_xy], [right_begin_xy, right_end_xy])
            

    def working(self):
        """
        幫動作計數，條件:離心不可太快、行程完整
        上至兩倍前臂長，下至腕至耳朵
        """

    def rest(self):
        """
        無法完成(黏滯過久)、完成目標次數
        """


    def __joint_angle__(self, point1, point2)->float:
        dx = point1[0] - point2[0]
        dy = point1[1] - point2[1]

        try:
            angle = math.atan(dy/dx)
        except ZeroDivisionError:
            return 90.0
        return math.degrees(angle)
    
    def __is_shoulder_press__(self, keypoints)->bool:
        joint_list = list()
        for data in keypoints.xy:
            if len(data) == 0:
                return False#沒有人在畫面中
            
            for _, point in enumerate(data):
                pt_x, pt_y = list(map(int, point[:2]))
                joint_list.append([pt_x, pt_y])#獲取所有關節xy座標
        
        if (joint_list[sp_idx.left_elbow.value][1] > joint_list[sp_idx.left_shoulder.value][1] and 
            joint_list[sp_idx.right_elbow.value][1] > joint_list[sp_idx.right_shoulder.value][1] and 
            75 <= self.__joint_angle__(joint_list[sp_idx.right_wrist.value], joint_list[sp_idx.right_elbow.value]) <= 105 and 
            75 <= self.__joint_angle__(joint_list[sp_idx.left_wrist.value], joint_list[sp_idx.left_elbow.value]) <= 105):
                return True#判斷肘部略低於肩部且腕肘角度接近垂直
        else:
            return False
    
    def __next_state__(self)->int:
        self.__current_state__ = state[(self.__current_state__+1)%3]
    
    def print_current_state(self):
        print(self.__current_state__.name)
        print(self.__state_changing_counter__)
                


        

        
