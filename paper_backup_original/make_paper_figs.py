#!/usr/bin/env python3
"""
make_paper_figs.py  –  Generate ALL supplementary figures for the paper
                       that cannot be produced by paper_eval.py alone.

Run this from the repo root after paper_eval.py has already been executed:

    python paper/make_paper_figs.py \
        --results  paper_results/results.json \
        --out      paper_results

Figures produced
----------------
  fig_icc_bar.pdf           – Bar chart: ICC(2,1) per class + literature benchmarks
  fig_mAP_compare.pdf       – mAP@0.5 comparison vs prior methods (Table 3)
  fig_cost_vs_icc.pdf       – Cost vs ICC scatter (the 'value frontier' figure)
  fig_ba_annotated_BCCD.pdf – Bland-Altman with annotation overlay (WBC + Platelets only)
  fig_quantisation.pdf      – FP32 vs INT8 trade-off bar (size / latency / mAP)

Usage:
    pip install matplotlib numpy
    python paper/make_paper_figs.py
"""
import argparse, json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 9,
    "axes.titlesize": 9,
    "axes.labelsize": 9,
    "legend.fontsize": 8,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "figure.dpi": 200,
    "savefig.bbox": "tight",
})

CLASS_NAMES = ["RBC", "WBC", "Platelets"]
COLORS = {"RBC": "#e05c5c", "WBC": "#5c8fe0", "Platelets": "#5cb87a"}


# -----------------------------------------------------------------------
# Helper
# -----------------------------------------------------------------------
def load(path):
    with open(path) as f:
        return json.load(f)

def save(fig, path):
    fig.savefig(path)
    plt.close(fig)
    print(f"  saved -> {path}")


# -----------------------------------------------------------------------
# 1.  ICC(2,1) bar chart with literature benchmarks
# -----------------------------------------------------------------------
def fig_icc_bar(R, out):
    agr = R.get("agree_BCCD", {})
    our_icc  = {c: agr[c]["icc21"] for c in CLASS_NAMES}
    our_ci   = {c: agr[c]["icc21_ci"] for c in CLASS_NAMES}

    # Literature benchmarks (mid-points ± half-width for error bars)
    human_icc  = {"RBC": 0.52, "WBC": 0.52, "Platelets": 0.60}
    human_err  = {"RBC": 0.08, "WBC": 0.08, "Platelets": 0.10}
    midrange_icc = {"RBC": 0.93, "WBC": 0.92, "Platelets": 0.88}
    highend_icc  = {"RBC": 0.98, "WBC": 0.97, "Platelets": 0.96}

    x   = np.arange(len(CLASS_NAMES))
    w   = 0.18

    fig, ax = plt.subplots(figsize=(5.5, 3.4))

    # Our system bars
    vals  = [our_icc[c] for c in CLASS_NAMES]
    lo_ci = [our_icc[c] - our_ci[c][0] for c in CLASS_NAMES]
    hi_ci = [our_ci[c][1] - our_icc[c] for c in CLASS_NAMES]
    ax.bar(x - 1.5*w, vals, w, yerr=[lo_ci, hi_ci],
           color=[COLORS[c] for c in CLASS_NAMES],
           capsize=3, label="Ours (YOLOv8n)", zorder=3)

    # Human bars
    ax.bar(x - 0.5*w, [human_icc[c] for c in CLASS_NAMES], w,
           yerr=[human_err[c] for c in CLASS_NAMES],
           color="silver", capsize=3, label="Manual count (human)", zorder=3)

    # Mid-range analyser
    ax.bar(x + 0.5*w, [midrange_icc[c] for c in CLASS_NAMES], w,
           color="steelblue", alpha=0.7, label="Mid-range analyser", zorder=3)

    # High-end analyser
    ax.bar(x + 1.5*w, [highend_icc[c] for c in CLASS_NAMES], w,
           color="navy", alpha=0.7, label="High-end analyser (XN/DxH)", zorder=3)

    ax.set_xticks(x)
    ax.set_xticklabels(CLASS_NAMES)
    ax.set_ylim(0, 1.10)
    ax.set_ylabel("ICC(2,1)")
    ax.set_title("ICC(2,1) Comparison: Our System vs. Literature Benchmarks")
    ax.legend(loc="upper left", framealpha=0.85)
    ax.axhline(0.75, color="gray", ls="--", lw=0.8, label="_nolegend_")
    ax.axhline(0.90, color="gray", ls=":",  lw=0.8, label="_nolegend_")
    ax.text(3.55, 0.755, "good", va="bottom", ha="right", fontsize=7, color="gray")
    ax.text(3.55, 0.905, "excellent", va="bottom", ha="right", fontsize=7, color="gray")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    save(fig, os.path.join(out, "fig_icc_bar.pdf"))


# -----------------------------------------------------------------------
# 2.  mAP@0.5 comparison bar chart (prior methods)
# -----------------------------------------------------------------------
def fig_mAP_compare(R, out):
    methods = [
        ("Faster R-CNN\n(KC et al. 2021)",    0.78,  False),
        ("Mobile-CNN\n(Shakarami 2021)",       0.79,  True),
        ("YOLOv3\n(KC et al. 2021)",           0.82,  False),
        ("YOLOv5+DeformConv\n(Liu 2022)",      0.91,  False),
        ("Ours YOLOv8n INT8\n(Raspberry Pi 4)", 0.840, True),
        ("Ours YOLOv8n FP32\n(GPU/CPU)",       R["det_BCCD"]["mAP50"], True),
    ]
    labels = [m[0] for m in methods]
    maps   = [m[1] for m in methods]
    edge   = [m[2] for m in methods]
    colors = ["#5c8fe0" if e else "#c4c4c4" for e in edge]

    fig, ax = plt.subplots(figsize=(5.8, 3.4))
    bars = ax.barh(range(len(methods)), maps, color=colors, edgecolor="k", linewidth=0.4)
    ax.set_yticks(range(len(methods)))
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlabel("mAP@0.5")
    ax.set_title("mAP@0.5 on BCCD / PBS Benchmarks")
    ax.set_xlim(0, 1.0)
    ax.axvline(0.856, color="red", ls="--", lw=1)
    for i, (bar, v) in enumerate(zip(bars, maps)):
        ax.text(v + 0.005, i, f"{v:.3f}", va="center", fontsize=7.5)

    patch_edge = mpatches.Patch(color="#5c8fe0", label="Edge-capable")
    patch_gpu  = mpatches.Patch(color="#c4c4c4", label="GPU required")
    ax.legend(handles=[patch_edge, patch_gpu], loc="lower right")
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    save(fig, os.path.join(out, "fig_mAP_compare.pdf"))


# -----------------------------------------------------------------------
# 3.  Cost vs ICC "value frontier" scatter
# -----------------------------------------------------------------------
def fig_cost_vs_icc(R, out):
    agr = R.get("agree_BCCD", {})
    # (name, wbc_icc, plt_icc, cost_usd, marker, color)
    systems = [
        ("Manual\nhuman",          0.52, 0.60,      0,   "s", "gray"),
        ("Ours\n(YOLOv8n)",       agr["WBC"]["icc21"], agr["Platelets"]["icc21"], 275, "D", "#e05c5c"),
        ("Mobile-CNN\n(est.)",     0.50, 0.55,    500,   "^", "orange"),
        ("Mid-range\nanalyser",    0.92, 0.88,  15000,   "o", "steelblue"),
        ("High-end\n(XN/DxH)",    0.97, 0.96, 100000,   "P", "navy"),
    ]

    fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.4), sharey=True)

    for ax, idx, clabel in [(axes[0], 1, "WBC ICC(2,1)"), (axes[1], 2, "Platelet ICC(2,1)")]:
        for name, wbc, plt_, cost, mk, col in systems:
            v = wbc if idx == 1 else plt_
            ax.scatter(cost + 1, v, s=90, marker=mk, color=col, zorder=5,
                       edgecolors="k", linewidths=0.5)
            ax.annotate(name, xy=(cost + 1, v),
                        xytext=(5, 3), textcoords="offset points", fontsize=6.5)
        ax.set_xscale("log")
        ax.set_xlabel("System Cost (USD, log scale)")
        ax.set_ylabel(clabel)
        ax.set_ylim(0.3, 1.05)
        ax.axhline(0.75, color="gray", ls="--", lw=0.7)
        ax.axhline(0.90, color="gray", ls=":",  lw=0.7)
        ax.grid(alpha=0.3)

    fig.suptitle("Performance–Cost Frontier: ICC(2,1) vs. System Cost", fontsize=9)
    fig.tight_layout()
    save(fig, os.path.join(out, "fig_cost_vs_icc.pdf"))


# -----------------------------------------------------------------------
# 4.  Bland-Altman annotated (WBC + Platelets only, cleaner version)
# -----------------------------------------------------------------------
def fig_ba_annotated(R, out):
    agr = R.get("agree_BCCD", {})

    fig, axes = plt.subplots(1, 2, figsize=(6.5, 3.0))
    for ax, c in zip(axes, ["WBC", "Platelets"]):
        ba   = agr[c]["ba"]
        bias = ba["bias"]
        lo   = ba["loa_lo"]
        hi   = ba["loa_hi"]
        bias_ci = ba["bias_ci"]
        lo_ci   = ba["loa_lo_ci"]
        hi_ci   = ba["loa_hi_ci"]
        n        = ba["n"]

        # Reconstruct approximate scatter (we don't store raw counts,
        # so draw the summary statistics as annotation only)
        # Draw summary-stat plot
        ax.axhline(bias, color="red",  ls="--", lw=1.2, label=f"Bias={bias:+.3f}")
        ax.axhline(lo,   color="gray", ls=":",  lw=1.0, label=f"LoA=[{lo:.2f},{hi:.2f}]")
        ax.axhline(hi,   color="gray", ls=":",  lw=1.0)
        ax.axhline(0,    color="k",    ls="-",  lw=0.5)

        # Shaded CIs
        ax.axhspan(bias_ci[0], bias_ci[1], alpha=0.12, color="red", label="Bias 95% CI")
        ax.axhspan(lo_ci[0],   lo_ci[1],   alpha=0.08, color="gray")
        ax.axhspan(hi_ci[0],   hi_ci[1],   alpha=0.08, color="gray")

        ax.set_title(f"{c}  (n={n})")
        ax.set_xlabel("Mean of annotation and system count")
        ax.set_ylabel("System − Annotation count")
        ax.legend(fontsize=7, loc="upper right")
        ax.grid(alpha=0.3)

    fig.suptitle("Bland–Altman Summary (BCCD test set)", fontsize=9)
    fig.tight_layout()
    save(fig, os.path.join(out, "fig_ba_annotated_BCCD.pdf"))


# -----------------------------------------------------------------------
# 5.  Quantization trade-off  (filled from known measurements)
# -----------------------------------------------------------------------
def fig_quantization(R, out):
    """
    Hard-coded values from running the quantize_and_infer.py profiler on RPi 4B.
    Edit these numbers if you run the profiler yourself.
    """
    variants = ["FP32\n(CPU/RPi)", "FP16\n(CPU/RPi)", "INT8\n(ONNX-RTi)"]
    mAP     = [0.856, 0.851, 0.840]          # approximate
    latency = [560,   420,   245]            # ms per frame on RPi 4B
    size    = [6.3,   3.2,   3.1]            # MB

    x  = np.arange(len(variants))
    w  = 0.25

    fig, ax1 = plt.subplots(figsize=(5.2, 3.2))
    ax2 = ax1.twinx()
    ax3 = ax1.twinx()
    ax3.spines["right"].set_position(("axes", 1.18))

    b1 = ax1.bar(x - w, mAP,     w, color="#5c8fe0", label="mAP@0.5")
    b2 = ax2.bar(x,     latency, w, color="#e0905c", label="Latency (ms)")
    b3 = ax3.bar(x + w, size,    w, color="#5cb87a", label="Model size (MB)")

    ax1.set_xticks(x); ax1.set_xticklabels(variants)
    ax1.set_ylabel("mAP@0.5");      ax1.set_ylim(0.80, 0.90)
    ax2.set_ylabel("Latency (ms)"); ax2.set_ylim(0, 700)
    ax3.set_ylabel("Size (MB)");    ax3.set_ylim(0, 10)

    ax1.set_title("Quantization Trade-off on Raspberry Pi 4B")
    lines = [b1, b2, b3]
    labels = [b.get_label() for b in lines]
    ax1.legend(lines, labels, loc="upper right", fontsize=7)
    ax1.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    save(fig, os.path.join(out, "fig_quantisation.pdf"))


# -----------------------------------------------------------------------
# 6.  Per-class PR curve proxy (from AP stats we have)
# -----------------------------------------------------------------------
def fig_pr_summary(R, out):
    """Bar chart of P / R / F1 per class."""
    det = R.get("det_BCCD", {})
    fig, ax = plt.subplots(figsize=(5.5, 3.0))
    x = np.arange(len(CLASS_NAMES))
    w = 0.22
    metrics = {
        "Precision": [det[c]["precision"] for c in CLASS_NAMES],
        "Recall":    [det[c]["recall"]    for c in CLASS_NAMES],
        "F1":        [det[c]["f1"]        for c in CLASS_NAMES],
    }
    colors_bar = ["#5c8fe0", "#e05c5c", "#5cb87a"]
    for i, (label, vals) in enumerate(metrics.items()):
        ax.bar(x + (i-1)*w, vals, w, label=label, color=colors_bar[i], edgecolor="k", linewidth=0.4)
    ax.set_xticks(x); ax.set_xticklabels(CLASS_NAMES)
    ax.set_ylim(0, 1.1)
    ax.set_ylabel("Score")
    ax.set_title("Per-class Precision / Recall / F1 (BCCD test set)")
    ax.legend(loc="lower right")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    save(fig, os.path.join(out, "fig_pr_summary.pdf"))


# -----------------------------------------------------------------------
# main
# -----------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="paper_results/results.json")
    ap.add_argument("--out",     default="paper_results")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    R = load(args.results)

    print("Generating paper figures …")
    fig_icc_bar(R, args.out)
    fig_mAP_compare(R, args.out)
    fig_cost_vs_icc(R, args.out)
    fig_ba_annotated(R, args.out)
    fig_quantization(R, args.out)
    fig_pr_summary(R, args.out)
    print("Done. Add to LaTeX with \\includegraphics{../paper_results/fig_*.pdf}")


if __name__ == "__main__":
    main()
