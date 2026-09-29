# Edge-AI-Based Automated Haematology Screening System

A deployment-ready Edge-AI deep learning repository for automated peripheral blood smear cytological detection, cell counting, and clinical diagnostic triage on resource-constrained embedded systems (Raspberry Pi 4 Model B).

Developed for **MIT World Peace University (Pune, India)** Capstone Research.

---

## 1. System Architecture & Hardware Setup
* **Edge Compute Platform:** Raspberry Pi 4 Model B (4GB / 8GB RAM, Broadcom BCM2711 quad-core Cortex-A72 @ 1.5 GHz).
* **Imaging Sensor:** Raspberry Pi High-Quality (HQ) Camera (12.3 MP Sony IMX477, 1.55um x 1.55um pixel pitch, CSI-2 interface).
* **Microscope Interface:** Compound Optical Microscope with C-mount to 23.2mm eyepiece adapter (100x Oil Immersion Objective).
* **Software Stack:** PyTorch 2.0+, ONNX Runtime 1.15+ (INT8 Quantization), OpenCV, ReportLab.

---

## 2. Repository Structure
```
edge_hematology_ai/
├── dataset.py               # VOC/YOLO dataset loader, Reinhard stain norm, CLAHE, augmentations
├── losses.py                # Alpha-balanced Focal Loss and Complete IoU (CIoU)
├── models/
│   ├── __init__.py          # Factory registry for edge models
│   ├── yolov8_model.py      # YOLOv8n / YOLOv11n Ultralytics edge integration
│   ├── ssdlite_mobilenetv3.py # SSDLite with MobileNetV3-Large & tuned cytological anchors
│   └── picodet_model.py     # PP-PicoDet-S lightweight ARM CPU architecture
├── train.py                 # Multi-model training script with early stopping & Cosine Annealing
├── quantize_and_infer.py    # ONNX export, INT8 Post-Training Quantization, and RPi profiler
├── metrics_evaluation.py    # Dual-tier CV (mAP) + Clinical (Bland-Altman, Pearson r, Passing-Bablok)
├── generate_report.py       # Clinical diagnostic triage PDF generator with visual explainability
├── test_pipeline.py         # End-to-end verification test suite
├── requirements.txt         # Environment dependencies
└── outputs/                 # Checkpoints, evaluation reports, plots, and PDF summaries
```

---

## 3. Resolving the Advisor's Dilemma: The Dual-Tier Evaluation Suite
Clinical automated hematology analyzers (Coulter counters / Flow cytometers) measure liquid cell volume and impedance, whereas microscopic vision models detect 2D spatial morphology on thin smears. To satisfy academic and clinical standards (CLSI EP09 guidelines), this repository evaluates:

1. **Computer Vision Tier:**
   - mAP@0.5 and mAP@0.5:0.95
   - Per-class Precision, Recall, and F1-Score
2. **Clinical Hematology Equivalence Tier:**
   - **Bland-Altman Agreement:** Mean Bias and 95% Limits of Agreement (LoA).
   - **Linearity & Correlation:** Pearson correlation ($r$) and Spearman rank ($ho$).
   - **Passing-Bablok Non-Parametric Regression:** Slope ($B$, proportional error) and Intercept ($A$, constant bias).
   - **Differential Leukocyte Count (DLC %):** Relative leukocyte distribution.

---

## 4. How to Use the 72 Bio-Engineering Labeled Images
**Do NOT train on the 72 hand-annotated images.**
Use them strictly as an **Independent External Validation / Out-of-Distribution (OOD) Benchmark**:
1. Train models on public datasets (BCCD / Kaggle Blood Cell Count).
2. Evaluate directly on the 72 unseen images to quantify cross-staining and cross-camera generalization.
3. Compute Inter-Annotator Agreement (Cohen's Kappa) against human baseline variance.

---

## 5. Quickstart & Execution

### Installation
```bash
pip install -r requirements.txt
```

### Run Verification Test
```bash
python test_pipeline.py
```

### Model Training
```bash
# Train YOLOv8n with Early Stopping and Weight Decay
python train.py --model yolov8n --data_dir data/BCCD --epochs 100 --batch_size 16

# Train SSDLite-MobileNetV3
python train.py --model ssdlite_mobilenetv3 --data_dir data/BCCD --epochs 80 --batch_size 8
```

### Model Quantization & Profiling
```bash
python -c "
import quantize_and_infer as qi
qi.quantize_onnx_to_int8('outputs/model_fp32.onnx', 'outputs/model_int8.onnx')
profile = qi.profile_edge_inference('outputs/model_int8.onnx')
print('Raspberry Pi 4 Inference Profile:', profile)
"
```
