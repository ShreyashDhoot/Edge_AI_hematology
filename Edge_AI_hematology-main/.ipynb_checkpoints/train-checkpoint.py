import os
import argparse
import time
import csv
import cv2
import numpy as np
import matplotlib.pyplot as plt

try:
    import torch
    import torch.optim as optim
    from torch.utils.data import DataLoader
    from torch.optim.lr_scheduler import CosineAnnealingLR
except ImportError:
    torch = None

from dataset import BloodSmearVOCDataset, blood_smear_collate_fn, convert_voc_to_yolo
from losses import AlphaBalancedFocalLoss
from models import get_model


def parse_args():
    parser = argparse.ArgumentParser(description="Train Edge-AI Hematology Models")
    parser.add_argument("--model", type=str, default="yolov8n", choices=["yolov8n", "ssdlite_mobilenetv3", "picodet_s"])
    parser.add_argument("--data_dir", type=str, default="data/BCCD")
    parser.add_argument("--img_size", type=int, default=640)
    parser.add_argument("--batch_size", type=int, default=16)
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--weight_decay", type=float, default=5e-4)
    parser.add_argument("--patience", type=int, default=15)
    parser.add_argument("--output_dir", type=str, default="outputs/checkpoints")
    return parser.parse_args()


def train_yolov8(args):
    from models.yolov8_model import YOLOv8HematologyDetector
    detector = YOLOv8HematologyDetector(model_size="yolov8n.pt", num_classes=3)
    data_yaml = os.path.join(args.data_dir, "data.yaml")
    if not os.path.exists(data_yaml):
        convert_voc_to_yolo(args.data_dir, os.path.join(args.data_dir, "yolo_format"))
        data_yaml = os.path.join(args.data_dir, "yolo_format", "data.yaml")
    return detector.train(
        data_yaml=data_yaml,
        epochs=args.epochs,
        imgsz=args.img_size,
        batch=args.batch_size,
        weight_decay=args.weight_decay,
        patience=args.patience,
        project_dir=args.output_dir
    )


def train_torch_model(args):
    if torch is None:
        raise RuntimeError("PyTorch is required for native model training.")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # Dedicated run folder for SSDLite / PicoDet matching YOLO's folder structure
    run_dir = os.path.join(args.output_dir, f"{args.model}_hematology")
    weights_dir = os.path.join(run_dir, "weights")
    os.makedirs(weights_dir, exist_ok=True)

    # 1. Dataset & DataLoader (Auto-tune input size: 320 for SSDLite, 640 default)
    input_size = 320 if "ssdlite" in args.model else args.img_size
    train_dataset = BloodSmearVOCDataset(args.data_dir, is_train=True, img_size=input_size)
    val_dataset = BloodSmearVOCDataset(args.data_dir, is_train=False, img_size=input_size)

    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True, 
                              collate_fn=blood_smear_collate_fn, num_workers=2)
    val_loader = DataLoader(val_dataset, batch_size=args.batch_size, shuffle=False, 
                            collate_fn=blood_smear_collate_fn, num_workers=2)

    # 2. Model & Optimizer
    model = get_model(args.model, num_classes=3, pretrained=True).to(device)
    optimizer = optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    scheduler = CosineAnnealingLR(optimizer, T_max=args.epochs, eta_min=1e-6)

    best_val_loss = float("inf")
    patience_counter = 0

    # Initialize CSV logger
    csv_path = os.path.join(run_dir, "results.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["epoch", "train/loss", "val/loss", "lr"])

    history = {"train_loss": [], "val_loss": [], "lr": []}

    print(f"=== Starting Training: {args.model} | Epochs: {args.epochs} | Device: {device} ===")
    for epoch in range(1, args.epochs + 1):
        model.train()
        epoch_loss = 0.0
        for images, targets in train_loader:
            images = images.to(device)
            targets = [{k: v.to(device) for k, v in t.items()} for t in targets]

            optimizer.zero_grad()
            loss_dict = model(images, targets)
            losses = sum(loss for loss in loss_dict.values())
            losses.backward()
            optimizer.step()
            epoch_loss += losses.item()

        current_lr = scheduler.get_last_lr()[0]
        scheduler.step()
        avg_train_loss = epoch_loss / max(1, len(train_loader))

        # Validation Phase (keep model in train mode to compute loss dict without gradient updates)
        val_loss = 0.0
        with torch.no_grad():
            for images, targets in val_loader:
                images = images.to(device)
                targets = [{k: v.to(device) for k, v in t.items()} for t in targets]
                loss_dict = model(images, targets)
                val_loss += sum(loss for loss in loss_dict.values()).item()

        avg_val_loss = val_loss / max(1, len(val_loader))
        print(f"Epoch [{epoch:03d}/{args.epochs:03d}] Train Loss: {avg_train_loss:.4f} | Val Loss: {avg_val_loss:.4f} | LR: {current_lr:.6f}")

        # Log metrics to CSV
        history["train_loss"].append(avg_train_loss)
        history["val_loss"].append(avg_val_loss)
        history["lr"].append(current_lr)

        with open(csv_path, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([epoch, avg_train_loss, avg_val_loss, current_lr])

        # Checkpoint Best Model
        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            patience_counter = 0
            best_ckpt = os.path.join(weights_dir, "best.pt")
            torch.save(model.state_dict(), best_ckpt)
            # Legacy path compatibility
            torch.save(model.state_dict(), os.path.join(args.output_dir, f"{args.model}_best.pth"))
            print(f"[*] Checkpoint saved: {best_ckpt}")
        else:
            patience_counter += 1
            if patience_counter >= args.patience:
                print(f"[!] Early stopping triggered at epoch {epoch}. Best Val Loss: {best_val_loss:.4f}")
                break

    # Save Last Model
    torch.save(model.state_dict(), os.path.join(weights_dir, "last.pt"))

    # 3. Generate Training Curves (results.png)
    plt.figure(figsize=(10, 4))
    plt.subplot(1, 2, 1)
    plt.plot(range(1, len(history["train_loss"]) + 1), history["train_loss"], label="Train Loss", color="royalblue")
    plt.plot(range(1, len(history["val_loss"]) + 1), history["val_loss"], label="Val Loss", color="crimson")
    plt.title(f"{args.model} Loss Convergence")
    plt.xlabel("Epoch")
    plt.ylabel("Loss")
    plt.legend()
    plt.grid(True, linestyle="--", alpha=0.5)

    plt.subplot(1, 2, 2)
    plt.plot(range(1, len(history["lr"]) + 1), history["lr"], label="Learning Rate", color="forestgreen")
    plt.title("Cosine Annealing LR Schedule")
    plt.xlabel("Epoch")
    plt.ylabel("LR")
    plt.legend()
    plt.grid(True, linestyle="--", alpha=0.5)

    plt.tight_layout()
    plots_path = os.path.join(run_dir, "results.png")
    plt.savefig(plots_path, dpi=200)
    plt.close()
    print(f"[*] Training curves saved to: {plots_path}")

    # 4. Generate Visual Validation Batch (val_batch0_pred.jpg vs val_batch0_labels.jpg)
    model.eval()
    with torch.no_grad():
        for images, targets in val_loader:
            img_disp = (images[0].permute(1, 2, 0).cpu().numpy() * 255.0).astype(np.uint8)
            img_pred = img_disp.copy()
            img_gt = img_disp.copy()

            # Draw Ground Truth Boxes (Green)
            for box, lbl in zip(targets[0]["boxes"].cpu().numpy(), targets[0]["labels"].cpu().numpy()):
                x1, y1, x2, y2 = map(int, box)
                cv2.rectangle(img_gt, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.imwrite(os.path.join(run_dir, "val_batch0_labels.jpg"), cv2.cvtColor(img_gt, cv2.COLOR_RGB2BGR))

            # Draw Predicted Boxes (Blue)
            preds = model([images[0].to(device)])[0]
            for box, score, lbl in zip(preds["boxes"].cpu().numpy(), preds["scores"].cpu().numpy(), preds["labels"].cpu().numpy()):
                if score >= 0.35:
                    x1, y1, x2, y2 = map(int, box)
                    cv2.rectangle(img_pred, (x1, y1), (x2, y2), (255, 0, 0), 2)
            cv2.imwrite(os.path.join(run_dir, "val_batch0_pred.jpg"), cv2.cvtColor(img_pred, cv2.COLOR_RGB2BGR))
            break
    print(f"[*] Visual validation batches saved to: {run_dir}")


if __name__ == "__main__":
    args = parse_args()
    if args.model == "yolov8n":
        train_yolov8(args)
    else:
        train_torch_model(args)