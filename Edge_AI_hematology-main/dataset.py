"""
dataset.py - Blood Smear Dataset Processing & Domain Augmentations

Features:
1. Reinhard Stain Normalization in Lab color space to address stain variability.
2. Contrast-Limited Adaptive Histogram Equalization (CLAHE) for cell morphology.
3. Pascal VOC XML & YOLO annotation parsing for multi-class cell detection (RBC, WBC, Platelets).
4. Microscopic rotational and photometric invariant data augmentations.
"""

import os
import glob
import xml.etree.ElementTree as ET
import numpy as np
import cv2

try:
    import torch
    from torch.utils.data import Dataset
except ImportError:
    class Dataset:
        pass
    torch = None

DEFAULT_CLASSES = ["RBC", "WBC", "Platelets"]
CLASS_TO_IDX = {cls_name: i + 1 for i, cls_name in enumerate(DEFAULT_CLASSES)}
IDX_TO_CLASS = {v: k for k, v in CLASS_TO_IDX.items()}

class ReinhardStainNormalizer:
    def __init__(self, target_img_path=None):
        self.target_mean = np.array([148.5, 142.3, 118.4])
        self.target_std = np.array([32.4, 18.2, 14.1])
        if target_img_path and os.path.exists(target_img_path):
            self.fit_target(target_img_path)

    def fit_target(self, img_path):
        img = cv2.imread(img_path)
        if img is None:
            raise ValueError(f"Unable to read target reference image: {img_path}")
        img_lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)
        self.target_mean = np.mean(img_lab, axis=(0, 1))
        self.target_std = np.std(img_lab, axis=(0, 1)) + 1e-6

    def normalize(self, img_bgr):
        img_lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
        src_mean = np.mean(img_lab, axis=(0, 1))
        src_std = np.std(img_lab, axis=(0, 1)) + 1e-6
        norm_lab = (img_lab - src_mean) * (self.target_std / src_std) + self.target_mean
        norm_lab = np.clip(norm_lab, 0, 255).astype(np.uint8)
        return cv2.cvtColor(norm_lab, cv2.COLOR_LAB2BGR)

def apply_clahe(img_bgr, clip_limit=2.0, tile_grid_size=(8, 8)):
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
    cl = clahe.apply(l)
    return cv2.cvtColor(cv2.merge((cl, a, b)), cv2.COLOR_LAB2BGR)

class BloodSmearAugmentor:
    def __init__(self, is_train=True):
        self.is_train = is_train

    def __call__(self, image, boxes, labels):
        if not self.is_train or len(boxes) == 0:
            return image, boxes, labels
        h, w, _ = image.shape
        if np.random.rand() > 0.5:
            image = cv2.flip(image, 1)
            boxes[:, [0, 2]] = w - boxes[:, [2, 0]]
        if np.random.rand() > 0.5:
            image = cv2.flip(image, 0)
            boxes[:, [1, 3]] = h - boxes[:, [3, 1]]
        rot_choice = np.random.choice([0, 1, 2, 3])
        if rot_choice == 1:
            image = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
            new_b = np.zeros_like(boxes)
            new_b[:, 0] = h - boxes[:, 3]
            new_b[:, 1] = boxes[:, 0]
            new_b[:, 2] = h - boxes[:, 1]
            new_b[:, 3] = boxes[:, 2]
            boxes = new_b
            h, w = w, h
        elif rot_choice == 2:
            image = cv2.rotate(image, cv2.ROTATE_180)
            boxes[:, [0, 2]] = w - boxes[:, [2, 0]]
            boxes[:, [1, 3]] = h - boxes[:, [3, 1]]
        elif rot_choice == 3:
            image = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
            new_b = np.zeros_like(boxes)
            new_b[:, 0] = boxes[:, 1]
            new_b[:, 1] = w - boxes[:, 2]
            new_b[:, 2] = boxes[:, 3]
            new_b[:, 3] = w - boxes[:, 0]
            boxes = new_b
            h, w = w, h

        if np.random.rand() > 0.3:
            alpha = np.random.uniform(0.85, 1.15)
            beta = np.random.uniform(-15, 15)
            image = np.clip(alpha * image + beta, 0, 255).astype(np.uint8)

        boxes[:, 0] = np.clip(boxes[:, 0], 0, w - 1)
        boxes[:, 2] = np.clip(boxes[:, 2], 0, w - 1)
        boxes[:, 1] = np.clip(boxes[:, 1], 0, h - 1)
        boxes[:, 3] = np.clip(boxes[:, 3], 0, h - 1)
        valid = (boxes[:, 2] > boxes[:, 0]) & (boxes[:, 3] > boxes[:, 1])
        return image, boxes[valid], labels[valid]

def parse_voc_xml(xml_path, class_to_idx=CLASS_TO_IDX):
    tree = ET.parse(xml_path)
    root = tree.getroot()
    boxes, labels = [], []
    for obj in root.findall("object"):
        name = obj.find("name").text.strip()
        canonical_name = None
        for key in class_to_idx.keys():
            if key.lower() in name.lower():
                canonical_name = key
                break
        if canonical_name is None:
            continue
        b = obj.find("bndbox")
        xmin = float(b.find("xmin").text)
        ymin = float(b.find("ymin").text)
        xmax = float(b.find("xmax").text)
        ymax = float(b.find("ymax").text)

        # Torchvision requires strictly positive-width/height boxes.
        if xmax <= xmin or ymax <= ymin:
            continue

        boxes.append([xmin, ymin, xmax, ymax])
        labels.append(class_to_idx[canonical_name])
    boxes = np.array(boxes, dtype=np.float32) if boxes else np.zeros((0, 4), dtype=np.float32)
    labels = np.array(labels, dtype=np.int64) if labels else np.zeros((0,), dtype=np.int64)
    return boxes, labels

class BloodSmearVOCDataset(Dataset):
    def __init__(self, root_dir, image_subdir="JPEGImages", annotation_subdir="Annotations",
                 img_size=640, is_train=False, use_stain_norm=True, use_clahe=True,
                 target_ref_img=None, class_to_idx=CLASS_TO_IDX):
        self.root_dir = root_dir
        self.img_size = img_size
        self.is_train = is_train
        self.class_to_idx = class_to_idx
        self.normalizer = ReinhardStainNormalizer(target_ref_img) if use_stain_norm else None
        self.use_clahe = use_clahe
        self.augmentor = BloodSmearAugmentor(is_train=is_train)
        img_dir = os.path.join(root_dir, image_subdir) if image_subdir else root_dir
        ann_dir = os.path.join(root_dir, annotation_subdir) if annotation_subdir else root_dir
        self.samples = []
        for ext in ["*.jpg", "*.jpeg", "*.png"]:
            for img_path in glob.glob(os.path.join(img_dir, ext)):
                base_id = os.path.splitext(os.path.basename(img_path))[0]
                xml_path = os.path.join(ann_dir, f"{base_id}.xml")
                if os.path.exists(xml_path):
                    self.samples.append((img_path, xml_path))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        img_path, xml_path = self.samples[idx]
        img_bgr = cv2.imread(img_path)
        if img_bgr is None:
            raise ValueError(f"Could not load image: {img_path}")
        boxes, labels = parse_voc_xml(xml_path, self.class_to_idx)
        if self.normalizer:
            img_bgr = self.normalizer.normalize(img_bgr)
        if self.use_clahe:
            img_bgr = apply_clahe(img_bgr)
        img_bgr, boxes, labels = self.augmentor(img_bgr, boxes, labels)
        orig_h, orig_w, _ = img_bgr.shape
        img_resized = cv2.resize(img_bgr, (self.img_size, self.img_size))
        if len(boxes) > 0:
            boxes[:, [0, 2]] *= (self.img_size / orig_w)
            boxes[:, [1, 3]] *= (self.img_size / orig_h)
        img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)
        if torch is not None:
            img_t = torch.from_numpy(img_rgb).permute(2, 0, 1).float() / 255.0
            return img_t, {"boxes": torch.as_tensor(boxes, dtype=torch.float32),
                           "labels": torch.as_tensor(labels, dtype=torch.int64),
                           "orig_size": torch.tensor([orig_h, orig_w])}
        return img_rgb, {"boxes": boxes, "labels": labels, "orig_size": (orig_h, orig_w)}

def blood_smear_collate_fn(batch):
    images, targets = list(zip(*batch))
    if torch is not None:
        images = torch.stack(images, dim=0)
    return images, targets

def convert_voc_to_yolo(voc_root, yolo_root, class_to_idx=CLASS_TO_IDX, val_ratio=0.15):
    os.makedirs(os.path.join(yolo_root, "images", "train"), exist_ok=True)
    os.makedirs(os.path.join(yolo_root, "images", "val"), exist_ok=True)
    os.makedirs(os.path.join(yolo_root, "labels", "train"), exist_ok=True)
    os.makedirs(os.path.join(yolo_root, "labels", "val"), exist_ok=True)
    dataset = BloodSmearVOCDataset(voc_root, is_train=False, use_stain_norm=False, use_clahe=False)
    indices = np.arange(len(dataset))
    np.random.seed(42)
    np.random.shuffle(indices)
    val_count = int(len(indices) * val_ratio)
    val_indices = set(indices[:val_count])
    for i, (img_path, xml_path) in enumerate(dataset.samples):
        subset = "val" if i in val_indices else "train"
        base_name = os.path.splitext(os.path.basename(img_path))[0]
        img = cv2.imread(img_path)
        h, w, _ = img.shape
        cv2.imwrite(os.path.join(yolo_root, "images", subset, f"{base_name}.jpg"), img)
        boxes, labels = parse_voc_xml(xml_path, class_to_idx)
        lines = []
        for box, lbl in zip(boxes, labels):
            yolo_cls = lbl - 1
            x_min, y_min, x_max, y_max = box
            xc, yc = ((x_min + x_max) / 2.0) / w, ((y_min + y_max) / 2.0) / h
            bw, bh = (x_max - x_min) / w, (y_max - y_min) / h
            lines.append(f"{yolo_cls} {xc:.6f} {yc:.6f} {bw:.6f} {bh:.6f}\n")
        with open(os.path.join(yolo_root, "labels", subset, f"{base_name}.txt"), "w") as f:
            f.writelines(lines)
    names_list = [k for k, v in sorted(class_to_idx.items(), key=lambda x: x[1])]
    yaml_content = f"path: {os.path.abspath(yolo_root)}\ntrain: images/train\nval: images/val\nnames:\n"
    for idx, name in enumerate(names_list):
        yaml_content += f"  {idx}: {name}\n"
    with open(os.path.join(yolo_root, "data.yaml"), "w") as f:
        f.write(yaml_content)
    print("VOC to YOLO conversion complete.")
