# Server Tasks Queue — Complete Task Registry

> **Updated:** 2026-09-29 (Run 2)  
> **Status:** All tasks reconciled with actual code signatures and paper `[[PENDING]]` markers.  
> **Convention:** All task artifacts should be placed in `server/results/<TASK-ID>/` for automated ingestion.

---

## Execution Overview

```
Phase 1:  T-G01 (Retrain) ──┬──> T-G02 (Multi-seed, P1)
                            │
Phase 2:  T-G03 (Split) ────>├──> T-G04 (Fine-tune, P1)
                            │
Phase 3:                    ├──> T-G05 (ONNX/INT8 Export, P0)
                            │
Phase 4:                    ├──> T-G06 (Ablation Eval, P0) ──> Fills Table V [[PENDING: T-G06]]
                            └──> T-G07 (Paper Eval Suite, P1) ──> Updates Tables I-IV
Phase 5:  T-01 (INT8 Bench), T-02 (CV%), T-03 (Human Study), T-05 (RPi Profiling)
```

**One-Command Fast Path:**
From `/LAB/edge_hematology_ai/Edge_AI_hematology-main`:
```bash
python retrain_and_evaluate.py \
    --data_dir /LAB/edge_hematology_ai/data/BCCD_r/BCCD \
    --clinical_dir /LAB/edge_hematology_ai/data/clinical_72 \
    --output_base outputs/generalized \
    --epochs 100 \
    --batch_size 16
```

---

## Detailed Task Registry

### T-G01: Retrain YOLOv8n with Enhanced Augmentations
- **Problem:** OOD performance drop on clinical smears (R1-C01, R2-C01). Need rotation invariance, vertical flip, mixup, and dropout regularization.
- **Effort:** Full training run (~45 min on GPU, ~3 hours on CPU).
- **Exact action:** Run `train.py` with expanded augmentation arguments.
- **Expected output:** `best.pt`, `args.yaml`, `results.csv`, `results.png`.
- **Output location:** `server/results/T-G01/` (or copy from `outputs/generalized/checkpoints/yolov8n_hematology_v2/`).
- **Paper impact:** Provides the `yolov8n_hematology_v2` model weights required for Table V (Ablation) and Section IV-H.
- **Priority:** P0 (Blocking for all ablation and evaluation tasks).
- **Suggested command:**
```bash
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
```

---

### T-G02: Multi-Seed Variance Logging (Seeds 1 and 2)
- **Problem:** Reporting single random seed (seed=0) without variance across initializations (R2-C02).
- **Effort:** Full training run (2 $\times$ 45 min on GPU).
- **Exact action:** Execute retraining with `--seed 1` and `--seed 2`.
- **Expected output:** `best.pt` and `results.csv` for each seed.
- **Output location:** `server/results/T-G02/`
- **Paper impact:** Section III-D and Table I multi-seed standard deviation ($\pm \sigma$).
- **Priority:** P1 (Important).
- **Suggested command:**
```bash
python train.py --model yolov8n --data_dir /LAB/edge_hematology_ai/data/BCCD_r/BCCD --epochs 100 --batch_size 16 --output_dir outputs/generalized/checkpoints --run_name yolov8n_hematology_v2_seed1 --seed 1 --degrees 180 --flipud 0.5 --mixup 0.15 --copy_paste 0.15 --dropout 0.1 --close_mosaic 15 --patience 20
python train.py --model yolov8n --data_dir /LAB/edge_hematology_ai/data/BCCD_r/BCCD --epochs 100 --batch_size 16 --output_dir outputs/generalized/checkpoints --run_name yolov8n_hematology_v2_seed2 --seed 2 --degrees 180 --flipud 0.5 --mixup 0.15 --copy_paste 0.15 --dropout 0.1 --close_mosaic 15 --patience 20
```

---

### T-G03: Prepare Clinical Train/Val Split
- **Problem:** Partitioning clinical 72 smear images into training and held-out evaluation sets without data leakage.
- **Effort:** Small script execution (<1 min).
- **Exact action:** Run `prepare_clinical_split.py` to convert VOC XML to YOLO format and partition at 70/30 ratio (50 train, 22 val).
- **Expected output:** `data.yaml`, `images/train/`, `images/val/`, `labels/train/`, `labels/val/`.
- **Output location:** `server/results/T-G03/` (or `outputs/generalized/clinical_split/`).
- **Paper impact:** Provides the partitioned split described in Section III-D.
- **Priority:** P0 (Required for clinical fine-tuning).
- **Suggested command:**
```bash
python prepare_clinical_split.py \
    --clinical_dir /LAB/edge_hematology_ai/data/clinical_72 \
    --output_dir outputs/generalized/clinical_split \
    --train_ratio 0.7 \
    --seed 42
```

---

### T-G04: Fine-Tune Retrained Model on Clinical Split
- **Problem:** Domain adaptation to local clinical staining using few-shot transfer learning with frozen backbone.
- **Effort:** Small fine-tuning run (~10 min on GPU).
- **Exact action:** Run `train.py` with `--finetune_weights` and `--freeze_backbone 10` on `clinical_split`.
- **Expected output:** `yolov8n_hematology_v2_clinical/weights/best.pt`, `results.csv`.
- **Output location:** `server/results/T-G04/` (or `outputs/generalized/checkpoints/yolov8n_hematology_v2_clinical/`).
- **Paper impact:** Fills row (g) in Table V (`[[PENDING: T-G06]]`).
- **Priority:** P1 (Important).
- **Suggested command:**
```bash
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
```

---

### T-G05: Export FP32 ONNX and Dynamic INT8 Quantization
- **Problem:** Model compression and execution preparation for Raspberry Pi ARM CPU.
- **Effort:** Small script execution (<2 min).
- **Exact action:** Export best checkpoint to ONNX and apply dynamic INT8 quantization via `quantize_and_infer.py`.
- **Expected output:** `yolov8n_hematology_v2.onnx` (~12.3 MB) and `yolov8n_hematology_v2_int8.onnx` (~3.4 MB).
- **Output location:** `server/results/T-G05/` (or `outputs/generalized/onnx/`).
- **Paper impact:** Table III INT8 comparison and Section III-F.
- **Priority:** P0 (Blocking for edge profiling).
- **Suggested command:**
```bash
python -c "
from ultralytics import YOLO
import shutil, os
from quantize_and_infer import quantize_onnx_to_int8

os.makedirs('outputs/generalized/onnx', exist_ok=True)
model = YOLO('outputs/generalized/checkpoints/yolov8n_hematology_v2/weights/best.pt')
exp = model.export(format='onnx', imgsz=640, dynamic=False)
shutil.copy2(exp, 'outputs/generalized/onnx/yolov8n_hematology_v2.onnx')
quantize_onnx_to_int8('outputs/generalized/onnx/yolov8n_hematology_v2.onnx', 'outputs/generalized/onnx/yolov8n_hematology_v2_int8.onnx')
print('ONNX and INT8 export complete.')
"
```

---

### T-G06: Run Generalization Ablation Evaluation Suite
- **Problem:** Missing empirical ablation numbers across baseline, retrained, stain-normalized, threshold-tuned, and TTA configurations.
- **Effort:** Evaluation run (~15 min on GPU/CPU).
- **Exact action:** Run `eval_generalized.py` across all datasets and configurations.
- **Expected output:** `generalized_results.json`, `ablation_table.tex`, `fig_ablation_mAP.pdf`, `fig_confusion_*.pdf`.
- **Output location:** `server/results/T-G06/` (or `outputs/generalized/results/`).
- **Paper impact:** Replaces all `[[PENDING: T-G06]]` cells in Table V.
- **Priority:** P0 (Core paper contribution).
- **Suggested command:**
```bash
python eval_generalized.py \
    --weights outputs/generalized/checkpoints/yolov8n_hematology_v2/weights/best.pt \
    --original_weights runs/detect/outputs/checkpoints/yolov8n_hematology/weights/best.pt \
    --bccd_test /LAB/edge_hematology_ai/data/BCCD_r/BCCD/yolo_format \
    --clinical_dir /LAB/edge_hematology_ai/data/clinical_72 \
    --bccd_ref_dir /LAB/edge_hematology_ai/data/BCCD_r/BCCD/JPEGImages \
    --out outputs/generalized/results \
    --use_stain_norm \
    --use_tta \
    --plt_conf 0.15
```

---

### T-G07: Run Comprehensive Paper Evaluation Suite
- **Problem:** Updating all formal CLSI EP09-A3 agreement statistics, Deming regression, and Bland-Altman plots with the retrained model.
- **Effort:** Small re-run (~15 min).
- **Exact action:** Run `paper_eval.py` using the retrained weights.
- **Expected output:** `results.json`, `paper_numbers.tex`, `table_detection.tex`, `table_agreement.tex`, `fig_ba_*.pdf`, `fig_pb_*.pdf`.
- **Output location:** `server/results/T-G07/` (or `outputs/generalized/paper_results/`).
- **Paper impact:** Updates Tables I–IV and all in-text macros in `paper/paper.tex`.
- **Priority:** P1 (Important).
- **Suggested command:**
```bash
python paper_eval.py \
    --weights outputs/generalized/checkpoints/yolov8n_hematology_v2/weights/best.pt \
    --onnx_fp32 outputs/generalized/onnx/yolov8n_hematology_v2.onnx \
    --onnx_int8 outputs/generalized/onnx/yolov8n_hematology_v2_int8.onnx \
    --bccd_test /LAB/edge_hematology_ai/data/BCCD_r/BCCD/yolo_format/images/val \
    --clinical_dir /LAB/edge_hematology_ai/data/clinical_72 \
    --out outputs/generalized/paper_results
```

---

### T-01: Benchmark INT8 ONNX Model (Exact mAP and Latency)
- **Problem:** INT8 mAP reported as approximate or unverified across multi-metrics (R1-C04).
- **Effort:** Small evaluation run (~5 min).
- **Exact action:** Evaluate INT8 ONNX directly on BCCD test set.
- **Expected output:** `results.json` containing exact AP per class and mAP.
- **Output location:** `server/results/T-01/`
- **Paper impact:** Table III and Section IV-F.
- **Priority:** P1.
- **Suggested command:**
```bash
mkdir -p server/results/T-01
python paper_eval.py \
    --weights outputs/generalized/onnx/yolov8n_hematology_v2_int8.onnx \
    --bccd_test /LAB/edge_hematology_ai/data/BCCD_r/BCCD/yolo_format/images/val \
    --clinical_dir /LAB/edge_hematology_ai/data/clinical_72 \
    --out server/results/T-01
```

---

### T-02: Repeatability CV% Benchmark (Protocol B)
- **Problem:** Repeatability coefficient of variation (CV%) was estimated rather than experimentally perturbed.
- **Effort:** Small evaluation run (~10 min).
- **Exact action:** Run `paper_eval.py` repeatability protocol.
- **Expected output:** `table_cv.tex`.
- **Output location:** `server/results/T-02/`
- **Paper impact:** Table IV (CV% column).
- **Priority:** P2.
- **Suggested command:**
```bash
mkdir -p server/results/T-02
python paper_eval.py \
    --weights outputs/generalized/checkpoints/yolov8n_hematology_v2/weights/best.pt \
    --bccd_test /LAB/edge_hematology_ai/data/BCCD_r/BCCD/yolo_format/images/val \
    --clinical_dir /LAB/edge_hematology_ai/data/clinical_72 \
    --out server/results/T-02
```

---

### T-03: Inter-Annotator Study (Second Human Annotator)
- **Problem:** Human-vs-human baseline on clinical smears requires paired independent annotations.
- **Effort:** External human annotation of 20 images + evaluation (<5 min compute).
- **Exact action:** Run `paper_eval.py` with `--second_annotator_dir`.
- **Expected output:** `table_human_baseline.tex`.
- **Output location:** `server/results/T-03/`
- **Paper impact:** Table IV human baseline.
- **Priority:** P3 (Optional / Capstone enhancement).

---

### T-05: Hardware Profiling on Physical Raspberry Pi 4B
- **Problem:** Power consumption (3.4 W) and latency (245 ms) should be measured on actual hardware.
- **Effort:** Small benchmark script on physical device (~5 min).
- **Exact action:** Execute `profile_edge_inference` on the Raspberry Pi 4B.
- **Expected output:** `edge_profile.json` (mean latency, FPS, memory footprint).
- **Output location:** `server/results/T-05/`
- **Paper impact:** Table III and Section III-A.
- **Priority:** P1.
- **Suggested command (run on Raspberry Pi):**
```bash
mkdir -p server/results/T-05
python -c "
import json
from quantize_and_infer import profile_edge_inference
profile = profile_edge_inference('outputs/generalized/onnx/yolov8n_hematology_v2_int8.onnx', num_runs=100)
print(json.dumps(profile, indent=2))
with open('server/results/T-05/edge_profile.json', 'w') as f:
    json.dump(profile, f, indent=2)
"
```
