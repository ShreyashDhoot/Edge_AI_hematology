# Changelog — Round 4 (Final Paper Submission & Empirical Ingestion)

**Date:** 2026-09-29  
**Branch:** `improve/autonomous`  
**Review Round:** Round 4 (Final Sign-Off)  
**Project Guide:** Dr. Anagha Deshpande (Assistant Professor, Dept. of DOEEE, MIT-WPU)  
**Authors:** Shreyash Dhoot, Abhishek Karad, Pranav Lute, Prince Gupta (Students, Dept. of DOEEE, MIT-WPU)  

---

## 1. Summary of Changes in Round 4

| Change Category | Details | Status |
|---|---|:---:|
| **Authorship & Affiliation** | Updated author block in `paper.tex` with all student authors and project guide Dr. Anagha Deshpande (Department of Electrical and Electronics Engineering, MIT World Peace University, Pune). | **Done** |
| **Faculty Acknowledgment** | Updated `\section*{Acknowledgment}` to express deep gratitude to Dr. Anagha Deshpande for supervision, mentorship, and guidance throughout the project. | **Done** |
| **Empirical Ingestion** | Replaced all `[[PENDING: T-G06]]` cells in Table V with verified empirical metrics from `server/results/T-G06/generalized_results.json`. | **Done** |
| **Ablation Discussion** | Rewrote Section IV-H in concise student voice (`paper-writing` skill) explaining leukocyte chromatin stability, erythrocyte gain under invariance augmentations, and the essential interaction between Reinhard stain normalization and lineage-specific thresholding ($\tau_{\text{PLT}}=0.15$). | **Done** |
| **Prose Concision** | Tightened Sections IV-H, V-A, V-B, and V-C, cutting padding words and ensuring the entire manuscript with bibliography fits within exactly 8.0 pages. | **Done** |
| **LaTeX Compilation** | Compiled to 8 pages with **0 errors and 0 overfull hboxes**. | **Done** |

---

## 2. Ingested Empirical Metrics (Table V)

| Configuration | Split | Preprocessing | Post-Processing | mAP@0.5 | RBC F1 | WBC F1 | PLT F1 |
|---|---|---|---|:---:|:---:|:---:|:---:|
| (a) Baseline (YOLOv8n) | BCCD Test ($n=364$) | None | Default ($\tau=0.25$) | 0.856 | 0.65 | 0.98 | 0.84 |
| (b) Baseline (Zero-Shot) | Clinical 72 ($n=72$) | None | Default ($\tau=0.25$) | 0.410 | 0.63 | 0.82 | 0.17 |
| (c) Retrained (v2 Augmentations) | Clinical 72 ($n=72$) | None | Default ($\tau=0.25$) | 0.411 | 0.67 | 0.82 | 0.06 |
| (d) Retrained v2 + Stain Norm | Clinical 72 ($n=72$) | Reinhard + CLAHE | Default ($\tau=0.25$) | 0.398 | 0.66 | 0.82 | 0.03 |
| (e) Retrained v2 + Thresholding | Clinical 72 ($n=72$) | Reinhard + CLAHE | Per-Class ($\tau_{\text{PLT}}=0.15$) | 0.414 | 0.66 | 0.82 | 0.21 |
| (f) In-Domain Retrained v2 | BCCD Test ($n=364$) | None | Default ($\tau=0.25$) | 0.829 | 0.64 | 0.98 | 0.84 |
