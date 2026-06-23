# [雲端修補版] 移除桌機 GUI 相依（cv2.imshow、pyttsx3）
#正手長球
from PoseModule import PoseDetector
import cv2
import numpy as np
def Long(file_filename):

    # 讀取影片檔案
    cap = cv2.VideoCapture(file_filename)

    # 取得影片的寬高
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # 設定視窗大小與影片大小相同
    #初始化姿勢檢測器
    detector = PoseDetector()
    text = 'Right foot needs to step back'
    text1 ='Elbow needs to be raised'
    #初始化變量
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
                angle, img = detector.findAngle(lmList[14], lmList[12],lmList[24], img)

                rightFooty = lmList[26][1]
                leftFooty = lmList[25][1]
                bar = np.interp(angle, (0, 180), (w//2-100, w//2+100))


                if angle <= 90 and rightFooty < leftFooty :
                    if dir == 0:
                        count = count + 0.5
                        dir = 1
                elif angle < 150 :
                    cv2.putText(img, text1, (10, 350), cv2.FONT_HERSHEY_TRIPLEX,1, (0, 0, 255), 1, cv2.LINE_AA)
                if angle >= 150 :
                    if dir == 1:
                        count = count + 0.5
                        dir = 0
                if rightFooty > leftFooty+10:
                    cv2.putText(img, text, (10, 400), cv2.FONT_HERSHEY_TRIPLEX,1, (0, 0, 255), 1, cv2.LINE_AA)

                msg = str(int(count))
                cv2.putText(img, msg, (0, 120),cv2.FONT_HERSHEY_SIMPLEX, 5,(0, 0, 0), 10)

        else:
            break
    return {"count": int(count), "success": True}
    cap.release()
    cv2.destroyAllWindows()