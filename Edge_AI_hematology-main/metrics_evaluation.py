import os, json, numpy as np, scipy.stats as stats, matplotlib.pyplot as plt

def compute_box_iou(box1, box2):
    x1, y1 = max(box1[0], box2[0]), max(box1[1], box2[1])
    x2, y2 = min(box1[2], box2[2]), min(box1[3], box2[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    a1 = max(0.0, (box1[2] - box1[0]) * (box1[3] - box1[1]))
    a2 = max(0.0, (box2[2] - box2[0]) * (box2[3] - box2[1]))
    return inter / (a1 + a2 - inter + 1e-7)

def evaluate_detection_metrics(all_preds, all_gts, class_names=["RBC", "WBC", "Platelets"], iou_threshold=0.5):
    results = {}
    aps = []
    for cls_idx, cls_name in enumerate(class_names, start=1):
        tp_list, fp_list, scores_list = [], [], []
        n_pos = 0
        for pred, gt in zip(all_preds, all_gts):
            gt_mask = (gt["labels"] == cls_idx)
            gt_boxes = gt["boxes"][gt_mask]
            n_pos += len(gt_boxes)
            detected = np.zeros(len(gt_boxes), dtype=bool)

            pred_mask = (pred["labels"] == cls_idx)
            pred_boxes = pred["boxes"][pred_mask]
            pred_scores = pred["scores"][pred_mask]

            sort_idx = np.argsort(-pred_scores) if len(pred_scores) > 0 else np.array([])
            for idx in sort_idx:
                p_box, p_score = pred_boxes[idx], pred_scores[idx]
                scores_list.append(p_score)
                best_iou, best_gt_idx = 0.0, -1
                for g_idx, g_box in enumerate(gt_boxes):
                    iou = compute_box_iou(p_box, g_box)
                    if iou > best_iou:
                        best_iou, best_gt_idx = iou, g_idx
                if best_iou >= iou_threshold and best_gt_idx >= 0 and not detected[best_gt_idx]:
                    tp_list.append(1); fp_list.append(0); detected[best_gt_idx] = True
                else:
                    tp_list.append(0); fp_list.append(1)

        if n_pos == 0:
            results[cls_name] = {"precision": 0.0, "recall": 0.0, "f1": 0.0, "ap": 0.0, "n_gt": 0}
            continue

        tp_arr, fp_arr, scores_arr = np.array(tp_list), np.array(fp_list), np.array(scores_list)
        if len(scores_arr) > 0:
            order = np.argsort(-scores_arr)
            tp_cumsum = np.cumsum(tp_arr[order])
            fp_cumsum = np.cumsum(fp_arr[order])
            recalls = tp_cumsum / n_pos
            precisions = tp_cumsum / np.maximum(tp_cumsum + fp_cumsum, 1e-7)
            ap = 0.0
            for t in np.linspace(0, 1.0, 11):
                p_thresh = precisions[recalls >= t]
                ap += (np.max(p_thresh) if len(p_thresh) > 0 else 0.0) / 11.0
            final_p = float(precisions[-1]) if len(precisions) > 0 else 0.0
            final_r = float(recalls[-1]) if len(recalls) > 0 else 0.0
            final_f1 = float((2 * final_p * final_r) / (final_p + final_r + 1e-7))
        else:
            final_p, final_r, final_f1, ap = 0.0, 0.0, 0.0, 0.0

        results[cls_name] = {"precision": final_p, "recall": final_r, "f1": final_f1, "ap": float(ap), "n_gt": int(n_pos)}
        aps.append(ap)
    results["mAP@0.5"] = float(np.mean(aps)) if aps else 0.0
    return results

def compute_bland_altman(model_counts, expert_counts):
    m = np.asarray(model_counts, dtype=np.float64)
    e = np.asarray(expert_counts, dtype=np.float64)
    diff = m - e
    mean_bias = float(np.mean(diff))
    sd_diff = float(np.std(diff, ddof=1)) if len(diff) > 1 else 0.0
    upper_loa = float(mean_bias + 1.96 * sd_diff)
    lower_loa = float(mean_bias - 1.96 * sd_diff)
    within = np.sum((diff >= lower_loa) & (diff <= upper_loa))
    pct_within = float((within / len(diff)) * 100.0) if len(diff) > 0 else 100.0
    return {
        "mean_bias": mean_bias, "sd_diff": sd_diff,
        "upper_loa_95": upper_loa, "lower_loa_95": lower_loa,
        "pct_within_loa": pct_within, "sample_size": int(len(diff))
    }

def compute_passing_bablok(model_counts, expert_counts):
    x, y = np.asarray(expert_counts, dtype=np.float64), np.asarray(model_counts, dtype=np.float64)
    n = len(x)
    slopes = []
    for i in range(n):
        for j in range(i + 1, n):
            dx, dy = x[j] - x[i], y[j] - y[i]
            if dx != 0:
                s = dy / dx
                if s != -1: slopes.append(s)
    slope = float(np.median(slopes)) if slopes else 1.0
    intercept = float(np.median(y - slope * x)) if len(x) > 0 else 0.0
    return {
        "slope": slope, "intercept": intercept,
        "proportional_bias_detected": not (0.95 <= slope <= 1.05),
        "constant_bias_detected": abs(intercept) > 2.0
    }

def compute_clinical_correlation(model_counts, expert_counts):
    m, e = np.asarray(model_counts, dtype=np.float64), np.asarray(expert_counts, dtype=np.float64)
    if np.std(m) > 1e-6 and np.std(e) > 1e-6:
        r, p_val = stats.pearsonr(m, e)
        rho, sp_val = stats.spearmanr(m, e)
    else:
        r, p_val, rho, sp_val = 1.0, 0.0, 1.0, 0.0
    mae = float(np.mean(np.abs(m - e)))
    safe_e = np.where(e == 0, 1.0, e)
    mape = float(np.mean(np.abs((m - e) / safe_e))) * 100.0
    return {"pearson_r": float(r), "pearson_p_value": float(p_val),
            "spearman_rho": float(rho), "spearman_p_value": float(sp_val),
            "mae": mae, "mape_percent": mape}

def compute_prediction_entropy(scores, num_classes=3):
    scores = np.clip(scores, 1e-7, 1.0)
    entropy = -np.sum(scores * np.log(scores)) / np.log(num_classes)
    return float(entropy)

def run_full_evaluation_pipeline(model_name, all_preds, all_gts, class_names=["RBC", "WBC", "Platelets"], output_dir="outputs"):
    os.makedirs(output_dir, exist_ok=True)
    report = {"model_name": model_name}
    cv_metrics = evaluate_detection_metrics(all_preds, all_gts, class_names=class_names, iou_threshold=0.5)
    report["cv_detection_metrics"] = cv_metrics

    clinical_metrics = {}
    for cls_idx, cls_name in enumerate(class_names, start=1):
        m_counts = [np.sum(p["labels"] == cls_idx) for p in all_preds]
        e_counts = [np.sum(g["labels"] == cls_idx) for g in all_gts]
        ba = compute_bland_altman(m_counts, e_counts)
        pb = compute_passing_bablok(m_counts, e_counts)
        corr = compute_clinical_correlation(m_counts, e_counts)
        clinical_metrics[cls_name] = {"bland_altman": ba, "passing_bablok": pb, "correlation": corr}

        diff = np.array(m_counts) - np.array(e_counts)
        mean_v = (np.array(m_counts) + np.array(e_counts)) / 2.0
        plt.figure(figsize=(7, 5))
        plt.scatter(mean_v, diff, color="navy", alpha=0.7, edgecolors="k", label="Blood Smear FOVs")
        plt.axhline(ba["mean_bias"], color="red", linestyle="--", label=f"Mean Bias: {ba['mean_bias']:.2f}")
        plt.axhline(ba["upper_loa_95"], color="darkorange", linestyle=":", label=f"+1.96 SD: {ba['upper_loa_95']:.2f}")
        plt.axhline(ba["lower_loa_95"], color="darkorange", linestyle=":", label=f"-1.96 SD: {ba['lower_loa_95']:.2f}")
        plt.title(f"Bland-Altman Agreement: {cls_name} ({model_name})", fontsize=12)
        plt.xlabel("Mean Count (Model + Expert) / 2", fontsize=11)
        plt.ylabel("Difference (Model - Expert)", fontsize=11)
        plt.grid(True, linestyle="--", alpha=0.5)
        plt.legend(loc="upper right", fontsize=9)
        plt.tight_layout()
        plot_path = os.path.join(output_dir, f"{model_name}_{cls_name}_bland_altman.png")
        plt.savefig(plot_path, dpi=200)
        plt.close()

    report["clinical_equivalence_metrics"] = clinical_metrics
    json_path = os.path.join(output_dir, f"{model_name}_evaluation_report.json")
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2)
    return report
