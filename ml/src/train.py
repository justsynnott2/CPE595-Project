#!/usr/bin/env python3
"""Compare study-time models and save the best one.

Usage: python ml/src/train.py [--data PATH] [--seed N]
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import TransformedTargetRegressor
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error
from sklearn.model_selection import GroupKFold, GroupShuffleSplit, cross_validate
from sklearn.pipeline import Pipeline

from ml.src.features import TARGET, TypeMeanRegressor, build_preprocessor, feature_columns

DEFAULT_DATA = ROOT / "ml" / "data" / "synthetic_assignments.csv"
MODEL_DIR = ROOT / "ml" / "models"
RESULTS_PATH = MODEL_DIR / "results.csv"
MODEL_PATH = MODEL_DIR / "study_time_model.joblib"
META_PATH = MODEL_DIR / "model_meta.json"

SEED = 595
GROUP = "student_id"
TEST_SIZE = 0.2
CV_FOLDS = 5
NO_DAYS_TOLERANCE = 0.1  # prefer the no-days variant if this close in CV MAE (hours)

SCORING = {
    "mae": "neg_mean_absolute_error",
    "rmse": "neg_root_mean_squared_error",
    "r2": "r2",
}
NEGATED_METRICS = {"mae", "rmse"}  # sklearn reports these as negative scores


def load_data(path=DEFAULT_DATA):
    """Read the assignment CSV."""
    return pd.read_csv(path)


def split_by_student(df, seed=SEED):
    """Split into train and test frames with no student in both."""
    splitter = GroupShuffleSplit(n_splits=1, test_size=TEST_SIZE, random_state=seed)
    train_idx, test_idx = next(splitter.split(df, groups=df[GROUP]))
    return df.iloc[train_idx].copy(), df.iloc[test_idx].copy()


def build_models(seed=SEED, include_days=True):
    """Return unfitted pipelines keyed by model name."""

    def with_preprocessor(model):
        return Pipeline([("preprocess", build_preprocessor(include_days)), ("model", model)])

    return {
        "baseline_type_mean": Pipeline([("model", TypeMeanRegressor())]),
        "linear": with_preprocessor(LinearRegression()),
        "log_linear": with_preprocessor(
            TransformedTargetRegressor(
                regressor=LinearRegression(), func=np.log, inverse_func=np.exp
            )
        ),
        "random_forest": with_preprocessor(
            RandomForestRegressor(n_estimators=300, random_state=seed, n_jobs=-1)
        ),
        "hist_gradient_boosting": with_preprocessor(
            HistGradientBoostingRegressor(random_state=seed)
        ),
    }


def score_predictions(y_true, y_pred):
    """Return MAE, RMSE and R^2 as plain floats."""
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(root_mean_squared_error(y_true, y_pred)),
        "r2": float(r2_score(y_true, y_pred)),
    }


def evaluate(pipeline, train, test, include_days):
    """Cross-validate on train, then fit on all of train and score on test.

    Returns the metrics row and the fitted pipeline.
    """
    columns = feature_columns(include_days)
    cv_scores = cross_validate(
        pipeline, train[columns], train[TARGET], groups=train[GROUP],
        cv=GroupKFold(n_splits=CV_FOLDS), scoring=SCORING,
    )

    row = {}
    for metric in SCORING:
        values = cv_scores[f"test_{metric}"]
        if metric in NEGATED_METRICS:
            values = -values
        row[f"cv_{metric}_mean"] = float(values.mean())
        row[f"cv_{metric}_std"] = float(values.std())

    pipeline.fit(train[columns], train[TARGET])
    test_scores = score_predictions(test[TARGET], pipeline.predict(test[columns]))
    row.update({f"test_{metric}": value for metric, value in test_scores.items()})
    return row, pipeline


def select_best(results):
    """Return the index of the run to save, using CV MAE only."""
    best_index = results["cv_mae_mean"].idxmin()
    best = results.loc[best_index]
    if not best["include_days"]:
        return best_index

    same_model = results["model"] == best["model"]
    no_days_index = results[same_model & ~results["include_days"]].index[0]
    gap = results.loc[no_days_index, "cv_mae_mean"] - best["cv_mae_mean"]
    return no_days_index if gap <= NO_DAYS_TOLERANCE else best_index


def run(data_path, seed):
    """Train every model, write the artifacts, and return the results table."""
    train, test = split_by_student(load_data(data_path), seed)

    rows, fitted = [], []
    for include_days in (True, False):
        for name, pipeline in build_models(seed, include_days).items():
            print(f"Evaluating {name} (include_days={include_days})", flush=True)
            metrics, model = evaluate(pipeline, train, test, include_days)
            rows.append({"model": name, "include_days": include_days, **metrics})
            fitted.append(model)

    results = pd.DataFrame(rows)
    selected = select_best(results)
    results["selected"] = results.index == selected
    chosen = results.loc[selected]

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    results.to_csv(RESULTS_PATH, index=False, float_format="%.4f")
    joblib.dump(fitted[selected], MODEL_PATH)  # already fit on the full train set
    meta = {
        "model_name": chosen["model"],
        "features": feature_columns(bool(chosen["include_days"])),
        "test_metrics": {m: float(chosen[f"test_{m}"]) for m in SCORING},
        "train_date": datetime.now(timezone.utc).date().isoformat(),
        "seed": seed,
    }
    META_PATH.write_text(json.dumps(meta, indent=2) + "\n")
    return results


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA, help="input CSV path")
    parser.add_argument("--seed", type=int, default=SEED, help="random seed")
    return parser.parse_args()


def main():
    args = parse_args()
    results = run(args.data, args.seed)
    columns = ["model", "include_days", "cv_mae_mean", "cv_mae_std", "test_mae", "selected"]
    print()
    print(results[columns].round(3).to_string(index=False))
    print(f"\nSaved model to {MODEL_PATH}")


if __name__ == "__main__":
    main()
