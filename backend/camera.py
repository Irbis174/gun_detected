from fastapi import APIRouter
import cv2

router = APIRouter()

#Получить поток с камеры
@router.get('/stream/{camera_id}')
def get_video(camera_id: int = 0):
    cameras = get_cameras()
    if id not in cameras['ID доступных камер']: 
        raise ValueError('Нет такой камеры')
    cap = cv2.VideoCapture(camera_id)  
    while True:
        ret, im = cap.read()
        cv2.namedWindow('Res', cv2.WINDOW_KEEPRATIO)
        cv2.imshow("Res", im)
        cv2.resizeWindow("Res", 1920, 1080)
        if cv2.waitKey(1) & 0xFF == ord('f'):
            break
    cv2.destroyWindow("Res")

#Получить поток со всех камер
@router.get('/stream/all')
def get_all_video():
    pass

#Получить информаци по ID доступных камер
@router.get('/cameras_list')
def get_cameras():
    cameras = []
    for i in range(10):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            cameras.append(i)
            cap.release()
    return {'ID доступных камер ': cameras}

#Полуить информацию о камере по его ID
@router.get('/cameras_list/{id}')
def get_camera_id(id: int = 0):
    cameras = get_cameras()
    if id in cameras['ID доступных камер']: 
        return {'camera': id}
    else:
        raise ValueError('Нет такой камеры')

#Написать включение и выключение камеры     
@router.post('/{id}')
def camera_on(id: int = 0):
    pass

@router.post('/{id}')
def camera_off(id: int = 0):
    pass
