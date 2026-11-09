# Scheduling

## 1. Purpose

This folder holds the logic for auto generating study schedules from assignments and predicted study times. `scheduler.py` is the generator, `tests/` holds its pytest suite, and `notebooks/01_schedule_demo.ipynb` runs it on one synthetic student.

Owner: Justin Synnott. Stack: Python standard library (`datetime`, `dataclasses`).

## 2. Algorithm

The scheduler is a deterministic greedy earliest-deadline-first pass. The same inputs always produce the same schedule.

1. **Filter.** Skip assignments marked `Done` or with no hours needed.
2. **Find free time.** For each day from the start date through the latest deadline, begin with the study window (`day_start` to `day_end`). Remove that weekday's commitments, and on the first day remove anything before `start`. Snap what is left onto `slot_step_minutes` boundaries.
3. **Order the work.** Sort by due date, then largest hours first, then id.
4. **Place blocks.** For each assignment, walk the days from the start through `finish_buffer_days` before the due date. Put each block in the earliest free time, as long as the limits allow: `max_block_hrs`, the free interval, `max_hours_per_day`, and `max_hours_per_assignment_per_day`. Skip any spot where a block of at least `min_block_hrs` will not fit. Remove the used time plus a `break_minutes` gap from the free time.
5. **Report shortfalls.** If hours remain after the last allowed day, add the assignment to `at_risk` with its hours scheduled and hours short. With `finish_buffer_days` of 1 or more, no block lands on or after the due date.

All hours are rounded to 0.25. A remainder below `min_block_hrs` becomes a full `min_block_hrs` block, so an assignment can receive up to 0.25 hours more than it needs (with the defaults). Merging a remainder into the previous block never applies, because each block is already as long as its limits allow and those limits never loosen.

Blocks are returned sorted by date and start time.

## 3. Configuration

`SchedulerConfig` fields and defaults:

| Field | Default | Meaning |
|---|---|---|
| `day_start` | 09:00 | Earliest time a block may start |
| `day_end` | 22:00 | Latest time a block may end |
| `max_hours_per_day` | 4.0 | Total study hours in one day |
| `max_hours_per_assignment_per_day` | 2.0 | Study hours per assignment per day, which forces spreading work out |
| `min_block_hrs` | 0.5 | Shortest block worth scheduling |
| `max_block_hrs` | 2.0 | Longest sitting |
| `break_minutes` | 15 | Gap after each block |
| `finish_buffer_days` | 1 | Days before the due date that work must finish (1 means the day before) |
| `slot_step_minutes` | 15 | Blocks start on multiples of this |

## 4. API

```python
@dataclass
class AssignmentInput:
    id: int
    title: str
    due_date: date
    hours_needed: float
    status: str             # matches backend Status enum

@dataclass
class CommitmentInput:
    day_of_week: int        # 0=Mon ... 6=Sun, matches backend
    start_time: time
    end_time: time

@dataclass
class StudyBlockOut:
    assignment_id: int
    date: date
    start_time: time
    end_time: time

@dataclass
class ScheduleResult:
    blocks: list[StudyBlockOut]
    at_risk: list[dict]     # assignment_id, title, hours_scheduled, hours_short

def generate_schedule(
    assignments: list[AssignmentInput],
    commitments: list[CommitmentInput],
    start: datetime,
    config: SchedulerConfig = SchedulerConfig(),
) -> ScheduleResult
```

A commitment whose `end_time` is earlier than its `start_time` runs overnight into the next day.

The repository root must be on `sys.path`. Example call:

```python
from datetime import date, datetime, time

from scheduling.scheduler import AssignmentInput, CommitmentInput, generate_schedule

assignments = [AssignmentInput(1, "HW 1", date(2026, 11, 13), 3.0, "Not Started")]
commitments = [CommitmentInput(0, time(10, 0), time(11, 15))]  # Mondays

result = generate_schedule(assignments, commitments, datetime(2026, 11, 9, 9, 0))

# result.blocks: Mon 11-09 09:00-10:00, Mon 11-09 11:15-12:15, Tue 11-10 09:00-10:00
# result.at_risk: []
```

## 5. Backend integration notes

- **Imports.** The backend runs from `backend/`, so the repository root must be added to `sys.path` before importing `scheduling.scheduler`.
- **Assignments.** Convert each of the user's `Assignment` rows to `AssignmentInput(id=row.id, title=row.title, due_date=row.due_date, hours_needed=row.ai_prediction_hrs, status=row.status)`. `ai_prediction_hrs` is nullable, so fill it with `predict_hours` first. `None` raises a `TypeError` in the scheduler.
- **Commitments.** Convert each `Commitment` row to `CommitmentInput(row.day_of_week, row.start_time, row.end_time)`. Both sides use 0=Mon ... 6=Sun.
- **Start time.** Pass the user's current local time as `start`, as a naive `datetime`.
- **Regenerating.** In one transaction, delete the user's future `StudyBlock` rows (a date after today, or today with `start_time` at or after now) and insert one row per `StudyBlockOut`, with `user_id` set to the user.
- **Partial progress.** The scheduler plans the full `hours_needed` every time. Time already spent on an `In Progress` assignment is not deducted unless the backend subtracts it from `hours_needed` first, for example the hours of that assignment's past blocks.
- **At-risk items.** Return `result.at_risk` to the frontend with the new schedule so it can warn the user.
