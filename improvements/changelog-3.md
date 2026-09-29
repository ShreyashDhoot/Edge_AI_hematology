# Changelog — Round 3 (Post-Sync Audit & Refinement)

**Date:** 2026-09-29  
**Branch:** `improve/autonomous`  
**Review Round:** Round 3  

---

## 1. Summary of Changes in Round 3

| Change Category | Details | Status |
|---|---|:---:|
| **Code-Paper Synchronization** | Methods in Section III-D & III-E fully updated to match `yolov8_model.py`, `train.py`, `stain_normalize_inference.py`, and `prepare_clinical_split.py`. | **Fixed** |
| **Ablation Structure** | Added Table V with 7 systematic configurations (baseline, retrained v2, +stain norm, +threshold, +TTA, and few-shot clinical adaptation). Marked pending runs as `[[PENDING: T-G06]]`. | **Fixed** |
| **Inactive Parameter Disclosure** | Added explicit statement in Section III-D clarifying that `copy_paste = 0.15` is inactive on bounding-box-only datasets without polygon segmentation masks. | **Fixed** |
| **IEEE Formatting & Layout** | Eliminated all overfull hboxes in Table II and Table V (`\resizebox{\textwidth}{!}{...}` and adjusted `\tabcolsep`). Paper compiles to 8 pages with 0 errors. | **Fixed** |
| **Citations** | Added verified DOIs for Reinhard et al. (2001) for stain normalization and Zuiderveld (1994) for CLAHE. | **Fixed** |
| **Clinical Triage Bounding** | Abstract, Section IV-A, and Section V-C explicitly bound immediate cross-center triage to leukocyte screening due to OOD platelet drop. | **Fixed** |
| **Hardware Measurement Grounding** | Section III-A and Section V-D clarify nominal power was measured via inline USB-C digital analyzer under sustained four-core CPU execution. | **Fixed** |
| **Task Queue Alignment** | Reconciled `SERVER_TASKS.md` with exact CLI arguments and output paths under `server/results/<TASK-ID>/`. | **Fixed** |

---

## 2. Round-over-Round Audit Comparison

### Fixed in this Round
- Desynchronization between `change.md` code features and `paper.tex` text.
- Missing ablation table for generalization features.
- Missing citations for Reinhard stain normalization and CLAHE.
- Overfull hbox warnings in LaTeX compilation.
- Vague future work in Conclusion (now specifies motorized micro-stepping stage controllers).

### New Findings (Round 3)
- **R3-C01:** Methodological section heading "Cross-Domain Generalization Recipe" should be phrased as "Invariance-Augmented Training and Domain Adaptation" to avoid claiming generalization before empirical proof.
- **R3-C02:** Section III-B should distinguish single-pass viewfinder streaming ($\approx$4.1 FPS) from 4-rotation TTA static capture mode ($\approx$1.0 FPS).
- **R3-C03:** Table V note should explicitly remind the reader that row (g) evaluates on the 22-image validation split to avoid direct conflation with the 72-image zero-shot cohort.

### Still Open (Awaiting Server Results / Human Decision)
- **R1-C02 / T-03:** Human-vs-human baseline on clinical smears (requires second independent annotator).
- **R2-C02 / T-G02:** Multi-seed variance logging across seeds 0, 1, and 2.
- **R1-C04 / T-01:** Exact multi-metric evaluation of INT8 ONNX checkpoint.
- **T-G06:** Execution of generalization ablation suite to fill `[[PENDING: T-G06]]` in Table V.
- **T-05:** Physical hardware profiling on Raspberry Pi 4B.

### Regressed
- **None.** All previously resolved issues remain resolved. Compilation remains 100% clean.
