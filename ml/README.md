# ML

## 1. Purpose

This folder holds the machine learning work for predicting study time, including data (in `data/`) and exploratory notebooks (in `notebooks/`).

Owner: Justin Synnott. Stack: scikit-learn.

## 2. Data generation

`data/generate.py` simulates student assignments and writes `data/synthetic_assignments.csv`. Each assignment's hours follow:

```
actual_hrs = base_hours[type] * difficulty_mult * course_mult * student_speed * lognormal_noise
```

All assumptions live in the `CONFIG` dict at the top of the script.

| Assumption | Value |
|---|---|
| Random seed | 595 |
| Students | 50 |
| Assignments per student | 15-40 |
| Semester | 15 weeks, 2026-08-31 to 2026-12-13 |
| Courses per student | 4 or 5, drawn from the list below |
| Course multiplier | CPE 595 1.2, CS 546 1.1, MA 222 1.3, HUM 103 0.8, CS 385 1.0 |
| Type mix | Homework 40%, Reading 25%, Lab 15%, Exam 12%, Project 8% |
| Difficulty mix | Easy 30%, Medium 50%, Hard 20%, independent of type |
| Difficulty multiplier | Easy 0.7, Medium 1.0, Hard 1.4 |
| Student speed | Lognormal, median 1.0, sigma 0.17 (about 0.7-1.4), fixed per student |
| Noise | Lognormal, mu 0, sigma 0.2, per assignment |
| Rounding | Nearest 0.25 hours, minimum 0.25 |

Base hours and lead time are drawn per assignment, uniformly from these ranges:

| Type | Base hours | Lead time (days) |
|---|---|---|
| Reading | 1-2 | 2-5 |
| Homework | 3-5 | 7-14 |
| Lab | 4-6 | 5-10 |
| Exam | 6-10 | 7-14 |
| Project | 15-25 | 21-35 |

`type` and `difficulty` values match the enums in `backend/models.py`. Output columns are `student_id`, `course`, `title`, `type`, `difficulty`, `assigned_date`, `due_date`, `days_until_due`, and `actual_hrs`.

## 3. Usage

Run these from the repository root.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Generate the dataset (all flags are optional)
python ml/data/generate.py --seed 595 --students 50 --out ml/data/synthetic_assignments.csv

# Re-execute the analysis and save its outputs
jupyter nbconvert --to notebook --execute --inplace ml/notebooks/01_eda.ipynb
```

## 4. Model training

Run from the repository root. Both flags are optional.

```bash
python ml/src/train.py --data ml/data/synthetic_assignments.csv --seed 595
```

This writes `results.csv`, `study_time_model.joblib`, and `model_meta.json` to `ml/models/`. Feature definitions live in `src/features.py`, and `notebooks/02_model_comparison.ipynb` analyzes the results.

**Split.** `GroupShuffleSplit` holds out 20% of students, so no student appears in both train and test. Models are compared with 5-fold `GroupKFold` on the train set. The test set is not used for selection.

**Models.** Each is run with and without `days_until_due`:

- `baseline_type_mean`: mean `actual_hrs` per type. It ignores every other column, so its two runs are identical.
- `linear`: `LinearRegression` on raw hours.
- `log_linear`: `LinearRegression` on log hours, with predictions exponentiated back.
- `random_forest`: `RandomForestRegressor` with 300 trees.
- `hist_gradient_boosting`: `HistGradientBoostingRegressor`.

**Selection.** The run with the lowest CV MAE wins. If it uses `days_until_due` and the same model without it is within 0.1 hours of CV MAE, the no-days run is saved instead. The saved model is fit on the full train set.

**Results** (seed 595, sorted by CV MAE, saved model in bold). MAE and RMSE are in hours.

| Model | Days feature | CV MAE (mean ± std) | CV RMSE | CV R² | Test MAE | Test RMSE | Test R² |
|---|---|---|---|---|---|---|---|
| **log_linear** | No | 1.397 ± 0.149 | 2.489 | 0.846 | 1.668 | 3.041 | 0.837 |
| log_linear | Yes | 1.403 ± 0.133 | 2.487 | 0.845 | 1.663 | 3.059 | 0.835 |
| random_forest | No | 1.484 ± 0.090 | 2.591 | 0.831 | 1.753 | 3.498 | 0.784 |
| hist_gradient_boosting | No | 1.489 ± 0.133 | 2.614 | 0.830 | 1.657 | 2.992 | 0.842 |
| hist_gradient_boosting | Yes | 1.599 ± 0.079 | 2.833 | 0.799 | 1.705 | 3.089 | 0.832 |
| random_forest | Yes | 1.617 ± 0.073 | 2.741 | 0.808 | 1.951 | 3.793 | 0.746 |
| linear | No | 1.836 ± 0.065 | 3.156 | 0.752 | 2.202 | 3.665 | 0.763 |
| linear | Yes | 1.848 ± 0.058 | 3.179 | 0.748 | 2.196 | 3.666 | 0.763 |
| baseline_type_mean | Yes | 2.114 ± 0.139 | 3.732 | 0.652 | 2.142 | 4.043 | 0.712 |
| baseline_type_mean | No | 2.114 ± 0.139 | 3.732 | 0.652 | 2.142 | 4.043 | 0.712 |

The data is synthetic, so these scores show how well each model recovers the generator's assumptions, not how well it predicts real students.

## 5. Prediction API

```python
predict_hours(assignment: dict) -> float
```

`src/predict.py` loads the saved model once and returns hours rounded to 0.25, with a minimum of 0.25. `course`, `type`, and `difficulty` are required, and `days_until_due` is required only if the saved model uses it. The current model does not. `type` and `difficulty` must match the enums in `backend/models.py`. Missing keys and invalid values raise `ValueError`. If no model has been trained, it raises `FileNotFoundError`.

The caller's environment needs the packages in `requirements.txt`, and the repository root must be on `sys.path`:

```python
import sys
sys.path.insert(0, "/path/to/CPE595-Project")

from ml.src.predict import predict_hours

hours = predict_hours({"course": "CPE 595", "type": "Homework", "difficulty": "Hard"})
```
