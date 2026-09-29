# Improvement Log (Ledger)

**Run:** Autonomous Improvement Loop  
**Repository:** Edge_AI_hematology-main  
**Branch:** `improve/autonomous`  

## Run 2 Start State (2026-09-29)

- **Loop Status:** Round 1 and Round 2 critiques completed. Round 1 issues R1-C01 through R1-C22 processed.
- **Ledger Status:** 20/22 items marked Done; R1-C02 awaiting paired human server results; R1-C04 empirical mAP integrated.
- **Round 2 Critiques:** Both `critique.md` (Prof. [Guide]) and `critique-2.md` (Adversarial) acknowledge substantial improvement and scientific honesty, noting remaining weaknesses:
  1. OOD clinical platelet collapse (AP@0.5 = 0.091, Recall = 0.098) requires explicit bounding as leukocyte-primary triage or stain normalization.
  2. Single seed variance (seed=0) without multi-seed confidence bounds.
  3. Server tasks T-01 to T-05 pending server execution.
- **New Code / Pipeline Status:** Code was modified in `Edge_AI_hematology-main/` to introduce generalization features (rotation 180°, flipud 0.5, mixup 0.15, copy-paste 0.15, dropout 0.1, stain normalization, 4-rotation TTA, per-class thresholding, and clinical split fine-tuning), documented in `change.md`.
- **Pipeline Execution & Results Status:**
  - On the remote server, initial execution of `retrain_and_evaluate.py` encountered an OpenCV headless library issue (`libxcb.so.1`) and CLI argument mismatch which were fixed. The remote server has not yet completed full retraining and evaluation across all clinical sets.
  - A local preliminary run exists in `Edge_AI_hematology-main/outputs/generalized/` evaluating BCCD test set only (`n_clin=0` because clinical data is on server). Crucially, the retrained model `b_v2_bccd` shows an empirical drop in in-domain BCCD mAP@0.5 from 0.856 to 0.581, with platelet AP@0.5 collapsing from 0.834 to 0.005 under heavy unguided augmentations.
  - No valid, complete cross-domain evaluation results from the new pipeline exist yet.
  - Per the non-negotiable rules: baseline numbers remain untouched; the paper is updated to reflect the new pipeline and methods factually; all new results remain marked `PENDING`.

---

## Issue Registry (Round 1)

| ID | Severity | Critique Source | Category / Issue | Label | Status | What Changed / What's Pending |
|---|---|---|---|---|---|---|
| R1-C01 | FATAL | Crit. 1 §1.3, Crit. 2 §A | 72-image OOD benchmark promised 4 times, no results presented | EXISTING | Done | Integrated empirical metrics from `outputs/clinical_results/YOLOv8n_Clinical72_evaluation_report.json` into Table I and Sec. IV-A. |
| R1-C02 | FATAL | Crit. 1 §1.2, Crit. 2 §E | "Better than human" claim unsupported by direct empirical evidence on task | FIX / SERVER | Awaiting server results | Rewrote all claims honestly; contextualized against literature (Rümke 1985); added Server Task T-03 for direct paired study. |
| R1-C03 | FATAL | Crit. 1 §1.1, Crit. 2 §E | RBC ICC=0.112, bias=+10.6, MAPE=101% excused without proof | FIX | Done | Provided transparent biological & optical density analysis; documented 4042 FP vs 3978 TP boundary intersections. |
| R1-C04 | FATAL | Crit. 1 §1.4, Crit. 2 §E | INT8 mAP reported as estimated "≈ 0.84" | FIX / SERVER | Done | Replaced with measured mAP=0.840 in Table III and Sec. IV-E; logged Server Task T-01 for multi-metric profiling. |
| R1-C05 | FATAL | Crit. 1 §5.1, Crit. 2 §L | 5/15 BibTeX entries have incorrect types; 0 DOIs | FIX | Done | Corrected `@article`, `@inproceedings`, `@incollection` types; added verified DOIs; fixed BCCD citation. |
| R1-C06 | MAJOR | Crit. 1 §3.3, Crit. 2 §F | "Our advisor" referenced in body text (Sec. IV-F, Sec. V-B) | FIX | Done | Removed all informal advisor references; replaced with rigorous academic terminology. |
| R1-C07 | MAJOR | Crit. 1 §4, Crit. 2 §H | IEEE spelling: "Acknowledgements" should be "Acknowledgment" | FIX | Done | Changed section heading to `\section*{Acknowledgment}` per IEEE style. |
| R1-C08 | MAJOR | Crit. 1 §4, Crit. 2 §H | Figure references use "Figure" instead of "Fig." | FIX | Done | Replaced all instances with `Fig.~\ref{}`. |
| R1-C09 | MAJOR | Crit. 1 §4, Crit. 2 §H | Keywords not alphabetized | FIX | Done | Alphabetized IEEE keywords list. |
| R1-C10 | MAJOR | Crit. 1 §4.1, Crit. 2 §I | Coloured hyperlinks in B&W print venue | FIX | Done | Set `\hypersetup{hidelinks}` for camera-ready IEEE compliance. |
| R1-C11 | MAJOR | Crit. 1 §3.2, Crit. 2 §G | Mixed British and American English (36 British vs 8 American) | FIX | Done | Standardized to 100% American English throughout. |
| R1-C12 | MAJOR | Crit. 1 §3.1, Crit. 2 §G | Abstract word count 245 words (guideline ≤ 200 words) | FIX | Done | Condensed abstract to exactly 185 words with structured clinical narrative. |
| R1-C13 | MAJOR | Crit. 1 §2.2, Crit. 2 §E | Passing-Bablok slope=1.000 is degenerate on narrow-range integer counts | FIX | Done | Added Deming orthogonal regression slope/intercept; explained integer tie collapse mechanism in P-B regression. |
| R1-C14 | MAJOR | Crit. 1 §4.2, Crit. 2 §J | Table II omits Spearman rho & Deming slope; unnecessary `table*` | FIX | Done | Added Spearman $\rho$, Deming slope/intercept, and MAPE; formatted cleanly. |
| R1-C15 | MAJOR | Crit. 1 §6.1, Crit. 2 §J | Missing system architecture diagram | FIX | Done | Generated vector diagram `fig_system_architecture.pdf` and included as Fig. 1. |
| R1-C16 | MAJOR | Crit. 1 §6.2, Crit. 2 §J | Missing qualitative detection example figure | EXISTING | Done | Generated `fig_qualitative_detections.pdf` from validation predictions and included as Fig. 2. |
| R1-C17 | MAJOR | Crit. 1 §7.1, Crit. 2 §M | Missing ethics statement and data availability statement | FIX | Done | Added formal unnumbered Ethics and Data Availability statement. |
| R1-C18 | MAJOR | Crit. 1 §7.3, Crit. 2 §F | No consolidated limitations subsection | FIX | Done | Added dedicated Subsection V-E (Limitations) consolidating operational and clinical boundaries. |
| R1-C19 | MINOR | Crit. 1 §4.5, Crit. 2 §I | `\balance` loaded but never called before bibliography | FIX | Done | Invoked `\balance` before bibliography. |
| R1-C20 | MINOR | Crit. 1 §4.6, Crit. 2 §H | Missing `\IEEEpeerreviewmaketitle` | FIX | Done | Added `\IEEEpeerreviewmaketitle`. |
| R1-C21 | MINOR | Crit. 1 §4.4, Crit. 2 §J | Supplementary figures generated but omitted from paper | FIX | Done | Integrated key figures into text; logged Task T-02 for repeatability CV%. |
| R1-C22 | MINOR | Crit. 1 §5.2, Crit. 2 §L | Thin bibliography (15 references) | FIX | Done | Expanded bibliography to 22 authoritative citations with DOIs (CLSI, Bland-Altman, CellProfiler, Deming). |
