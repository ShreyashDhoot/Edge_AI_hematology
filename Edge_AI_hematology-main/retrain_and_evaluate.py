import argparse
import subprocess
import sys
import os
from pathlib import Path

def print_banner(text):
    print("\n" + "="*80)
    print(f"=== {text} ===")
    print("="*80 + "\n")

def run_step(step_num, step_name, cmd, executed_steps, errors):
    print_banner(f"Step {step_num}: {step_name}")
    try:
        print(f"Running command: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)
        executed_steps.append(f"Step {step_num}: {step_name}")
    except subprocess.CalledProcessError as e:
        err_msg = f"Step {step_num} failed with exit code {e.returncode}"
        print(f"ERROR: {err_msg}")
        errors.append(err_msg)
    except Exception as e:
        err_msg = f"Step {step_num} failed with error: {str(e)}"
        print(f"ERROR: {err_msg}")
        errors.append(err_msg)

def main():
    parser = argparse.ArgumentParser(description="Master Orchestration Script for Edge AI Hematology")
    parser.add_argument('--data_dir', type=str, default='data/BCCD_r/BCCD', help='BCCD dataset root')
    parser.add_argument('--clinical_dir', type=str, default='data/clinical_72', help='Clinical 72-image dir')
    parser.add_argument('--output_base', type=str, default='outputs/generalized', help='Base output directory')
    parser.add_argument('--epochs', type=int, default=100, help='Number of epochs for retraining')
    parser.add_argument('--batch_size', type=int, default=16, help='Batch size')
    parser.add_argument('--seed', type=int, default=0, help='Random seed')
    parser.add_argument('--skip_retrain', action='store_true', help='Skip retraining, only run eval')
    parser.add_argument('--skip_finetune', action='store_true', help='Skip clinical fine-tuning')
    parser.add_argument('--skip_eval', action='store_true', help='Skip evaluation')
    parser.add_argument('--skip_quantize', action='store_true', help='Skip ONNX export & INT8 quantization')
    
    args = parser.parse_args()

    executed_steps = []
    errors = []

    # Setup directories
    output_base_path = Path(args.output_base)
    checkpoints_dir = output_base_path / "checkpoints"
    clinical_split_dir = output_base_path / "clinical_split"
    onnx_dir = output_base_path / "onnx"
    results_dir = output_base_path / "results"
    paper_results_dir = output_base_path / "paper_results"

    for d in [checkpoints_dir, clinical_split_dir, onnx_dir, results_dir, paper_results_dir]:
        d.mkdir(parents=True, exist_ok=True)

    base_weights_path = checkpoints_dir / "yolov8n_hematology_v2" / "weights" / "best.pt"
    finetuned_weights_path = checkpoints_dir / "yolov8n_hematology_v2_clinical" / "weights" / "best.pt"
    
    # Step 1: Retrain
    if not args.skip_retrain:
        cmd_train = [
            sys.executable, 'train.py',
            '--model', 'yolov8n',
            '--data_dir', args.data_dir,
            '--epochs', str(args.epochs),
            '--batch_size', str(args.batch_size),
            '--output_dir', str(checkpoints_dir),
            '--run_name', 'yolov8n_hematology_v2',
            '--seed', str(args.seed),
            '--degrees', '180',
            '--flipud', '0.5',
            '--mixup', '0.15',
            '--copy_paste', '0.15',
            '--dropout', '0.1',
            '--close_mosaic', '15',
            '--patience', '20'
        ]
        run_step(1, "Retrain YOLOv8n with generalization improvements", cmd_train, executed_steps, errors)
    else:
        print("Skipping Step 1: Retrain YOLOv8n")

    # Step 2: Prepare clinical split
    if not args.skip_finetune:
        cmd_split = [
            sys.executable, 'prepare_clinical_split.py',
            '--clinical_dir', args.clinical_dir,
            '--output_dir', str(clinical_split_dir),
            '--train_ratio', '0.7',
            '--seed', '42'
        ]
        run_step(2, "Prepare clinical split", cmd_split, executed_steps, errors)

    # Step 3: Fine-tune
    if not args.skip_finetune:
        cmd_finetune = [
            sys.executable, 'train.py',
            '--model', 'yolov8n',
            '--data_dir', str(clinical_split_dir),
            '--finetune_weights', str(base_weights_path),
            '--epochs', '30',
            '--batch_size', '8',
            '--output_dir', str(checkpoints_dir),
            '--run_name', 'yolov8n_hematology_v2_clinical',
            '--finetune_lr', '0.001',
            '--freeze_backbone', '10'
        ]
        run_step(3, "Fine-tune on clinical data", cmd_finetune, executed_steps, errors)
    else:
        print("Skipping Steps 2 & 3: Clinical split and Fine-tuning")

    # Step 4: Export ONNX + INT8 quantization
    if not args.skip_quantize:
        print_banner("Step 4: Export ONNX + INT8 quantization")
        try:
            weights_to_export = finetuned_weights_path if finetuned_weights_path.exists() else base_weights_path
            print(f"Exporting weights: {weights_to_export}")
            
            # Use ultralytics YOLO to export to ONNX
            from ultralytics import YOLO
            model = YOLO(str(weights_to_export))
            model.export(format='onnx', imgsz=640)
            
            onnx_path = weights_to_export.with_suffix('.onnx')
            
            cmd_quant = [
                sys.executable, 'quantize_and_infer.py',
                '--weights', str(onnx_path),
                '--output_dir', str(onnx_dir)
            ]
            print(f"Running command: {' '.join(cmd_quant)}")
            subprocess.run(cmd_quant, check=False)
            
            executed_steps.append("Step 4: Export ONNX + INT8 quantization")
        except Exception as e:
            err_msg = f"Step 4 failed with error: {str(e)}"
            print(f"ERROR: {err_msg}")
            errors.append(err_msg)
    else:
        print("Skipping Step 4: Export ONNX + INT8 quantization")

    # Step 5: Run comprehensive evaluation
    if not args.skip_eval:
        weights_to_eval = finetuned_weights_path if finetuned_weights_path.exists() else base_weights_path
        cmd_eval = [
            sys.executable, 'eval_generalized.py',
            '--weights', str(weights_to_eval),
            '--data_dir', args.data_dir,
            '--output_dir', str(results_dir),
            '--use_stain_norm',
            '--use_tta'
        ]
        run_step(5, "Run comprehensive evaluation", cmd_eval, executed_steps, errors)
        
        # Step 6: Run paper_eval.py
        cmd_paper_eval = [
            sys.executable, 'paper_eval.py',
            '--weights', str(weights_to_eval),
            '--output_dir', str(paper_results_dir)
        ]
        run_step(6, "Run paper evaluation suite", cmd_paper_eval, executed_steps, errors)
    else:
        print("Skipping Steps 5 & 6: Evaluation")

    print_banner("Summary")
    print(f"Output Base Directory: {output_base_path.absolute()}")
    print("\nOutputs saved to:")
    print(f"  Checkpoints: {checkpoints_dir}")
    print(f"  Clinical Split: {clinical_split_dir}")
    print(f"  ONNX/Quantized: {onnx_dir}")
    print(f"  Evaluation Results: {results_dir}")
    print(f"  Paper Eval Results: {paper_results_dir}")
    
    print("\nExecuted Steps:")
    for step in executed_steps:
        print(f"  - {step}")
        
    if errors:
        print("\nErrors Encountered:")
        for err in errors:
            print(f"  - {err}")
    else:
        print("\nAll executed steps completed successfully.")

if __name__ == '__main__':
    main()
