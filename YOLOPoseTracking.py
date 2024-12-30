from enum import Enum
import time
import threading
from YOLOPoseConstant import shoulder_press_joint_index as sp_idx
import math
import os
import cv2

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
    __time_counter__ = None#倒數1秒
    __state_changing_counter__ = 2
    __ACTION_OFFSET__ = 50 # 動作高點(可能需可變?)
    __begin_flag__ = False#(Thread is not start yet)

    def __init__(self):
        self.__current_state__ = state.ready
        self.repetition = 0
        self.action_track = list()
        self.standard_track = list()

    def begin(self, keypoints):
        
        if not self.__current_state__ is state.ready:
            return

        is_shoulder_press = self.__is_shoulder_press__(keypoints)
        
        
        if is_shoulder_press:
            print("nextstage")  
            self.__next_state__()

            try:
                left_begin_xy = list(map(int,keypoints.xy[0][sp_idx.left_elbow.value][:2]))#將肘部關節轉換為整數列表
                left_end_xy = [left_begin_xy[0], left_begin_xy[1]+self.__ACTION_OFFSET__]
                right_begin_xy = list(map(int,keypoints.xy[0][sp_idx.right_elbow.value][:2]))
                right_end_xy = [right_begin_xy[0], right_begin_xy[1]+self.__ACTION_OFFSET__]
                self.standard_track.append((left_begin_xy, left_end_xy))
                self.standard_track.append((right_begin_xy, right_end_xy))
            except IndexError as e:
                print(f'IndexError{e}')
                print("elbow is not is list")
                os.system("pause")
                return
        else:
            self.__begin_flag__ = False
            

    def working(self):
        """
        幫動作計數，條件:離心不可太快、行程完整
        上至兩倍前臂長，下至腕至耳朵
        """

    def rest(self):
        """
        無法完成(黏滯過久)、完成目標次數
        """


   
    
    def __joint_angle__2(self, elbow, wrist, shouler)->float:
        cos_a=1
        dx = elbow[0] -shouler[0]
        dx2 = elbow[1] -shouler[1]
        dx_len=math.sqrt(pow(dx,2)+pow(dx2,2))

        dy = elbow[0] -wrist[0]
        dy2 = elbow[1] -wrist[1]
        dy_len=math.sqrt(pow(dy,2)+pow(dy2,2))

        dz = wrist[0] -shouler[0]
        dz2 = wrist[1] -shouler[1]
        dz_len=math.sqrt(pow(dz,2)+pow(dz2,2))
        if(dy_len!=0 and dx_len!=0):
            cos_a=(pow(dx_len,2)+pow(dy_len,2)-pow(dz_len,2))/(2*dy_len*dx_len)

        try:
            #angle = math.atan(dy/dx)
            angle= math.acos(cos_a)
        except ZeroDivisionError:
            return 90.0
        return abs(math.degrees(angle))
    
    def __is_shoulder_press__(self, keypoints)->bool:
        joint_list = list()
        for data in keypoints.xy:
            # if len(data) == 0:
            #     print("No person in the img")
            #     return False#沒有人在畫面中
            
            for _, point in enumerate(data):
                pt_x, pt_y = list(map(int, point[:2]))
                joint_list.append([pt_x, pt_y])#獲取所有關節xy座標
        
        if not self.__key_joint_exists__(joint_list):
            return False
        
        print(self.__joint_angle__2(joint_list[sp_idx.right_elbow.value], joint_list[sp_idx.right_wrist.value], joint_list[sp_idx.right_shoulder.value]))
        print(self.__joint_angle__2(joint_list[sp_idx.left_elbow.value],joint_list[sp_idx.left_wrist.value], joint_list[sp_idx.left_shoulder.value]))
        # if (joint_list[sp_idx.left_elbow.value][1] > joint_list[sp_idx.left_shoulder.value][1] and 
        #     joint_list[sp_idx.right_elbow.value][1] > joint_list[sp_idx.right_shoulder.value][1] and 
        #     60 <= self.__joint_angle__2(joint_list[sp_idx.right_elbow.value],joint_list[sp_idx.right_wrist.value], joint_list[sp_idx.right_shoulder.value]) <= 90 and 
        #     60 <= self.__joint_angle__2(joint_list[sp_idx.left_elbow.value],joint_list[sp_idx.left_wrist.value], joint_list[sp_idx.left_shoulder.value]) <= 90):
        if (60 <= self.__joint_angle__2(joint_list[sp_idx.right_elbow.value],joint_list[sp_idx.right_wrist.value], joint_list[sp_idx.right_shoulder.value]) <= 120 and 
            60 <= self.__joint_angle__2(joint_list[sp_idx.left_elbow.value],joint_list[sp_idx.left_wrist.value], joint_list[sp_idx.left_shoulder.value]) <= 120):
                return True#判斷肘部略低於肩部且腕肘角度接近垂直
        else:
            return False
    
    def __next_state__(self)->int:
        if self.__current_state__.value == 0:
            self.__current_state__ = state.start
        elif self.__current_state__.value == 1:
            self.__current_state__ = state.action
        elif self.__current_state__.value == 2:
            self.__current_state__ = state.end
        elif self.__current_state__.value == 3:
            self.__current_state__ = state.ready
        
        
    
    def print_current_state(self):
        print(self.__current_state__.name)
        print(self.__state_changing_counter__)
                
    def __key_joint_exists__(self, in_list)->bool:
        in_list = in_list[5:11]#所有關節(肩推)皆在畫面中
        for l in in_list:
            if l == [0,0]:
                return False
        return True
        

        
