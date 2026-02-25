# packages/ml/src/ml/main.py
import time
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from ml.fake_camera import FakeCameraStream

app = FastAPI()
stream = FakeCameraStream(fps=10.0)


@app.on_event('startup')
def startup():
    stream.start()


@app.on_event('shutdown')
def shutdown():
    stream.stop()


def mjpeg_generator():
    boundary = b'--frame\r\n'
    content_type = b'Content-Type: image/jpeg\r\n'

    while True:
        jpg, ts = stream.latest()
        if jpg is None:
            time.sleep(0.05)
            continue

        # "один кадр" в MJPEG: boundary + заголовки + пустая строка + jpg + \r\n
        yield (
            boundary
            + content_type
            + f'X-Timestamp: {ts}\r\n'.encode()
            + b'Content-Length: ' + str(len(jpg)).encode() + b'\r\n\r\n'
            + jpg
            + b'\r\n'
        )


@app.get('/mjpeg')
def mjpeg():
    return StreamingResponse(
        mjpeg_generator(),
        media_type='multipart/x-mixed-replace; boundary=frame',
    )