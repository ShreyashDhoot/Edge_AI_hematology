# Project Evidence Map: Edge-AI Hematology Screening

**Date:** 2026-09-29  
**Branch:** `improve/autonomous`  
**Target Paper:** `paper/paper.tex` / `paper/main.tex`  

---

## 1. Overview of Sections & Structure
- **Title & Authors:** YOLOv8n on Raspberry Pi 4 for resource-constrained hematology screening.
- **Section I (Introduction):** Context of CBC, cost of commercial analyzers ($30k-$200k), gap in low-resource settings, contributions (1. HW-SW edge pipeline, 2. Dual-tier CV + CLSI EP09c evaluation, 3. Analysis of impedance vs 2D morphology gap, 4. 72-image OOD benchmark).
- **Section II (Related Work):** Commercial analyzers (Sysmex, Beckman Coulter), Deep learning on blood smears (Liang 2018, Kc 2021, Liu 2022, Shakarami 2021), Edge deployment (INT8 ONNX).
- **Section III (Methodology):** Hardware platform (RPi 4B, HQ Camera, optical microscope), Software stack (Ultralytics, ONNX Runtime, OpenCV, ReportLab), Datasets (BCCD 364 images, 72-image OOD set), Model architecture (YOLOv8n 3.2M params), Quantization (dynamic INT8), Evaluation framework (Tier 1: CV metrics + Wilson CIs; Tier 2: CLSI EP09c Bland-Altman, Pearson r, Spearman rho, ICC(2,1), Passing-Bablok, Deming; Calibration: ECE).
- **Section IV (Results):** Detection performance on BCCD (Table I), Confusion matrix (Fig. 1), Agreement statistics on BCCD (Table II), Bland-Altman & Passing-Bablok plots (Fig. 2, 3), Reliability/Calibration (Fig. 4), Comparison with prior image-based methods (Table III), Commercial analyzer positioning (Table IV).
- **Section V (Discussion):** RBC counting and annotation incompleteness, Measurement-principle gap (impedance vs 2D morphology), Comparison limitations, Edge deployment viability.
- **Section VI (Conclusion) & References.**

---

## 2. Inventory of Experiments, Models, and Datasets

### Datasets
1. **BCCD Dataset:**
   - 364 test images with Pascal VOC annotations (`data/BCCD_r/BCCD/yolo_format`).
   - Ground truth: RBC (4155 boxes), WBC (372 boxes), Platelets (361 boxes).
   - Traceable in `paper_results/results.json`.
2. **Clinical 72-image OOD Dataset:**
   - 72 blood smear images from an independent staining protocol, annotated by a bioengineering student.
   - Files exist on the remote server (`./data/clinical_72/annotations/` [72 xml], `./data/clinical_72/images/` [364 jpeg]).
   - **Crucial finding:** Local folder `outputs/clinical_results/` ALREADY contains the full evaluation results: `YOLOv8n_Clinical72_evaluation_report.json` and `SSDLite_Clinical72_evaluation_report.json`!
   - Status: *Traceable* in `outputs/clinical_results/`.

### Models
1. **YOLOv8n (FP32):**
   - Weights: `runs/detect/outputs/checkpoints/yolov8n_hematology/weights/best.pt` (6.2 MB).
   - Parameters: ~3.2M. Architecture: Ultralytics YOLOv8n.
   - Status: *Traceable*.
2. **YOLOv8n (INT8 ONNX):**
   - Weights: `outputs/yolov8n_int8.onnx` (3.2 MB).
   - Exported and dynamically quantized via ONNX Runtime.
   - Status: *Traceable*.
3. **SSDLite MobileNetV3:**
   - Weights: `outputs/checkpoints/ssdlite_mobilenetv3_best.pth` and `ssdlite_mobilenetv3_hematology/weights/best.pt`.
   - Evaluated on Clinical 72 dataset in `outputs/clinical_results/SSDLite_Clinical72_evaluation_report.json`.
   - Status: *Traceable*.

---

## 3. Claim-to-Evidence Audit

| Claim in Paper | Source Location in Paper | Evidence File / Code | Status | Notes / Remediation |
|---|---|---|---|---|
| BCCD mAP@0.5 = 0.856, mAP@0.5:0.95 = 0.617 | Abstract, Sec. IV-A | `paper_results/results.json` line 62-63 | **Traceable** | Exact match: 0.85588, 0.61677 |
| Per-class F1: RBC=0.65, WBC=0.98, Platelets=0.84 | Abstract, Table I | `paper_results/results.json` line 12, 31, 50 | **Traceable** | Exact match: RBC=0.653, WBC=0.975, PLT=0.844 |
| WBC ICC(2,1) = 0.568, BA bias = 0.047 | Abstract, Table II | `paper_results/results.json` line 128, 137 | **Traceable** | Exact match: ICC=0.56788, bias=0.04670 |
| Platelet ICC(2,1) = 0.862, Pearson r = 0.871 | Abstract, Table II | `paper_results/results.json` line 176, 182 | **Traceable** | Exact match: r=0.87105, ICC=0.86197 |
| RBC ICC(2,1) = 0.112, bias = +10.6, MAPE = 101% | Sec. IV-C, Table II | `paper_results/results.json` line 74, 80, 83 | **Traceable** | Model has 4042 FP vs 3978 TP for RBC |
| System positions "substantially above published human baselines" | Abstract, Sec. IV-C | Literature cite only (Rümke 1985) | **Untraceable** | No local human-vs-human empirical data. Must weaken claim and clarify task difference. |
| 72-image OOD benchmark evaluated | Abstract, Sec. I, Sec. III-C, Sec. V-C | `outputs/clinical_results/YOLOv8n_Clinical72_evaluation_report.json` | **Traceable** | Evaluation exists in repo! Table I and text must be updated with real clinical_72 numbers. |
| YOLOv8n INT8 mAP ≈ 0.84 | Sec. IV-E, Table III | Estimated in text | **Probably traceable** | `outputs/yolov8n_int8.onnx` exists. Run local benchmark or state approximation clearly. |
| Raspberry Pi 4 latency ~245 ms (4.1 FPS), 3.4W | Sec. III-E, Sec. V-D | Code in `quantize_and_infer.py` | **Probably traceable** | Profiler exists in code. Need clear labeling whether measured on physical RPi or CPU emulation. |
| Sysmex / Beckman Coulter CV% and ICC numbers | Sec. II-A, Sec. IV-G, Table IV | `Comparison_Metrics_Notes (1).docx` | **Traceable** | Document cites Horiba 2022, Sysmex 2020, Briggs 2009. |
| Deming regression slopes (RBC=0.876, WBC=1.149, PLT=1.012) | Omitted from Table II | `paper_results/results.json` lines 116, 170, 224 | **Traceable** | Computed in code but omitted from Table II. Should be included. |
| Spearman rank correlations (RBC=0.461, WBC=0.583, PLT=0.843) | Omitted from Table II | `paper_results/results.json` lines 73, 127, 181 | **Traceable** | Computed in code but omitted from Table II. Should be included. |

---

## 4. Key Mismatches Between Code/Evidence and Paper Text
1. **OOD 72-image clinical results were completely omitted from Table I & Table II** despite `outputs/clinical_results/` having complete evaluation JSON reports for both YOLOv8n and SSDLite!
2. **"Our advisor" named in body text (Sec. IV-F, Sec. V-B):** Informal tone that violates blind review.
3. **5 BibTeX entries have incorrect types** (`@inproceedings` for journal articles, `@article` for CVPR).
4. **British and American English mixed:** 36 British vs 8 American words.
5. **RBC performance justification was purely speculative:** Needs honest presentation, demarcation of clinical counting limitations, and contrast with WBC/Platelet success.
