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
    action_track = list()#[[left_begin_xy, left_end_xy], [right_begin_xy, right_end_xy]]
    standard_track = list()
    set_recorder = list()#[repetition]
    __prev_wrist_height__ = list()
    __time_counter__ = None#倒數1秒
    __state_changing_counter__ = 2
    __begin_flag__ = False#(Thread is not start yet)
    __exhaustion_event__ = threading.Event()
    
    __ACTION_OFFSET__ = 100 # 動作高點(可能需可變?)
    __exhaustion_threshold__ = 5
    __MOVE_THRESHOLD__ = 100 #超過此值視為偵測錯誤
    
    __target_repetition__ = 5#from SQL
    __target_rest_time__ = 10#休息時間#from SQL
    __set_weight__ = 10#(from SQL)

    def __init__(self):
        self.__current_state__ = state.ready
        self.repetition = 0
        self.action_track = list()
        self.standard_track = list()
    
    def detect(self, keypoints):
        if self.__current_state__ is state.ready:
            self.__begin__(keypoints)
        elif self.__current_state__ is state.start:
            self.__concentric__(keypoints)
        elif self.__current_state__ is state.action:
            self.__eccentric__(keypoints)
        elif self.__current_state__ is state.end:
            self.__rest__()

    def __begin__(self, keypoints):
        
        if not self.__current_state__ is state.ready:
            return

        is_shoulder_press = self.__is_shoulder_press__(keypoints)
        
        
        if is_shoulder_press:
            print("nextstage")  
            self.repetition = 0
            self.__next_state__()
        
        elif len(self.standard_track) == 0:#不重複加入
            try:
                left_begin_xy = list(map(int,keypoints.xy[0][sp_idx.left_wrist.value][:2]))#將肘部關節轉換為整數列表
                left_end_xy = [left_begin_xy[0], max(left_begin_xy[1] - self.__ACTION_OFFSET__, 0)]
                right_begin_xy = list(map(int,keypoints.xy[0][sp_idx.right_wrist.value][:2]))
                right_end_xy = [right_begin_xy[0], max(right_begin_xy[1]-self.__ACTION_OFFSET__, 0)]
                self.standard_track.append((left_begin_xy, left_end_xy))
                self.standard_track.append((right_begin_xy, right_end_xy))
            except IndexError as e:
                print(f'IndexError{e}')
                print("elbow is not is list")
                os.system("pause")
                return
        else:
            self.__begin_flag__ = False
            

    def __concentric__(self, keypoints):
        """
        幫動作計數，條件:離心不可太快、行程完整
        上至兩倍前臂長，下至腕至耳朵
        如果手腕不在肩膀,以上計時2秒後或完成目標次數next_state
        如果夾角接近180度，count+1
        左手track加入到action_track[0],右手track加入到action_track[1]
        """
        if not self.__current_state__ is state.start:
            return
        
        if not self.__is_working__(keypoints):#for 2 seconds
            self.__next_state__()
            self.set_recorder.append(self.repetition)
            return
        
        try:
            left_wrist = list(map(int,keypoints.xy[0][sp_idx.left_wrist.value][:2]))
            right_wrist = list(map(int,keypoints.xy[0][sp_idx.right_wrist.value][:2]))
            left_elbow = list(map(int,keypoints.xy[0][sp_idx.left_elbow.value][:2]))
            right_elbow = list(map(int,keypoints.xy[0][sp_idx.right_elbow.value][:2]))
            left_shoulder = list(map(int,keypoints.xy[0][sp_idx.left_shoulder.value][:2]))
            right_shoulder = list(map(int,keypoints.xy[0][sp_idx.right_shoulder.value][:2]))
        except IndexError as e:
            print(f'IndexError{e}')
            print("key joint is not is list")
            os.system("pause")
            return
        
        if len(self.action_track) == 0:
            self.action_track.append([left_wrist, right_wrist])#全部動作的軌跡
        else:
            prev_point = self.action_track[-1]
            curr_point = [left_wrist, right_wrist]
            if (self.__two_point_distance__(prev_point[0], curr_point[0]) < self.__MOVE_THRESHOLD__ 
            and self.__two_point_distance__(prev_point[1], curr_point[1]) < self.__MOVE_THRESHOLD__):
                """在手腕移動不超過閾值時，才會被記錄"""
                self.action_track.append([left_wrist, right_wrist])#全部動作的軌跡



        # print(self.__joint_angle__2(left_elbow, left_wrist, left_shoulder))
        # print(self.__joint_angle__2(right_elbow, right_wrist, right_shoulder))
        # print(self.repetition)

        if (self.__joint_angle__2(left_elbow, left_wrist, left_shoulder) > 130 and
            self.__joint_angle__2(right_elbow, right_wrist, right_shoulder) > 130):
            self.repetition += 1
            self.__next_state__()
        
    def __eccentric__(self, keypoints):
        """
        下放動作後回到concentric，才能再次計數
        """
        if not self.__current_state__ is state.action:
            return
        
        try:
            left_wrist = list(map(int,keypoints.xy[0][sp_idx.left_wrist.value][:2]))
            right_wrist = list(map(int,keypoints.xy[0][sp_idx.right_wrist.value][:2]))
            left_elbow = list(map(int,keypoints.xy[0][sp_idx.left_elbow.value][:2]))
            right_elbow = list(map(int,keypoints.xy[0][sp_idx.right_elbow.value][:2]))
            left_shoulder = list(map(int,keypoints.xy[0][sp_idx.left_shoulder.value][:2]))
            right_shoulder = list(map(int,keypoints.xy[0][sp_idx.right_shoulder.value][:2]))
        except IndexError as e:
            print(f'IndexError{e}')
            print("key joint is not is list")
            os.system("pause")
            return
        
        if len(self.action_track) == 0:
            self.action_track.append([left_wrist, right_wrist])#全部動作的軌跡
        else:
            prev_point = self.action_track[-1]
            curr_point = [left_wrist, right_wrist]
            if (self.__two_point_distance__(prev_point[0], curr_point[0]) < self.__MOVE_THRESHOLD__ 
            and self.__two_point_distance__(prev_point[1], curr_point[1]) < self.__MOVE_THRESHOLD__):
                """在手腕移動不超過閾值時，才會被記錄"""
                self.action_track.append([left_wrist, right_wrist])#全部動作的軌跡

        if (self.__joint_angle__2(left_elbow, left_wrist, left_shoulder) < 130 and
            self.__joint_angle__2(right_elbow, right_wrist, right_shoulder) < 130):
            if self.repetition < self.__target_repetition__:
                self.__next_state__(False)
            else:
                self.__next_state__(True)
        


    def __rest__(self):
        """
        紀錄第幾組以及次數
        休息時間計時
        如果完成目標次數且低於預期秒數，則重量+2.5kg/5lbs
        如果完成目標次數且高於預期秒數，則重量維持
        如果未完成目標次數，則重量-2.5kg/5lbs，兩次以上直接結束該動作
        目標組數完成結束動作，否則進入ready狀態
        顯示: 第幾組、次數、休息時間、重量
        """
        if self.__current_state__ is not state.end or self.__time_counter__ is not None:
            return
        
        if self.__time_counter__ is None:
            self.__time_counter__ = threading.Thread(target=self.__timer__)
            self.__time_counter__.start()

    def __timer__(self):
        rest_time = 0
        while rest_time < self.__target_rest_time__:
            time.sleep(1)
            rest_time += 1
            print(f"休息時間: {rest_time} 秒", end='\r')
        self.__next_state__()
        self.__time_counter__ = None


    def __is_working__(self, keypoints)->bool:
        joint_list = list()
        for data in keypoints.xy:
            
            for _, point in enumerate(data):
                pt_x, pt_y = list(map(int, point[:2]))
                joint_list.append([pt_x, pt_y])#獲取所有關節xy座標
        
        if not self.__key_joint_exists__(joint_list):
            return False
        
        if (joint_list[sp_idx.right_wrist.value][1] > joint_list[sp_idx.right_shoulder.value][1]
            and joint_list[sp_idx.left_wrist.value][1] > joint_list[sp_idx.left_shoulder.value][1]):
            return False
        
        return True
   
    
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
        
        if (60 <= self.__joint_angle__2(joint_list[sp_idx.right_elbow.value],joint_list[sp_idx.right_wrist.value], joint_list[sp_idx.right_shoulder.value]) <= 120 and 
            60 <= self.__joint_angle__2(joint_list[sp_idx.left_elbow.value],joint_list[sp_idx.left_wrist.value], joint_list[sp_idx.left_shoulder.value]) <= 120):
                return True#判斷肘部略低於肩部且腕肘角度接近垂直
        else:
            return False
    
    def __next_state__(self, finish=False)->int:
        if self.__current_state__.value == 0:
            self.__current_state__ = state.start
        elif self.__current_state__.value == 1 and not finish:
            self.__current_state__ = state.action
        elif self.__current_state__.value == 1 and finish:
            self.__current_state__ = state.end
        elif self.__current_state__.value == 2 and not finish:
            self.__current_state__ = state.start
        elif self.__current_state__.value == 2 and finish:
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

    def __calculate_score__(self) -> float:
        """
        計算分數，分數=次數*重量
        """
        """
        兩條直線，對所有action track算出到直線距離，並打分
        """
        coefficient_a1 = self.standard_track[0][0][1]-self.standard_track[0][1][1] #y1-y2 = the coefficient of the x
        coefficient_b1 = self.standard_track[0][1][0]-self.standard_track[0][0][0] #x2-x1 = the coefficient of the y
        coefficient_c1 = coefficient_a1*self.standard_track[0][0][0]+coefficient_b1*self.standard_track[0][0][1]
        #x1*coe. of x + y1*coe. of y = c
        coefficient_a2 = self.standard_track[1][0][1]-self.standard_track[1][1][1]
        coefficient_b2 = self.standard_track[1][1][0]-self.standard_track[1][0][0]
        coefficient_c2 = coefficient_a2*self.standard_track[1][0][0]+coefficient_b2*self.standard_track[1][0][1]

        #forall point in action track, calculate the distance to the line
        for list in self.action_track:
            left_pt = list[0]
            right_pt = list[1]
            distance1 = abs(coefficient_a1*left_pt[0]+coefficient_b1*left_pt[1]-coefficient_c1)/math.sqrt(pow(coefficient_a1,2)+pow(coefficient_b1,2))
            distance2 = abs(coefficient_a2*right_pt[0]+coefficient_b2*right_pt[1]-coefficient_c2)/math.sqrt(pow(coefficient_a2,2)+pow(coefficient_b2,2))

    def __two_point_distance__(self, pt1, pt2)->float:
        return math.sqrt(pow(pt1[0]-pt2[0],2)+pow(pt1[1]-pt2[1],2))
    
    def __fetch_data_from_db__(self):
        """
        database structure:
        id----date----weight----repetition----rest_time----score
        """
        pass

    def __update_data_to_db__(self):
        pass
        

        