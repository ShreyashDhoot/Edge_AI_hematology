# How to Build the Paper

## 1. Generate Supplementary Figures
Run this from the **repo root** (after `paper_eval.py` has already run and `paper_results/results.json` exists):

```bash
python paper/make_paper_figs.py \
    --results paper_results/results.json \
    --out     paper_results
```

This produces six PDF figures in `paper_results/`:
| Figure | Description |
|---|---|
| `fig_icc_bar.pdf` | ICC(2,1) bar chart + literature benchmarks |
| `fig_mAP_compare.pdf` | mAP@0.5 vs prior methods |
| `fig_cost_vs_icc.pdf` | Cost–performance frontier scatter |
| `fig_ba_annotated_BCCD.pdf` | Bland–Altman with shaded CI overlay |
| `fig_quantisation.pdf` | FP32 / FP16 / INT8 quantization trade-off |
| `fig_pr_summary.pdf` | Per-class P / R / F1 bar chart |

`paper_eval.py` also produces:
- `fig_confusion_BCCD.pdf`
- `fig_ba_BCCD.pdf`
- `fig_pb_BCCD.pdf`
- `fig_reliability.pdf`

## 2. Compile the LaTeX Paper

You need a LaTeX distribution with **IEEEtran**.  
With TeX Live or MiKTeX installed:

```bash
cd paper
pdflatex main
bibtex main
pdflatex main
pdflatex main
```

The final `main.pdf` will be in `paper/`.

## 3. Customise Before Submission
- Fill in **author names** in `\author{...}`.
- If you have Raspberry Pi latency measurements from `quantize_and_infer.py`, update the hard-coded values in `make_paper_figs.py → fig_quantization()`.
- If you run the second-annotator study (`--second_annotator_dir`), uncomment Table V (human baseline) in `main.tex`.

## 4. Missing Arguments in paper_eval.py
The following optional arguments improve the paper but are not required:

| Argument | What it unlocks |
|---|---|
| `--second_annotator_dir` | **Key table**: human vs human ICC → lets you claim "better than a human" with data |
| `--fields_dir` | Protocol-A repeatability CV% (10–20 fields from one slide) |
| `--onnx_int8` | INT8 latency + size comparison (Table G in eval output) |
| `--clinical_dir` | OOD domain-shift evaluation (currently 0 images) |

