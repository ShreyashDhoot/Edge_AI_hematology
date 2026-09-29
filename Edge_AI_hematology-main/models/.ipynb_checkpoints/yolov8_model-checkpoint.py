class YOLOv8HematologyDetector:
    def __init__(self, model_size='yolov8n.pt', num_classes=3):
        self.model_size = model_size
        self.num_classes = num_classes
        self.model = None

    def load_model(self):
        try:
            from ultralytics import YOLO
            self.model = YOLO(self.model_size)
            return self.model
        except ImportError:
            return None

    def train(self, data_yaml, epochs=100, imgsz=640, batch=16, weight_decay=0.0005, patience=20, project_dir='runs/train', 
              run_name='yolov8n_hematology_v2', name=None, seed=0, dropout=0.1, degrees=180.0, flipud=0.5, mixup=0.15, copy_paste=0.15, close_mosaic=15, **kwargs):
        if name is not None:
            run_name = name
        if self.model is None:
            self.load_model()
        if self.model is None:
            raise RuntimeError('Ultralytics YOLO could not be loaded.')
        return self.model.train(
            data=data_yaml,
            epochs=epochs,
            imgsz=imgsz,
            batch=batch,
            weight_decay=weight_decay,
            patience=patience,
            cos_lr=True,
            project=project_dir,
            name=run_name,
            exist_ok=True,
            plots=True,
            save=True,
            seed=seed,
            dropout=dropout,
            degrees=degrees,
            flipud=flipud,
            mixup=mixup,
            copy_paste=copy_paste,
            close_mosaic=close_mosaic,
            mosaic=1.0,
            fliplr=0.5,
            erasing=0.4,
            auto_augment='randaugment'
        )

    def train_finetune(self, weights_path, data_yaml, epochs=30, imgsz=640, batch=16, weight_decay=0.0005, patience=10, project_dir='runs/train', 
                       run_name='yolov8n_hematology_finetune', name=None, seed=0, dropout=0.1, degrees=180.0, flipud=0.5, mixup=0.15, copy_paste=0.15, close_mosaic=15, lr0=0.001, freeze=10, **kwargs):
        if name is not None:
            run_name = name
        try:
            from ultralytics import YOLO
            self.model = YOLO(weights_path)
        except ImportError:
            raise RuntimeError('Ultralytics YOLO could not be loaded.')
            
        return self.model.train(
            data=data_yaml,
            epochs=epochs,
            imgsz=imgsz,
            batch=batch,
            weight_decay=weight_decay,
            patience=patience,
            lr0=0.001,
            freeze=10,
            cos_lr=True,
            project=project_dir,
            name=run_name,
            exist_ok=True,
            plots=True,
            save=True,
            seed=seed,
            dropout=dropout,
            degrees=degrees,
            flipud=flipud,
            mixup=mixup,
            copy_paste=copy_paste,
            close_mosaic=close_mosaic,
            mosaic=1.0,
            fliplr=0.5,
            erasing=0.4,
            auto_augment='randaugment'
        )

    def export_onnx(self, output_path='outputs/yolov8n_hematology.onnx', imgsz=640, half=False):
        if self.model is None:
            self.load_model()
        return self.model.export(format='onnx', imgsz=imgsz, half=half, dynamic=False)
