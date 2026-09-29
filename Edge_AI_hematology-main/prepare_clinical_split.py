import os
import argparse
import random
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import defaultdict

CLASS_MAPPING = {
    'rbc': 0,
    'wbc': 1,
    'platelets': 2
}

def parse_voc_xml(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    size = root.find('size')
    width = int(size.find('width').text)
    height = int(size.find('height').text)
    
    boxes = []
    for obj in root.findall('object'):
        name = obj.find('name').text.lower().strip()
        if name not in CLASS_MAPPING:
            continue
            
        class_id = CLASS_MAPPING[name]
        bndbox = obj.find('bndbox')
        xmin = float(bndbox.find('xmin').text)
        ymin = float(bndbox.find('ymin').text)
        xmax = float(bndbox.find('xmax').text)
        ymax = float(bndbox.find('ymax').text)
        
        # Convert to YOLO format (cx, cy, w, h) normalized
        dw = 1.0 / width
        dh = 1.0 / height
        # Pascal VOC is 1-indexed, but usually 0-indexed works similarly. Adjusting minimally.
        x = (xmin + xmax) / 2.0
        y = (ymin + ymax) / 2.0
        w = xmax - xmin
        h = ymax - ymin
        
        x = x * dw
        w = w * dw
        y = y * dh
        h = h * dh
        
        boxes.append((class_id, x, y, w, h))
        
    return boxes

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--clinical_dir', type=str, required=True, help='Path to clinical_72 directory')
    parser.add_argument('--output_dir', type=str, default='data/clinical_split')
    parser.add_argument('--train_ratio', type=float, default=0.7)
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args()
    
    random.seed(args.seed)
    
    clinical_dir = Path(args.clinical_dir)
    images_dir = clinical_dir / 'images'
    annotations_dir = clinical_dir / 'annotations'
    
    if not images_dir.exists() or not annotations_dir.exists():
        print(f"Error: Could not find images/ and annotations/ in {clinical_dir}")
        return
        
    # Discover matching files
    image_files = []
    for ext in ['.jpg', '.png', '.jpeg']:
        image_files.extend(list(images_dir.glob(f'*{ext}')))
        image_files.extend(list(images_dir.glob(f'*{ext.upper()}')))
        
    valid_pairs = []
    for img_path in image_files:
        xml_path = annotations_dir / f"{img_path.stem}.xml"
        if xml_path.exists():
            valid_pairs.append((img_path, xml_path))
            
    print(f"Found {len(valid_pairs)} image-annotation pairs.")
    
    # Shuffle and split
    random.shuffle(valid_pairs)
    split_idx = int(len(valid_pairs) * args.train_ratio)
    train_pairs = valid_pairs[:split_idx]
    val_pairs = valid_pairs[split_idx:]
    
    # Create YOLO dirs
    out_dir = Path(args.output_dir)
    for split in ['train', 'val']:
        (out_dir / 'images' / split).mkdir(parents=True, exist_ok=True)
        (out_dir / 'labels' / split).mkdir(parents=True, exist_ok=True)
        
    class_counts = {'train': defaultdict(int), 'val': defaultdict(int)}
    
    def process_split(pairs, split_name):
        for img_path, xml_path in pairs:
            # Copy image
            dest_img = out_dir / 'images' / split_name / img_path.name
            shutil.copy(img_path, dest_img)
            
            # Parse XML and save YOLO txt
            boxes = parse_voc_xml(xml_path)
            dest_txt = out_dir / 'labels' / split_name / f"{img_path.stem}.txt"
            
            with open(dest_txt, 'w') as f:
                for box in boxes:
                    class_id, x, y, w, h = box
                    f.write(f"{class_id} {x:.6f} {y:.6f} {w:.6f} {h:.6f}\n")
                    # Update counts
                    for name, id_ in CLASS_MAPPING.items():
                        if class_id == id_:
                            class_counts[split_name][name] += 1
                            
    process_split(train_pairs, 'train')
    process_split(val_pairs, 'val')
    
    # Generate data.yaml
    # We use forward slashes for paths in YOLO data.yaml
    out_dir_posix = out_dir.absolute().as_posix()
    yaml_content = f"""path: {out_dir_posix}
train: images/train
val: images/val

names:
  0: RBC
  1: WBC
  2: Platelets
"""
    with open(out_dir / 'data.yaml', 'w') as f:
        f.write(yaml_content)
        
    print(f"\\nCreated YOLO dataset at {out_dir}")
    print(f"Train images: {len(train_pairs)}")
    print(f"Val images: {len(val_pairs)}")
    
    print("\\nClass instance counts:")
    print("Train:")
    for k, v in class_counts['train'].items():
        print(f"  {k.upper()}: {v}")
    print("Val:")
    for k, v in class_counts['val'].items():
        print(f"  {k.upper()}: {v}")

if __name__ == "__main__":
    main()
