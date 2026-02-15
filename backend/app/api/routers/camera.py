from fastapi import APIRouter, HTTPException
import cv2

router = APIRouter()

#Получить информаци по ID доступных камер
def scan_cameras():
    cameras = []
    for i in range(10):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            cameras.append(i)
        cap.release()
    return cameras

@router.get("/cameras_list")
def get_cameras():  
    return {'ID доступных камер': scan_cameras()}

#Полуить информацию о камере по его ID
@router.get("/cameras_list/{camera_id}")
def get_camera(camera_id: int):
    cameras = scan_cameras()
    if camera_id in cameras:
        return {"camera": camera_id}
    raise HTTPException(status_code=404, detail="Нет такой камеры")

#Получить поток с камеры
@router.get('/stream/{camera_id}')
def get_video(camera_id: int = 0):
    cameras = scan_cameras()
    if camera_id not in cameras: 
        raise HTTPException(status_code=404, detail="Нет такой камеры")
    cap = cv2.VideoCapture(camera_id) 
    cv2.namedWindow('Res', cv2.WINDOW_KEEPRATIO)
    cv2.resizeWindow("Res", 1920, 1080) 
    while True:
        ret, im = cap.read()
        if not ret:
            break
        cv2.imshow("Res", im)
        if cv2.waitKey(1) & 0xFF == ord('f'):
            break

    cap.release()
    cv2.destroyWindow("Res")

#Получить поток со всех камер
@router.get('/stream/all')
def get_all_video():
    pass

#Написать включение и выключение камеры     
@router.post('/{camera_id}')
def camera_on(camera_id: int = 0):
    return {'camera_id': camera_id, 'status': 'on'}

@router.post('/camera_off/{camera_id}')
def camera_off(camera_id: int = 0):
    return {'camera_id': camera_id, 'status': 'off'}
