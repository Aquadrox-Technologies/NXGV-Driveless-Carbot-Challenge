#!/usr/bin/env python3
"""
YOLOv8-Nano Training Script — RISA-Bot Signage Detection

Trains a lightweight YOLOv8n model on your labeled signage images.
Run this on a PC/laptop with a GPU (or it will fall back to CPU).

Usage:
    # Install ultralytics first:
    pip install ultralytics

    # Train (from this directory):
    python train.py

    # Train with custom args:
    python train.py --epochs 150 --imgsz 640 --batch 32

    # Resume interrupted training:
    python train.py --resume

Output:
    runs/detect/signage_v1/weights/best.pt   — PyTorch weights (deploy on robot)
    runs/detect/signage_v1/weights/best.onnx — ONNX model (for RDK X5 BPU conversion)
"""

import argparse
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description='Train YOLOv8n for RISA-bot signage detection'
    )
    parser.add_argument(
        '--data', type=str, default='data.yaml',
        help='Path to dataset YAML config (default: data.yaml in this directory)'
    )
    parser.add_argument(
        '--model', type=str, default='yolov8n.pt',
        help='Base model to fine-tune from (default: yolov8n.pt — nano)'
    )
    parser.add_argument(
        '--epochs', type=int, default=100,
        help='Number of training epochs (default: 100)'
    )
    parser.add_argument(
        '--imgsz', type=int, default=320,
        help='Input image size (default: 320 — matches robot camera resize_width)'
    )
    parser.add_argument(
        '--batch', type=int, default=16,
        help='Batch size (default: 16, reduce if GPU OOM)'
    )
    parser.add_argument(
        '--patience', type=int, default=20,
        help='Early stopping patience in epochs (default: 20)'
    )
    parser.add_argument(
        '--resume', action='store_true',
        help='Resume training from last checkpoint'
    )
    parser.add_argument(
        '--export-only', type=str, default=None,
        help='Skip training, just export an existing .pt file to ONNX'
    )
    args = parser.parse_args()

    # ── Dependency check ─────────────────────────────────────────────────
    try:
        from ultralytics import YOLO
    except ImportError:
        print('ERROR: ultralytics not installed. Run:')
        print('  pip install ultralytics')
        sys.exit(1)

    # ── Export-only mode ─────────────────────────────────────────────────
    if args.export_only:
        pt_path = Path(args.export_only)
        if not pt_path.exists():
            print(f'ERROR: Model file not found: {pt_path}')
            sys.exit(1)
        print(f'\n=== Exporting {pt_path} to ONNX ===\n')
        model = YOLO(str(pt_path))
        model.export(format='onnx', imgsz=args.imgsz, simplify=True)
        print('\nDone! ONNX model saved alongside the .pt file.')
        return

    # ── Validate dataset config ──────────────────────────────────────────
    data_path = Path(args.data)
    if not data_path.exists():
        print(f'ERROR: Dataset config not found: {data_path}')
        print(f'Expected at: {data_path.resolve()}')
        print('Please edit data.yaml with your dataset path first.')
        sys.exit(1)

    # ── Train ────────────────────────────────────────────────────────────
    print('\n' + '=' * 60)
    print('  RISA-Bot Signage Detector — YOLOv8n Training')
    print('=' * 60)
    print(f'  Model    : {args.model}')
    print(f'  Dataset  : {data_path.resolve()}')
    print(f'  Image sz : {args.imgsz}')
    print(f'  Epochs   : {args.epochs}')
    print(f'  Batch    : {args.batch}')
    print(f'  Patience : {args.patience}')
    print('=' * 60 + '\n')

    model = YOLO(args.model)

    if args.resume:
        print('Resuming from last checkpoint...\n')
        results = model.train(resume=True)
    else:
        results = model.train(
            data=str(data_path),
            epochs=args.epochs,
            imgsz=args.imgsz,
            batch=args.batch,
            patience=args.patience,
            project='runs/detect',
            name='signage_v1',
            exist_ok=True,
            # Augmentation for small datasets
            hsv_h=0.015,       # hue augmentation
            hsv_s=0.7,         # saturation augmentation
            hsv_v=0.4,         # value/brightness augmentation
            degrees=10.0,      # rotation ±10°
            translate=0.1,     # translation ±10%
            scale=0.5,         # scale ±50%
            fliplr=0.5,        # horizontal flip 50%
            flipud=0.0,        # no vertical flip (signs don't appear upside down)
            mosaic=1.0,        # mosaic augmentation
            mixup=0.1,         # mixup augmentation
            # Performance
            workers=4,
            verbose=True,
        )

    # ── Evaluate on validation set ───────────────────────────────────────
    print('\n=== Validation Results ===\n')

    # Dynamically find best.pt from the trainer's save directory
    save_dir = Path(str(results.save_dir)) if results and hasattr(results, 'save_dir') else None
    best_path = save_dir / 'weights' / 'best.pt' if save_dir else None

    # Fallback: search for best.pt under runs/
    if not best_path or not best_path.exists():
        candidates = list(Path('runs').rglob('best.pt'))
        if candidates:
            # Use the most recently modified one
            best_path = max(candidates, key=lambda p: p.stat().st_mtime)

    if best_path and best_path.exists():
        best_model = YOLO(str(best_path))
        metrics = best_model.val(data=str(data_path), imgsz=args.imgsz)
        print(f'\n  mAP50    : {metrics.box.map50:.4f}')
        print(f'  mAP50-95 : {metrics.box.map:.4f}')
        print(f'  Precision: {metrics.box.mp:.4f}')
        print(f'  Recall   : {metrics.box.mr:.4f}')

        # Quality gate
        if metrics.box.map50 < 0.8:
            print('\n  WARNING: mAP50 < 0.8 -- consider adding more training images')
        else:
            print('\n  Model quality looks good!')

        # ── Export to ONNX ───────────────────────────────────────────────
        print('\n=== Exporting to ONNX ===\n')
        best_model.export(format='onnx', imgsz=args.imgsz, simplify=True)
        print(f'\nDone! Files saved to:')
        print(f'  PyTorch : {best_path.resolve()}')
        print(f'  ONNX    : {best_path.with_suffix(".onnx").resolve()}')
        print(f'\nCopy best.pt to your robot and set the model_path parameter.')
    else:
        print('ERROR: best.pt not found -- training may have failed.')
        sys.exit(1)


if __name__ == '__main__':
    main()
