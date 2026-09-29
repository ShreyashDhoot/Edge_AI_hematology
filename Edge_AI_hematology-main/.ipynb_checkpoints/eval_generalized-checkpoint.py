#!/usr/bin/env python3
"""
eval_generalized.py - Systematic Ablation & Evaluation for Generalized Hematology Model

Evaluates:
  a. Original baseline model (on BCCD and Clinical)
  b. Retrained model (on BCCD and Clinical)
  c. Retrained model + Stain Normalization + CLAHE (on Clinical)
  d. Retrained model + Stain Norm + Per-Class Threshold (PLT=0.15) (on Clinical)
  e. Retrained model + Stain Norm + Per-Class Threshold + 4-Rotation TTA (on Clinical)
"""
import os
import sys
import json
import argparse
import numpy as np
import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from stain_normalize_inference import (
    ReinhardNormalizerFromStats, CLAHEPreprocessor, PreprocessPipeline,
    TestTimeAugmentor, PerClassThresholder
)
from paper_eval import (
    YoloPT, find_dataset, run_model, detection_metrics, counts_from,
    agreement_bundle, confusion, fig_bland_altman, fig_scatter_pb,
    fig_confusion, CLASS_NAMES
)

def evaluate_config(name, model, items, conf=0.25, preprocess=None, thresholder=None, out_dir="."):
    print(f"\n--- Running: {name} (N={len(items)}) ---")
    if not items:
        print(f"Skipping {name}: no images found.")
        return None

    preds, gts = run_model(model, items, conf=conf, preprocess=preprocess)

    if thresholder is not None:
        preds = [thresholder.filter(p) for p in preds]

    det = detection_metrics(preds, gts)
    P, G = counts_from(preds, gts)
    agr = {c: agreement_bundle(P[c], G[c]) for c in CLASS_NAMES}
    M = confusion(preds, gts)

    # Plot confusion matrix
    cm_path = os.path.join(out_dir, f"fig_confusion_{name}.pdf")
    fig_confusion(M, cm_path, f"{name}")

    # Plot Bland-Altman
    ba_path = os.path.join(out_dir, f"fig_ba_{name}.pdf")
    fig_bland_altman({c: (P[c], G[c]) for c in CLASS_NAMES}, f"Bland-Altman ({name})", ba_path)

    print(f"{name}: mAP@0.5={det['mAP50']:.3f} | mAP@0.5:0.95={det['mAP5095']:.3f}")
    for c in CLASS_NAMES:
        print(f"   {c:9s}: P={det[c]['precision']:.3f} R={det[c]['recall']:.3f} F1={det[c]['f1']:.3f} AP50={det[c]['ap50']:.3f}")

    return {
        "detection": det,
        "agreement": agr,
        "confusion": M.tolist()
    }

def clean_dict(o):
    if isinstance(o, dict): return {k: clean_dict(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)): return [clean_dict(v) for v in o]
    if isinstance(o, (np.floating,)): return float(o)
    if isinstance(o, (np.integer,)): return int(o)
    if isinstance(o, float) and not np.isfinite(o): return None
    return o

def main():
    parser = argparse.ArgumentParser(description="Evaluate Generalized Model with Improvements")
    parser.add_argument('--weights', type=str, default='outputs/generalized/checkpoints/yolov8n_hematology_v2/weights/best.pt')
    parser.add_argument('--original_weights', type=str, default='runs/detect/outputs/checkpoints/yolov8n_hematology/weights/best.pt')
    parser.add_argument('--bccd_test', type=str, default='data/BCCD_r/BCCD/yolo_format')
    parser.add_argument('--clinical_dir', type=str, default='data/clinical_72')
    parser.add_argument('--bccd_ref_dir', type=str, default='data/BCCD_r/BCCD/JPEGImages')
    parser.add_argument('--out', type=str, default='outputs/generalized/results')
    parser.add_argument('--use_tta', action='store_true', default=False)
    parser.add_argument('--use_stain_norm', action='store_true', default=False)
    parser.add_argument('--plt_conf', type=float, default=0.15)
    parser.add_argument('--conf', type=float, default=0.25)
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)

    print("Locating datasets...")
    bccd_items = find_dataset(args.bccd_test) if os.path.exists(args.bccd_test) else []
    clin_items = find_dataset(args.clinical_dir) if os.path.exists(args.clinical_dir) else []
    print(f"BCCD test set: {len(bccd_items)} images")
    print(f"Clinical 72 set: {len(clin_items)} images")

    # Load retrained model
    if not os.path.exists(args.weights):
        sys.exit(f"Error: Model weights not found at {args.weights}")
    new_model = YoloPT(args.weights, conf=args.conf)

    # Load original model if available
    orig_model = None
    if os.path.exists(args.original_weights):
        orig_model = YoloPT(args.original_weights, conf=args.conf)
    else:
        print(f"Notice: Original baseline weights not found at {args.original_weights}. Skipping baseline config.")

    # Setup Preprocessing (Stain Normalization + CLAHE)
    preprocess_fn = None
    if args.use_stain_norm:
        ref_dir = args.bccd_ref_dir
        if not os.path.exists(ref_dir) and bccd_items:
            ref_dir = os.path.dirname(bccd_items[0][0])
        pipeline = PreprocessPipeline(use_stain_norm=True, use_clahe=True, ref_dir=ref_dir)
        preprocess_fn = lambda img: pipeline(img)

    # Setup Per-Class Thresholder
    thresholder = PerClassThresholder({1: args.conf, 2: args.conf, 3: args.plt_conf})

    all_results = {}

    # Config a: Original Baseline
    if orig_model is not None:
        if bccd_items:
            all_results["a_orig_bccd"] = evaluate_config(
                "a_orig_bccd", orig_model, bccd_items, conf=args.conf, out_dir=args.out
            )
        if clin_items:
            all_results["a_orig_clinical"] = evaluate_config(
                "a_orig_clinical", orig_model, clin_items, conf=args.conf, out_dir=args.out
            )

    # Config b: Retrained v2 (no inference prep)
    if bccd_items:
        all_results["b_v2_bccd"] = evaluate_config(
            "b_v2_bccd", new_model, bccd_items, conf=args.conf, out_dir=args.out
        )
    if clin_items:
        all_results["b_v2_clinical"] = evaluate_config(
            "b_v2_clinical", new_model, clin_items, conf=args.conf, out_dir=args.out
        )

    # Config c: Retrained v2 + Stain Normalization
    if args.use_stain_norm and clin_items:
        all_results["c_v2_stain_clinical"] = evaluate_config(
            "c_v2_stain_clinical", new_model, clin_items, conf=args.conf, preprocess=preprocess_fn, out_dir=args.out
        )

    # Config d: Retrained v2 + Stain Norm + Per-Class Threshold
    if args.use_stain_norm and clin_items:
        # We run the model at a lower threshold (e.g. 0.05 or min of thresholds) so the thresholder can filter
        min_conf = min(args.conf, args.plt_conf)
        all_results["d_v2_stain_thresh_clinical"] = evaluate_config(
            "d_v2_stain_thresh_clinical", new_model, clin_items, conf=min_conf,
            preprocess=preprocess_fn, thresholder=thresholder, out_dir=args.out
        )

    # Config e: Retrained v2 + Stain Norm + Threshold + 4-Rotation TTA
    if args.use_tta and clin_items:
        min_conf = min(args.conf, args.plt_conf)
        tta_model = TestTimeAugmentor(new_model)
        all_results["e_v2_all_tta_clinical"] = evaluate_config(
            "e_v2_all_tta_clinical", tta_model, clin_items, conf=min_conf,
            preprocess=preprocess_fn, thresholder=thresholder, out_dir=args.out
        )

    # Save JSON results
    with open(os.path.join(args.out, "generalized_results.json"), "w") as f:
        json.dump(clean_dict(all_results), f, indent=2)

    # Build Ablation Table
    rows = []
    for cfg, res in all_results.items():
        if res is None:
            continue
        det = res["detection"]
        row = {
            "Configuration": cfg,
            "mAP@0.5": det["mAP50"],
            "mAP@0.5:0.95": det["mAP5095"],
            "RBC_P": det["RBC"]["precision"],
            "RBC_R": det["RBC"]["recall"],
            "RBC_F1": det["RBC"]["f1"],
            "RBC_AP50": det["RBC"]["ap50"],
            "WBC_P": det["WBC"]["precision"],
            "WBC_R": det["WBC"]["recall"],
            "WBC_F1": det["WBC"]["f1"],
            "WBC_AP50": det["WBC"]["ap50"],
            "PLT_P": det["Platelets"]["precision"],
            "PLT_R": det["Platelets"]["recall"],
            "PLT_F1": det["Platelets"]["f1"],
            "PLT_AP50": det["Platelets"]["ap50"]
        }
        rows.append(row)

    if rows:
        df = pd.DataFrame(rows)
        # Format table
        float_cols = [c for c in df.columns if c != "Configuration"]
        df_formatted = df.copy()
        for c in float_cols:
            df_formatted[c] = df_formatted[c].map(lambda x: f"{x:.3f}" if pd.notnull(x) else "--")

        # Save LaTeX Table
        with open(os.path.join(args.out, "ablation_table.tex"), "w") as f:
            f.write(df_formatted.to_latex(index=False))

        # Save ablation bar plot
        plt.figure(figsize=(8, 4))
        plt.bar(df["Configuration"], df["mAP@0.5"], color="steelblue")
        plt.xticks(rotation=30, ha="right")
        plt.ylabel("mAP@0.5")
        plt.title("Ablation Study: Detection Performance across Configurations")
        plt.grid(axis="y", linestyle="--", alpha=0.5)
        plt.tight_layout()
        plt.savefig(os.path.join(args.out, "fig_ablation_mAP.pdf"))
        plt.close()

        print("\n================== ABLATION SUMMARY ==================")
        print(df_formatted.to_string(index=False))
        print(f"\nAll outputs saved to: {args.out}")

if __name__ == "__main__":
    main()
