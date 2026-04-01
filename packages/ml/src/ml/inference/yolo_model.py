from ultralytics import YOLO

from ml.config import ML_DEVICE, MODEL_PATH

_model: YOLO | None = None


def load_model() -> YOLO:
    global _model
    if _model is None:
        _model = YOLO(MODEL_PATH)
        _model.to(ML_DEVICE)
    return _model


def get_model() -> YOLO:
    if _model is None:
        return load_model()
    return _model
