# Morning Handoff: Autonomous Paper Improvement Loop (Run 2)

**Session Date:** 2026-09-29  
**Git Branch:** `improve/autonomous`  
**Current Paper Build:** `paper/paper.pdf` (compiled, 8 pages, 0 errors, 0 overfull hboxes)  
**Run 1 Backup:** `improvements/handoff-run-1.md`  

---

## 1. Work Completed Across Run 2

### 1.1 Code-to-Paper Synchronization (Phase 1)
- **Code & Change Log Audit:** Audited `change.md` and repository commits against the actual Python implementation files (`models/yolov8_model.py`, `train.py`, `stain_normalize_inference.py`, `prepare_clinical_split.py`, `eval_generalized.py`, `retrain_and_evaluate.py`).
- **Inactive Augmentation Disclosure:** Identified that `copy_paste = 0.15` in the Ultralytics configuration requires polygon segmentation masks (`instances.segments`), whereas BCCD and Clinical 72 provide only Pascal VOC bounding boxes (`instances.bboxes`). Explicitly documented in Section III-D that `copy_paste` is non-functional on box-only datasets to preserve scientific integrity.
- **Section III-D (Training Recipes):** Added complete exposition of both baseline training (SGD, lr=0.01, mosaic 1.0, 100 epochs, seed 0) and the new invariance-augmented training recipe (180° rotation, vertical flips $p=0.5$, MixUp 0.15, dropout 0.1, 15-epoch mosaic closure, patience 20).
- **Section III-E (Domain Adaptation Pipeline):** Formalized the mathematical foundations of Reinhard CIELAB stain transfer ($\mu, \sigma$ channel alignment against a BCCD reference smear) and CLAHE contrast enhancement ($L$-channel clip limit 2.0, $8 \times 8$ grid). Formalized per-class decision thresholding ($\tau_{\text{PLT}} = 0.15$, $\tau_{\text{RBC/WBC}} = 0.25$) and 4-rotation test-time augmentation (TTA).
- **Table V (Structured Ablation Study):** Constructed a comprehensive 7-row ablation matrix (Table V) detailing configurations from baseline zero-shot through stain normalization, threshold tuning, 4-rotation TTA, and few-shot clinical adaptation. All unexecuted server evaluations are demarcated with `[[PENDING: T-G06]]`, leaving the baseline row intact as the empirical reference.
- **Verified Citations:** Added verified citations with DOIs to `paper/references.bib`: Reinhard et al. (2001) for color transfer (DOI: `10.1109/38.946629`) and Zuiderveld (1994) for CLAHE (DOI: `10.1016/B978-0-12-336156-1.50061-6`), bringing the total verified bibliography to 24 references.
- **Synchronized Task Queue:** Fully reconciled `SERVER_TASKS.md` with verified script CLI arguments, strict input path constraints, and output directories mapped to `server/results/<TASK-ID>/`.

### 1.2 Round 3 Kill-Improve Cycle (Phases 3 & 4)
- **Round 3 Reviews Generated:** Authored full-spectrum audit `critiques/round-3/critique.md` (Prof. [Guide]) and statistical red-team review `critiques/round-3/critique-2.md` (Adversarial Audit).
- **Section III-D Heading Terminology (R3-C01):** Renamed heading to *"Invariance-Augmented Training and Domain Adaptation Pipeline"* to avoid claiming cross-domain generalization before empirical server results are ingested.
- **TTA Latency vs. Live Viewfinder (R3-C02):** Refined Section III-B to explicitly distinguish single-pass INT8 execution ($\approx$4.1 FPS / 245 ms latency) for interactive live viewfinder guidance from multi-pass 4-rotation TTA ($\approx$1.0 FPS / 980 ms latency) operating on captured static diagnostic fields.
- **Held-Out Split Comparability Warning (R3-C03):** Added explicit caveats in Section IV-H and Table V clarifying that row (g) assesses few-shot adaptation strictly on the 22 held-out clinical validation images to preserve zero-leakage protocol, preventing direct apples-to-oranges conflation with the 72-image zero-shot totals.
- **Overfull Hbox Elimination:** Refined Table II (`\tabcolsep{4.0pt}`) and wrapped Table V in `\resizebox{\textwidth}{!}{...}`. Compiled `paper/paper.tex` cleanly to exactly 8 pages with **0 errors and 0 overfull hboxes**.
- **Changelog and Ledger Updates:** Created `improvements/changelog-3.md` and updated `improvements/IMPROVEMENT_LOG.md` recording all Round 2 and Round 3 items.

---

## 2. Code-vs-Paper Discrepancies Found and Resolved

| # | Discrepancy Found | Code Reality | Paper Resolution |
|---|---|---|---|
| 1 | **`copy_paste` Augmentation Utility** | `change.md` claimed `copy_paste = 0.15` synthesizes platelet-dense regions. In Ultralytics YOLOv8, `CopyPaste` is silently skipped unless polygon segmentation masks are present. | Section III-D explicitly notes that `copy_paste = 0.15` is inactive on bounding-box annotations, ensuring no performance changes are falsely attributed to it. |
| 2 | **CLI Signature Mismatches** | `train.py` took `run_name` while early wrapper scripts passed `name`; `retrain_and_evaluate.py` passed `--data_dir` instead of `--bccd_test`. | Verified exact signatures in code; corrected all execution calls in `SERVER_TASKS.md` and `code-sync-1.md`. |
| 3 | **In-Domain Degradation Risk** | Preliminary local evaluation showed that heavy augmentations in `b_v2_bccd` dropped in-domain BCCD mAP@0.5 from 0.856 to 0.581 (platelet AP dropped from 0.834 to 0.005). | Kept original baseline numbers intact in Table I and Table V. Refrained from making unverified claims in prose until server outputs arrive. |
| 4 | **Premature Generalization Wording** | Manuscript referred to the retrained model as "Cross-Domain Generalization Recipe" before empirical evidence on the clinical dataset. | Renamed Section III-D and reworded claims to "Invariance-Augmented Training and Domain Adaptation Pipeline". |
| 5 | **Inference Frame Rate Ambiguity** | Paper cited 4.1 FPS streaming while introducing 4-rotation TTA (which requires 4 sequential passes $\approx$ 1 FPS). | Clarified in Section III-B and Section V-E that 4.1 FPS is single-pass viewfinder mode, while 4-rotation TTA is static field mode. |

---

## 3. Evaluation-Validity Gate Results

| Check | Gate Status | Detailed Finding & Paper Safeguard |
|---|:---:|---|
| **1. Split Leakage** | **OK (Guarded)** | 50 images from Clinical 72 are partitioned for few-shot adaptation; the fine-tuned model is evaluated strictly on the 22 held-out images. **Warning:** If `eval_generalized.py` is called with `--clinical_dir data/clinical_72` rather than the held-out split, training contamination occurs. `SERVER_TASKS.md` explicitly specifies `--clinical_test_dir outputs/generalized/clinical_split/images/val`. |
| **2. Held-Out Size** | **RISK** | The held-out clinical validation set contains only 22 images ($N_{\text{RBC}} \approx 1{,}100$, $N_{\text{WBC}} \approx 30$, $N_{\text{PLT}} \approx 45$). Small sample sizes widen confidence intervals. Highlighted as a formal clinical limitation in Section V-E. |
| **3. Metric Suitability** | **OK** | Both object detection metrics (AP@0.5, mAP@0.5, Precision, Recall, F1) and CLSI EP09-A3 clinical agreement metrics (Bland-Altman LoA, Deming regression, Passing-Bablok, Spearman $\rho$, MAPE) are implemented and reported. |
| **4. Baselines Integrity** | **OK** | Baseline zero-shot numbers on BCCD ($0.856$) and Clinical 72 ($0.412$) remain untouched. To enable true comparability, Server Task T-G06 evaluates the zero-shot baseline on the exact same 22-image validation split. |
| **5. Split Composition** | **RISK** | The 50/22 split was partitioned randomly (`seed=42`). Cellular distribution or stain variations between splits could introduce selection bias. Documented in Section V-E. |
| **6. Failure Modes** | **OK** | The acute out-of-distribution platelet drop (AP@0.5 = 0.091, recall = 0.10) is prominently disclosed. The manuscript bounds immediate clinical utility to primary leukocyte triage, preventing overclaiming. |
| **7. Fairness / Subgroups** | **UNKNOWN** | Neither BCCD nor Clinical 72 contains patient demographic metadata (age, sex, hematologic pathology classification). Performance differences across disease subtypes (e.g., leukemic blasts vs normal lymphocytes) remain unmeasured. |
| **8. Pipeline Latency Cost** | **OK** | 4-rotation TTA incurs a 4$\times$ latency multiplier ($\approx$980 ms per frame on Raspberry Pi 4B CPU). This operational boundary is documented in Section III-E and Section V-E. |

---

## 4. Remaining Weaknesses

### 4.1 Fixable by Writing
- **None.** All identified prose, structural, mathematical, citation, and IEEE layout defects from Rounds 1, 2, and 3 have been resolved. The manuscript compiles with 0 errors and 0 overfull hboxes.

### 4.2 Blocked on Server Results
1. **Table V Ablation Cells (`[[PENDING: T-G06]]`):** Rows (c) through (g) require empirical numbers from `eval_generalized.py` on the GPU server.
2. **Multi-Seed Variance Estimates (Task T-G02):** Reporting $\pm \sigma$ across seeds 0, 1, and 2 for Table I and Section III-D requires training runs on the server.
3. **INT8 Profiling and Repeatability (Tasks T-01 & T-02):** Exact multi-metric INT8 evaluation and repeatability CV% require server evaluation.
4. **Physical Hardware Profile (Task T-05):** Accurate thermal and latency benchmarks require execution on physical Raspberry Pi 4 hardware.

### 4.3 Blocked on Human Decisions
1. **Target Conference Page Budget (6 vs 8 Pages):** The paper currently compiles to exactly 8.0 pages. If the target IEEE conference imposes a strict 6-page limit (without overlength fees), Sections III and IV will require aggressive condensation, moving Bland-Altman and Passing-Bablok plots to supplementary materials.
2. **Primary Clinical Framing:** Decide whether the final publication emphasizes *zero-shot cross-center robustness* (using stain normalization and TTA across all 72 clinical images) or *few-shot on-site transfer learning* (using the 50/22 split). Currently, Table V presents both.

---

## 5. Prioritized Server Tasks Queue

| Task ID | Priority | Description & Purpose | Paper Section Affected | Expected Output | Est. Runtime | Risk & Fallback Plan |
|---|:---:|---|---|---|:---:|---|
| **T-G01** | **P0** | Retrain YOLOv8n with rotation (180°), flipud (0.5), MixUp (0.15), and dropout (0.1). | Sec. III-D, Table V row (c) | `outputs/generalized/checkpoints/yolov8n_hematology_v2/weights/best.pt` | ~45 min (GPU) | **Risk:** Over-regularization degrades in-domain AP. **Fallback:** If in-domain drops >15%, fall back to baseline weights + test-time stain normalization. |
| **T-G03** | **P0** | Partition Clinical 72 images into 50 train / 22 val splits via `prepare_clinical_split.py`. | Sec. III-D, Table V row (g) | `outputs/generalized/clinical_split/data.yaml` | <1 min | **Risk:** Split script fails on missing XML tags. **Fallback:** Script already handles missing bounding boxes gracefully. |
| **T-G04** | **P1** | Fine-tune `yolov8n_hematology_v2` on 50 clinical images with frozen backbone (`freeze=10`). | Sec. III-D, Table V row (g) | `outputs/generalized/checkpoints/yolov8n_hematology_v2_clinical/weights/best.pt` | ~10 min (GPU) | **Risk:** Overfitting on small 50-image set. **Fallback:** High learning rate decay and early stopping (`patience=15`). |
| **T-G05** | **P0** | Export FP32 ONNX and dynamic INT8 quantized ONNX models. | Sec. III-F, Table III | `yolov8n_hematology_v2.onnx` and `..._int8.onnx` | ~2 min | **Risk:** Dynamic quantization drops mAP >2%. **Fallback:** Baseline INT8 checkpoint is preserved as reference. |
| **T-G06** | **P0** | Run full generalization ablation suite across all 7 configurations. | Table V (all pending cells) | `outputs/generalized/results/generalized_results.json` and `ablation_table.tex` | ~15 min | **Risk:** TTA or stain norm shows marginal gains. **Fallback:** Table V honestly reports true delta, highlighting leukocyte stability. |
| **T-G07** | **P1** | Run formal CLSI EP09-A3 agreement suite on retrained model. | Tables I, II, IV; Figs. 3, 4, 5 | `outputs/generalized/paper_results/results.json` and LaTeX tables | ~15 min | **Risk:** Bland-Altman LoA widens. **Fallback:** Retain baseline numbers and report generalization suite in Table V. |
| **T-G02** | **P1** | Retrain across seeds 1 and 2 to compute standard deviations ($\pm \sigma$). | Sec. III-D, Table I | `outputs/generalized/checkpoints/yolov8n_hematology_v2_seed{1,2}/` | ~90 min (GPU) | **Risk:** High seed variance. **Fallback:** Report Wilson score confidence intervals if multi-seed training is omitted. |
| **T-01** | **P1** | Direct multi-metric evaluation of INT8 ONNX checkpoint on BCCD test set. | Table III, Sec. IV-E | `server/results/T-01/results.json` | ~5 min | **Risk:** Latency discrepancy with preliminary table. **Fallback:** Table III already contains verified empirical 245 ms. |
| **T-05** | **P1** | Profile INT8 inference latency and memory on physical Raspberry Pi 4B. | Table III, Sec. III-A | `server/results/T-05/edge_profile.json` | ~5 min | **Risk:** Raspberry Pi unavailable. **Fallback:** Report ONNX Runtime ARM Cortex-A72 reference benchmarks. |

---

## 6. Exact Server Terminal Commands

Run the following commands sequentially on the remote server (`/LAB/edge_hematology_ai/Edge_AI_hematology-main`).

```bash
#!/usr/bin/env bash
set -e  # Exit immediately if any command fails

echo "=== Step 1: Retraining YOLOv8n with Invariance Augmentations (T-G01) ==="
python train.py \
    --model yolov8n \
    --data_dir /LAB/edge_hematology_ai/data/BCCD_r/BCCD \
    --epochs 100 \
    --batch_size 16 \
    --output_dir outputs/generalized/checkpoints \
    --run_name yolov8n_hematology_v2 \
    --seed 0 \
    --degrees 180 \
    --flipud 0.5 \
    --mixup 0.15 \
    --copy_paste 0.15 \
    --dropout 0.1 \
    --close_mosaic 15 \
    --patience 20

echo "=== Step 2: Preparing Clinical 50/22 Train/Val Split (T-G03) ==="
python prepare_clinical_split.py \
    --clinical_dir /LAB/edge_hematology_ai/data/clinical_72 \
    --output_dir outputs/generalized/clinical_split \
    --train_ratio 0.7 \
    --seed 42

echo "=== Step 3: Few-Shot Fine-Tuning on Clinical Smears (T-G04) ==="
python train.py \
    --model yolov8n \
    --data_dir outputs/generalized/clinical_split \
    --finetune_weights outputs/generalized/checkpoints/yolov8n_hematology_v2/weights/best.pt \
    --epochs 30 \
    --batch_size 8 \
    --output_dir outputs/generalized/checkpoints \
    --run_name yolov8n_hematology_v2_clinical \
    --finetune_lr 0.001 \
    --freeze_backbone 10 \
    --patience 15

echo "=== Step 4: ONNX Export and Dynamic INT8 Quantization (T-G05) ==="
python -c "
import os, shutil
from ultralytics import YOLO
from quantize_and_infer import quantize_onnx_to_int8

os.makedirs('outputs/generalized/onnx', exist_ok=True)
model = YOLO('outputs/generalized/checkpoints/yolov8n_hematology_v2/weights/best.pt')
exp = model.export(format='onnx', imgsz=640, dynamic=False)
shutil.copy2(exp, 'outputs/generalized/onnx/yolov8n_hematology_v2.onnx')
quantize_onnx_to_int8('outputs/generalized/onnx/yolov8n_hematology_v2.onnx', 'outputs/generalized/onnx/yolov8n_hematology_v2_int8.onnx')
print('ONNX and INT8 export complete.')
"

echo "=== Step 5: Running Generalization Ablation Suite (T-G06) ==="
python eval_generalized.py \
    --weights outputs/generalized/checkpoints/yolov8n_hematology_v2/weights/best.pt \
    --original_weights runs/detect/outputs/checkpoints/yolov8n_hematology/weights/best.pt \
    --bccd_test /LAB/edge_hematology_ai/data/BCCD_r/BCCD/yolo_format \
    --clinical_dir /LAB/edge_hematology_ai/data/clinical_72 \
    --clinical_test_dir outputs/generalized/clinical_split/images/val \
    --bccd_ref_dir /LAB/edge_hematology_ai/data/BCCD_r/BCCD/JPEGImages \
    --out outputs/generalized/results \
    --use_stain_norm \
    --use_tta \
    --plt_conf 0.15

echo "=== Step 6: Archiving Outputs into server/results/ ==="
mkdir -p server/results/T-G01 server/results/T-G04 server/results/T-G05 server/results/T-G06
cp -r outputs/generalized/checkpoints/yolov8n_hematology_v2/weights/best.pt server/results/T-G01/
cp -r outputs/generalized/checkpoints/yolov8n_hematology_v2_clinical/weights/best.pt server/results/T-G04/
cp -r outputs/generalized/onnx/* server/results/T-G05/
cp -r outputs/generalized/results/* server/results/T-G06/

echo "=== ALL SERVER PIPELINE STEPS COMPLETED SUCCESSFULLY ==="
```

---

## 7. Human Decisions Needed

1. **Target Conference Page Limit:**
   - The paper currently compiles to exactly **8.0 pages** (IEEE standard limit with optional paid overlength pages).
   - *Question for you:* Is your target venue a strict 6-page maximum conference (e.g., IEEE EMBC, IEEE BHI initial submission) or an 8-page venue (e.g., IEEE JBHI, IEEE Access, IEEE TBME)? If 6 pages, confirm so we can condense Section IV and shift Bland-Altman figures to an appendix.
2. **Framing: Zero-Shot Robustness vs. Few-Shot Adaptation:**
   - Table V provides both paradigms: rows (d)-(f) present zero-shot stain normalization + TTA on all 72 images, while row (g) presents few-shot transfer learning on 50 images evaluated on 22.
   - *Question for you:* Which narrative should dominate your discussion? We recommend presenting zero-shot stain normalization as the primary deployment mode for decentralized field clinics, and few-shot adaptation as an optional calibration pathway for regional reference centers.
3. **Copy-Paste Augmentation Code Cleanup:**
   - In Ultralytics YOLOv8, `copy_paste = 0.15` does not execute without polygon segmentation masks.
   - *Question for you:* Do you wish to leave the parameter in `train.py` as documented (with our honest paper disclosure), or remove it from the command-line flags in future training scripts?

---

## 8. Instructions for Next Agent Iteration (When Results Return)

When the server run finishes and outputs are copied into `server/results/T-G06/`:
1. **Verify Artifact Presence:** Inspect `server/results/T-G06/generalized_results.json` and `server/results/T-G06/ablation_table.tex`.
2. **Ingest Ablation Numbers into Table V:**
   - Open `paper/paper.tex`.
   - Locate `\begin{table*}[!t]` and `\label{tab:ablation}` in Section IV-H.
   - Replace every `[[PENDING: T-G06]]` marker with the real measured metrics (mAP@0.5, RBC AP, WBC AP, PLT AP, Precision, Recall, F1).
3. **Update Text in Section IV-H:**
   - Rewrite the discussion in Section IV-H to analyze the observed empirical deltas (e.g., whether Reinhard stain normalization improved platelet recall, whether 4-rotation TTA boosted boundary precision, and the adaptation performance on the 22 held-out images).
4. **Compile and Verify:**
   - Run `pdflatex paper.tex` and `bibtex paper`.
   - Verify page budget (8 pages) and confirm 0 errors and 0 overfull hboxes.
5. **Git Commit:**
   - Commit changes on `improve/autonomous`: `feat(paper): ingest empirical ablation results into Table V`.

---

## 9. Final Paper Status

- **Page Count:** 8 pages (exact, balanced columns on page 8).
- **Overfull `\hbox`es:** **0** (strictly 0, fully verified via `paper.log`).
- **Citations:** **24 total citations**, all 24 verified with DOIs / official URLs (Reinhard 2001, Zuiderveld 1994, CLSI EP09-A3, Rümke 1985, Bland-Altman 1986, etc.).
- **Figures:** **6 vector figures**, all high-resolution PDFs (`fig_system_architecture.pdf`, `fig_qualitative_detections.pdf`, `fig_confusion_BCCD.pdf`, `fig_ba_BCCD.pdf`, `fig_pb_BCCD.pdf`, `fig_reliability.pdf`).
- **Tables:** **5 formal IEEE tables**, formatted with booktabs and uppercase labels (`TABLE I` through `TABLE V`), with captions properly placed above the tables.
- **LaTeX Compilation Status:** **Clean (0 errors, 0 warnings, 0 overfull hboxes).**
