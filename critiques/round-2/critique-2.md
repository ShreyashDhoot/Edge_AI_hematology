# 🔴 Round 2 Adversarial Scientific Audit — Independent Statistical & Evidence Review

> **Paper Focus:** Evaluation Validity, Claims vs. Evidence, Statistical Rigor, and Edge Reproducibility.  
> **Target:** `paper/paper.tex` (Revised Version).  

---

## 1. Adversarial Audit of Claims vs. Evidence

### 1.1 The OOD Clinical Benchmark ($n=72$): Evidence vs. Narrative
- **The Evidence:** On the independent 72-image clinical benchmark, YOLOv8n achieves:
  - WBC: Precision = 0.95, Recall = 0.73, F1 = 0.83, AP@0.5 = 0.711.
  - RBC: Precision = 0.68, Recall = 0.51, F1 = 0.58, AP@0.435.
  - Platelets: Precision = 0.33, Recall = 0.10, F1 = 0.15, AP@0.5 = 0.091.
  - Overall mAP@0.5 = 0.412.
- **The Audit Finding:** The paper now reports these numbers with complete transparency in Table I and Section IV-A. This eliminates the fatal "undelivered promise" from Round 1.
- **Adversarial Critique:** In Section IV-A, the narrative notes that WBC precision remains 0.95, which is correct. However, platelet detection drops severely (F1 drops from 0.84 to 0.15, recall drops to 0.10). An adversarial reviewer will argue: "Platelet counting in uncurated smears fails completely. Can this device realistically contribute to thrombocytopenia screening in LMICs?"
- **Required Action:** The authors must explicitly state that the system in its present state serves as a **leukocyte screening tool** when applied across unseen clinical centers without prior stain normalization, while platelet triage requires either local stain normalization (e.g., Reinhard algorithm) or curated focal acquisition.

### 1.2 The RBC Disparity (ICC = 0.112, Bias = +10.62)
- **The Evidence:** 4,041 false positive background detections against 3,978 true positives.
- **The Audit Finding:** The revised paper honestly explains that BCCD ground truth contains an average of only 11.41 annotated cells per field, whereas standard 100$\times$ oil immersion fields contain 40–80 packed erythrocytes. The high model sensitivity (recall 0.96) catches unannotated cells, creating an additive over-count offset.
- **Adversarial Critique:** While biologically and methodologically sound, an adversarial reader will question whether any of those 4,041 detections represent non-cellular debris or stain precipitates.
- **Required Action:** Ensure the discussion explicitly suggests future architectural improvements, such as area-based cell density estimation or semantic contour segmentation, to replace bounding-box detection for dense erythrocyte monolayers.

---

## 2. Statistical Weakness and Methodological Integrity

### 2.1 Deming vs. Passing--Bablok Regression Integrity
- **The Audit Finding:** Table II now presents both Passing--Bablok slope (1.00 for all three classes) AND Deming orthogonal regression slope (0.876 for RBC, 1.149 for WBC, 1.012 for Platelets).
- **Adversarial Assessment:** The explanation in Section IV-D correctly attributes the P-B slope of 1.00 to discrete integer ties in low cell counts per field (mean WBC reference = 1.02 cells/field). This demonstrates high statistical integrity.

### 2.2 Lack of Cross-Validation and Seed Variance
- **The Audit Finding:** The model training relies on a single fixed split and seed=0.
- **Adversarial Assessment:** While common for edge deployment benchmarks with standardized splits (BCCD), multi-seed variance ($\pm \sigma$) on mAP should be documented.
- **Remediation:** Server Task T-04 is documented in `SERVER_TASKS.md` to compute multi-seed variance upon server execution.

---

## 3. Data Leakage and Reproducibility Check
- **Data Leakage:** Verified. The 72 clinical images were strictly held out and never seen during training or validation. The BCCD test split ($n=364$) was evaluated post-convergence.
- **Reproducibility:** Code and checkpoints are referenced, random seed is specified (seed=0), hyperparameters (SGD, momentum 0.937, weight decay 0.0005, cosine annealing) are completely documented in Section III-D.

---

## 4. Overall Adversarial Verdict

**STRONG REVISION — SCIENTIFICALLY SOUND.**  
The revised paper eliminates cherry-picking, reports real out-of-distribution numbers, contextualizes clinical claims honestly against literature standards, and conforms to rigorous statistical reporting conventions.
