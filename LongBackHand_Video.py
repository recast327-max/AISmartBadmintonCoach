# [雲端修補版] 移除桌機 GUI 相依（cv2.imshow、pyttsx3）
#反手長球
from PoseModule import PoseDetector
import cv2
import numpy as np
def LongBackHand(file_filename):
    # 讀取影片
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

            img = cv2.resize(img, (640, 480))
            h, w, c = img.shape

            pose, img = detector.findPose(img, draw=True)
            if pose:

                lmList = pose["lmList"]
                angle, img = detector.findAngle(lmList[14], lmList[12],lmList[24], img)
                angle1, img = detector.findAngle(lmList[16], lmList[14],lmList[12], img)
                rightFoot = lmList[26][0]
                leftFoot = lmList[25][0]

                bar = np.interp(angle1, (0, 180), (w//2-100, w//2+100)) #//是整數除法運算符
                bar = np.interp(angle, (0, 180), (w//2-100, w//2+100)) #//是整數除法運算符

                if angle <= 60 and rightFoot > leftFoot and angle1 <= 40:
                    if dir == 0:
                        count = count + 0.5
                        dir = 1
                elif angle <= 90 and angle1 < 160:
                    cv2.putText(img, text1, (10, 350), cv2.FONT_HERSHEY_TRIPLEX,1, (0, 0, 255), 1, cv2.LINE_AA)
                if angle >= 90 and angle1 > 160:
                    if dir == 1:
                        count = count + 0.5
                        dir = 0
                if  rightFoot < leftFoot:
                    cv2.putText(img, text, (10, 400), cv2.FONT_HERSHEY_TRIPLEX,1, (0, 0, 255), 1, cv2.LINE_AA)



                msg = str(int(count))
                cv2.putText(img, msg, (0, 120),cv2.FONT_HERSHEY_SIMPLEX, 5,(0, 0, 0), 10)

        else:
            break
    return {"count": int(count), "success": True}
    cap.release()
    cv2.destroyAllWindows()