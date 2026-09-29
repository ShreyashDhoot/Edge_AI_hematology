# Server Tasks Queue — Complete Start-to-End Pipeline

> **Updated:** 2026-09-29 — Merged generalization improvements with original paper evaluation tasks.
> 
> **All outputs consolidate under `outputs/generalized/`** to avoid scattering results across directories.

---

## Prerequisites

```bash
# 1. Activate your Python environment
# 2. Ensure you are in the project root:
cd Edge_AI_hematology-main

# 3. Install dependencies (if not already done)
pip install -r requirements.txt

# 4. Verify data is in place:
#    - BCCD dataset:  data/BCCD_r/BCCD/  (with JPEGImages/ and Annotations/)
#    - Clinical 72:   data/clinical_72/  (with images/ and annotations/ containing VOC XMLs)
```

---

## Phase 1: Retrain with Generalization Improvements

### T-G01: Retrain YOLOv8n with Enhanced Augmentations

**What changed:** degrees=180, flipud=0.5, mixup=0.15, copy_paste=0.15, dropout=0.1, close_mosaic=15, patience=20

```bash
python train.py \
    --model yolov8n \
    --data_dir data/BCCD_r/BCCD \
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

- **Expected time:** ~45 min on GPU, ~3 hours on CPU
- **Output:** `outputs/generalized/checkpoints/yolov8n_hematology_v2/weights/best.pt`
- **Verify:** Check `outputs/generalized/checkpoints/yolov8n_hematology_v2/results.csv` for convergence

---

### T-G02: Multi-Seed Retraining (Seeds 1 and 2)

**Why:** Report mean ± std across 3 seeds for mAP and per-class F1 (addresses R1-C06, R2-C08)

```bash
python train.py \
    --model yolov8n \
    --data_dir data/BCCD_r/BCCD \
    --epochs 100 \
    --batch_size 16 \
    --output_dir outputs/generalized/checkpoints \
    --run_name yolov8n_hematology_v2_seed1 \
    --seed 1 \
    --degrees 180 --flipud 0.5 --mixup 0.15 --copy_paste 0.15 --dropout 0.1 --close_mosaic 15 --patience 20

python train.py \
    --model yolov8n \
    --data_dir data/BCCD_r/BCCD \
    --epochs 100 \
    --batch_size 16 \
    --output_dir outputs/generalized/checkpoints \
    --run_name yolov8n_hematology_v2_seed2 \
    --seed 2 \
    --degrees 180 --flipud 0.5 --mixup 0.15 --copy_paste 0.15 --dropout 0.1 --close_mosaic 15 --patience 20
```

- **Expected time:** ~45 min per seed on GPU
- **Output:** `outputs/generalized/checkpoints/yolov8n_hematology_v2_seed{1,2}/weights/best.pt`
- **Paper impact:** Table I reports mAP ± σ across 3 seeds

---

## Phase 2: Clinical Domain Adaptation

### T-G03: Prepare Clinical Train/Val Split

```bash
python prepare_clinical_split.py \
    --clinical_dir data/clinical_72 \
    --output_dir outputs/generalized/clinical_split \
    --train_ratio 0.7 \
    --seed 42
```

- **Expected time:** <1 min
- **Output:** `outputs/generalized/clinical_split/` with `images/`, `labels/`, `data.yaml`
- **Split:** 50 train, 22 val (at 0.7 ratio from 72)

---

### T-G04: Fine-Tune Retrained Model on Clinical Data

**Prerequisite:** T-G01 and T-G03 must complete first.

```bash
python train.py \
    --model yolov8n \
    --data_dir outputs/generalized/clinical_split \
    --epochs 30 \
    --batch_size 8 \
    --output_dir outputs/generalized/checkpoints \
    --run_name yolov8n_hematology_v2_clinical \
    --finetune_weights outputs/generalized/checkpoints/yolov8n_hematology_v2/weights/best.pt \
    --seed 0 \
    --degrees 180 --flipud 0.5 --mixup 0.15 --copy_paste 0.15 --dropout 0.1 --close_mosaic 15 \
    --patience 15
```

- **Expected time:** ~10 min on GPU
- **Output:** `outputs/generalized/checkpoints/yolov8n_hematology_v2_clinical/weights/best.pt`
- **Note:** Backbone is frozen (first 10 layers), lr0=0.001 — only detection head adapts

---

## Phase 3: ONNX Export & Quantization

### T-G05: Export Retrained Model to ONNX + INT8

**Prerequisite:** T-G01 must complete first.

```bash
# Export FP32 ONNX
python -c "
from ultralytics import YOLO
model = YOLO('outputs/generalized/checkpoints/yolov8n_hematology_v2/weights/best.pt')
model.export(format='onnx', imgsz=640, half=False, dynamic=False)
import shutil, os
src = 'outputs/generalized/checkpoints/yolov8n_hematology_v2/weights/best.onnx'
dst = 'outputs/generalized/onnx/yolov8n_hematology_v2.onnx'
os.makedirs('outputs/generalized/onnx', exist_ok=True)
shutil.copy2(src, dst)
print(f'FP32 ONNX saved to: {dst}')
"

# Quantize to INT8
python -c "
from quantize_and_infer import quantize_onnx_to_int8
quantize_onnx_to_int8(
    'outputs/generalized/onnx/yolov8n_hematology_v2.onnx',
    'outputs/generalized/onnx/yolov8n_hematology_v2_int8.onnx'
)
"
```

- **Output:** `outputs/generalized/onnx/yolov8n_hematology_v2.onnx` and `yolov8n_hematology_v2_int8.onnx`

---

## Phase 4: Evaluation (Ablation Study)

### T-G06: Run Ablation Evaluation (Retrained vs Original, with/without stain norm + TTA)

**Prerequisite:** T-G01 must complete. T-G05 optional (for ONNX comparison).

```bash
python eval_generalized.py \
    --weights outputs/generalized/checkpoints/yolov8n_hematology_v2/weights/best.pt \
    --original_weights runs/detect/outputs/checkpoints/yolov8n_hematology/weights/best.pt \
    --bccd_test data/BCCD_r/BCCD/yolo_format \
    --clinical_dir data/clinical_72 \
    --bccd_ref_dir data/BCCD_r/BCCD/yolo_format/images/train \
    --out outputs/generalized/results \
    --use_stain_norm \
    --use_tta \
    --plt_conf 0.15
```

- **Expected time:** ~10–20 min (TTA runs each image 4× per configuration)
- **Output:**
  - `outputs/generalized/results/generalized_results.json` — all numbers
  - `outputs/generalized/results/ablation_table.tex` — LaTeX table for paper
  - `outputs/generalized/results/fig_confusion_*.pdf` — per-configuration confusion matrices
  - `outputs/generalized/results/fig_ablation_mAP.pdf` — bar chart comparison

---

### T-G07: Run Full Paper Evaluation Suite (Retrained Model)

**Prerequisite:** T-G01 must complete.

```bash
python paper_eval.py \
    --weights outputs/generalized/checkpoints/yolov8n_hematology_v2/weights/best.pt \
    --onnx_fp32 outputs/generalized/onnx/yolov8n_hematology_v2.onnx \
    --onnx_int8 outputs/generalized/onnx/yolov8n_hematology_v2_int8.onnx \
    --bccd_test data/BCCD_r/BCCD/yolo_format/images/val \
    --clinical_dir data/clinical_72 \
    --out outputs/generalized/paper_results
```

- **Expected time:** ~15 min
- **Output:** `outputs/generalized/paper_results/` with all tables, figures, and `results.json`
- **Paper impact:** ALL numbers in Tables I–IV get updated from the retrained model

---

## Phase 5: Original Paper Tasks (Preserved from Round 1)

> These tasks use the **retrained v2 model** unless otherwise noted.

### T-01: Benchmark INT8 ONNX Model (Exact mAP and Latency)

```bash
mkdir -p outputs/generalized/server_results/T-01

python paper_eval.py \
    --weights outputs/generalized/onnx/yolov8n_hematology_v2_int8.onnx \
    --bccd_test data/BCCD_r/BCCD/yolo_format/images/val \
    --clinical_dir data/clinical_72 \
    --out outputs/generalized/server_results/T-01
```

- **Output:** `outputs/generalized/server_results/T-01/results.json`
- **Paper impact:** Table III (INT8 column) — real mAP, no "≈"

---

### T-02: Repeatability CV% Benchmark (Protocol B)

```bash
mkdir -p outputs/generalized/server_results/T-02

python paper_eval.py \
    --weights outputs/generalized/checkpoints/yolov8n_hematology_v2/weights/best.pt \
    --bccd_test data/BCCD_r/BCCD/yolo_format/images/val \
    --clinical_dir data/clinical_72 \
    --out outputs/generalized/server_results/T-02
```

- **Output:** `outputs/generalized/server_results/T-02/table_cv.tex`
- **Paper impact:** Table IV (Repeatability CV%)

---

### T-03: Inter-Annotator Study (Second Annotator)

**Prerequisite:** Have a second annotator independently label 20 images from `clinical_72` in YOLO txt format, saved to `data/second_annotator_dir/`.

```bash
mkdir -p outputs/generalized/server_results/T-03

python paper_eval.py \
    --weights outputs/generalized/checkpoints/yolov8n_hematology_v2/weights/best.pt \
    --bccd_test data/BCCD_r/BCCD/yolo_format/images/val \
    --clinical_dir data/clinical_72 \
    --second_annotator_dir data/second_annotator_dir \
    --out outputs/generalized/server_results/T-03
```

- **Output:** `outputs/generalized/server_results/T-03/table_human_baseline.tex`
- **Paper impact:** Table V (Human-vs-Human Baseline)

---

### T-05: Hardware Profiling on Physical Raspberry Pi 4B

**Run this on the actual Raspberry Pi:**

```bash
mkdir -p outputs/generalized/server_results/T-05

python -c "
import json
from quantize_and_infer import profile_edge_inference
profile = profile_edge_inference('outputs/generalized/onnx/yolov8n_hematology_v2_int8.onnx', num_runs=100)
print(json.dumps(profile, indent=2))
" > outputs/generalized/server_results/T-05/edge_profile.json
```

- **Output:** `outputs/generalized/server_results/T-05/edge_profile.json`
- **Paper impact:** Section III-E, Table III (latency, FPS, power)

---

## Quick Reference: Execution Order

```
Phase 1:  T-G01 ──┬──> T-G02 (optional, multi-seed)
                   │
Phase 2:  T-G03 ──>├──> T-G04 (fine-tune, requires T-G01 + T-G03)
                   │
Phase 3:           ├──> T-G05 (ONNX export, requires T-G01)
                   │
Phase 4:           ├──> T-G06 (ablation eval, requires T-G01)
                   └──> T-G07 (paper eval, requires T-G01)

Phase 5:  T-01, T-02, T-03, T-05 (independent, require T-G01 + T-G05)
```

**Minimum viable path:** T-G01 → T-G05 → T-G06 → T-G07 (~2 hours on GPU)

**Full path including fine-tuning:** T-G01 → T-G02 → T-G03 → T-G04 → T-G05 → T-G06 → T-G07 → T-01 → T-02 → T-05 (~5 hours on GPU)

---

## One-Command Alternative

If you want to run everything automatically (Phases 1–4):

```bash
python retrain_and_evaluate.py \
    --data_dir data/BCCD_r/BCCD \
    --clinical_dir data/clinical_72 \
    --output_base outputs/generalized \
    --epochs 100 \
    --batch_size 16
```

Add `--skip_finetune` to skip clinical fine-tuning, `--skip_quantize` to skip ONNX export.
