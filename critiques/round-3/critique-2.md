# 🔴 Round 3 Adversarial Scientific Audit — Independent Statistical & Evidence Review

> **Paper Focus:** Evaluation Validity, Claims vs. Evidence, Leakage Vulnerabilities, Selection Bias, and Edge Reproducibility.  
> **Target Manuscript:** `paper/paper.tex` (Post-Sync Revision).  

---

## 1. Adversarial Audit of Claims vs. Evidence

### 1.1 Integrity of Baseline vs. Generalization Narrative
- **The Evidence:** The paper maintains all baseline figures intact: BCCD mAP@0.5 = 0.856, Clinical 72 OOD mAP@0.5 = 0.412, WBC F1 = 0.83, Platelet recall = 0.10.
- **The Audit Finding:** The authors have completely refrained from fabricating post-retraining metrics. Section IV-H presents Table V with explicit `[[PENDING: T-G06]]` markers. This preserves absolute scientific integrity.
- **Adversarial Scrutiny:** While the authors do not claim unverified performance gains, Section III-D titles the new augmentation recipe as a *"Cross-Domain Generalization Recipe"*. An adversarial reviewer may argue: *"The authors call this a generalization recipe before presenting evidence that it actually improves cross-domain generalization."*  
- **Required Action:** Ensure all introductory and methodological references to the v2 model frame it as an *"Invariance-Augmented Training Pipeline"* or *"Proposed Adaptation Recipe"*, explicitly reserving the label *"Generalized"* until empirical validation is ingested.

---

## 2. Evaluation-Validity Gate: Critical Protocol Audits

### 2.1 The Clinical Fine-Tuning Leakage Risk (CRITICAL PROTOCOL CHECK)
- **The Vulnerability:** The authors implement a 50-train / 22-val clinical split in `prepare_clinical_split.py`. The paper text in Section III-D asserts: *"To prevent data leakage, fine-tuned models are evaluated strictly on the 22 held-out images."*
- **The Audit Finding:** In `eval_generalized.py` line 115, the evaluation script defaults to `args.clinical_dir` unless `--clinical_test_dir` is explicitly passed. If an investigator runs `eval_generalized.py` using only `--clinical_dir data/clinical_72`, the fine-tuned model would be evaluated across all 72 images, which contains 50 images used for training (a 69.4% training set contamination rate).
- **Adversarial Demand:** The orchestration script and `eval_generalized.py` must enforce that whenever evaluating fine-tuned weights (`yolov8n_hematology_v2_clinical`), the input path is strictly pointed to `outputs/generalized/clinical_split/images/val` (or VOC equivalent) to prevent accidental data leakage.

### 2.2 Comparability of Held-Out Split ($n=22$) vs. Zero-Shot Benchmark ($n=72$)
- **The Audit Finding:** Table V lists both the zero-shot baseline ($n=72$) and the few-shot adapted model ($n=22$) in the same table.
- **Adversarial Assessment:** Comparing a model evaluated on $n=22$ images against a baseline scored on $n=72$ images introduces sample composition bias. The 22 images in the random split may have higher or lower mean stain quality, cellular density, or focus sharpness than the full cohort.
- **Remediation:** To ensure strict mathematical comparability, when server task T-G06 executes, the baseline zero-shot model MUST also be evaluated on the exact same 22-image validation split, providing an apples-to-apples baseline row beside the 72-image cohort row.

### 2.3 Post-Hoc Threshold Provenance ($\tau_{\text{PLT}} = 0.15$)
- **The Audit Finding:** The paper honestly discloses in Section V-E (Limitations) that $\tau_{\text{PLT}} = 0.15$ was selected based on observed clinical false negatives.
- **Adversarial Assessment:** In clinical diagnostics, post-hoc threshold tuning without cross-validation on an independent calibration fold risks overfitting to specific smear idiosyncrasies. The authors' disclosure in Section V-E mitigates this, but a future cross-validation task should be logged.

---

## 3. Statistical Rigor and Edge Realism

### 3.1 TTA Latency vs. Operational Clinical Utility
- **The Evidence:** 4-rotation TTA incurs 4 sequential inferences per field. At 245 ms per forward pass on the Raspberry Pi 4B CPU, total inference latency rises to $\approx$980 ms per field ($\approx$1.02 FPS).
- **Adversarial Assessment:** The paper claims in Section III-B: *"Digital slide captures are resized... and streamed directly into the quantized inference pipeline."* At 1 FPS, streaming video is impossible; the system operates as a static frame-capture digitizer.
- **Remediation:** The authors have correctly added this trade-off to Section V-E. Ensure Section III-B clarifies that 4.1 FPS applies to single-pass live viewfinder mode, whereas 4-rotation TTA is engaged during static diagnostic report compilation.

### 3.2 Multi-Seed Variance (Seed=0 Vulnerability)
- **The Audit Finding:** All current baseline numbers stem from `seed=0`.
- **Adversarial Assessment:** Single-seed evaluation does not establish whether reported gains or drops are statistically significant or artifacts of weight initialization.
- **Remediation:** Execution of Server Task T-G02 (evaluating across seeds 0, 1, and 2) remains necessary to furnish empirical confidence intervals ($\pm \sigma$) for the final publication.

---

## 4. Overall Adversarial Verdict

**VERDICT: METHODOLOGICALLY PROTECTED; EMPIRICAL PIPELINE REQUIRES ISOLATION ENFORCEMENT.**

The paper is structurally defended against desk-rejection: it does not fabricate numbers, it labels pending results honestly, and it exposes its operational boundaries. Prior to camera-ready publication, the evaluation script must strictly isolate the 22-image validation split to guarantee zero data leakage.
