#正手挑球即時辨識
from PoseModule import PoseDetector
import cv2
import numpy as np
import pyttsx3
import speech_recognition as sr
import threading
import time
# 初始化攝影機，預設使用內建相機
camera_index = 0
cap = cv2.VideoCapture(camera_index)
engine = pyttsx3.init()
test=""
cap=None
def thread1():
    global test
    cv2.namedWindow('Pose', cv2.WINDOW_NORMAL) #先設定視窗為可調整大小
    cv2.setWindowProperty('Pose', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN) #將視窗設定為全螢幕
    global cap
    cap = cv2.VideoCapture(0)
    detector = PoseDetector()

    text1 ='Elbow needs to be raised'
    dir = 0
    count = 0
    if not cap.isOpened():
        print("Cannot open camera")
        exit()

    while True:
        success, img = cap.read()
        if success:

            img = cv2.resize(img, (640, 480))
            h, w, c = img.shape

            pose, img = detector.findPose(img, draw=True)
            if pose:
                lmList = pose["lmList"]
                angle, img = detector.findAngle(lmList[16], lmList[14],lmList[12], img)
                angle1, img = detector.findAngle(lmList[14], lmList[12],lmList[24], img) #右
                angle2, img = detector.findAngle(lmList[13], lmList[11],lmList[23], img)#左
                bar = np.interp(angle1, (0, 180), (w//2-100, w//2+100)) #//是整數除法運算符
                bar = np.interp(angle2, (0, 180), (w//2-100, w//2+100)) #//是整數除法運算符
                bar = np.interp(angle, (0, 180), (w//2-100, w//2+100)) #//是整數除法運算符

                if angle >= 140 and angle1 < angle2:
                    if dir == 0:
                        count = count + 0.5
                        dir = 1


                if angle <= 60 and angle1 >= angle2:
                    if dir == 1:
                        count = count + 0.5
                        dir = 0
                else :
                    cv2.putText(img, text1, (10, 400), cv2.FONT_HERSHEY_TRIPLEX,1, (0, 0, 255), 1, cv2.LINE_AA)

                msg = str(int(count))
                cv2.putText(img, msg, (0, 120),cv2.FONT_HERSHEY_SIMPLEX, 5,(0, 0, 0), 10)

            cv2.imshow("Pose", img)
        else:
            break
        # 捕捉鍵盤輸入，按 '0' 切換至內建相機，按 '1' 切換至外接相機
        key = cv2.waitKey(1) & 0xFF
        if key == ord("0"):
            camera_index = 0
            cap.release()
            cap = cv2.VideoCapture(camera_index)
        elif key == ord("1"):
            camera_index = 1
            cap.release()
            cap = cv2.VideoCapture(camera_index)
        if cv2.waitKey(1) & 0xFF == ord("q") :
            break
        if "關閉"==test or "關閉" in test:
            break

def thread2():
    while True:

        # 建立Recognizer物件
        r = sr.Recognizer()

        # 開啟麥克風並進行錄音
        with sr.Microphone() as source:
            audio = r.listen(source)

        # 使用Google語音辨識引擎將錄音轉換為文字
        try:
            global test
            test = r.recognize_google(audio, language='zh-TW')
            if "關閉"==test or "關閉" in test:

                break
        except sr.UnknownValueError:
            print("無法辨識您的語音")
        except sr.RequestError as e:
            print("無法連線至Google語音辨識服務：{0}".format(e))


t1=threading.Thread(target=thread1)
t2=threading.Thread(target=thread2)
t1.start()
t2.start()
t1.join()
engine.say("系統已關閉")
engine.runAndWait()
cap.release()
cv2.destroyAllWindows()