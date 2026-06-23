# [雲端修補版] 移除桌機 GUI 相依（cv2.imshow、pyttsx3）
#反手挑球影片辨識
from PoseModule import PoseDetector
import cv2
import numpy as np
def BackHandFlick(file_filename):
    # cap = cv2.VideoCapture("20230512_205010.mp4")
    cap = cv2.VideoCapture(file_filename)
    # 取得影片的寬高
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    # 設定視窗大小與影片大小相同
    #初始化姿勢檢測器
    detector = PoseDetector()
        text = 'Right foot needs to step left'
    text1 ='Elbow needs to be raised'

    #初始化變量
    dir = 0
    count = 0
    while True:
        #讀取影片
        success, img = cap.read()
        if success:
            #調整圖像大小
            img = cv2.resize(img, (640, 480))
            h, w, c = img.shape
            #查找人體姿勢
            pose, img = detector.findPose(img, draw=True)
            if pose:
                #查找肘部、肩部和腰部之間的角度
                lmList = pose["lmList"]
                angle, img = detector.findAngle(lmList[14], lmList[12],lmList[24], img)
                rightFoot = lmList[28][1]
                leftFoot = lmList[27][1]
                # 將角度值從 0 到 180 映射到像素坐標範圍內的位置
                #bar = np.interp(angle2, (0, 180), (w//2-100, w//2+100)) #//是整數除法運算符
                bar = np.interp(angle, (0, 180), (w//2-100, w//2+100)) #//是整數除法運算符
                # 在圖像上繪製矩形標尺
                #cv2.rectangle(img, (w//2-100, 50), (int(bar), 100),(0, 255, 0), cv2.FILLED)
                #計算次數
                if angle <=40 and rightFoot > leftFoot:
                    if dir == 0:
                        count = count + 0.5
                        dir = 1
                elif angle < 100:
                    cv2.putText(img, text1, (10, 350), cv2.FONT_HERSHEY_TRIPLEX,1, (0, 0, 255), 1, cv2.LINE_AA)
                if angle >= 100 :
                    if dir == 1:
                        count = count + 0.5
                        dir = 0
                if  rightFoot < leftFoot:
                    cv2.putText(img, text, (10, 400), cv2.FONT_HERSHEY_TRIPLEX,1, (0, 0, 255), 1, cv2.LINE_AA)

                # 在圖像上顯示次數
                msg = str(int(count))
                cv2.putText(img, msg, (0, 120),cv2.FONT_HERSHEY_SIMPLEX, 5,(0, 0, 0), 10)
            # 顯示圖像
        else:
            break
    return {"count": int(count), "success": True}
    cap.release()
    cv2.destroyAllWindows()