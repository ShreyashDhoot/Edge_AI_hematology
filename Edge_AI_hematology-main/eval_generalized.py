import argparse
import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import cv2
from pathlib import Path

# Assuming these are available in the local directory
from stain_normalize_inference import (
    ReinhardNormalizerFromStats, CLAHEPreprocessor, PreprocessPipeline, 
    TestTimeAugmentor, PerClassThresholder
)
from paper_eval import (
    YoloPT, find_dataset, detection_metrics, counts_from, agreement_bundle, confusion, calibration,
    fig_bland_altman, fig_scatter_pb, fig_confusion, fig_reliability,
    CLASS_NAMES
)

def make_pipeline(model, preprocess_fn=None, tta=False):
    # Returns a callable with same interface as model
    def run(img_bgr, conf=None):
        if preprocess_fn:
            img_bgr = preprocess_fn(img_bgr)
        return model(img_bgr, conf=conf)
    if tta:
        return TestTimeAugmentor(run)
    return run

class WrappedModel:
    def __init__(self, pipeline_fn, thresholder=None):
        self.pipeline_fn = pipeline_fn
        self.thresholder = thresholder
        
    def __call__(self, img_bgr, conf=0.25):
        preds = self.pipeline_fn(img_bgr, conf=conf)
        if self.thresholder:
            preds = self.thresholder(preds)
        return preds

def run_eval(config_name, model_wrapper, dataset_dir, out_dir, conf=0.25):
    print(f"Evaluating {config_name} on {dataset_dir}")
    images, targets = find_dataset(dataset_dir)
    if len(images) == 0:
        print(f"No images found in {dataset_dir}")
        return None
        
    preds = []
    for img_path in images:
        img = cv2.imread(img_path)
        if img is None:
            print(f"Failed to read image {img_path}")
            continue
        pred = model_wrapper(img, conf=conf)
        preds.append(pred)
        
    metrics = detection_metrics(targets, preds)
    cm = confusion(targets, preds, num_classes=len(CLASS_NAMES))
    
    # agreement
    gt_counts = counts_from(targets)
    pred_counts = counts_from(preds)
    agr = agreement_bundle(gt_counts, pred_counts)
    
    # plotting
    fig_conf = fig_confusion(cm, CLASS_NAMES)
    fig_conf.savefig(os.path.join(out_dir, f'fig_confusion_{config_name}.pdf'))
    plt.close(fig_conf)
    
    for i, cls_name in enumerate(CLASS_NAMES):
        fig_ba = fig_bland_altman(gt_counts[:, i], pred_counts[:, i], title=f"{cls_name} - {config_name}")
        fig_ba.savefig(os.path.join(out_dir, f'fig_ba_{config_name}_{cls_name}.pdf'))
        plt.close(fig_ba)
        
    return {
        'metrics': metrics,
        'agreement': agr,
        'confusion': cm.tolist()
    }

def main():
    parser = argparse.ArgumentParser(description="Evaluate Generalized Model with Improvements")
    parser.add_argument('--weights', type=str, default='runs/detect/outputs/checkpoints/yolov8n_hematology_v2/weights/best.pt')
    parser.add_argument('--original_weights', type=str, default='runs/detect/outputs/checkpoints/yolov8n_hematology/weights/best.pt')
    parser.add_argument('--bccd_test', type=str, default='data/BCCD_r/BCCD/yolo_format')
    parser.add_argument('--clinical_dir', type=str, default='data/clinical_72')
    parser.add_argument('--clinical_test_dir', type=str, default='')
    parser.add_argument('--bccd_ref_dir', type=str, default='data/BCCD_r/BCCD/yolo_format/images/train')
    parser.add_argument('--out', type=str, default='outputs/generalized_results')
    parser.add_argument('--use_tta', action='store_true', default=False)
    parser.add_argument('--use_stain_norm', action='store_true', default=False)
    parser.add_argument('--plt_conf', type=float, default=0.15)
    parser.add_argument('--conf', type=float, default=0.25)
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)
    
    # Setup Models
    orig_model = YoloPT(args.original_weights)
    new_model = YoloPT(args.weights)
    
    # Preprocessing setup
    preprocess_fn = None
    if args.use_stain_norm:
        normalizer = ReinhardNormalizerFromStats(args.bccd_ref_dir)
        clahe = CLAHEPreprocessor()
        preprocess_fn = PreprocessPipeline([normalizer, clahe])
        
    # Thresholder setup
    thresholder = PerClassThresholder(default_conf=args.conf, class_confs={2: args.plt_conf})
    
    results = {}
    
    clinical_ds = args.clinical_test_dir if args.clinical_test_dir else args.clinical_dir
    
    # a. Baseline (original model, no prep)
    wrap_orig = WrappedModel(make_pipeline(orig_model))
    results['a_orig_bccd'] = run_eval('orig_bccd', wrap_orig, args.bccd_test, args.out, conf=args.conf)
    results['a_orig_clinical'] = run_eval('orig_clinical', wrap_orig, clinical_ds, args.out, conf=args.conf)
    
    # b. Retrained, no prep
    wrap_new_noprep = WrappedModel(make_pipeline(new_model))
    results['b_new_noprep_bccd'] = run_eval('new_noprep_bccd', wrap_new_noprep, args.bccd_test, args.out, conf=args.conf)
    results['b_new_noprep_clinical'] = run_eval('new_noprep_clinical', wrap_new_noprep, clinical_ds, args.out, conf=args.conf)
    
    if args.use_stain_norm:
        # c. Retrained + stain norm
        wrap_new_stain = WrappedModel(make_pipeline(new_model, preprocess_fn=preprocess_fn))
        results['c_new_stain_clinical'] = run_eval('new_stain_clinical', wrap_new_stain, clinical_ds, args.out, conf=args.conf)
        
        # d. Retrained + stain norm + threshold
        wrap_new_stain_thresh = WrappedModel(make_pipeline(new_model, preprocess_fn=preprocess_fn), thresholder=thresholder)
        results['d_new_stain_thresh_clinical'] = run_eval('new_stain_thresh_clinical', wrap_new_stain_thresh, clinical_ds, args.out, conf=args.conf)
        
        if args.use_tta:
            # e. Retrained + stain norm + threshold + tta
            wrap_new_all = WrappedModel(make_pipeline(new_model, preprocess_fn=preprocess_fn, tta=True), thresholder=thresholder)
            results['e_new_all_clinical'] = run_eval('new_all_clinical', wrap_new_all, clinical_ds, args.out, conf=args.conf)
            
    # Save JSON
    with open(os.path.join(args.out, 'generalized_results.json'), 'w') as f:
        json.dump(results, f, indent=2)
        
    # Table generation
    table_data = []
    for k, v in results.items():
        if v is None: continue
        metrics = v.get('metrics', {})
        row = {'Configuration': k, 'mAP@0.5': metrics.get('mAP@0.5', 0.0)}
        for i, c in enumerate(CLASS_NAMES):
            row[f'{c}_P'] = metrics.get('P', {}).get(i, 0.0) if isinstance(metrics.get('P'), dict) else metrics.get(f'{c}_P', 0.0)
            row[f'{c}_R'] = metrics.get('R', {}).get(i, 0.0) if isinstance(metrics.get('R'), dict) else metrics.get(f'{c}_R', 0.0)
        table_data.append(row)
        
    df = pd.DataFrame(table_data)
    # Using df.to_latex()
    with open(os.path.join(args.out, 'ablation_table.tex'), 'w') as f:
        f.write(df.to_latex(index=False))
    
    # Ablation Plot
    if not df.empty:
        plt.figure(figsize=(10, 6))
        plt.bar(df['Configuration'], df['mAP@0.5'])
        plt.xticks(rotation=45, ha='right')
        plt.title('Ablation Comparison: mAP@0.5')
        plt.tight_layout()
        plt.savefig(os.path.join(args.out, 'fig_ablation_mAP.pdf'))
        plt.close()
        
    print("\n--- Evaluation Summary ---")
    print(df.to_markdown(index=False))

if __name__ == '__main__':
    main()
