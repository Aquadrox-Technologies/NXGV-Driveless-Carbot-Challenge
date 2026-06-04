#!/usr/bin/env python3
"""
COCO → YOLO Format Converter for RISA-Bot Signage Dataset

Reads a Roboflow COCO-format dataset and converts it to YOLO format:
  - Copies images into images/train and images/val
  - Converts COCO bounding-box annotations to YOLO .txt label files

Usage:
    python convert_coco_to_yolo.py \
        --coco-dir "C:/Users/Victus/OneDrive/Desktop/RISAbot.v1-risabotdataset.coco" \
        --output-dir "./dataset_yolo"
"""

import argparse
import json
import shutil
import sys
from pathlib import Path


def convert_coco_split(coco_json_path: Path, images_src_dir: Path,
                       images_dst_dir: Path, labels_dst_dir: Path,
                       cat_id_remap: dict):
    """Convert a single COCO split (train or val) to YOLO format."""
    with open(coco_json_path, 'r') as f:
        coco = json.load(f)

    # Build lookup: image_id -> image info
    id_to_img = {img['id']: img for img in coco['images']}

    # Build lookup: image_id -> list of annotations
    img_to_anns = {}
    for ann in coco['annotations']:
        img_id = ann['image_id']
        img_to_anns.setdefault(img_id, []).append(ann)

    images_dst_dir.mkdir(parents=True, exist_ok=True)
    labels_dst_dir.mkdir(parents=True, exist_ok=True)

    converted = 0
    skipped_cats = set()

    for img_id, img_info in id_to_img.items():
        filename = img_info['file_name']
        img_w = img_info['width']
        img_h = img_info['height']

        # Copy image
        src_img = images_src_dir / filename
        dst_img = images_dst_dir / filename
        if src_img.exists() and not dst_img.exists():
            shutil.copy2(src_img, dst_img)

        # Convert annotations to YOLO format
        label_file = labels_dst_dir / (Path(filename).stem + '.txt')
        lines = []
        for ann in img_to_anns.get(img_id, []):
            cat_id = ann['category_id']
            if cat_id not in cat_id_remap:
                skipped_cats.add(cat_id)
                continue
            yolo_class = cat_id_remap[cat_id]

            # COCO bbox = [x_min, y_min, width, height] (absolute pixels)
            bx, by, bw, bh = ann['bbox']

            # Convert to YOLO: x_center, y_center, width, height (normalized)
            x_center = (bx + bw / 2.0) / img_w
            y_center = (by + bh / 2.0) / img_h
            w_norm = bw / img_w
            h_norm = bh / img_h

            # Clamp to [0, 1]
            x_center = max(0.0, min(1.0, x_center))
            y_center = max(0.0, min(1.0, y_center))
            w_norm = max(0.0, min(1.0, w_norm))
            h_norm = max(0.0, min(1.0, h_norm))

            lines.append(f'{yolo_class} {x_center:.6f} {y_center:.6f} '
                          f'{w_norm:.6f} {h_norm:.6f}')

        with open(label_file, 'w') as f:
            f.write('\n'.join(lines))
            if lines:
                f.write('\n')

        converted += 1

    if skipped_cats:
        print(f'  ⚠ Skipped category IDs (not in remap): {skipped_cats}')

    return converted


def main():
    parser = argparse.ArgumentParser(
        description='Convert Roboflow COCO dataset to YOLO format'
    )
    parser.add_argument(
        '--coco-dir', type=str, required=True,
        help='Path to the Roboflow COCO dataset root '
             '(contains train/ and valid/ subdirectories)'
    )
    parser.add_argument(
        '--output-dir', type=str, default='./dataset_yolo',
        help='Output directory for the YOLO dataset (default: ./dataset_yolo)'
    )
    args = parser.parse_args()

    coco_root = Path(args.coco_dir)
    output_root = Path(args.output_dir)

    # Validate input
    if not coco_root.exists():
        print(f'ERROR: COCO dataset directory not found: {coco_root}')
        sys.exit(1)

    # Read categories from training annotations
    train_json = coco_root / 'train' / '_annotations.coco.json'
    if not train_json.exists():
        print(f'ERROR: Training annotations not found: {train_json}')
        sys.exit(1)

    with open(train_json, 'r') as f:
        coco_data = json.load(f)

    categories = coco_data['categories']
    print(f'\n=== COCO Categories Found ===')
    for cat in categories:
        print(f"  ID {cat['id']}: {cat['name']}")

    # Build COCO category ID → YOLO class ID mapping
    # Skip the generic 'RISAbot' parent category (id=0) if present
    # Remap remaining categories to sequential 0-based YOLO class IDs
    useful_cats = [c for c in categories if c['name'] != 'RISAbot']
    useful_cats.sort(key=lambda c: c['id'])

    cat_id_remap = {}
    yolo_names = {}
    for yolo_id, cat in enumerate(useful_cats):
        cat_id_remap[cat['id']] = yolo_id
        yolo_names[yolo_id] = cat['name']

    print(f'\n=== YOLO Class Mapping ===')
    for yolo_id, name in yolo_names.items():
        coco_id = [k for k, v in cat_id_remap.items() if v == yolo_id][0]
        print(f'  YOLO {yolo_id} <- COCO {coco_id}: {name}')

    # Convert train split
    print(f'\n--- Converting train split ---')
    train_count = convert_coco_split(
        coco_json_path=coco_root / 'train' / '_annotations.coco.json',
        images_src_dir=coco_root / 'train',
        images_dst_dir=output_root / 'images' / 'train',
        labels_dst_dir=output_root / 'labels' / 'train',
        cat_id_remap=cat_id_remap
    )
    print(f'  Converted {train_count} images')

    # Convert valid split
    valid_dir = coco_root / 'valid'
    if valid_dir.exists() and (valid_dir / '_annotations.coco.json').exists():
        print(f'\n--- Converting valid split ---')
        val_count = convert_coco_split(
            coco_json_path=valid_dir / '_annotations.coco.json',
            images_src_dir=valid_dir,
            images_dst_dir=output_root / 'images' / 'val',
            labels_dst_dir=output_root / 'labels' / 'val',
            cat_id_remap=cat_id_remap
        )
        print(f'  Converted {val_count} images')
    else:
        print(f'\n  ⚠ No valid/ split found, skipping validation set')

    # Generate data.yaml for YOLO training
    data_yaml_path = output_root / 'data.yaml'
    abs_output = output_root.resolve().as_posix()
    yaml_lines = [
        f'# Auto-generated YOLO dataset config',
        f'# Source: {coco_root.resolve()}',
        f'',
        f'path: {abs_output}',
        f'train: images/train',
        f'val: images/val',
        f'',
        f'nc: {len(yolo_names)}',
        f'names:',
    ]
    for yolo_id, name in yolo_names.items():
        yaml_lines.append(f'  {yolo_id}: {name}')

    with open(data_yaml_path, 'w') as f:
        f.write('\n'.join(yaml_lines) + '\n')

    print(f'\n=== Done! ===')
    print(f'  Output directory : {output_root.resolve()}')
    print(f'  data.yaml        : {data_yaml_path.resolve()}')
    print(f'  Classes ({len(yolo_names)}):')
    for yid, name in yolo_names.items():
        print(f'    {yid}: {name}')
    print(f'\nNext step: python train.py --data "{data_yaml_path.resolve()}"')


if __name__ == '__main__':
    main()
