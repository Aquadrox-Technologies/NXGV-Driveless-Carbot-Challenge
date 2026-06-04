#!/usr/bin/env python3
"""
COCO to YOLOv8 Dataset Converter — RISA-Bot
Converts Roboflow COCO JSON dataset to YOLOv8 TXT format.
"""

import json
import os
import shutil
from pathlib import Path

# Paths configuration
COCO_DIR = Path("C:/Users/Victus/Desktop/RISAbot.v1-risabotdataset.coco")
YOLO_DIR = Path("C:/Users/Victus/Desktop/RISAbot.v1-risabotdataset.yolo")


def convert_coco_to_yolo():
    if not COCO_DIR.exists():
        print(f"ERROR: Source COCO dataset directory not found at: {COCO_DIR}")
        return

    print(f"Starting conversion: {COCO_DIR} -> {YOLO_DIR}")

    # Recreate clean output directories
    if YOLO_DIR.exists():
        print(f"Removing existing YOLO folder: {YOLO_DIR}")
        shutil.rmtree(YOLO_DIR)

    categories_map = {}
    class_names = []

    # Process splits
    splits = ["train", "valid"]
    for split in splits:
        split_src = COCO_DIR / split
        json_file = split_src / "_annotations.coco.json"

        if not json_file.exists():
            print(f"WARNING: Annotation file not found for split '{split}': {json_file}")
            continue

        print(f"\nProcessing split: {split}")
        with open(json_file, "r") as f:
            coco_data = json.load(f)

        # Parse categories (map category IDs to 0-based indexes)
        for cat in coco_data.get("categories", []):
            cat_id = cat["id"]
            cat_name = cat["name"]
            if cat_id not in categories_map:
                categories_map[cat_id] = len(class_names)
                class_names.append(cat_name)

        # Map images
        images_info = {img["id"]: img for img in coco_data.get("images", [])}

        # Create output directories
        out_img_dir = YOLO_DIR / "images" / split
        out_lbl_dir = YOLO_DIR / "labels" / split
        out_img_dir.mkdir(parents=True, exist_ok=True)
        out_lbl_dir.mkdir(parents=True, exist_ok=True)

        # Group annotations by image_id
        annotations_by_image = {}
        for ann in coco_data.get("annotations", []):
            img_id = ann["image_id"]
            if img_id not in annotations_by_image:
                annotations_by_image[img_id] = []
            annotations_by_image[img_id].append(ann)

        # Process each image
        copied_count = 0
        for img_id, img_info in images_info.items():
            filename = img_info["file_name"]
            src_image_path = split_src / filename

            if not src_image_path.exists():
                print(f"  WARNING: Image file not found: {src_image_path}")
                continue

            # Copy image
            shutil.copy(src_image_path, out_img_dir / filename)
            copied_count += 1

            # Convert annotations to YOLO format
            img_width = img_info["width"]
            img_height = img_info["height"]
            yolo_lines = []

            for ann in annotations_by_image.get(img_id, []):
                cat_id = ann["category_id"]
                class_idx = categories_map[cat_id]

                # COCO box format: [x_min, y_min, width, height] (absolute pixels)
                x_min, y_min, w, h = ann["bbox"]

                # Calculate center and normalize
                x_center = x_min + w / 2.0
                y_center = y_min + h / 2.0

                x_center_norm = x_center / img_width
                y_center_norm = y_center / img_height
                w_norm = w / img_width
                h_norm = h / img_height

                yolo_lines.append(f"{class_idx} {x_center_norm:.6f} {y_center_norm:.6f} {w_norm:.6f} {h_norm:.6f}")

            # Write label file (.txt)
            label_filename = Path(filename).with_suffix(".txt")
            with open(out_lbl_dir / label_filename, "w") as lf:
                lf.write("\n".join(yolo_lines) + "\n")

        print(f"  Done. Copied {copied_count} images and created labels.")

    # Write data.yaml file
    yaml_content = f"""# YOLOv8 Dataset Configuration
path: {YOLO_DIR.as_posix()}
train: images/train
val: images/valid

nc: {len(class_names)}
names:
"""
    for idx, name in enumerate(class_names):
        yaml_content += f"  {idx}: {name}\n"

    with open(YOLO_DIR / "data.yaml", "w") as yf:
        yf.write(yaml_content)

    print(f"\nCreated data.yaml at: {YOLO_DIR / 'data.yaml'}")
    print(f"Detected classes: {class_names}")
    print("Dataset conversion successfully completed!")


if __name__ == "__main__":
    convert_coco_to_yolo()
