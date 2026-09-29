import cv2
import numpy as np
import os
import argparse
import glob
import json

class ReinhardNormalizerFromStats:
    def __init__(self, ref_dir):
        self.target_mean = np.array([148.5, 142.3, 118.4])
        self.target_std = np.array([32.4, 18.2, 14.1])
        
        if ref_dir and os.path.isdir(ref_dir):
            images = glob.glob(os.path.join(ref_dir, '*.[jp][pn]*[g]'))
            if images:
                means, stds = [], []
                for img_path in images:
                    img = cv2.imread(img_path)
                    if img is not None:
                        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)
                        means.append(np.mean(lab, axis=(0,1)))
                        stds.append(np.std(lab, axis=(0,1)))
                if means:
                    self.target_mean = np.mean(means, axis=0)
                    self.target_std = np.mean(stds, axis=0)

    def normalize(self, img_bgr):
        lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
        mean = np.mean(lab, axis=(0, 1))
        std = np.std(lab, axis=(0, 1))
        
        std[std == 0] = 1e-6
        
        lab = ((lab - mean) * (self.target_std / std)) + self.target_mean
        lab = np.clip(lab, 0, 255).astype(np.uint8)
        return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


class CLAHEPreprocessor:
    def __init__(self, clip_limit=2.0, tile_grid_size=(8, 8)):
        self.clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
        
    def process(self, img_bgr):
        lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        l = self.clahe.apply(l)
        lab = cv2.merge((l, a, b))
        return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


class PreprocessPipeline:
    def __init__(self, use_stain_norm=True, use_clahe=True, ref_dir=None):
        self.use_stain_norm = use_stain_norm
        self.use_clahe = use_clahe
        self.stain_norm = ReinhardNormalizerFromStats(ref_dir) if use_stain_norm else None
        self.clahe = CLAHEPreprocessor() if use_clahe else None

    def __call__(self, img_bgr):
        img = img_bgr.copy()
        if self.use_stain_norm:
            img = self.stain_norm.normalize(img)
        if self.use_clahe:
            img = self.clahe.process(img)
        return img


def nms(boxes, scores, labels, iou_threshold=0.5):
    if len(boxes) == 0:
        return boxes, scores, labels
        
    unique_labels = np.unique(labels)
    keep_boxes = []
    keep_scores = []
    keep_labels = []
    
    for c in unique_labels:
        mask = (labels == c)
        c_boxes = boxes[mask]
        c_scores = scores[mask]
        
        # cv2.dnn.NMSBoxes expects boxes as [x, y, w, h] format
        # but sometimes it accepts [x1, y1, x2, y2]. Let's convert to [x, y, w, h] to be safe
        c_boxes_xywh = np.zeros_like(c_boxes)
        c_boxes_xywh[:, 0] = c_boxes[:, 0]
        c_boxes_xywh[:, 1] = c_boxes[:, 1]
        c_boxes_xywh[:, 2] = c_boxes[:, 2] - c_boxes[:, 0]
        c_boxes_xywh[:, 3] = c_boxes[:, 3] - c_boxes[:, 1]
        
        indices = cv2.dnn.NMSBoxes(c_boxes_xywh.tolist(), c_scores.tolist(), score_threshold=0.0, nms_threshold=iou_threshold)
        
        if len(indices) > 0:
            indices = indices.flatten()
            for idx in indices:
                keep_boxes.append(c_boxes[idx])
                keep_scores.append(c_scores[idx])
                keep_labels.append(c)
                
    if not keep_boxes:
        return np.array([]), np.array([]), np.array([])
        
    return np.array(keep_boxes), np.array(keep_scores), np.array(keep_labels)


class TestTimeAugmentor:
    def __init__(self, model):
        self.model = model

    def __call__(self, img_bgr, conf=None):
        H, W = img_bgr.shape[:2]
        
        img_0 = img_bgr
        img_90 = cv2.rotate(img_bgr, cv2.ROTATE_90_CLOCKWISE)
        img_180 = cv2.rotate(img_bgr, cv2.ROTATE_180)
        img_270 = cv2.rotate(img_bgr, cv2.ROTATE_90_COUNTERCLOCKWISE)
        
        images = [img_0, img_90, img_180, img_270]
        all_boxes, all_scores, all_labels = [], [], []
        
        for idx, img_rot in enumerate(images):
            preds = self.model(img_rot, conf=conf)
            boxes = np.array(preds.get('boxes', []))
            scores = np.array(preds.get('scores', []))
            labels = np.array(preds.get('labels', []))
            
            if len(boxes) == 0:
                continue
                
            orig_boxes = np.zeros_like(boxes)
            for i, box in enumerate(boxes):
                x1, y1, x2, y2 = box
                if idx == 0:
                    orig_boxes[i] = [x1, y1, x2, y2]
                elif idx == 1: 
                    orig_boxes[i] = [y1, W - x2, y2, W - x1]
                elif idx == 2: 
                    orig_boxes[i] = [W - x2, H - y2, W - x1, H - y1]
                elif idx == 3: 
                    orig_boxes[i] = [H - y2, x1, H - y1, x2]
            
            all_boxes.append(orig_boxes)
            all_scores.append(scores)
            all_labels.append(labels)
            
        if not all_boxes:
            return {'boxes': np.zeros((0, 4)), 'scores': np.zeros(0), 'labels': np.zeros(0, int)}
            
        all_boxes = np.concatenate(all_boxes, axis=0)
        all_scores = np.concatenate(all_scores, axis=0)
        all_labels = np.concatenate(all_labels, axis=0)
        
        final_boxes, final_scores, final_labels = nms(all_boxes, all_scores, all_labels, iou_threshold=0.5)
        
        return {
            'boxes': final_boxes if len(final_boxes) > 0 else np.zeros((0, 4)),
            'scores': final_scores if len(final_scores) > 0 else np.zeros(0),
            'labels': final_labels.astype(int) if len(final_labels) > 0 else np.zeros(0, int)
        }

class PerClassThresholder:
    def __init__(self, thresholds=None):
        if thresholds is None:
            self.thresholds = {1: 0.25, 2: 0.25, 3: 0.15}
        else:
            self.thresholds = thresholds

    def filter(self, preds_dict):
        boxes = np.asarray(preds_dict.get('boxes', np.zeros((0, 4))), dtype=np.float32).reshape(-1, 4)
        scores = np.asarray(preds_dict.get('scores', np.zeros(0)), dtype=np.float32)
        labels = np.asarray(preds_dict.get('labels', np.zeros(0, int)), dtype=int)
        
        if len(boxes) == 0:
            return {'boxes': np.zeros((0, 4)), 'scores': np.zeros(0), 'labels': np.zeros(0, int)}
        
        keep = np.array([scores[i] >= self.thresholds.get(int(labels[i]), 0.25) for i in range(len(scores))])
        
        return {
            'boxes': boxes[keep] if keep.any() else np.zeros((0, 4)),
            'scores': scores[keep] if keep.any() else np.zeros(0),
            'labels': labels[keep] if keep.any() else np.zeros(0, int)
        }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model_weights', required=True)
    parser.add_argument('--input_dir', required=True)
    parser.add_argument('--output_dir', required=True)
    parser.add_argument('--bccd_ref_dir', default=None)
    parser.add_argument('--use_tta', action='store_true')
    parser.add_argument('--use_stain_norm', action='store_true')
    parser.add_argument('--use_clahe', action='store_true')
    parser.add_argument('--plt_conf', type=float, default=0.15)
    
    args = parser.parse_args()
    
    os.makedirs(args.output_dir, exist_ok=True)
    
    pipeline = PreprocessPipeline(
        use_stain_norm=args.use_stain_norm,
        use_clahe=args.use_clahe,
        ref_dir=args.bccd_ref_dir
    )
    
    try:
        import sys
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from paper_eval import YoloPT
        model = YoloPT(args.model_weights)
    except ImportError:
        # Fallback dummy class if YoloPT cannot be imported
        class DummyModel:
            def __init__(self, weights):
                from ultralytics import YOLO
                self.model = YOLO(weights)
            def __call__(self, img, conf=None):
                results = self.model(img, conf=conf if conf is not None else 0.01, verbose=False)
                r = results[0]
                return {
                    'boxes': r.boxes.xyxy.cpu().numpy().tolist(),
                    'scores': r.boxes.conf.cpu().numpy().tolist(),
                    'labels': r.boxes.cls.cpu().numpy().astype(int).tolist()
                }
        model = DummyModel(args.model_weights)
        
    if args.use_tta:
        model = TestTimeAugmentor(model)
        
    thresholder = PerClassThresholder({1: 0.25, 2: 0.25, 3: args.plt_conf})
    
    image_paths = glob.glob(os.path.join(args.input_dir, '*.*'))
    
    for img_path in image_paths:
        if not img_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff')):
            continue
            
        img_bgr = cv2.imread(img_path)
        if img_bgr is None:
            continue
            
        processed_img = pipeline(img_bgr)
        
        preds = model(processed_img)
        final_preds = thresholder.filter(preds)
        
        out_name = os.path.splitext(os.path.basename(img_path))[0] + '.json'
        with open(os.path.join(args.output_dir, out_name), 'w') as f:
            json.dump(final_preds, f, indent=4)

if __name__ == '__main__':
    main()
