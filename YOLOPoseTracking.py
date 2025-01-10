from enum import Enum
from YOLOPoseConstant import shoulder_press_joint_index as sp_idx
import os
import threading
import math
import time
import cv2

class state(Enum):
    ready = 0
    start = 1
    action = 2
    end = 3

class action_state(object):
    __current_state__ = state.ready #當前狀態
    __standrad_track__ = [] #標準軌跡
    __set_recorder__ = [] #紀錄每組的次數
    __time_counter__ = None #計時器
    __exhaustion_counter__ = threading.Event() #疲勞標誌
    __repetition__ = 0 #重複次數
    __target_repetition__ = 10 #目標重複次數
    __target_rest_time__ = 60 #目標休息時間(from SQL)
    __exhaustion_threshold__ = 5 #疲勞時間閾值
    __target__group__ = 3 #目標組數
    __current_group__ = 1 #當前組數
    __fail_counter__ = 0 #失敗次數
    __fail_flag__ = False #失敗標誌
    __current_time__ = 0 #當前時間
    
    def render_text(self, image):
        """
        在圖像上渲染所有狀態相關的文字，位置固定：
        - 當前狀態：左上角
        - 組數和重複次數：右上角（休息時僅顯示組數）
        - 疲勞警告：畫面下方中央
        - 休息時間：畫面正中央
        """
        height, width = image.shape[:2] #取得圖像高度和寬度
        
        # 左上角 - 當前狀態
        cv2.putText(image, f"State: {self.__current_state__.name}", 
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
        
        # 右上角 - 組數和重複次數
        group_text = ""
        #如果進入休息狀態，剔除重複次數並向右對齊
        if self.__current_state__ is state.end:
            group_text = f"Group: {self.__current_group__}/{self.__target__group__}"
            (text_width, text_height), baseline = cv2.getTextSize(group_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
               
        # 如果不在休息狀態，加入重複次數
        if self.__current_state__ is not state.end and self.__repetition__ is not None:
            group_text += f" Rep: {self.__repetition__}/{self.__target_repetition__}"
        
        # 計算右上角位置，留出10像素邊距
        cv2.putText(image, group_text, 
                    (width - text_width - 10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # 畫面下方中央 - 疲勞警告（類似字幕位置）
        if self.__fail_flag__:
            warning_text = "Warning: 檢測到疲勞狀態！進入休息階段"
            (text_width, text_height), baseline = cv2.getTextSize(warning_text, cv2.FONT_HERSHEY_SIMPLEX, 1.0, 2)
            # 計算中心位置
            text_x = (width - text_width) // 2
            text_y = int(height * 0.85)
            cv2.putText(image, warning_text,
                        (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
        
        # 畫面正中央 - 休息時間
        if self.__current_state__ is state.end and self.__time_counter__ is not None:
            if self.__current_group__ <= self.__target__group__:
                rest_text = f"Rest Time: {self.__target_rest_time__}s"
                (text_width, text_height), baseline = cv2.getTextSize(rest_text, cv2.FONT_HERSHEY_SIMPLEX, 1.2, 2)
                
                text_x = (width - text_width) // 2
                text_y = height // 2
                
                # # 半透明背景
                # overlay = image.copy()
                # cv2.rectangle(overlay, 
                #             (text_x - 10, text_y - text_height - 10),
                #             (text_x + text_width + 10, text_y + 10),
                #             (0, 0, 0), -1)
                # alpha = 0.6 #透明度
                # image = cv2.addWeighted(overlay, alpha, image, 1 - alpha, 0) #混合圖像
                
                cv2.putText(image, rest_text,
                            (text_x, text_y), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)
            else:
                rest_text = "目標組數完成, Congratulation!"
                (text_width, text_height), baseline = cv2.getTextSize(rest_text, cv2.FONT_HERSHEY_SIMPLEX, 1.2, 2)
                
                text_x = (width - text_width) // 2
                text_y = height // 2
                
                cv2.putText(image, rest_text,
                            (text_x, text_y), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)
        return image

    def detect(self, keypoints, image):
        if self.__current_state__ is state.ready:
            self.__ready__(keypoints) #開始動作
        elif self.__current_state__ is state.start:
            self.__start__(keypoints) #肩推進行中(向上)
        elif self.__current_state__ is state.action:
            self.__action__(keypoints) #肩推進行中(向下)
        elif self.__current_state__ is state.end:
            self.__rest__() #休息時間
        
        return self.render_text(image)

    def __ready__(self, keypoints):
        """
        開始動作
        如果手腕在肩膀上方,進入start
        """
        if self.__current_state__ is not state.ready:
            return
        
        is_shoulder_press = self.__is_shoulder_press__(keypoints)
        
        if is_shoulder_press:
            # print(f"第{self.__current_group__}肩推開始")
            self.repitition = 0
            self.__next_state__()
        elif len(self.__standrad_track__) == 0: #不重複加入
            try:
                left_begin_xy = list(map(int,keypoints.xy[0][sp_idx.left_wrist.value][:2])) #將肘部關節轉換為整數列表
                left_end_xy = [left_begin_xy[0], max(left_begin_xy[1] - self.__ACTION_OFFSET__, 0)]
                right_begin_xy = list(map(int,keypoints.xy[0][sp_idx.right_wrist.value][:2]))
                right_end_xy = [right_begin_xy[0], max(right_begin_xy[1]-self.__ACTION_OFFSET__, 0)]
                self.__standrad_track__.append((left_begin_xy, left_end_xy))
                self.__standrad_track__.append((right_begin_xy, right_end_xy))
            except IndexError as e:
                print(f'IndexError{e}')
                print("elbow is not is list")
                os.system("pause")
                return
        # else:
        #     self.__begin_flag__ = False  #重複加入標誌        
    
    def __start__(self, keypoints):
        """
        肩推進行中(向上)
        如果手腕不在肩膀,以上計時2秒後或完成目標次數next_state
        如果夾角接近180度,count+1
        左手track加入到action_track[0],右手track加入到action_track[1]
        """
        self.__fail_flag__ = False
        self.__current_time__ = time.time()
        
        if self.__current_state__ is not state.start:
            return
        
        if not self.__is_working__(keypoints):
            self.__next_state__()
            self.__set_recorder__.append(self.repitition)
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

        #印出夾角&次數
        print(self.__joint_angle__(left_elbow, left_wrist, left_shoulder))
        print(self.__joint_angle__(right_elbow, right_wrist, right_shoulder))
        print(self.__repetition__)

        if (self.__joint_angle__(left_elbow, left_wrist, left_shoulder) > 130 and 
            self.__joint_angle__(right_elbow, right_wrist, right_shoulder) > 130):
            self.repitition += 1
            self.__next_state__()

        is_exhaustion = self.__exhaustion__()
        if is_exhaustion:
            self.__fail_flag__ = True
            self.__next_state__(True)
        else:
            self.__next_state__()
        
    def __action__(self, keypoints):
        """
        肩推進行中(向下)
        下放動作後回到start,才能再次計數
        """
        if self.__current_state__ is not state.action:
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
        
        if (self.__joint_angle__(left_elbow, left_wrist, left_shoulder) < 130 and
            self.__joint_angle__(right_elbow, right_wrist, right_shoulder) < 130):
            if self.__repetition__ < self.__target_repetition__:
                self.__next_state__(False)
            else:
                self.__next_state__(True)

    def __rest__(self):
        """
        紀錄第幾組以及次數
        休息時間計時
        如果完成目標次數且低於預期秒數，則重量+2.5kg/5lbs
        如果完成目標次數且高於預期秒數，則重量維持
        如果未完成目標次數，則重量-2.5kg/5lbs,兩次以上直接結束該動作
        目標組數完成結束動作,否則進入ready狀態
        顯示: 第幾組、次數、休息時間、重量
        """
        self.__repetition__ = None
        if self.__current_state__ is not state.end or self.__time_counter__ is not None: 
            return
        
        if self.__fail_counter__ and not self.__fail_flag__:
            print("動作失敗, 請重新開始")
            return
        if self.__fail_counter__ >= 2 and self.__fail_flag__:
            print("連續動作失敗超過兩次，建議結束本次訓練！")
            return
        
        #休息時間計時
        if self.__current_group__ < self.__target__group__:
            self.__time_counter__ = threading.Thread(target=self.__timer__)
            self.__time_counter__.start()
        elif self.__current_group__ == self.__target__group__:
            print(f"目標組數完成, Congratulation!")

    def __exhaustion__(self, wrist_height) -> bool:
        """
        疲勞判斷
        """
        if time.time() - self.__current_time__ >= self.__exhaustion_threshold__:
            print("檢測到疲勞狀態！進入休息階段")
            self.__fail_counter__ += 1
            return True

    def __timer__(self):
        """
        計時器
        """
        rest_time = 0

        while rest_time < self.__target_rest_time__:
            time.sleep(1)
            rest_time += 1
            print(f"第{self.__current_group__}組結束, 休息時間:{rest_time}秒")
        self.__current_group__ += 1
        self.__next_state__()
        self.__time_counter__ = None
    
    def __is_working__(self, keypoints) -> bool:
        """
        判斷是否在進行肩推
        """
        joint_list = []

        if not self.__key_joint_exists__(joint_list):
            return False

        #判斷手腕是否在肩膀上方
        if (joint_list[sp_idx.right_wrist.value][1] > joint_list[sp_idx.right_shoulder.value][1] 
            and joint_list[sp_idx.left_wrist.value][1] > joint_list[sp_idx.left_shoulder.value][1]):
            return False
           
        return True
    
    def __joint_angle__(self, elbow, wrist, shouler) -> float:
        """
        計算肘部與肩部的夾角
        """
        cos_a = 1
        dx = elbow[0] - shouler[0]
        dx2 = elbow[1] - shouler[1]
        dx_len=math.sqrt(pow(dx, 2)+pow(dx2, 2))

        dy = elbow[0] - wrist[0]
        dy2 = elbow[1] - wrist[1]
        dy_len=math.sqrt(pow(dy, 2)+pow(dy2, 2))

        dz = wrist[0] - shouler[0]
        dz2 = wrist[1] - shouler[1]
        dz_len=math.sqrt(pow(dz, 2) + pow(dz2, 2))
        if(dy_len != 0 and dx_len != 0):
            cos_a = (pow(dx_len, 2)+pow(dy_len, 2)-pow(dz_len, 2)) / (2*dy_len*dx_len)

        try:
            #angle = math.atan(dy/dx)
            angle= math.acos(cos_a)
        except ZeroDivisionError:
            return 90.0
        return abs(math.degrees(angle))

    def __next_state__(self, state_change = False):
        """
        下一個狀態
        """
        if self.__current_state__ is state.ready:
            self.__current_state__ = state.start

        if self.__current_state__ is state.start:
            self.__current_state__ = state.action

        if self.__current_state__ is state.action and state_change:
            self.__current_state__ = state.end
        else:
            self.__current_state__ = state.start

        
    def __is_shoulder_press__(self, keypoints) -> bool:
        """
        判斷肩推準備動作
        """
        joint_list = []

        # for data in keypoints.xy:
        #     for point in enumerate(data):
        #         pt_x, pt_y = list(map(int, point[:2]))
        #         joint_list.append((pt_x, pt_y))

        if not self.__key_joint_exists__(joint_list):
            return False
        
        #判斷腕肘角度>60且<120
        if (60 <= self.__joint_angle__(joint_list[sp_idx.right_elbow.value],joint_list[sp_idx.right_wrist.value], joint_list[sp_idx.right_shoulder.value]) <= 120 and 
            60 <= self.__joint_angle__(joint_list[sp_idx.left_elbow.value],joint_list[sp_idx.left_wrist.value], joint_list[sp_idx.left_shoulder.value]) <= 120):
                return True
        else:
            return False
    
    def print_current_state(self):
        """
        印出當前狀態
        """
        print(self.__current_state__.name)
        print(self.__state_changing_counter__)
        
    def __key_joint_exists__(self, in_list)->bool:
        """
        判斷所有關節點都在畫面中
        """
        in_list = in_list[5:11]
        for l in in_list:
            if l == [0,0]:
                return False
        return True