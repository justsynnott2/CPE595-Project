"""Smoke tests for predict_hours. Requires a trained model in ml/models/."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ml.src.predict import predict_hours

VALID = {"course": "CPE 595", "type": "Homework", "difficulty": "Medium", "days_until_due": 10}


def test_valid_assignment_returns_positive_float():
    hours = predict_hours(VALID)
    assert isinstance(hours, float)
    assert hours > 0


def test_invalid_type_raises_value_error():
    with pytest.raises(ValueError, match="invalid type"):
        predict_hours({**VALID, "type": "Quiz"})
