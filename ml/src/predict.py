"""Predict study hours for one assignment using the saved model."""
import json
import math
import numbers
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import joblib
import pandas as pd

from ml.src.features import ALLOWED_DIFFICULTIES, ALLOWED_TYPES

MODEL_PATH = ROOT / "ml" / "models" / "study_time_model.joblib"
META_PATH = ROOT / "ml" / "models" / "model_meta.json"
HOURS_STEP = 0.25

_cache = None


def _load():
    """Return (model, feature names), reading from disk only on the first call."""
    global _cache
    if _cache is None:
        if not MODEL_PATH.exists() or not META_PATH.exists():
            raise FileNotFoundError(
                f"No saved model in {MODEL_PATH.parent}. Run: python ml/src/train.py"
            )
        features = json.loads(META_PATH.read_text())["features"]
        _cache = (joblib.load(MODEL_PATH), features)
    return _cache


def _validate(assignment, features):
    """Raise ValueError if the assignment cannot be scored."""
    if not isinstance(assignment, dict):
        raise ValueError(f"assignment must be a dict, got {type(assignment).__name__}")

    missing = [key for key in features if key not in assignment]
    if missing:
        raise ValueError(f"assignment is missing required keys: {missing}")

    course = assignment["course"]
    if not isinstance(course, str) or not course.strip():
        raise ValueError(f"course must be a non-empty string, got {course!r}")
    if assignment["type"] not in ALLOWED_TYPES:
        raise ValueError(f"invalid type {assignment['type']!r}, expected one of {ALLOWED_TYPES}")
    if assignment["difficulty"] not in ALLOWED_DIFFICULTIES:
        raise ValueError(
            f"invalid difficulty {assignment['difficulty']!r}, "
            f"expected one of {ALLOWED_DIFFICULTIES}"
        )

    if "days_until_due" in features:
        days = assignment["days_until_due"]
        is_number = isinstance(days, numbers.Real) and not isinstance(days, bool)
        if not is_number or not math.isfinite(days) or days < 0:
            raise ValueError(f"days_until_due must be a non-negative number, got {days!r}")


def predict_hours(assignment: dict) -> float:
    """Return predicted study hours, rounded to 0.25 with a minimum of 0.25.

    Requires course, type and difficulty. Also requires days_until_due if the
    saved model uses it. Extra keys are ignored. Raises ValueError on bad input.
    """
    model, features = _load()
    _validate(assignment, features)
    frame = pd.DataFrame([{key: assignment[key] for key in features}], columns=features)
    hours = float(model.predict(frame)[0])
    return float(max(HOURS_STEP, round(hours / HOURS_STEP) * HOURS_STEP))
