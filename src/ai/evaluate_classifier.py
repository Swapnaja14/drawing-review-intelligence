"""
src/ai/evaluate_classifier.py
Comprehensive evaluation suite for fine-tuned DistilBERT:
Accuracy, Precision, Recall, F1-Score, Confusion Matrix, and Confidence Threshold Calibration.
"""

import sys
import json
import csv
from pathlib import Path
from typing import List, Dict, Tuple, Any

import torch
import numpy as np
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    classification_report,
    confusion_matrix
)

# Ensure clean UTF-8 console output
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATASET_DIR = PROJECT_ROOT / "dataset" / "classification_dataset"
MODEL_DIR = PROJECT_ROOT / "models" / "distilbert_engineering_classifier"

CATEGORIES = [
    "Technical",
    "Drafting",
    "Dimension",
    "Cosmetic",
    "Standards",
    "Coordination",
    "Documentation",
    "Revision",
    "Calculation",
    "Feasibility",
    "Material",
    "Notes",
    "BOM"
]


def load_test_data(test_file: Path) -> Tuple[List[str], List[int]]:
    """Loads unseen test dataset."""
    texts = []
    labels = []
    with open(test_file, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            t = row["text"].strip()
            l = int(row["label"])
            if t:
                texts.append(t)
                labels.append(l)
    return texts, labels


def evaluate_model(batch_size: int = 16, max_length: int = 128) -> Dict[str, Any]:
    """Runs full evaluation on the unseen test set."""
    print("=" * 80)
    print(" [DISTILBERT MODEL EVALUATION & THRESHOLD CALIBRATION]")
    print("=" * 80)

    test_file = DATASET_DIR / "test.csv"
    if not test_file.exists():
        raise FileNotFoundError(f"Test CSV not found at {test_file}")

    if not MODEL_DIR.exists():
        raise FileNotFoundError(f"Trained model not found at {MODEL_DIR}. Please run train_distilbert.py first.")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Loading model from: {MODEL_DIR} (Device: {device})")

    tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_DIR)
    model.to(device)
    model.eval()

    texts, true_labels = load_test_data(test_file)
    print(f"Loaded {len(texts)} unseen test samples across {len(CATEGORIES)} classes.\n")

    # Run batched inference
    all_preds = []
    all_probs = []
    all_max_confs = []

    with torch.no_grad():
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            encoding = tokenizer(
                batch_texts,
                truncation=True,
                padding=True,
                max_length=max_length,
                return_tensors="pt"
            ).to(device)

            outputs = model(**encoding)
            logits = outputs.logits
            probs = torch.softmax(logits, dim=1).cpu().numpy()

            preds = np.argmax(probs, axis=1)
            confs = np.max(probs, axis=1)

            all_preds.extend(preds)
            all_probs.extend(probs)
            all_max_confs.extend(confs)

    all_preds = np.array(all_preds)
    true_labels = np.array(true_labels)
    all_max_confs = np.array(all_max_confs)

    # 1. Overall Metrics
    acc = accuracy_score(true_labels, all_preds)
    macro_p, macro_r, macro_f1, _ = precision_recall_fscore_support(true_labels, all_preds, average="macro", zero_division=0)
    weighted_p, weighted_r, weighted_f1, _ = precision_recall_fscore_support(true_labels, all_preds, average="weighted", zero_division=0)

    mean_conf = float(np.mean(all_max_confs))
    median_conf = float(np.median(all_max_confs))
    min_conf = float(np.min(all_max_confs))
    max_conf = float(np.max(all_max_confs))

    print("-" * 80)
    print(" 📊 OVERALL EVALUATION METRICS (TEST SET)")
    print("-" * 80)
    print(f"   Accuracy:            {acc * 100:.2f}%")
    print(f"   Macro Precision:     {macro_p * 100:.2f}%")
    print(f"   Macro Recall:        {macro_r * 100:.2f}%")
    print(f"   Macro F1-Score:      {macro_f1 * 100:.2f}%")
    print(f"   Weighted F1-Score:   {weighted_f1 * 100:.2f}%")
    print(f"   Mean Confidence:     {mean_conf * 100:.2f}%")
    print(f"   Median Confidence:   {median_conf * 100:.2f}%")
    print(f"   Min/Max Confidence:  {min_conf * 100:.2f}% / {max_conf * 100:.2f}%")
    print("-" * 80)

    # 2. Per-Class Report
    print("\n 📋 PER-CLASS CLASSIFICATION & CONFIDENCE REPORT")
    print("-" * 85)
    report_dict = classification_report(
        true_labels,
        all_preds,
        target_names=CATEGORIES,
        output_dict=True,
        zero_division=0
    )
    print(f"{'Category':<28} | {'Precision':<9} | {'Recall':<9} | {'F1-Score':<9} | {'Avg Conf':<9} | {'Support':<7}")
    print("-" * 85)
    class_conf_dict = {}
    for idx, cat in enumerate(CATEGORIES):
        metrics = report_dict.get(cat, {})
        p = metrics.get("precision", 0) * 100
        r = metrics.get("recall", 0) * 100
        f1 = metrics.get("f1-score", 0) * 100
        sup = int(metrics.get("support", 0))
        
        # Average confidence for true instances of this class
        mask_cat = true_labels == idx
        avg_cat_conf = float(np.mean(all_max_confs[mask_cat])) if np.sum(mask_cat) > 0 else 0.0
        class_conf_dict[cat] = round(avg_cat_conf, 4)
        
        print(f"{cat:<28} | {p:>7.2f}% | {r:>7.2f}% | {f1:>7.2f}% | {avg_cat_conf * 100:>7.2f}% | {sup:>7}")
    print("-" * 85)

    # 3. Confusion Matrix
    print("\n 🔢 CONFUSION MATRIX")
    print("-" * 80)
    cm = confusion_matrix(true_labels, all_preds)
    header = "Pred -> " + " | ".join([f"{c[:6]:>6}" for c in CATEGORIES])
    print(f"{'Actual':<15} | {header}")
    print("-" * 80)
    for idx, row in enumerate(cm):
        cat_short = CATEGORIES[idx][:15]
        row_str = " | ".join([f"{val:>6}" for val in row])
        print(f"{cat_short:<15} | {row_str}")
    print("-" * 80)

    # 4. Confidence Threshold Calibration
    print("\n 🎯 CONFIDENCE THRESHOLD CALIBRATION ANALYSIS")
    print("-" * 80)
    print(f"{'Threshold (τ)':<15} | {'Coverage':<12} | {'Accuracy Above τ':<18} | {'Flagged for Review':<18}")
    print("-" * 70)
    
    thresholds = [0.50, 0.60, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95]
    threshold_results = []

    for tau in thresholds:
        mask = all_max_confs >= tau
        covered_count = int(np.sum(mask))
        total_count = len(all_max_confs)
        coverage_pct = (covered_count / total_count) * 100

        if covered_count > 0:
            tau_acc = accuracy_score(true_labels[mask], all_preds[mask]) * 100
        else:
            tau_acc = 100.0

        flagged_count = total_count - covered_count
        flagged_pct = (flagged_count / total_count) * 100

        print(f"{tau:<15.2f} | {coverage_pct:>10.1f}% | {tau_acc:>16.2f}% | {flagged_count:>5} ({flagged_pct:.1f}%)")
        threshold_results.append({
            "threshold": tau,
            "coverage_pct": round(coverage_pct, 2),
            "accuracy_above_threshold": round(tau_acc, 2),
            "flagged_for_review_count": flagged_count,
            "flagged_for_review_pct": round(flagged_pct, 2)
        })
    print("-" * 70)

    # 5. Qualitative Prediction Samples
    print("\n 🔍 QUALITATIVE SAMPLE PREDICTIONS")
    print("-" * 85)
    sample_indices = np.linspace(0, len(texts) - 1, min(10, len(texts)), dtype=int)
    for s_idx in sample_indices:
        t_sample = texts[s_idx]
        actual_name = CATEGORIES[true_labels[s_idx]]
        pred_name = CATEGORIES[all_preds[s_idx]]
        conf_val = all_max_confs[s_idx]
        status = "✅ PASS" if true_labels[s_idx] == all_preds[s_idx] else "❌ FAIL"
        snippet = (t_sample[:50] + "...") if len(t_sample) > 50 else t_sample
        print(f"[{status}] Conf: {conf_val*100:5.1f}% | Actual: {actual_name:<20} | Pred: {pred_name:<20} | '{snippet}'")
    print("-" * 85)

    # Save full evaluation artifact
    eval_payload = {
        "overall": {
            "accuracy": round(acc, 4),
            "macro_precision": round(macro_p, 4),
            "macro_recall": round(macro_r, 4),
            "macro_f1": round(macro_f1, 4),
            "weighted_f1": round(weighted_f1, 4),
            "mean_confidence": round(mean_conf, 4),
            "median_confidence": round(median_conf, 4),
            "min_confidence": round(min_conf, 4),
            "max_confidence": round(max_conf, 4),
            "test_sample_count": len(texts)
        },
        "per_class": report_dict,
        "per_class_confidence": class_conf_dict,
        "confusion_matrix": cm.tolist(),
        "categories": CATEGORIES,
        "threshold_calibration": threshold_results
    }

    report_path = MODEL_DIR / "evaluation_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(eval_payload, f, indent=2)

    print(f"\n[OK] Full evaluation report saved to: {report_path}")
    return eval_payload


if __name__ == "__main__":
    evaluate_model()
