# Change Log: Generalization Improvements

**Date:** 2026-09-29
**Branch:** `improve/autonomous`
**Purpose:** Implement all generalization improvements identified in the OOD audit to improve cross-domain performance on the Clinical 72 benchmark (current mAP@0.5 = 0.412)

---

## Summary of Changes

### 1. Training Augmentation Overhaul — `models/yolov8_model.py`

| Hyperparameter | Old Value | New Value | Rationale |
|---|---|---|---|
| `degrees` | 0.0 | **180.0** | Full rotation invariance — microscopy has no canonical orientation |
| `flipud` | 0.0 | **0.5** | Vertical flip — same reasoning as horizontal flip |
| `mixup` | 0.0 | **0.15** | Soft decision boundary regularization |
| `copy_paste` | 0.0 | **0.15** | Synthesize platelet-dense regions to address class imbalance |
| `dropout` | 0.0 | **0.1** | Regularization in detection head to reduce domain-specific memorization |
| `close_mosaic` | 10 | **15** | Longer stabilization phase after mosaic is disabled |
| `patience` | 15 | **20** | More exploration room with heavier augmentation |
| `run_name` | `yolov8n_hematology` | **`yolov8n_hematology_v2`** | Distinguish retrained model from original |

**Unchanged (kept as-is):** `mosaic=1.0`, `fliplr=0.5`, `erasing=0.4`, `auto_augment=randaugment`, `hsv_h=0.015`, `hsv_s=0.7`, `hsv_v=0.4`, `scale=0.5`, `translate=0.1`, `cos_lr=True`, `pretrained=True`

**New method added:** `train_finetune()` — loads a trained checkpoint, freezes the first 10 backbone layers, fine-tunes the detection head on clinical data with `lr0=0.001` for 30 epochs.

### 2. CLI Argument Expansion — `train.py`

New arguments added to `parse_args()`:

| Argument | Type | Default | Purpose |
|---|---|---|---|
| `--run_name` | str | `yolov8n_hematology_v2` | Output subfolder name |
| `--seed` | int | 0 | Training seed |
| `--dropout` | float | 0.1 | Dropout rate in detection head |
| `--degrees` | float | 180.0 | Rotation augmentation degrees |
| `--flipud` | float | 0.5 | Vertical flip probability |
| `--mixup` | float | 0.15 | MixUp alpha |
| `--copy_paste` | float | 0.15 | Copy-paste augmentation probability |
| `--close_mosaic` | int | 15 | Epoch to disable mosaic |
| `--finetune_weights` | str | `""` | Path to .pt for fine-tuning |
| `--finetune_lr` | float | 0.001 | Learning rate for fine-tuning |
| `--freeze_backbone` | int | 10 | Layers to freeze in fine-tuning |

`train_yolov8()` now branches: if `--finetune_weights` is set, calls `detector.train_finetune()`; otherwise calls `detector.train()` with all new augmentation args.

`train_torch_model()` is **completely untouched** — SSDLite/PicoDet training path is preserved.

### 3. Stain Normalization & TTA Pipeline — `stain_normalize_inference.py` (NEW)

| Class | Purpose |
|---|---|
| `ReinhardNormalizerFromStats` | Computes LAB mean/std across BCCD reference images; normalizes OOD images to match |
| `CLAHEPreprocessor` | Adaptive histogram equalization on L channel (clip=2.0, grid=8×8) |
| `PreprocessPipeline` | Chains Reinhard + CLAHE into a single callable |
| `TestTimeAugmentor` | 4-rotation TTA (0°/90°/180°/270°) with coordinate back-mapping and per-class NMS merge |
| `PerClassThresholder` | Per-class confidence thresholds (RBC=0.25, WBC=0.25, PLT=0.15) |

All classes return numpy arrays compatible with `paper_eval.py`'s detection metric functions.

### 4. Clinical Data Split — `prepare_clinical_split.py` (NEW)

Splits the 72 annotated clinical images into YOLO-format train/val:
- Default: 70% train (50 images), 30% val (22 images)
- Converts VOC XML annotations to YOLO txt format
- Creates `data.yaml` with absolute paths
- Prints class instance counts per split

### 5. Ablation Evaluation — `eval_generalized.py` (NEW)

Runs a systematic ablation study comparing:

| Configuration | Preprocessing | Model | Notes |
|---|---|---|---|
| Baseline (original) | None | Original best.pt | Reference |
| Retrained (v2) | None | v2 best.pt | Augmentation improvements only |
| v2 + stain norm | Reinhard + CLAHE | v2 best.pt | Preprocessing only |
| v2 + stain norm + threshold | Reinhard + CLAHE + per-class conf | v2 best.pt | + PLT threshold 0.15 |
| v2 + stain norm + threshold + TTA | Reinhard + CLAHE + per-class conf + 4-rot | v2 best.pt | Full pipeline |

Outputs per configuration:
- Detection metrics (P, R, F1, AP@0.5 per class, mAP@0.5, mAP@0.5:0.95)
- Agreement stats (Pearson, ICC, Bland-Altman, Passing-Bablok)
- Confusion matrix figure
- Ablation comparison table (LaTeX + JSON)

### 6. Master Orchestration — `retrain_and_evaluate.py` (NEW)

Single-command pipeline that runs all 6 steps:

1. **Retrain** YOLOv8n with generalization improvements
2. **Prepare** clinical train/val split
3. **Fine-tune** retrained model on clinical data
4. **Export** ONNX + INT8 quantization
5. **Evaluate** via `eval_generalized.py` (ablation study)
6. **Paper eval** via `paper_eval.py` (full paper metrics)

Each step is independently skippable (`--skip_retrain`, `--skip_finetune`, `--skip_eval`, `--skip_quantize`) and failure-isolated.

---

## Output Directory Structure

All outputs from the generalization pipeline are saved under `outputs/generalized/`:

```
outputs/generalized/
├── checkpoints/
│   ├── yolov8n_hematology_v2/          # Retrained model
│   │   ├── weights/
│   │   │   ├── best.pt                 # Best retrained checkpoint
│   │   │   └── last.pt
│   │   ├── args.yaml                   # Training config
│   │   ├── results.csv                 # Training log
│   │   └── results.png                 # Loss curves
│   └── yolov8n_hematology_v2_clinical/ # Fine-tuned model
│       └── weights/
│           ├── best.pt                 # Best fine-tuned checkpoint
│           └── last.pt
├── clinical_split/                     # Clinical train/val data
│   ├── images/train/
│   ├── images/val/
│   ├── labels/train/
│   ├── labels/val/
│   └── data.yaml
├── onnx/                              # Quantized models
│   ├── yolov8n_hematology_v2.onnx     # FP32 ONNX
│   └── yolov8n_hematology_v2_int8.onnx # INT8 ONNX
├── results/                           # Ablation evaluation results
│   ├── generalized_results.json
│   ├── ablation_table.tex
│   ├── fig_confusion_*.pdf
│   ├── fig_ba_*.pdf
│   └── fig_ablation_mAP.pdf
└── paper_results/                     # Full paper_eval.py results
    ├── results.json
    ├── table_detection.tex
    ├── table_agreement.tex
    └── fig_*.pdf
```

---

## Downstream Impact on Paper

After running the pipeline, the following paper sections will need updating with new numbers:

| Paper Section | Table/Figure | What Changes |
|---|---|---|
| Table I (Detection Metrics) | All per-class P/R/F1/AP values | Retrained v2 numbers replace original |
| Table II (Agreement Statistics) | Pearson, ICC, Bland-Altman, P-B | Retrained v2 agreement stats |
| Table III (Quantization) | INT8 mAP, size, latency | New ONNX from retrained model |
| Section IV-A (Results) | In-text mAP claims | Updated values |
| Section V (Discussion) | OOD performance analysis | Ablation results discussion |
| New: Ablation Table | mAP across configurations | Shows improvement trajectory |
| New: Domain Adaptation Discussion | Stain norm + TTA gains | Positions inference-time fixes |

---

## Files Changed

| File | Status | Lines Changed |
|---|---|---|
| `models/yolov8_model.py` | **Modified** | 39 → 87 lines (+48) |
| `train.py` | **Modified** | 203 → 242 lines (+39) |
| `stain_normalize_inference.py` | **Created** | 254 lines |
| `prepare_clinical_split.py` | **Created** | ~150 lines |
| `eval_generalized.py` | **Created** | ~300 lines |
| `retrain_and_evaluate.py` | **Created** | ~250 lines |
| `SERVER_TASKS.md` | **Rewritten** | Complete rewrite with start-to-end commands |

---

## How to Run

### Quick Start (one command does everything):
```bash
python retrain_and_evaluate.py \
    --data_dir data/BCCD_r/BCCD \
    --clinical_dir data/clinical_72 \
    --output_base outputs/generalized \
    --epochs 100 --batch_size 16
```

### See `SERVER_TASKS.md` for the detailed step-by-step command sequence.
