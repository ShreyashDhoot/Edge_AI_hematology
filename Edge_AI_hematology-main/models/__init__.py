from .ssdlite_mobilenetv3 import build_ssdlite_mobilenetv3
from .yolov8_model import YOLOv8HematologyDetector
from .picodet_model import PicoDetSModel

SUPPORTED_MODELS = ["yolov8n", "ssdlite_mobilenetv3", "picodet_s"]

def get_model(model_name, num_classes=3, pretrained=True):
    name = model_name.lower()
    if name in ["yolov8n", "yolov8"]:
        return YOLOv8HematologyDetector(model_size='yolov8n.pt', num_classes=num_classes)
    elif name in ["ssdlite", "ssdlite_mobilenetv3"]:
        return build_ssdlite_mobilenetv3(num_classes=num_classes + 1, pretrained=pretrained)
    elif name in ["picodet", "picodet_s"]:
        return PicoDetSModel(num_classes=num_classes)
    else:
        raise ValueError(f"Unknown model architecture: {model_name}. Supported: {SUPPORTED_MODELS}")
