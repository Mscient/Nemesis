#!/usr/bin/env python3
"""
eval/score_labels.py — Evaluate anomaly label accuracy against ground truth.

Usage:
    python eval/score_labels.py \
        --ground-truth ../../data/sample/anomaly_ground_truth.csv \
        [--output-json results.json]

The ground truth CSV must have columns:
    anomaly_id, sku, date, true_class

The script calls suggest_anomaly_labels() with the mock provider
(AI_ENABLED=true, LLM_PROVIDER=mock) and computes:
    - Overall accuracy
    - Per-class precision / recall / F1
    - Confusion matrix

Read-only access to data/: no writes to the data directory.
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

# Ensure the ai package is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

import stocksense_ai as ai
from stocksense_ai.schemas import AnomalyContext

CLASSES = ["promotion", "data_error", "stockout_censored", "unknown"]


def load_ground_truth(path: str) -> list[dict]:
    rows = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def ground_truth_to_contexts(rows: list[dict]) -> list[AnomalyContext]:
    contexts = []
    for row in rows:
        try:
            contexts.append(
                AnomalyContext(
                    anomaly_id=int(row["anomaly_id"]),
                    sku=row["sku"],
                    date=date.fromisoformat(row["date"]),
                    value=float(row.get("value", 0)),
                    expected_value=float(row.get("expected_value", 0)),
                    robust_z=float(row.get("robust_z", 0)),
                    flags=row.get("flags", "").split("|") if row.get("flags") else [],
                )
            )
        except (KeyError, ValueError) as exc:
            print(f"Warning: skipping row {row} — {exc}", file=sys.stderr)
    return contexts


def compute_metrics(
    true_labels: dict[int, str],
    pred_labels: dict[int, str],
) -> dict:
    all_ids = set(true_labels) & set(pred_labels)
    if not all_ids:
        return {"error": "no matching IDs"}

    correct = sum(1 for i in all_ids if true_labels[i] == pred_labels[i])
    total = len(all_ids)
    accuracy = correct / total

    # Per-class metrics
    per_class: dict[str, dict] = {}
    for cls in CLASSES:
        tp = sum(1 for i in all_ids if true_labels[i] == cls and pred_labels[i] == cls)
        fp = sum(1 for i in all_ids if true_labels[i] != cls and pred_labels[i] == cls)
        fn = sum(1 for i in all_ids if true_labels[i] == cls and pred_labels[i] != cls)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        per_class[cls] = {"precision": round(precision, 3), "recall": round(recall, 3), "f1": round(f1, 3)}

    # Confusion matrix (rows=true, cols=pred)
    confusion: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for i in all_ids:
        confusion[true_labels[i]][pred_labels[i]] += 1

    return {
        "total_evaluated": total,
        "correct": correct,
        "accuracy": round(accuracy, 4),
        "per_class": per_class,
        "confusion_matrix": {k: dict(v) for k, v in confusion.items()},
    }


async def run_eval(ground_truth_path: str, output_json: str | None) -> None:
    # Force mock provider for reproducibility
    os.environ["AI_ENABLED"] = "true"
    os.environ["LLM_PROVIDER"] = "mock"

    print(f"Loading ground truth from: {ground_truth_path}")
    rows = load_ground_truth(ground_truth_path)
    true_labels = {int(r["anomaly_id"]): r["true_class"] for r in rows}
    print(f"Loaded {len(rows)} ground-truth labels.")

    contexts = ground_truth_to_contexts(rows)
    print(f"Requesting AI suggestions for {len(contexts)} items...")

    batch = await ai.suggest_anomaly_labels(contexts)
    pred_labels = {s.anomaly_id: s.cls for s in batch.suggestions}

    metrics = compute_metrics(true_labels, pred_labels)

    print("\n=== Anomaly Label Accuracy ===")
    print(f"Accuracy:  {metrics.get('accuracy', 0):.1%}  ({metrics.get('correct', 0)}/{metrics.get('total_evaluated', 0)})")
    print("\nPer-class:")
    for cls, m in metrics.get("per_class", {}).items():
        print(f"  {cls:25s}  P={m['precision']:.2f}  R={m['recall']:.2f}  F1={m['f1']:.2f}")

    if output_json:
        Path(output_json).write_text(json.dumps(metrics, indent=2))
        print(f"\nResults saved to: {output_json}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Score anomaly label accuracy against ground truth.")
    parser.add_argument("--ground-truth", required=True, help="Path to anomaly_ground_truth.csv")
    parser.add_argument("--output-json", default=None, help="Optional path to save JSON results")
    args = parser.parse_args()

    asyncio.run(run_eval(args.ground_truth, args.output_json))


if __name__ == "__main__":
    main()
