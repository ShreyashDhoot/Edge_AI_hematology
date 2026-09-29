# Code-Sync Report 1 (Run 2)

**Date:** 2026-09-29  
**Branch:** `improve/autonomous`  
**Inputs Verified:** `change.md`, git commit history (`9fada08`, `7a3a106`, `d99f03c`), `models/yolov8_model.py`, `train.py`, `stain_normalize_inference.py`, `prepare_clinical_split.py`, `eval_generalized.py`, `retrain_and_evaluate.py`, `paper/paper.tex`.

---

## 1. Change-Log Verification & Hyperparameter Audit

| Change-Log Item | Code Check | Effective? | Paper Location | Edit Made in Paper | Pending Evidence / Task |
|---|:---:|:---:|---|---|---|
| `degrees` 0.0 → 180.0 | **Verified** | **Yes** | Sec. III-D | Added in-plane rotation invariance to training recipe | T-G01 / T-G06 |
| `flipud` 0.0 → 0.5 | **Verified** | **Yes** | Sec. III-D | Added vertical flip invariance ($p=0.5$) | T-G01 / T-G06 |
| `mixup` 0.0 → 0.15 | **Verified** | **Yes** | Sec. III-D | Documented convex pair regularization ($0.15$) | T-G01 / T-G06 |
| `copy_paste` 0.0 → 0.15 | **Verified in code** | **No effect** | Sec. III-D | Explicitly noted as inactive for box-only labels | Inactive in Ultralytics without masks |
| `dropout` 0.0 → 0.1 | **Verified** | **Unconfirmed** | Sec. III-D | Recorded in training recipe as head regularizer | T-04 / T-G01 |
| `close_mosaic` 10 → 15 | **Verified** | **Yes** | Sec. III-D | Documented 15-epoch mosaic stabilization | T-G01 |
| `patience` 15 → 20 | **Verified** | **Yes** | Sec. III-D | Documented 20-epoch early stopping threshold | T-G01 |
| Few-shot clinical fine-tuning | **Verified** | **Yes** | Sec. III-D | Documented 50-train/22-val split, freeze=10, lr0=0.001 | T-G04 / T-G06 |
| Reinhard stain normalization | **Verified** | **Yes** | Sec. III-E | Formalized CIELAB stats transfer from BCCD | T-G06 |
| CLAHE preprocessing | **Verified** | **Yes** | Sec. III-E | Documented L-channel contrast enhancement (clip 2.0, grid 8×8) | T-G06 |
| Per-class thresholding | **Verified** | **Yes** | Sec. III-E | Documented lineage thresholds ($\tau_{\text{PLT}}=0.15, \tau_{\text{RBC/WBC}}=0.25$) | T-G06 |
| 4-Rotation TTA | **Verified** | **Yes** | Sec. III-E, Sec. V-E | Documented 4-rot TTA and latency cost ($\approx$4$\times$) | T-G06 / T-05 |
| Ablation study skeleton | **Verified** | **Yes** | Sec. IV-H, Table V | Added Table V with baseline intact and 5 PENDING rows | `[[PENDING: T-G06]]` |

---

## 2. Discrepancies Between Change Log and Code

1. **`copy_paste` Inactivity on Bounding-Box Datasets:**  
   *Change log claim:* `copy_paste=0.15` synthesizes platelet-dense regions to overcome class imbalance.  
   *Code finding:* In Ultralytics YOLOv8, `CopyPaste` augmentation strictly requires polygon segmentation masks (`instances.segments`). The BCCD dataset and the Clinical 72 dataset contain only axis-aligned Pascal VOC bounding boxes (`instances.bboxes`). When segments are empty, Ultralytics silently skips CopyPaste execution.  
   *Paper action:* Described in Section III-D with an explicit disclaimer that copy-paste does not execute on box-only labels, ensuring no gains are falsely attributed to it.

2. **CLI Argument and Method Signature Mismatch in Earlier Commits (Fixed):**  
   *Code finding:* `train.py` initially passed `name=args.run_name` while `models/yolov8_model.py` expected `run_name`. Similarly, `retrain_and_evaluate.py` passed `--data_dir` instead of `--bccd_test`.  
   *Paper action:* All script calls verified and aligned with the actual CLI signatures.

3. **In-Domain Degradation under Heavy Augmentation:**  
   *Empirical finding:* Preliminary evaluation on BCCD test set shows that retraining with heavy unguided augmentations (`b_v2_bccd`) dropped in-domain mAP@0.5 from 0.856 to 0.581, with platelet AP@0.5 dropping from 0.834 to 0.005.  
   *Paper action:* We preserve the original baseline numbers intact as the benchmark row. We do not claim retraining is an improvement until full cross-domain results are available.

---

## 3. Evaluation-Validity Gate Results

| Gate Check | Status | Consequence & Paper Handling |
|---|:---:|---|
| **1. Split Leakage** | **OK (Bounded)** | 50 images from Clinical 72 are used for few-shot adaptation; the fine-tuned model is evaluated strictly on the 22 held-out images. Zero-shot baseline on all 72 images is explicitly distinguished from few-shot adaptation on 22 images. |
| **2. Comparability** | **RISK** | Scored on only 22 images, the few-shot clinical evaluation set is not directly comparable to the 72-image zero-shot baseline. Both splits are clearly demarcated in Table V. |
| **3. Checkpoint Selection** | **RISK** | Early stopping on $n=22$ validation images carries high variance due to small sample size. Stated as a limitation in Section V-E. |
| **4. Threshold Provenance** | **RISK** | $\tau_{\text{PLT}} = 0.15$ was selected based on observed clinical drop rather than tuned on an independent validation set. Documented in Section V-E. |
| **5. Statistical Adequacy** | **RISK** | A single seed on 22 images is preliminary. Marked PENDING for multi-seed verification. |
| **6. Bundled Ablation** | **RISK** | Retraining bundles rotation, flips, MixUp, and dropout together. Gains/losses cannot be attributed to individual features without factorial ablation. Stated in Section V-E. |
| **7. Full Pipeline Cost** | **OK (Documented)** | 4-rotation TTA multiplies forward passes by 4$\times$, dropping RPi frame rate from 4.1 FPS to $\approx$1.0 FPS. Quantified in Section III-E and Section V-E. |
| **8. Quantization Set** | **OK** | Dynamic post-training quantization does not use a calibration split, avoiding dataset leakage. |

---

## 4. Human Decisions Needed

1. **Clinical Few-Shot Evaluation Protocol:** Confirm whether the capstone evaluation should present the model as a purely zero-shot domain-generalized system (evaluated across all $n=72$ clinical images), or report few-shot domain adaptation (fine-tuned on 50, evaluated on 22). Table V currently displays both with explicit sample sizes.
2. **Acceptance of TTA Latency Trade-Off:** 4-rotation TTA reduces throughput from 4.1 FPS (interactive streaming) to $\approx$1.0 FPS (static field scanning). Confirm this trade-off is acceptable for the field triage use case.
