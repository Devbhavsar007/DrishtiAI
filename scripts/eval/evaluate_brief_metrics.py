"""
DrishtiAI — Brief-Mandated Evaluation Metrics

Computes the exact metrics required by PS 26038:
  - Sensitivity for referable DR (ICDR Level >= 2)   target: >90%
  - Specificity for referable DR (ICDR Level >= 2)    target: >85%
  - Quadratic Weighted Kappa (QWK) for 5-class ordinal grading
  - 5x5 Confusion Matrix with per-class precision/recall
  - Calibration metrics (ECE)

Usage:
    python evaluate_brief_metrics.py --data data/aptos/colored_images
    python evaluate_brief_metrics.py --data data/aptos/colored_images --patient-split
"""

import argparse
import json
import sys
import os
from pathlib import Path
from collections import Counter, defaultdict

import numpy as np

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent))

import torch
from engine.detector import _load_pytorch_model, _preprocess_for_effnet, EFFNET_INPUT_SIZE
from engine.preprocessor import preprocess_for_display

STAGE_NAMES = {
    0: "No DR",
    1: "Mild NPDR",
    2: "Moderate NPDR",
    3: "Severe NPDR",
    4: "Proliferative DR",
}


def quadratic_weighted_kappa(y_true, y_pred, num_classes=5):
    """Compute Quadratic Weighted Kappa (the standard APTOS/DR metric)."""
    hist_true = np.zeros(num_classes)
    hist_pred = np.zeros(num_classes)
    confusion = np.zeros((num_classes, num_classes))

    for t, p in zip(y_true, y_pred):
        confusion[t, p] += 1
        hist_true[t] += 1
        hist_pred[p] += 1

    n = len(y_true)
    expected = np.outer(hist_true, hist_pred) / n

    weights = np.zeros((num_classes, num_classes))
    for i in range(num_classes):
        for j in range(num_classes):
            weights[i, j] = (i - j) ** 2 / (num_classes - 1) ** 2

    num = np.sum(weights * confusion)
    den = np.sum(weights * expected)
    return 1.0 - num / max(den, 1e-9)


def expected_calibration_error(confidences, accuracies, num_bins=10):
    """Compute Expected Calibration Error (ECE)."""
    bins = np.linspace(0, 1, num_bins + 1)
    ece = 0.0
    total = len(confidences)

    for i in range(num_bins):
        mask = (confidences >= bins[i]) & (confidences < bins[i + 1])
        if mask.sum() == 0:
            continue
        avg_conf = confidences[mask].mean()
        avg_acc = accuracies[mask].mean()
        ece += mask.sum() / total * abs(avg_conf - avg_acc)
    return ece


def load_dataset(data_dir: Path, max_per_class: int = None):
    """Load images from a CSV-based dataset (APTOS style) or folder-structured."""
    image_paths = []
    labels = []
    
    # Find valid.csv in parent dirs
    csv_path = None
    for p in [data_dir, data_dir.parent, data_dir.parent.parent]:
        if (p / "valid.csv").exists():
            csv_path = p / "valid.csv"
            break
            
    if csv_path:
        import csv
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                img_path = data_dir / f"{row['id_code']}.png"
                if img_path.exists():
                    image_paths.append(str(img_path))
                    labels.append(int(row['diagnosis']))
    else:
        for stage in range(5):
            class_dir = data_dir / str(stage)
            if not class_dir.exists():
                continue
            exts = ("*.png", "*.jpg", "*.jpeg", "*.bmp", "*.tiff")
            images = []
            for ext in exts:
                images.extend(class_dir.glob(ext))
            for img_path in images:
                image_paths.append(str(img_path))
                labels.append(stage)

    if max_per_class:
        from collections import defaultdict
        import random
        random.seed(42)
        class_images = defaultdict(list)
        for p, l in zip(image_paths, labels):
            class_images[l].append(p)
        image_paths = []
        labels = []
        for stage, paths in class_images.items():
            sampled = random.sample(paths, min(len(paths), max_per_class))
            image_paths.extend(sampled)
            labels.extend([stage] * len(sampled))

    return image_paths, labels


def run_inference(model, calib, image_paths, device="cpu"):
    """Run pipeline grading inference on all images."""
    all_probs = []
    all_preds = []

    from engine.pipeline.structures import extract_structures
    from engine.pipeline.iqa import estimate_fov, run_iqa
    from engine.pipeline.grading import predict_batch
    import cv2

    for i, img_path in enumerate(image_paths):
        if (i + 1) % 10 == 0 or i == 0:
            print(f"  Inference: {i + 1}/{len(image_paths)}", end="\r")

        try:
            img_bgr = cv2.imread(img_path)
            iqa, processed = run_iqa(img_bgr, allow_enhance=True)
            if processed is None:
                processed = img_bgr

            fov = estimate_fov(processed)
            structures = extract_structures(processed, fov)
            
            img_resized = cv2.resize(processed, (300, 300))
            img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB).astype('float32') / 255.0
            mean = np.array([0.485, 0.456, 0.406], dtype='float32')
            std = np.array([0.229, 0.224, 0.225], dtype='float32')
            img_norm = (img_rgb - mean) / std
            
            x = torch.from_numpy(img_norm.transpose(2, 0, 1)).unsqueeze(0).to(device)
            lesion_feats = torch.from_numpy(structures.lesion_features).unsqueeze(0).to(device)

            pred = predict_batch(model, x, lesion_feats, calib, device, tta=False)
            probs = pred["probs"][0]
            
            all_probs.append(probs)
            all_preds.append(int(pred["grade"][0]))
        except Exception as e:
            print(f"\n  [ERROR] Failed on {img_path}: {e}")
            all_probs.append(np.array([0.2, 0.2, 0.2, 0.2, 0.2]))
            all_preds.append(0)

    print(f"  Inference: {len(image_paths)}/{len(image_paths)} — done")
    return np.array(all_probs), np.array(all_preds)


def compute_metrics(y_true, y_pred, probs):
    """Compute all brief-mandated metrics."""
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    n = len(y_true)

    results = {}

    # ── 1. Referable DR metrics (Level >= 2) ──
    true_referable = y_true >= 2
    pred_referable = y_pred >= 2

    TP = np.sum(true_referable & pred_referable)
    FN = np.sum(true_referable & ~pred_referable)
    TN = np.sum(~true_referable & ~pred_referable)
    FP = np.sum(~true_referable & pred_referable)

    sensitivity = TP / max(TP + FN, 1) * 100
    specificity = TN / max(TN + FP, 1) * 100
    ppv = TP / max(TP + FP, 1) * 100
    npv = TN / max(TN + FN, 1) * 100

    results["referable_dr"] = {
        "sensitivity_pct": round(sensitivity, 2),
        "specificity_pct": round(specificity, 2),
        "ppv_pct": round(ppv, 2),
        "npv_pct": round(npv, 2),
        "true_positives": int(TP),
        "false_negatives": int(FN),
        "true_negatives": int(TN),
        "false_positives": int(FP),
        "meets_brief_sensitivity": sensitivity > 90.0,
        "meets_brief_specificity": specificity > 85.0,
    }

    # ── 2. Quadratic Weighted Kappa ──
    qwk = quadratic_weighted_kappa(y_true, y_pred)
    results["qwk"] = round(qwk, 4)

    # ── 3. Overall 5-class accuracy ──
    accuracy = np.sum(y_true == y_pred) / n * 100
    results["overall_accuracy_pct"] = round(accuracy, 2)

    # ── 4. Confusion matrix ──
    confusion = np.zeros((5, 5), dtype=int)
    for t, p in zip(y_true, y_pred):
        confusion[t, p] += 1
    results["confusion_matrix"] = confusion.tolist()

    # ── 5. Per-class metrics ──
    per_class = {}
    for c in range(5):
        class_total = np.sum(y_true == c)
        class_correct = confusion[c, c]
        class_precision = class_correct / max(np.sum(y_pred == c), 1)
        class_recall = class_correct / max(class_total, 1)
        f1 = 2 * class_precision * class_recall / max(class_precision + class_recall, 1e-9)
        per_class[STAGE_NAMES[c]] = {
            "support": int(class_total),
            "precision": round(float(class_precision) * 100, 1),
            "recall": round(float(class_recall) * 100, 1),
            "f1": round(float(f1) * 100, 1),
        }
    results["per_class"] = per_class

    # ── 6. Calibration (ECE) ──
    max_probs = np.max(probs, axis=1)
    correct = (y_true == y_pred).astype(float)
    ece = expected_calibration_error(max_probs, correct)
    results["calibration"] = {
        "ece": round(ece, 4),
        "mean_confidence": round(float(max_probs.mean()) * 100, 1),
        "mean_accuracy": round(accuracy, 1),
    }

    results["total_images"] = n
    return results


def print_report(results):
    """Pretty-print the evaluation report."""
    print("\n" + "=" * 70)
    print("  DrishtiAI — PS 26038 Brief-Mandated Evaluation Report")
    print("=" * 70)

    ref = results["referable_dr"]
    print(f"\n{'-' * 50}")
    print(f"  REFERABLE DR (Level >= 2) — PRIMARY BRIEF METRIC")
    print(f"{'-' * 50}")
    sens_icon = "✅" if ref["meets_brief_sensitivity"] else "❌"
    spec_icon = "✅" if ref["meets_brief_specificity"] else "❌"
    print(f"  Sensitivity:  {ref['sensitivity_pct']:.1f}%  (target: >90%) {sens_icon}")
    print(f"  Specificity:  {ref['specificity_pct']:.1f}%  (target: >85%) {spec_icon}")
    print(f"  PPV:          {ref['ppv_pct']:.1f}%")
    print(f"  NPV:          {ref['npv_pct']:.1f}%")
    print(f"  TP/FN/TN/FP:  {ref['true_positives']}/{ref['false_negatives']}/{ref['true_negatives']}/{ref['false_positives']}")

    print(f"\n{'-' * 50}")
    print(f"  ORDINAL GRADING METRICS")
    print(f"{'-' * 50}")
    print(f"  Quadratic Weighted Kappa:  {results['qwk']:.4f}")
    print(f"  Overall 5-class Accuracy:  {results['overall_accuracy_pct']:.1f}%")
    print(f"  Total images evaluated:    {results['total_images']}")

    print(f"\n{'-' * 50}")
    print(f"  5×5 CONFUSION MATRIX")
    print(f"{'-' * 50}")
    cm = np.array(results["confusion_matrix"])
    header = "         " + "  ".join(f"Pred_{i}" for i in range(5))
    print(header)
    for i in range(5):
        row = f"  True_{i}  " + "  ".join(f"{cm[i, j]:5d}" for j in range(5))
        print(row)

    print(f"\n{'-' * 50}")
    print(f"  PER-CLASS PERFORMANCE")
    print(f"{'-' * 50}")
    print(f"  {'Stage':<20s} {'Support':>8s} {'Prec':>7s} {'Recall':>8s} {'F1':>7s}")
    for name, metrics in results["per_class"].items():
        print(f"  {name:<20s} {metrics['support']:8d} {metrics['precision']:6.1f}% {metrics['recall']:7.1f}% {metrics['f1']:6.1f}%")

    print(f"\n{'-' * 50}")
    print(f"  CALIBRATION")
    print(f"{'-' * 50}")
    cal = results["calibration"]
    print(f"  ECE (Expected Calibration Error):  {cal['ece']:.4f}")
    print(f"  Mean Confidence:  {cal['mean_confidence']:.1f}%")
    print(f"  Mean Accuracy:    {cal['mean_accuracy']:.1f}%")
    print(f"  Gap:              {abs(cal['mean_confidence'] - cal['mean_accuracy']):.1f}% {'(well-calibrated)' if abs(cal['mean_confidence'] - cal['mean_accuracy']) < 5 else '(needs calibration)'}")

    print("\n" + "=" * 70)


def main():
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    parser = argparse.ArgumentParser(description="DrishtiAI — Brief-mandated evaluation")
    parser.add_argument("--data", default="data/aptos/val_images/val_images",
                        help="Path to folder-structured dataset or flat dir with valid.csv parent")
    parser.add_argument("--max-per-class", type=int, default=None,
                        help="Max images per class (for fast testing)")
    parser.add_argument("--output", default="results/brief_metrics.json",
                        help="Path to save JSON results")
    args = parser.parse_args()

    data_dir = Path(args.data)
    if not data_dir.exists():
        print(f"[ERROR] Data directory not found: {data_dir}")
        print("  Download the APTOS dataset first: python download_dataset.py")
        sys.exit(1)

    print("\n[1/3] Loading model...")
    from config import PIPELINE_WEIGHTS, PIPELINE_CALIBRATION
    from engine.pipeline.grading import load_grading_model, Calibration
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if not Path(PIPELINE_WEIGHTS).exists():
        print(f"[ERROR] Pipeline model not found at {PIPELINE_WEIGHTS}")
        sys.exit(1)
        
    model = load_grading_model(PIPELINE_WEIGHTS, device)
    calib = Calibration.load(PIPELINE_CALIBRATION)

    print("\n[2/3] Loading dataset...")
    image_paths, labels = load_dataset(data_dir, args.max_per_class)
    if not image_paths:
        print("[ERROR] No images found")
        sys.exit(1)

    print(f"\n[3/3] Running inference on {len(image_paths)} images...")
    probs, preds = run_inference(model, calib, image_paths, device)

    results = compute_metrics(labels, preds, probs)
    print_report(results)

    # Save JSON
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Results saved to: {args.output}\n")


if __name__ == "__main__":
    main()
