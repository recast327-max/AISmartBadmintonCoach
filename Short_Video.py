# [雲端修補版] 移除桌機 GUI 相依（cv2.imshow、pyttsx3）
# 小球
from PoseModule import PoseDetector
import cv2
import numpy as np
def Short(file_filename):

    cap = cv2.VideoCapture(file_filename)

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    detector = PoseDetector()
        text='arms need to be straight'
    dir = 0
    count = 0
    while True:

        success, img = cap.read()
        if success:

            img = cv2.resize(img, (640, 480))
            h, w, c = img.shape

            pose, img = detector.findPose(img, draw=True)
            if pose:

                lmList = pose["lmList"]
                angle, img = detector.findAngle(lmList[16], lmList[14],lmList[12], img)
                angle2, img = detector.findAngle(lmList[14], lmList[12],lmList[24], img)

                bar = np.interp(angle, (0, 180), (w//2-100, w//2+100)) #//是整數除法運算符
                bar = np.interp(angle2, (0, 180), (w//2-100, w//2+100)) #//是整數除法運算符

                if angle <= 120 and angle2 <= 60:
                    if dir == 0:
                        count = count + 0.5
                        dir = 1
                elif  angle < 140 and angle2 < 90:
                        cv2.putText(img, text, (10, 400), cv2.FONT_HERSHEY_TRIPLEX,1, (0, 0, 255), 1, cv2.LINE_AA)
                if angle >= 140 and angle2 >= 90:
                    if dir == 1:
                        count = count + 0.5
                        dir = 0
                msg = str(int(count))
                cv2.putText(img, msg, (0, 120),cv2.FONT_HERSHEY_SIMPLEX, 5,(0, 0, 0), 10)

        else:
            break
    return {"count": int(count), "success": True}
    cap.release()
    cv2.destroyAllWindows()