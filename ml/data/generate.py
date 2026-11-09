#!/usr/bin/env python3
"""Generate a synthetic assignment dataset for the study-time predictor.

actual_hrs = base_hours[type] * difficulty_mult * course_mult
             * student_speed * lognormal_noise

Usage: python ml/data/generate.py [--seed N] [--students N] [--out PATH]
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

CONFIG = {
    # Defaults for the CLI flags.
    "seed": 595,                     # fixed seed for reproducible output
    "n_students": 50,                # number of simulated students
    "out": Path(__file__).resolve().parent / "synthetic_assignments.csv",

    # Calendar.
    "semester_start": "2026-08-31",  # first day of term (a Monday)
    "semester_weeks": 15,            # last possible due date is 2026-12-13

    # Per-student workload.
    "assignments_per_student": (15, 40),  # inclusive range of assignment counts
    "courses_per_student": (4, 5),        # inclusive range of courses taken

    # Course name -> fixed workload multiplier (0.8-1.3).
    "course_mult": {
        "CPE 595": 1.2,
        "CS 546": 1.1,
        "MA 222": 1.3,
        "HUM 103": 0.8,
        "CS 385": 1.0,
    },

    # Keys below must match the enums in backend/models.py exactly.
    # Share of assignments of each type.
    "type_weights": {
        "Homework": 0.40,
        "Reading": 0.25,
        "Lab": 0.15,
        "Exam": 0.12,
        "Project": 0.08,
    },
    # Base hours, sampled uniformly per assignment from (low, high).
    "base_hours": {
        "Reading": (1, 2),
        "Homework": (3, 5),
        "Lab": (4, 6),
        "Exam": (6, 10),
        "Project": (15, 25),
    },
    # Days between assigned_date and due_date, inclusive (low, high).
    "lead_days": {
        "Reading": (2, 5),
        "Homework": (7, 14),
        "Lab": (5, 10),
        "Exam": (7, 14),
        "Project": (21, 35),
    },
    # Share of assignments at each difficulty, independent of type.
    "difficulty_weights": {"Easy": 0.30, "Medium": 0.50, "Hard": 0.20},
    # Hours multiplier for each difficulty.
    "difficulty_mult": {"Easy": 0.7, "Medium": 1.0, "Hard": 1.4},

    # Lognormal sigmas; the underlying normal has mean 0, so the median is 1.0.
    "student_speed_sigma": 0.17,     # drawn once per student, +/-2 sigma is ~0.71-1.40
    "noise_sigma": 0.2,              # drawn once per assignment

    # Rounding of actual_hrs.
    "hours_step": 0.25,              # round to this increment, and use it as the floor
}

COLUMNS = [
    "student_id", "course", "title", "type", "difficulty",
    "assigned_date", "due_date", "days_until_due", "actual_hrs",
]


def simulate_student(student_id, rng, cfg):
    """Return one record per assignment for a single student."""
    start = pd.Timestamp(cfg["semester_start"])
    last_day_offset = cfg["semester_weeks"] * 7 - 1

    # Sorted so a given seed does not depend on dict ordering.
    course_names = sorted(cfg["course_mult"])
    low, high = cfg["courses_per_student"]
    n_courses = min(int(rng.integers(low, high + 1)), len(course_names))
    courses = rng.choice(course_names, size=n_courses, replace=False)

    speed = rng.lognormal(0, cfg["student_speed_sigma"])

    types = list(cfg["type_weights"])
    type_p = list(cfg["type_weights"].values())
    difficulties = list(cfg["difficulty_weights"])
    difficulty_p = list(cfg["difficulty_weights"].values())

    low, high = cfg["assignments_per_student"]
    records = []
    for _ in range(int(rng.integers(low, high + 1))):
        course = str(rng.choice(courses))
        kind = str(rng.choice(types, p=type_p))
        difficulty = str(rng.choice(difficulties, p=difficulty_p))

        # Lead time first, so assigned_date cannot fall before the semester.
        lead_low, lead_high = cfg["lead_days"][kind]
        lead = int(rng.integers(lead_low, lead_high + 1))
        due_offset = int(rng.integers(lead, last_day_offset + 1))
        due = start + pd.Timedelta(days=due_offset)

        hours = (
            rng.uniform(*cfg["base_hours"][kind])
            * cfg["difficulty_mult"][difficulty]
            * cfg["course_mult"][course]
            * speed
            * rng.lognormal(0, cfg["noise_sigma"])
        )
        step = cfg["hours_step"]
        records.append({
            "student_id": student_id,
            "course": course,
            "type": kind,
            "difficulty": difficulty,
            "assigned_date": due - pd.Timedelta(days=lead),
            "due_date": due,
            "days_until_due": lead,
            "actual_hrs": max(step, round(hours / step) * step),
        })
    return records


def generate(cfg, seed, n_students):
    """Build the full dataset as a DataFrame with COLUMNS."""
    rng = np.random.default_rng(seed)
    records = []
    for student_id in range(1, n_students + 1):
        records.extend(simulate_student(student_id, rng, cfg))

    df = pd.DataFrame(records)
    # Stable sort: ties on date keep their generation order, so output is repeatable.
    df = df.sort_values(["student_id", "due_date"], kind="stable").reset_index(drop=True)

    # Number titles in due-date order within each student, course and type.
    number = df.groupby(["student_id", "course", "type"]).cumcount() + 1
    df["title"] = df["type"] + " " + number.astype(str)
    return df[COLUMNS]


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seed", type=int, default=CONFIG["seed"], help="random seed")
    parser.add_argument("--students", type=int, default=CONFIG["n_students"],
                        help="number of students to simulate")
    parser.add_argument("--out", type=Path, default=CONFIG["out"], help="output CSV path")
    args = parser.parse_args()
    if args.students < 1:
        parser.error("--students must be at least 1")
    return args


def main():
    args = parse_args()
    df = generate(CONFIG, args.seed, args.students)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False, date_format="%Y-%m-%d")
    print(f"Wrote {len(df)} rows for {args.students} students to {args.out}")


if __name__ == "__main__":
    main()
