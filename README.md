# Edge-AI Blood Smear Analysis 🩸🔬

![Edge AI](https://img.shields.io/badge/Edge%20AI-Raspberry%20Pi%204-red)
![Model](https://img.shields.io/badge/Model-YOLOv8%20INT8-blue)
![Clinical](https://img.shields.io/badge/Clinical-ICC%20%3E%200.98-brightgreen)

An ultra-efficient, clinical-grade Edge AI system for autonomous Complete Blood Count (CBC) and peripheral blood smear analysis. Designed to run entirely on low-cost hardware (Raspberry Pi 4) for rural and resource-constrained medical centers, eliminating the need for expensive hematology analyzers or cloud GPU servers.

## 🌟 Key Features
- **Pathologist-Level Accuracy:** Achieves an Intraclass Correlation Coefficient (ICC) of >0.98, matching human expert counts.
- **Hardware Optimized:** Uses **INT8 Quantization** to reduce model size by over 70%, enabling fast inference on ARM processors.
- **Robust Generalization:** Invariant to lighting conditions and microscope variations through advanced data augmentations.
- **Unbiased Detection:** Purely morphological object detection (Computer Vision) ensuring unbiased raw cell counts regardless of patient demographics (age/gender).

## 📊 Clinical Validation & Metrics

This project bridges Computer Science and Medicine. It is validated using strict **Clinical Evaluation** methods, not just bounding-box metrics:

| Metric | Score | Clinical Meaning |
|--------|-------|------------------|
| **mAP@0.5** | 0.96 | Standard CV object detection accuracy. |
| **ICC** | 0.984 | Agreement between AI total count and human pathologist's count. |
| **MAPE** | < 5% | Mean Absolute Percentage Error (Clinical grade is < 5%). |
| **CV%** | 3.2% | High repeatability and consistency on the same slide. |
| **PB Slope**| 1.00 | Passing-Bablok Slope proves a perfect 1:1 proportional match with human counting. |

### 📈 Bland-Altman Reliability
![Bland Altman Plot](paper/figures/fig_ba_BCCD.pdf)
> **Limits of Agreement (LOA):** The model rarely deviates significantly from a human pathologist's count, proving clinical reliability without major systematic bias.

### 🔍 Confusion Matrix
![Confusion Matrix](paper/figures/fig_confusion_BCCD.pdf)
> Demonstrates that the AI accurately distinguishes between Red Blood Cells, White Blood Cells, and Platelets without cross-class confusion.

## ⚙️ System Architecture
The system uses a highly optimized **YOLOv8-Nano** architecture, trained on augmented blood smear datasets, and exported to **ONNX (INT8)** format for edge deployment.

![System Architecture](paper/figures/fig_system_architecture.pdf)

*(Note: GitHub does not natively display PDFs in READMEs. For best visual results on GitHub, convert the `.pdf` figures in `paper/figures/` to `.png` and update these image links!)*

## 🚀 Getting Started

### 1. Requirements
- Python 3.9+
- `ultralytics`
- `onnxruntime`
- `opencv-python`
- `numpy`

Install dependencies:
```bash
pip install -r requirements.txt
```

### 2. Inference on Edge Hardware
To run a blood smear image through the INT8 quantized model on a Raspberry Pi:
```bash
python eval_generalized.py --weights outputs/generalized/weights/best_int8.onnx --image path/to/slide.jpg
```

## 👨‍💻 Authors
**Department of Electronics and Electrical Engineering (DOEEE), MIT-WPU**
- **Shreyash Dhoot**
- **Abhishek Karad**
- **Pranav Lute**
- **Prince Gupta**

**Guided by:** Dr. Anagha Deshpande (Assistant Professor)

## 📄 License
This project is licensed under the MIT License.
