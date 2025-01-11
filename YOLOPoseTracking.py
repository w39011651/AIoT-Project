from enum import Enum
import time
import threading
from YOLOPoseConstant import shoulder_press_joint_index as sp_idx
import os
import threading
import math
import time
import cv2
import mysql.connector
from PIL import Image

class state(Enum):
    ready = 0
    start = 1
    action = 2
    end = 3
    
class action_state(object):
    __current_state__ = state.ready #當前狀態
    repetition = 0
    action_track = list() #[[left_begin_xy, left_end_xy], [right_begin_xy, right_end_xy]]
    standard_track = list()
    set_recorder = list() #[repetition] #紀錄每組的次數
    __prev_wrist_height__ = list()
    __time_counter__ = None #倒數1秒
    __state_changing_counter__ = 2
    __begin_flag__ = False #(Thread is not start yet)
    __exhaustion_event__ = threading.Event()
    
    __ACTION_OFFSET__ = 100 #動作高點(可能需可變?)
    __exhaustion_threshold__ = 5000 #疲勞時間閾值
    __MOVE_THRESHOLD__ = 100 #超過此值視為偵測錯誤
    
    __db_connection__ = None
    __set_indicator__ = 0 #第幾組 #當前組數
    __target_set_count__ = 0 #目標組數
    __target_repetition__ = [] #from SQL #目標重複次數
    __target_rest_time__ = [] #目標休息時間(from SQL)
    __target_weight__ = [] #(from SQL)
    __score_record__ = [] #紀錄每次動作的分數
    #長度代表組數
    
    #merge新增變數
    __fail_counter__ = 0 #失敗次數
    __fail_flag__ = False #失敗標誌
    __current_time__ = 0 #當前時間
    __exhaustion_counter__ = threading.Event() #疲勞標誌
    __time_flag__ = False #時間標誌 #避免time()重複賦予
    __rest_time__ = 0 #休息時間

    def test_method(self):
        self.__target_set_count__ = 3
        self.__target_repetition__ = [15, 15, 15]
        self.__target_rest_time__ = [90, 90, 90]
        self.__target_weight__ = [10, 10, 10]
        self.__score_record__ = [80, 80, 80]
        self.insert_data_to_db()

    def __init__(self):
        self.__current_state__ = state.ready
        self.repetition = 0
        self.action_track = list()
        self.standard_track = list()
        self.__db_connection__ = self.__connect_to_db__()
        self.__determine_actions__()
    
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
        
        group_text = f"Group: {self.__set_indicator__+1}/{self.__target_set_count__}"
        (text_width, text_height), baseline = cv2.getTextSize(group_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
        
        if self.__current_state__ is not state.end and self.repetition is not None: #如果不在休息狀態，加入重複次數
            group_text += f" Rep: {self.repetition}/{self.__target_repetition__[self.__set_indicator__]}"
            (text_width, text_height), baseline = cv2.getTextSize(group_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
        
        cv2.putText(image, group_text, 
                    (width - text_width - 10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # 畫面下方中央 - 疲勞警告（類似字幕位置）
        if self.__fail_flag__ and self.__current_state__ is state.action:
            warning_text = "Warning: 檢測到疲勞狀態！進入休息階段"
            (text_width, text_height), baseline = cv2.getTextSize(warning_text, cv2.FONT_HERSHEY_SIMPLEX, 1.0, 2)

            text_x = (width - text_width) // 2
            text_y = int(height * 0.85)
            cv2.putText(image, warning_text,
                        (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
        
        # 畫面正中央 - 休息時間
        if self.__current_state__ is state.end and self.__time_counter__ is not None:
            if self.__set_indicator__ < self.__target_set_count__:
                rest_text = f"Rest Time: {self.__target_rest_time__[self.__set_indicator__] - self.__rest_time__}s"
                (text_width, text_height), baseline = cv2.getTextSize(rest_text, cv2.FONT_HERSHEY_SIMPLEX, 1.2, 2)
                
                text_x = (width - text_width) // 2
                text_y = height // 2
            elif self.__set_indicator__ + 1 == self.__target_set_count__:
                rest_text = "目標組數完成, Congratulation!"
                (text_width, text_height), baseline = cv2.getTextSize(rest_text, cv2.FONT_HERSHEY_SIMPLEX, 1.2, 2)
                
            # # 半透明背景
            overlay = image.copy()
            cv2.rectangle(overlay, 
                        (text_x - 10, text_y - text_height - 10),
                        (text_x + text_width + 10, text_y + 10),
                        (0, 0, 0), -1)
            alpha = 0.6 #透明度
            image = cv2.addWeighted(overlay, alpha, image, 1 - alpha, 0) #混合圖像
            
            text_x = (width - text_width) // 2
            text_y = height // 2
            
            cv2.putText(image, rest_text,
                        (text_x, text_y), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)

        return image

    def detect(self, keypoints, image):
        """
        肩推動作流程檢測
        """
        if self.__current_state__ is state.ready:
            self.__begin__(keypoints) #開始動作
        elif self.__current_state__ is state.start:
            self.__concentric__(keypoints) #肩推進行中(向上)
        elif self.__current_state__ is state.action:
            self.__eccentric__(keypoints) #肩推進行中(向下)
        elif self.__current_state__ is state.end:
            self.__rest__() #休息時間
        
        return self.render_text(image)

    def __begin__(self, keypoints):
        """
        開始動作
        如果手腕在肩膀上方,進入start
        """
        if self.__current_state__ is not state.ready:
            return
        
        self.__time_flag__ = False
        
        is_shoulder_press = self.__is_shoulder_press__(keypoints)
        
        if is_shoulder_press:
            print("nextstage")  
            self.repetition = 0
            self.__next_state__()
        elif len(self.standard_track) == 0: #不重複加入
            try:
                #手肘可能不會被偵測到而變為[0,0]
                SLOPE = 3.7320508075688 #斜率=tan60^o
                left_begin_xy = list(map(int,keypoints.xy[0][sp_idx.left_wrist.value][:2])) #將肘部關節轉換為整數列表
                right_begin_xy = list(map(int,keypoints.xy[0][sp_idx.right_wrist.value][:2]))

                if left_begin_xy == [0,0] or right_begin_xy == [0,0]:
                    return

                #left_end_xy = [left_begin_xy[0], 0]#更改為到最上面(因為只看橫移)
                left_end_xy = [int(left_begin_xy[0] - left_begin_xy[1]//SLOPE), 0]
                #right_end_xy = [right_begin_xy[0], 0]
                right_end_xy = [int(right_begin_xy[0] + right_begin_xy[1]//SLOPE), 0]

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
        肩推動作進行中(向上)
        幫動作計數，條件:離心不可太快、行程完整
        上至兩倍前臂長，下至腕至耳朵
        如果手腕不在肩膀,以上計時2秒後或完成目標次數next_state
        如果夾角接近180度,count+1
        左手track加入到action_track[0],右手track加入到action_track[1]
        """
        self.__fail_flag__ = False
        
        if self.__time_flag__ is False:
            self.__current_time__ = time.time()
            self.__time_flag__ = True
        
        if self.__current_state__ is not state.start:
            return
        
        if not self.__is_working__(keypoints):
            # self.__next_state__()
            # self.set_recorder.append(self.repetition)
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

        if (self.__joint_angle__(left_elbow, left_wrist, left_shoulder) > 120 and
            self.__joint_angle__(right_elbow, right_wrist, right_shoulder) > 120):
            self.repetition += 1
            self.__next_state__()
            #self.__set_recorder__.append(self.__calculate_score__())

        is_exhaustion = self.__exhaustion__()
        if is_exhaustion:
            self.__fail_flag__ = True
            self.__next_state__(True)
        # else:
        #     self.__next_state__()
        
    def __eccentric__(self, keypoints):
        """
        肩推進行中(向下)
        下放動作後回到start,才能再次計數
        下放動作後回到concentric，才能再次計數
        """
        if self.__current_state__ is not state.action:
            return
        
        self.__time_flag__ = False
        
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

        if (self.__joint_angle__(left_elbow, left_wrist, left_shoulder) < 95 and
            self.__joint_angle__(right_elbow, right_wrist, right_shoulder) < 95):
            if self.repetition < self.__target_repetition__[self.__set_indicator__]:
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
        self.repetition = None

        if self.__current_state__ is not state.end or self.__time_counter__ is not None: 
            return

        if self.__fail_counter__ and self.__fail_flag__:
            print("動作失敗, 請重新開始")
            return
        if self.__fail_counter__ >= 2 and self.__fail_flag__:
            print("連續動作失敗超過兩次，建議結束本次訓練！")
            return
        
        if self.__time_counter__ is None:
            __set_score__ = self.__calculate_score__()
            print(f"動作分數:{__set_score__}")
            self.__score_record__.append(__set_score__)
        #休息時間計時
        if self.__set_indicator__ < self.__target_set_count__ - 1:
            self.__time_counter__ = threading.Thread(target=self.__timer__)
            self.__time_counter__.start()
        elif self.__set_indicator__ + 1 == self.__target_set_count__:
            print(f"目標組數完成, Congratulation!")

    def __exhaustion__(self) -> bool:
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
        self.__rest_time__ = 0

        while self.__rest_time__ < self.__target_rest_time__[self.__set_indicator__]:
            time.sleep(1)
            self.__rest_time__ += 1
            print(f"第{self.__set_indicator__+1}組結束, 休息時間:{self.__rest_time__}秒")
        self.__set_indicator__ += 1
        self.__next_state__()
        self.__time_counter__ = None

    def __is_working__(self, keypoints) -> bool:
        """
        判斷是否在進行肩推
        """
        joint_list = list()
        for data in keypoints.xy:
            for _, point in enumerate(data):
                pt_x, pt_y = list(map(int, point[:2]))
                joint_list.append([pt_x, pt_y])#獲取所有關節xy座標
        
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

    def __is_shoulder_press__(self, keypoints) -> bool:
        """
        判斷肩推準備動作
        """
        joint_list = list()

        for data in keypoints.xy:
            # if len(data) == 0:
            #     print("No person in the img")
            #     return False#沒有人在畫面中
            
            for _, point in enumerate(data):
                pt_x, pt_y = list(map(int, point[:2]))
                joint_list.append([pt_x, pt_y]) #獲取所有關節xy座標
                
        if not self.__key_joint_exists__(joint_list):
            return False
        
        print(self.__joint_angle__(joint_list[sp_idx.right_elbow.value], joint_list[sp_idx.right_wrist.value], joint_list[sp_idx.right_shoulder.value]))
        print(self.__joint_angle__(joint_list[sp_idx.left_elbow.value],joint_list[sp_idx.left_wrist.value], joint_list[sp_idx.left_shoulder.value]))
        
        if (60 <= self.__joint_angle__(joint_list[sp_idx.right_elbow.value],joint_list[sp_idx.right_wrist.value], joint_list[sp_idx.right_shoulder.value]) <= 120 and 
            60 <= self.__joint_angle__(joint_list[sp_idx.left_elbow.value],joint_list[sp_idx.left_wrist.value], joint_list[sp_idx.left_shoulder.value]) <= 120):
                return True #判斷肘部略低於肩部且腕肘角度接近垂直
        else:
            return False
        
    def __next_state__(self, finish = False) -> int:
        """
        下一個狀態
        """
        if self.__current_state__ is state.ready:
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

    def __calculate_score__(self) -> float:
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
        total_distance = 0
        #forall point in action track, calculate the distance to the line
        for list in self.action_track:
            left_pt = list[0]
            right_pt = list[1]
            distance1 = abs(coefficient_a1*left_pt[0]+coefficient_b1*left_pt[1]-coefficient_c1)/math.sqrt(pow(coefficient_a1,2)+pow(coefficient_b1,2))
            distance2 = abs(coefficient_a2*right_pt[0]+coefficient_b2*right_pt[1]-coefficient_c2)/math.sqrt(pow(coefficient_a2,2)+pow(coefficient_b2,2))
            total_distance = total_distance + distance1 + distance2
            #分數: score = 100 - coefficient\times\sum_{i=1}^{n} distance
        total_distance = total_distance/len(self.action_track)#取平均距離
        self.action_track.clear()
        
        return 0.5*total_distance

    def __two_point_distance__(self, pt1, pt2)->float:
        return math.sqrt(pow(pt1[0]-pt2[0],2)+pow(pt1[1]-pt2[1],2))
    
    def __connect_to_db__(self):
        connection = mysql.connector.connect(
        host="database-1.c7862uku0eq4.ap-northeast-1.rds.amazonaws.com",
        user="admin",
        password="33818236",
        database="demo_database"
        )
        return connection
    
    def __fetch_data_from_db__(self):
        """
        database structure:
        id----workout_date----weight----repetition----rest_time----score
        """
        with self.__db_connection__ as conn:
            cursor=conn.cursor(dictionary=True, buffered=True)
            cursor.execute("SELECT * FROM workout_data ORDER BY id DESC LIMIT 1")
            last_action = cursor.fetchone()#找到最後一筆資料
            cursor.reset()
            if last_action:
                last_date = last_action['workout_date']
                query = "SELECT * FROM workout_data WHERE workout_date = %s"
                cursor.execute(query, (last_date,))
                rows = cursor.fetchall()

                cursor.close()
                print(rows)
                return rows
            else:
                cursor.close()
                return None
            
    def __determine_actions__(self):
        """
        判斷這次的重量、次數以及休息時間
        """
        last_actions = self.__fetch_data_from_db__()
        """action_target = [weight, repetition, set_number, rest_time]"""
        action_target = []
        if last_actions is None:
            """如果是第一次: 重量10, 次數15, 休息時間1:30"""
            action_target = [5,15,3,90]
        else:
            """
            如果不是第一次，判斷上次的組數、次數、休息時間和重量的差值
            決定這次的重量、次數和休息時間
            """
            """
            algo:
            重量: 
            如果減少，則保持重量、增加目標次數
            如果增加或不變，則可以增加重量
            次數: 
            如果到達12~15區間，則增加重量
            如果為6~8區間且重量下降，則增加組數
            休息時間:
            12~15區間: 1:30
            8~12區間: 2:00
            6~8區間: 3:00
            """
            weight_diff = last_actions[-1]["weight"] - last_actions[0]["weight"]
            set_number = len(last_actions)
            repetition = last_actions[0]["repetition"]

            if weight_diff < 0:
                action_target.append(last_actions[-1]["weight"])
                if repetition < 12:
                    action_target.append(repetition+3)
                    action_target.append(set_number)
                else:
                    action_target.append(repetition)
                    action_target.append(set_number+1)
            else:
                action_target.append(last_actions[-1]["weight"]+1.25)
                action_target.append(repetition)
                action_target.append(set_number)

            if repetition >= 12:
                action_target.append(90)
            elif repetition >= 8:
                action_target.append(120)
            else:
                action_target.append(180)

        self.__target_set_count__ = action_target[2]
        for _ in range(0, self.__target_set_count__):
            self.__target_weight__.append(action_target[0])
            self.__target_repetition__.append(action_target[1])
            self.__target_rest_time__.append(action_target[3])      

    def insert_data_to_db(self):
        with self.__db_connection__ as conn:
            conn.reconnect()
            cursor=conn.cursor()
            sql = "INSERT INTO workout_data (workout_date, weight, repetition, rest_time, score) VALUES (%s, %s, %s, %s, %s)"
            
            for i in range(self.__target_set_count__):
                rest_time_str = f"00:{self.__target_rest_time__[i]//60}:{self.__target_rest_time__[i]%60}"
                cursor.execute(sql, (time.strftime("%Y-%m-%d"), self.__target_weight__[i], self.__target_repetition__[i], rest_time_str, self.__score_record__[i]))
                conn.commit()
            cursor.close()