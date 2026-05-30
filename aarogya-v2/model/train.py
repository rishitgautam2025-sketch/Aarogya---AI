"""
Aarogya AI V2 — Model Training Pipeline
Trains Naive Bayes, Random Forest, and XGBoost on the Disease Symptom Prediction dataset.
Saves the best model + metadata for the FastAPI layer.

Dataset: Kaggle — Pranay Patil, Disease Symptom Prediction
         https://www.kaggle.com/datasets/itachi9604/disease-symptom-description-dataset
         Place Training.csv in /data/Training.csv before running.

Usage:
    python train.py                  # uses data/Training.csv
    python train.py --data path.csv  # custom path
"""

import argparse
import json
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    classification_report,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.naive_bayes import GaussianNB
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent / "data"
MODEL_DIR = Path(__file__).parent

# ─────────────────────────────────────────────
# 1. LOAD AND VALIDATE DATASET
# ─────────────────────────────────────────────

def load_data(csv_path: str) -> tuple[pd.DataFrame, list[str], str]:
    """Load dataset — handles both binary matrix format and Kaggle wide format
    (Disease, Symptom_1, Symptom_2, ... Symptom_N with symptom names as values)."""
    df = pd.read_csv(csv_path)
    df.columns = df.columns.str.strip()

    # Identify target column
    target_col = None
    for col in df.columns:
        if col.lower() in ("prognosis", "disease", "label"):
            target_col = col
            break

    if target_col is None:
        raise ValueError("Could not find target column. Expected 'prognosis', 'disease', or 'label'.")

    # Detect Kaggle wide format: symptom columns contain string names not 0/1
    symptom_raw_cols = [c for c in df.columns if c != target_col]
    sample = df[symptom_raw_cols].iloc[0].dropna().values
    is_wide_format = any(isinstance(v, str) for v in sample)

    if is_wide_format:
        # Convert wide format to binary matrix
        # Collect all unique symptom names across all symptom columns
        all_symptoms = set()
        for col in symptom_raw_cols:
            all_symptoms.update(df[col].dropna().str.strip().unique())
        symptom_cols = sorted(all_symptoms)

        # Build binary matrix
        binary = pd.DataFrame(0, index=df.index, columns=symptom_cols)
        for col in symptom_raw_cols:
            for idx, val in df[col].dropna().items():
                s = val.strip()
                if s in binary.columns:
                    binary.at[idx, s] = 1

        df = pd.concat([binary, df[[target_col]].reset_index(drop=True)], axis=1)
        df = df.reset_index(drop=True)
    else:
        symptom_cols = symptom_raw_cols
        df[symptom_cols] = df[symptom_cols].fillna(0).astype(int).clip(0, 1)

    df[target_col] = df[target_col].str.strip()

    print(f"[DATA] Loaded {len(df)} examples, {len(symptom_cols)} symptoms, "
          f"{df[target_col].nunique()} diseases")
    print(f"[DATA] Diseases: {sorted(df[target_col].unique())}\n")

    return df, symptom_cols, target_col


# ─────────────────────────────────────────────
# 2. TRAIN ALL THREE MODELS
# ─────────────────────────────────────────────

def train_and_evaluate(X_train, X_test, y_train, y_test, le):
    """Train NB, RF, XGBoost. Return results dict with trained models."""

    models = {
        "naive_bayes": GaussianNB(),
        "random_forest": RandomForestClassifier(
            n_estimators=200,
            max_depth=None,
            min_samples_leaf=1,
            random_state=42,
            n_jobs=-1,
        ),
        "xgboost": XGBClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.1,
            use_label_encoder=False,
            eval_metric="mlogloss",
            random_state=42,
            n_jobs=-1,
        ),
    }

    results = {}
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    for name, model in models.items():
        print(f"[TRAIN] Training {name}...")

        # Fit
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)

        # Metrics
        acc = (y_pred == y_test).mean()
        precision = precision_score(y_test, y_pred, average="weighted", zero_division=0)
        recall = recall_score(y_test, y_pred, average="weighted", zero_division=0)
        f1 = f1_score(y_test, y_pred, average="weighted", zero_division=0)

        # 5-fold CV accuracy
        cv_scores = cross_val_score(model, X_train, y_train, cv=cv, scoring="accuracy", n_jobs=-1)

        results[name] = {
            "model": model,
            "accuracy": round(float(acc), 4),
            "precision": round(float(precision), 4),
            "recall": round(float(recall), 4),
            "f1": round(float(f1), 4),
            "cv_mean": round(float(cv_scores.mean()), 4),
            "cv_std": round(float(cv_scores.std()), 4),
        }

        print(
            f"   Accuracy: {acc:.4f} | Precision: {precision:.4f} | "
            f"Recall: {recall:.4f} | F1: {f1:.4f} | "
            f"CV: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}"
        )

    return results


# ─────────────────────────────────────────────
# 3. SAVE BEST MODEL + ARTIFACTS
# ─────────────────────────────────────────────

def save_artifacts(results, symptom_cols, le, model_dir: Path):
    """Save best model, label encoder, symptom list, and comparison report."""

    # Pick best model by F1 score
    best_name = max(results, key=lambda k: results[k]["f1"])
    best = results[best_name]

    print(f"\n[SAVE] Best model: {best_name} (F1={best['f1']})")

    # Save model and encoder
    joblib.dump(best["model"], model_dir / "best_model.pkl")
    joblib.dump(le, model_dir / "label_encoder.pkl")

    # Save symptom column list
    with open(model_dir / "symptoms.json", "w") as f:
        json.dump(symptom_cols, f, indent=2)

    # Save comparison report
    report = {
        "best_model": best_name,
        "models": {
            name: {k: v for k, v in data.items() if k != "model"}
            for name, data in results.items()
        },
    }
    with open(model_dir / "model_report.json", "w") as f:
        json.dump(report, f, indent=2)

    print(f"[SAVE] Artifacts saved to {model_dir}/")
    return best_name, report


# ─────────────────────────────────────────────
# 4. MAIN
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default=str(DATA_DIR / "Training.csv"))
    args = parser.parse_args()

    print("=" * 60)
    print("Aarogya AI V2 — Model Training Pipeline")
    print("=" * 60 + "\n")

    # Load
    df, symptom_cols, target_col = load_data(args.data)

    # Encode labels
    le = LabelEncoder()
    y = le.fit_transform(df[target_col])
    X = df[symptom_cols].values

    # Split (80/20 stratified)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print(f"[SPLIT] Train: {len(X_train)} | Test: {len(X_test)}\n")

    # Train
    results = train_and_evaluate(X_train, X_test, y_train, y_test, le)

    # Save
    best_name, report = save_artifacts(results, symptom_cols, le, MODEL_DIR)

    # Print comparison table
    print("\n" + "=" * 60)
    print("MODEL COMPARISON SUMMARY")
    print("=" * 60)
    print(f"{'Model':<20} {'Accuracy':>10} {'Precision':>10} {'Recall':>10} {'F1':>10} {'CV Mean':>10}")
    print("-" * 60)
    for name, data in report["models"].items():
        marker = " ← BEST" if name == best_name else ""
        print(
            f"{name:<20} {data['accuracy']:>10.4f} {data['precision']:>10.4f} "
            f"{data['recall']:>10.4f} {data['f1']:>10.4f} {data['cv_mean']:>10.4f}{marker}"
        )

    print(f"\n[DONE] Run: uvicorn api.main:app --reload  to start the API\n")


if __name__ == "__main__":
    main()
