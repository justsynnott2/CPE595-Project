"""Single source of truth for the study-time model's features."""
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder

CATEGORICAL = ["course", "type", "difficulty"]
NUMERIC = ["days_until_due"]
TARGET = "actual_hrs"

# Must match AssignmentType and Difficulty in backend/models.py.
ALLOWED_TYPES = ("Homework", "Lab", "Reading", "Exam", "Project")
ALLOWED_DIFFICULTIES = ("Easy", "Medium", "Hard")


def feature_columns(include_days=True):
    """Return the input column names for a model."""
    return CATEGORICAL + (NUMERIC if include_days else [])


def build_preprocessor(include_days=True):
    """Return a ColumnTransformer that one-hot encodes categoricals."""
    # Dense output because HistGradientBoostingRegressor rejects sparse input.
    encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    transformers = [("cat", encoder, CATEGORICAL)]
    if include_days:
        transformers.append(("num", "passthrough", NUMERIC))
    return ColumnTransformer(transformers, verbose_feature_names_out=False)


class TypeMeanRegressor(RegressorMixin, BaseEstimator):
    """Baseline that predicts the training mean of actual_hrs for each type.

    Defined here rather than in train.py so that a saved baseline can be
    unpickled by code that never imports the training script.
    """

    def fit(self, X, y):
        hours = pd.Series(np.asarray(y, dtype=float))
        self.means_ = hours.groupby(np.asarray(X["type"])).mean().to_dict()
        self.global_mean_ = float(hours.mean())
        return self

    def predict(self, X):
        predictions = X["type"].map(self.means_).astype(float)
        return predictions.fillna(self.global_mean_).to_numpy()
