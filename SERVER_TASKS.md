# Server Tasks Queue

This file tracks the outstanding computation, benchmarking, and extraction tasks to be executed on the server or edge hardware.

---

### T-01: Benchmark INT8 ONNX Model (Exact mAP and Latency)
- **Problem:** Table III reported INT8 mAP as "≈ 0.84" instead of an empirical measurement (R1-C04, R2-C04).
- **Effort:** Small re-run / local evaluation (~2 mins).
- **Exact action:** Run evaluation of `outputs/yolov8n_int8.onnx` on the BCCD test set using `paper_eval.py` with ONNX runtime.
- **Expected output:** Exact mAP@0.5, mAP@0.5:0.95, and per-class Precision/Recall for INT8 quantized model.
- **Output location:** `server/results/T-01/`
- **Paper impact:** Table III and Section IV-E. Eliminates the approximation marker.
- **Priority:** P1 important
- **Suggested command:**
  ```bash
  python paper_eval.py --weights outputs/yolov8n_int8.onnx --bccd_test data/BCCD_r/BCCD/yolo_format --out server/results/T-01
  ```

---

### T-02: Repeatability CV% Benchmark (Protocol A & Protocol B)
- **Problem:** Repeatability table (`table_cv.tex`) contains `--` placeholders because `--fields_dir` was omitted and Protocol B was skipped (R1-C07, R2-C10).
- **Effort:** Small run (~5 mins on CPU/GPU).
- **Exact action:** Run Protocol B (algorithmic perturbation jitter: rotation ±3°, scale, brightness, contrast) across 10 sample images for 20 repetitions each.
- **Expected output:** Median CV% and IQR for RBC, WBC, and Platelets under perturbation.
- **Output location:** `server/results/T-02/table_cv.tex`
- **Paper impact:** Populates Table IV (Repeatability CV%) in Section IV.
- **Priority:** P1 important
- **Suggested command:**
  ```bash
  python paper_eval.py --weights runs/detect/outputs/checkpoints/yolov8n_hematology/weights/best.pt --bccd_test data/BCCD_r/BCCD/yolo_format --out server/results/T-02
  ```

---

### T-03: Inter-Annotator Study (Second Annotator Subset)
- **Problem:** Claim of "better than human" is unsupported by direct empirical evidence on the same task (R1-C02, R2-C02).
- **Effort:** Human annotation (~2–3 hours) + evaluation run (<1 min).
- **Exact action:** Have a second annotator independently label 20 images from `clinical_72` blind to the first annotator's labels, save YOLO txt labels in `data/second_annotator_dir`, and run `paper_eval.py --second_annotator_dir`.
- **Expected output:** Human-vs-human ICC(2,1), Bland-Altman bias/LoA, and MAPE vs Model-vs-human ICC(2,1).
- **Output location:** `server/results/T-03/table_human_baseline.tex`
- **Paper impact:** Unlocks Table V (Human-vs-Human Baseline), providing direct empirical support for clinical positioning.
- **Priority:** P0 critical for "better than human" claim (P2 if claim is framed around published literature)
- **Suggested command:**
  ```bash
  python paper_eval.py --weights runs/detect/outputs/checkpoints/yolov8n_hematology/weights/best.pt --bccd_test data/BCCD_r/BCCD/yolo_format --clinical_dir data/clinical_72 --second_annotator_dir data/second_annotator_dir --out server/results/T-03
  ```

---

### T-04: Multi-Seed Training Variance (Seeds 1, 2, 3)
- **Problem:** Single train/val/test split and single random seed (seed=0) without variance or error bars (R1-C06, R2-C08).
- **Effort:** Full training run (~1.5 hours on GPU).
- **Exact action:** Train YOLOv8n with seeds 1 and 2 for 100 epochs each on BCCD, evaluate on test set, compute mean ± standard deviation for mAP@0.5 and per-class F1.
- **Expected output:** `seed_variance.json` with mean and std for all metrics.
- **Output location:** `server/results/T-04/`
- **Paper impact:** Section IV-A and Table I reporting mean ± std.
- **Priority:** P2 useful
- **Suggested command:**
  ```bash
  for s in 1 2; do
    python train.py --model yolov8n --data_dir data/BCCD_r/BCCD/yolo_format --epochs 100 --batch_size 16
  done
  ```

---

### T-05: Hardware Profiling on Physical Raspberry Pi 4 Model B
- **Problem:** Latency (245 ms / 4.1 FPS) and power (3.4 W) were based on preliminary profiling; need verified hardware benchmark trace (R1-C05, R2-C05).
- **Effort:** Small test on physical device (~10 mins).
- **Exact action:** Run `quantize_and_infer.py` profiling routine on an actual Raspberry Pi 4B (4GB) running Raspberry Pi OS 64-bit with ONNX Runtime 1.17.
- **Expected output:** Latency distribution (mean, 50th/95th percentile ms), memory footprint (RSS MB), and power consumption.
- **Output location:** `server/results/T-05/edge_profile.json`
- **Paper impact:** Section III-E, Section V-D, and hardware efficiency table.
- **Priority:** P1 important
- **Suggested command:**
  ```bash
  python -c "import quantize_and_infer as qi; res = qi.profile_edge_inference('outputs/yolov8n_int8.onnx', num_runs=100); print(res)" > server/results/T-05/edge_profile.json
  ```
