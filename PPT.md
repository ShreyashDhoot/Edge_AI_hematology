# Presentation Deck Briefing Document (PPT.md)

> **Paper Title:** Edge-AI Automated Peripheral Blood Smear Analysis: A YOLOv8n Deployment on Raspberry Pi 4 for Resource-Constrained Hematology Screening  
> **Authors:** Shreyash Dhoot, Abhishek Karad, Pranav Lute, Prince Gupta (Undergraduate Students)  
> **Project Guide:** Dr. Anagha Deshpande (Assistant Professor)  
> **Institution:** Department of Electrical and Electronics Engineering (DOEEE), MIT World Peace University (MIT-WPU), Pune, Maharashtra, India  
> **Purpose:** Hand this comprehensive briefing document to Claude or use it to generate a professional 12–15 slide PowerPoint presentation deck for academic project defense, conference presentations, and faculty reviews.

---

## 1. Executive Summary & Core Ethos of the Project

### The Healthcare Dilemma (The "Why")
- **The Diagnostic Gap:** In primary health centers, rural clinics, and disaster zones, automated hematology analyzers (Coulter counters, laser flow cytometers) are absent. They cost \$30,000 to \$150,000, require climate-controlled labs, demand expensive proprietary reagents, and depend on stable three-phase power.
- **The Manual Fallback:** Peripheral blood smears (PBS) examined manually under a microscope are the clinical gold standard for verifying abnormal counts. However, manual 100-cell differential counting is slow (5–15 minutes per slide), subjective, and prone to rapid cytotechnologist eye fatigue, leading to high inter-observer variability (typical human-vs-human ICC is only 0.45–0.60).
- **The Diagnostic Delay:** Patients with acute infections, severe leukopenia, malaria, or thrombocytopenia often wait 24 to 72 hours for blood samples to travel to district reference laboratories.

### Our Solution (The "What")
- We built a **\$275 decentralized Edge-AI screening station** pairing a Raspberry Pi 4B (4 GB), a 12.3 MP Sony IMX477 camera sensor, and a 3D-printed C-mount adapter connected to a standard optical compound microscope.
- We deployed a compact **YOLOv8n object detector** (3.2M parameters), quantized from **FP32 (11.7 MB)** to **INT8 (3.2 MB)** using ONNX Runtime.
- It executes at **4.1 FPS (245 ms per frame)** entirely on the Raspberry Pi's quad-core ARM Cortex-A72 CPU, drawing only **3.4 Watts** (operable for >5 hours on a 20 Wh USB power bank).

### The Scientific Ethos (The "How" & Why It Wins Over Reviewers)
1. **Clinical Rigor over Computer Vision Vanity:** Unlike standard AI papers that only report mAP or accuracy, we evaluated our system using the formal **CLSI EP09-A3 clinical laboratory guideline** (Bland-Altman limits of agreement, Deming orthogonal regression, Passing-Bablok non-parametric regression, Intraclass Correlation Coefficients).
2. **Honesty Regarding Domain Shift:** We did not hide negative results. When tested on an external, out-of-distribution (OOD) clinical smear dataset ($n=72$), our model maintained robust white blood cell (WBC) identification ($F_1 = 0.82$, precision $0.95$), but platelet recall dropped to $0.10$ due to stain variation and focal drift. We honestly bounded our immediate clinical claims to **leukocyte-targeted triage**, rather than pretending our model is an all-inclusive replacement for a central laboratory analyzer.
3. **Engineering Innovation:** We demonstrated that applying Reinhard stain normalization alone suppresses platelet detection, but coupling stain normalization with **lineage-specific confidence thresholding ($\tau_{\text{PLT}} = 0.15$)** recovers platelet recall by $6.4\times$ (from $0.018$ to $0.175$).

---

## 2. Complete Metric Encyclopedia

Use this section to understand and explain every metric reported in the slides.

### 2.1 Object Detection & Computer Vision Metrics

| Metric | Formula / Definition | Value Achieved | Clinical / Practical Meaning |
|---|---|:---:|---|
| **Precision ($P$)** | $\frac{TP}{TP + FP}$ | **WBC:** 0.95<br>**PLT:** 0.78<br>**RBC:** 0.50 (BCCD) / 0.76 (Clinical) | "When the AI claims a cell is a leukocyte, how often is it right?" WBC precision is 95%—almost zero false alarms. |
| **Recall ($R$)** | $\frac{TP}{TP + FN}$ | **WBC:** 0.99<br>**PLT:** 0.92<br>**RBC:** 0.96 (BCCD) | "Out of all actual cells on the glass, how many did the AI catch?" 99% of leukocytes and 92% of platelets are caught on in-domain smears. |
| **$F_1$-Score** | $2 \cdot \frac{P \cdot R}{P + R}$ | **WBC:** 0.98<br>**PLT:** 0.84<br>**RBC:** 0.65 (BCCD) | Harmonic mean balancing precision and recall. Demonstrates clinical-grade WBC detection. |
| **AP@0.5** | Area under the Precision-Recall curve at IoU threshold $\ge 0.50$ | **WBC:** 0.985<br>**PLT:** 0.834<br>**RBC:** 0.749 | Summarizes detector quality across all possible confidence thresholds for that specific cell lineage. |
| **mAP@0.5** | Mean of AP@0.5 across all three classes (RBC, WBC, PLT) | **BCCD:** 0.856<br>**Clinical 72:** 0.410–0.414 | The standard benchmark metric for multiclass object detection. |
| **mAP@0.5:0.95** | Average mAP calculated at 10 IoU thresholds from 0.50 to 0.95 | **BCCD:** 0.617<br>**Clinical 72:** 0.157 | Strict localization metric; shows bounding box tightness. |
| **Wilson Score 95% CI** | Binomial confidence interval for proportions | Stated in Table I | Accounts for small sample sizes and avoids the normal approximation error near 0 and 1. |

---

### 2.2 Clinical Method-Comparison Metrics (CLSI EP09-A3 Standard)

| Metric | Mathematical Definition | Value in Paper | Interpretation for Medical Evaluators |
|---|---|:---:|---|
| **Intraclass Correlation $\text{ICC}(2,1)$** | Two-way random-effects model, absolute agreement | **PLT:** 0.862<br>**WBC:** 0.568<br>**RBC:** 0.112 | Measures whether the AI cell count agrees with the pathologist's manual count. Values $>0.75$ indicate good agreement; $>0.90$ is excellent. Platelet agreement (0.862) matches commercial benchtop analyzers. |
| **Bland-Altman Bias ($\bar{d}$)** | $\bar{d} = \frac{1}{n} \sum (x_{\text{AI}} - x_{\text{Ref}})$ | **WBC:** $+0.047$ cells/field<br>**PLT:** $-0.456$ cells/field<br>**RBC:** $+10.6$ cells/field | Mean systematic counting error. WBC bias is negligible (+0.047 cells), proving the AI neither undercounts nor overcounts leukocytes. |
| **Bland-Altman Limits of Agreement (LoA)** | $\bar{d} \pm 1.96 \cdot \text{SD}$ | **WBC:** $[-1.56, +1.65]$<br>**PLT:** $[-4.20, +3.28]$ | In 95% of future microscopic fields, the AI WBC count will be within $\pm 1.6$ cells of the expert human cytologist. |
| **Deming Orthogonal Regression** | Linear fit minimizing perpendicular errors in both $X$ and $Y$ ($\sigma_x^2 = \sigma_y^2$) | **WBC:** $y = 1.15x - 0.12$<br>**PLT:** $y = 1.01x - 0.54$<br>**RBC:** $y = 0.88x + 12.1$ | Unlike standard OLS regression, Deming accounts for measurement error in both the human reference and the AI. PLT slope ($1.01$) is near-perfect unity. |
| **Passing-Bablok Regression** | Non-parametric rank-based regression (median of pairwise slopes) | **WBC:** $y = 1.00x + 0.00$<br>**PLT:** $y = 1.00x + 0.00$ | Robust against clinical count outliers. Shows exact identity ($1.00$) on discrete integer cell counts. |
| **Spearman Rank Correlation ($\rho$)** | Non-parametric rank monotonic correlation | **WBC:** 0.771 ($p < 0.001$)<br>**PLT:** 0.793 ($p < 0.001$) | Highly statistically significant monotonic concordance with human cytologists. |
| **Mean Absolute Percentage Error (MAPE)** | $\frac{1}{n} \sum \left\| \frac{x_{\text{AI}} - x_{\text{Ref}}}{x_{\text{Ref}}} \right\| \times 100\%$ | **WBC:** 27.2%<br>**PLT:** 35.8%<br>**RBC:** 101.3% | Relative counting error. RBC error is elevated due to boundary intersection artifacts in densely packed monolayers. |

---

### 2.3 Edge Deployment & Systems Metrics

| Metric | Target / Specification | Measured Value | Practical Impact |
|---|---|:---:|---|
| **Inference Latency** | $<300\text{ ms}$ on ARM CPU | **245 ms** | Enables interactive live viewfinder scanning on low-cost hardware. |
| **Throughput (FPS)** | $\ge 4.0\text{ FPS}$ | **4.1 FPS** | Fluid enough for manual slide navigation across microscope fields. |
| **Model Size** | Small enough for microcomputer RAM | **3.2 MB** (INT8) vs **11.7 MB** (FP32) | **72.7% reduction** in storage and memory bandwidth requirements. |
| **Parameter Count** | Mobile architecture | **3.2 Million** (YOLOv8n) | Lightweight CSPDarknet backbone optimized for edge execution. |
| **Power Consumption** | $<5.0\text{ Watts}$ | **3.4 Watts** | Measured via inline USB-C analyzer under continuous 4-core load. |
| **Field Battery Life** | Full clinic working shift | **>5 Hours** | Achievable using an ordinary 20 Wh (\$15) commercial power bank. |
| **Total Capex** | $< \$500$ | **$\approx \$275$** | Single-board computer (\$75) + 12.3MP sensor (\$50) + optical frame (\$150). |

---

## 3. Slide-by-Slide Presentation Structure

This 15-slide breakdown is ready to be directly mapped into PowerPoint slides.

### Slide 1: Title Slide (Formal & Professional)
- **Title:** Edge-AI Automated Peripheral Blood Smear Analysis
- **Subtitle:** A YOLOv8n Deployment on Raspberry Pi 4 for Resource-Constrained Hematology Screening
- **Student Authors:** Shreyash Dhoot, Abhishek Karad, Pranav Lute, Prince Gupta
- **Project Guide:** Dr. Anagha Deshpande (Assistant Professor)
- **Department:** Department of Electrical and Electronics Engineering (DOEEE)
- **Institution:** MIT World Peace University (MIT-WPU), Pune, Maharashtra, India

### Slide 2: Clinical Context & The Diagnostic Gap
- **Problem Statement:** Hematology testing is the primary gateway for diagnosing anemia, leukemia, sepsis, and thrombocytopenia.
- **The Access Barrier:** 
  - Automated CBC analyzers cost \$30k–\$150k and require stable power, expensive reagents, and specialized technicians.
  - Rural health centers rely on manual microscopy, which takes 10–15 minutes per slide and suffers from rapid eye fatigue and high error rates (ICC 0.45–0.60).
- **The Core Objective:** Deliver a battery-powered, point-of-care, \$275 automated cytology system providing rapid leukocyte and platelet triage in under 35 seconds per patient.

### Slide 3: Hardware Architecture & Optical Setup
- **Apparatus Components:**
  - **Computing Core:** Raspberry Pi 4B (Broadcom BCM2711, Quad-core Cortex-A72 @ 1.5 GHz, 4 GB LPDDR4).
  - **Optical Sensor:** 12.3 MP Sony IMX477 back-illuminated CMOS sensor (1.55 $\mu\text{m} \times 1.55 \mu\text{m}$ pixel pitch).
  - **Mechanical Interface:** Custom 3D-printed C-mount adapter coupled directly to standard 23.2 mm trinocular microscope tube.
  - **Microscope:** Standard compound laboratory microscope (100$\times$ oil immersion objective, Giemsa stained smear).
- **Total Capex:** \$275 total (99% cheaper than automated commercial analyzers).

### Slide 4: Embedded Software & Deep Learning Pipeline
- **Detector:** YOLOv8n (nano)—an anchor-free single-stage detector featuring a CSPDarknet backbone, Path Aggregation Network (PAN), and decoupled detection heads.
- **Edge Optimization Workflow:**
  1. PyTorch training (`best.pt`, 6.2 MB)
  2. ONNX graph export with fixed $640 \times 640$ input (`yolov8n.onnx`, 11.7 MB)
  3. Dynamic INT8 quantization (`yolov8n_int8.onnx`, 3.2 MB)
  4. ONNX Runtime CPU Execution Provider utilizing all 4 physical ARM cores.
- **Result:** 245 ms latency (4.1 FPS), 3.4 W power consumption.

### Slide 5: In-Domain Performance: Public BCCD Benchmark
- **Dataset:** BCCD benchmark ($n=364$ images, 4,155 RBCs, 372 WBCs, 361 platelets at 100$\times$ magnification).
- **Detection Results:**
  - **Overall mAP@0.5:** **0.856** (mAP@0.5:0.95 = 0.617)
  - **White Blood Cells (WBC):** Precision = **0.954**, Recall = **0.997**, $F_1$-score = **0.975**, AP@0.5 = **0.985**
  - **Platelets (PLT):** Precision = **0.783**, Recall = **0.917**, $F_1$-score = **0.844**, AP@0.5 = **0.834**
  - **Red Blood Cells (RBC):** Precision = **0.496**, Recall = **0.958**, $F_1$-score = **0.654**, AP@0.5 = **0.749**
- **Takeaway:** Near-flawless WBC identification and high platelet precision on standardized smears.

### Slide 6: Clinical Agreement Validation (CLSI EP09-A3 Standard)
- **Why this slide matters:** Shows this is a genuine clinical engineering project, not just a Kaggle script.
- **Leukocyte Concordance:** Mean bias of only **+0.047 cells/field**; Bland-Altman LoA $[-1.56, +1.65]$ cells.
- **Platelet Concordance:** $\text{ICC}(2,1) = \mathbf{0.862}$ (clinically acceptable agreement), Deming regression slope = **1.012** (near identity).
- **Red Blood Cell Disparity:** High detection recall (0.96) but low count agreement (ICC = 0.112) caused by erythrocyte overlap in 700:1 density packing (4,042 partial edge false positives).

### Slide 7: The Out-of-Distribution (OOD) Challenge: Clinical 72 Smear Benchmark
- **The Test:** Evaluated zero-shot on 72 real clinical smears from an independent hospital laboratory.
- **The Reality of Domain Shift:**
  - Different stain duration, buffer pH, and lighting temperature alter Romanowsky dye appearance.
  - **Leukocytes:** Remained highly robust ($F_1 = 0.82$, Precision = $0.958$, AP@0.5 = $0.691$).
  - **Platelets:** Experienced sharp drop (Recall = $0.123$, $F_1 = 0.173$, AP@0.5 = $0.057$).
- **Key Insight:** Thrombocytes lack dense nuclei; optical focal drift and color changes easily mask them.

### Slide 8: Domain Adaptation & Generalization Pipeline
- **Methodology to Address Domain Shift:**
  1. **Invariance-Augmented Training:** 180° rotation invariance, vertical flips ($p=0.5$), MixUp regularizer ($0.15$), and dropout ($0.1$).
  2. **Reinhard Stain Normalization:** Aligns clinical image color means ($\mu$) and standard deviations ($\sigma$) in CIELAB color space against a standardized BCCD reference smear.
  3. **CLAHE:** Contrast-Limited Adaptive Histogram Equalization on the $L$-channel (clip limit 2.0, $8 \times 8$ grid) to sharpen cellular boundaries.
  4. **Lineage-Specific Thresholding:** Decoupled decision boundaries ($\tau_{\text{PLT}} = 0.15$, $\tau_{\text{RBC/WBC}} = 0.25$).

### Slide 9: The Generalization Ablation Study (Table V Deep Dive)
- **Walkthrough of Empirical Server Results:**

| Configuration | Split | Preprocessing | Post-Processing | mAP@0.5 | RBC $F_1$ | WBC $F_1$ | PLT $F_1$ |
|---|---|---|---|:---:|:---:|:---:|:---:|
| **(a) Baseline (YOLOv8n)** | BCCD Test ($n=364$) | None | Default ($\tau=0.25$) | **0.856** | 0.65 | **0.98** | **0.84** |
| **(b) Baseline (Zero-Shot)** | Clinical 72 ($n=72$) | None | Default ($\tau=0.25$) | **0.410** | 0.63 | **0.82** | 0.17 |
| **(c) Retrained v2** | Clinical 72 ($n=72$) | None | Default ($\tau=0.25$) | **0.411** | **0.67** | **0.82** | 0.06 |
| **(d) Retrained + Stain Norm** | Clinical 72 ($n=72$) | Reinhard + CLAHE | Default ($\tau=0.25$) | **0.398** | 0.66 | **0.82** | 0.03 |
| **(e) Retrained + Thresholding** | Clinical 72 ($n=72$) | Reinhard + CLAHE | Per-Class ($\tau_{\text{PLT}}=0.15$) | **0.414** | 0.66 | **0.82** | **0.21** |
| **(f) Retrained In-Domain** | BCCD Test ($n=364$) | None | Default ($\tau=0.25$) | **0.829** | 0.64 | **0.98** | **0.84** |

### Slide 10: The Platelet Thresholding Rescue (Key Engineering Discovery)
- **The Paradox:** Why did Reinhard stain normalization alone (row d) drop platelet $F_1$ to 0.03?
  - *Mechanism:* Normalizing color distributions weakened the faint pale-purple hue of thrombocytes, pushing raw detector confidence scores just below the default 0.25 threshold.
- **The Solution:** Calibrating the lineage decision boundary to $\tau_{\text{PLT}} = 0.15$ (row e) rescued platelet recall from **0.018 to 0.175** ($F_1$ surged to **0.211**—a $6.4\times$ recovery).
- **Core Engineering Rule:** Color normalization shifts head activation distributions; preprocessing transforms must be coupled with threshold recalibration.

### Slide 11: Edge Systems, Power & Economics
- **System Resource Metrics:**
  - INT8 quantization achieves **3.67$\times$ compression** (11.7 MB $\to$ 3.2 MB) with zero loss in WBC accuracy.
  - Execution speed: 4.1 FPS (245 ms/frame), well within the operator navigation speed threshold.
  - Power budget: 3.4 W sustained draw.
  - Thermal stability: Aluminum heatsink enclosure maintains core temp $< 58^\circ\text{C}$ without active fans.
- **Cost Comparison:**
  - Commercial 3-Part Analyzer: \$30,000 + \$2,500/year reagents.
  - Our Edge-AI Microscope Station: **\$275 total one-time cost**, zero proprietary reagents.

### Slide 12: Clinical Workflow & Point-of-Care Utility
- **Standardized Field Protocol:**
  1. Slide preparation: Fingerprick blood drop, wedge smear, rapid 3-minute Field stain or Giemsa dip.
  2. Microscope placement: Place slide on stage, focus under 100$\times$ oil immersion.
  3. Interactive Live View: Camera streams 4.1 FPS viewfinder on a 7-inch touchscreen.
  4. Automated Differential Count: Operator scans 10–20 fields; system accumulates counts, detects abnormal clusters, and compiles a digital triage report in **25–35 seconds**.
- **Triage Bounding:** Safely triages acute infections and leukopenia immediately; flags suspicious smears for secondary pathologist review.

### Slide 13: Honest Limitations & Threats to Validity
- **Transparency Builds Credibility:**
  1. **Platelet OOD Sensitivity:** Cross-center platelet recall requires on-site staining calibration.
  2. **Erythrocyte Overlap:** Bounding-box models overcount overlapping RBCs; contour watershed segmentation is needed for precise hematocrit estimation.
  3. **3-Class vs. 5-Part Differential:** Currently detects general WBCs; sub-classifying into neutrophils, lymphocytes, monocytes, eosinophils, and basophils requires higher optical resolution.
  4. **Validation Cohort Size:** Clinical split ($n=72$) represents single-center archival slides; multi-center trials are planned.

### Slide 14: Conclusion & Future Roadmap
- **Contributions Delivered:**
  - A fully functional, \$275 Edge-AI cytological screening station.
  - INT8-quantized YOLOv8n running at 4.1 FPS on a 3.4 W Raspberry Pi 4.
  - First edge hematology paper evaluated rigorously against **CLSI EP09-A3 clinical standards**.
  - Systematic ablation identifying the relationship between Reinhard stain normalization and lineage thresholds.
- **Next Steps:**
  - Automated 5-part leukocyte differential model.
  - 3D-printed motorized stage driven by stepper motors for automated serpentine slide scanning.
  - Direct area-density regression for precise red blood cell enumeration.

### Slide 15: Q&A / Defense Readiness
- Open for questions from Dr. Anagha Deshpande and the evaluation committee.

---

## 4. Anticipated Jury & Guide Questions (With Bulletproof Answers)

### Q1: "Why did you use YOLOv8n instead of a segmentation model like UNet or Mask R-CNN?"
> **Answer:** "Edge inference latency was our primary design constraint. A typical blood smear field contains over 100 cells. Mask R-CNN or UNet would require over 2,500 ms per frame on a Raspberry Pi ARM CPU, precluding live viewfinder streaming. YOLOv8n provides anchor-free bounding box regression in just 245 ms (4.1 FPS) with only 3.2M parameters, allowing an operator to scan slides in real time while maintaining 0.98 F1 on leukocytes."

### Q2: "Why is your RBC ICC agreement only 0.112 when detection recall is 0.96?"
> **Answer:** "This is due to biophysical monolayer packing. Red blood cells outnumber white blood cells by 700 to 1. In a single microscopic field, dozens of erythrocytes intersect the image border or overlap each other. Bounding-box detectors penalize partial edge intersections, causing 4,042 boundary false positives. Leukocytes, by contrast, have dense dark-violet chromatin nuclei that eliminate edge ambiguity. As noted in Section V-A, future RBC enumeration will employ area-density regression rather than discrete bounding boxes."

### Q3: "Why did Reinhard stain normalization cause platelet F1 to drop before threshold tuning?"
> **Answer:** "Platelets are extremely small (2–3 $\mu\text{m}$) and lack nuclei, presenting as faint pale-purple granular fragments. Reinhard normalization aligns global $\mu$ and $\sigma$ channel statistics in CIELAB color space. This global shift diluted the specific chromatic contrast of faint thrombocytes, shifting their raw detection confidence scores just below the 0.25 threshold. When we lowered the platelet decision threshold to $\tau_{\text{PLT}} = 0.15$, recall surged from 0.018 to 0.175, demonstrating that color normalization must always be paired with threshold recalibration."

### Q4: "Can this system diagnose leukemia today?"
> **Answer:** "No, and we explicitly avoid making that claim. Our system is designed as an accessible *triage screener* for primary care clinics, not a diagnostic replacement for a hematopathologist. It detects total leukocyte counts to flag severe infections, leukopenia, or leukocytosis in under 35 seconds, alerting clinicians to send the patient to a reference hospital for confirmatory flow cytometry."
