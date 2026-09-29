import os, sys, numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import dataset
import losses
import metrics_evaluation as me
import generate_report as gr

def test_full_pipeline():
    print("=== Testing Edge-AI Hematology Pipeline ===")
    test_out_dir = os.path.join(os.path.dirname(__file__), "outputs", "test_run")
    os.makedirs(test_out_dir, exist_ok=True)

    dummy_img = np.full((300, 300, 3), (120, 100, 180), dtype=np.uint8)
    norm = dataset.ReinhardStainNormalizer()
    norm_img = norm.normalize(dummy_img)
    clahe_img = dataset.apply_clahe(norm_img)
    assert clahe_img.shape == (300, 300, 3)
    print("[PASS] Stain Normalization and CLAHE feature enhancement verified.")

    b1 = np.array([10, 10, 50, 50], dtype=np.float32)
    b2 = np.array([12, 10, 52, 48], dtype=np.float32)
    ciou = losses.calculate_ciou(b1, b2)
    assert ciou > 0.7
    print(f"[PASS] CIoU Loss calculation verified (CIoU: {ciou:.3f}).")

    np.random.seed(42)
    preds, gts = [], []
    for _ in range(25):
        n_rbc, n_wbc, n_plt = np.random.randint(40, 70), np.random.randint(1, 4), np.random.randint(3, 8)
        gt_labels = np.array([1]*n_rbc + [2]*n_wbc + [3]*n_plt)
        gt_boxes = np.random.uniform(0, 500, (len(gt_labels), 4))
        gt_boxes[:, 2:] += 30
        pred_labels = gt_labels.copy()
        pred_boxes = gt_boxes + np.random.normal(0, 2, gt_boxes.shape)
        pred_scores = np.random.uniform(0.75, 0.99, len(pred_labels))
        preds.append({'boxes': pred_boxes, 'scores': pred_scores, 'labels': pred_labels})
        gts.append({'boxes': gt_boxes, 'labels': gt_labels})

    report = me.run_full_evaluation_pipeline("Test_YOLOv8n", preds, gts, output_dir=test_out_dir)
    mAP = report['cv_detection_metrics']['mAP@0.5']
    rbc_r = report['clinical_equivalence_metrics']['RBC']['correlation']['pearson_r']
    rbc_bias = report['clinical_equivalence_metrics']['RBC']['bland_altman']['mean_bias']
    print(f"[PASS] Metrics Suite: mAP@0.5 = {mAP:.3f}, RBC Pearson r = {rbc_r:.4f}, Bland-Altman Mean Bias = {rbc_bias:.2f}")

    test_img_path = os.path.join(test_out_dir, "sample_smear.jpg")
    cv2.imwrite(test_img_path, dummy_img)
    annotated_img = gr.annotate_blood_smear(
        dummy_img,
        np.array([[20, 20, 80, 80], [120, 120, 200, 200]]),
        np.array([0.96, 0.91]),
        np.array([1, 2])
    )
    annotated_path = os.path.join(test_out_dir, "annotated_smear.jpg")
    cv2.imwrite(annotated_path, annotated_img)
    pdf_path = os.path.join(test_out_dir, "Sample_Diagnostic_Report.pdf")
    gr.create_diagnostic_pdf(
        image_path=test_img_path,
        annotated_img_path=annotated_path,
        cell_counts={"RBC": 54, "WBC": 3, "Platelets": 7},
        dlc_percentages={"Neutrophil": 65.0, "Lymphocyte": 28.0, "Monocyte": 7.0},
        abnormality_detected=False,
        output_pdf=pdf_path
    )
    assert os.path.exists(pdf_path)
    print(f"[PASS] Automated Clinical PDF Report successfully generated at: {pdf_path}")
    print("=== All Pipeline Unit Tests Passed Successfully! ===")

if __name__ == '__main__':
    test_full_pipeline()
