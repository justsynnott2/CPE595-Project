"""Greedy earliest-deadline-first study schedule generator.

Pure Python with no database or web code, and deterministic: the same inputs
always produce the same schedule. See scheduling/README.md for the algorithm.
"""
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

DONE_STATUS = "Done"            # matches backend Status.done
HOURS_STEP_MINUTES = 15         # all hours are rounded to 0.25
MINUTES_PER_DAY = 24 * 60


@dataclass
class AssignmentInput:
    id: int
    title: str
    due_date: date
    hours_needed: float
    status: str                 # matches backend Status enum


@dataclass
class CommitmentInput:
    day_of_week: int            # 0=Mon ... 6=Sun, matches backend
    start_time: time
    end_time: time


@dataclass(frozen=True)
class SchedulerConfig:
    day_start: time = time(9, 0)                    # earliest time a block may start
    day_end: time = time(22, 0)                     # latest time a block may end
    max_hours_per_day: float = 4.0                  # total study hours in one day
    max_hours_per_assignment_per_day: float = 2.0   # forces spreading work out
    min_block_hrs: float = 0.5                      # shortest block worth scheduling
    max_block_hrs: float = 2.0                      # longest sitting
    break_minutes: int = 15                         # gap after each block
    finish_buffer_days: int = 1                     # finish the day before the due date
    slot_step_minutes: int = 15                     # blocks start on multiples of this


@dataclass
class StudyBlockOut:
    assignment_id: int
    date: date
    start_time: time
    end_time: time


@dataclass
class ScheduleResult:
    blocks: list[StudyBlockOut]
    at_risk: list[dict]         # assignment_id, title, hours_scheduled, hours_short


def _hours_to_minutes(hours: float) -> int:
    """Convert hours to minutes, rounded half up to the nearest 0.25 hours."""
    return int(hours * 60 / HOURS_STEP_MINUTES + 0.5) * HOURS_STEP_MINUTES


def _floor_minutes(clock: time) -> int:
    return clock.hour * 60 + clock.minute


def _ceil_minutes(clock: time) -> int:
    return _floor_minutes(clock) + (1 if clock.second or clock.microsecond else 0)


def _minutes_to_time(minutes: int) -> time:
    return time(minutes // 60, minutes % 60)


def _subtract(free, busy_start, busy_end):
    """Return the (start, end) minute intervals of free minus the busy range."""
    remaining = []
    for start, end in free:
        if busy_end <= start or busy_start >= end:
            remaining.append((start, end))
            continue
        if start < busy_start:
            remaining.append((start, busy_start))
        if busy_end < end:
            remaining.append((busy_end, end))
    return remaining


def _snap(free, step):
    """Shrink each interval onto multiples of step and drop any left empty."""
    snapped = []
    for start, end in free:
        start = -(-start // step) * step
        end = end // step * step
        if start < end:
            snapped.append((start, end))
    return snapped


def _usable_minutes(interval) -> int:
    """Longest block, in whole 0.25-hour steps, that fits in the interval."""
    start, end = interval
    return (end - start) // HOURS_STEP_MINUTES * HOURS_STEP_MINUTES


def _busy_by_weekday(commitments) -> dict[int, list[tuple[int, int]]]:
    """Group commitments as minute ranges by weekday, splitting overnight ones."""
    busy: dict[int, list[tuple[int, int]]] = {}
    for commitment in commitments:
        start = _floor_minutes(commitment.start_time)
        end = _ceil_minutes(commitment.end_time)
        day = commitment.day_of_week
        if start < end:
            busy.setdefault(day, []).append((start, end))
        elif end < start:
            busy.setdefault(day, []).append((start, MINUTES_PER_DAY))
            busy.setdefault((day + 1) % 7, []).append((0, end))
    return busy


def _free_intervals(day, start, busy, config):
    """Return the snapped free minute intervals for one calendar day."""
    first_minute = _ceil_minutes(config.day_start)
    if day == start.date():
        first_minute = max(first_minute, _ceil_minutes(start.time()))
    free = [(first_minute, _floor_minutes(config.day_end))]
    for busy_start, busy_end in busy.get(day.weekday(), []):
        free = _subtract(free, busy_start, busy_end)
    return _snap(free, config.slot_step_minutes)


def generate_schedule(
    assignments: list[AssignmentInput],
    commitments: list[CommitmentInput],
    start: datetime,
    config: SchedulerConfig = SchedulerConfig(),
) -> ScheduleResult:
    """Place study blocks earliest-deadline-first and report what did not fit."""
    active = sorted(
        (a for a in assignments if a.status != DONE_STATUS and a.hours_needed > 0),
        key=lambda a: (a.due_date, -a.hours_needed, a.id),
    )
    if not active:
        return ScheduleResult(blocks=[], at_risk=[])

    first_day = start.date()
    day_count = (max(a.due_date for a in active) - first_day).days + 1
    days = [first_day + timedelta(days=offset) for offset in range(day_count)]
    busy = _busy_by_weekday(commitments)
    free = {day: _free_intervals(day, start, busy, config) for day in days}
    day_used = dict.fromkeys(days, 0)

    min_block = max(HOURS_STEP_MINUTES, _hours_to_minutes(config.min_block_hrs))
    max_block = _hours_to_minutes(config.max_block_hrs)
    day_cap = _hours_to_minutes(config.max_hours_per_day)
    assignment_cap = _hours_to_minutes(config.max_hours_per_assignment_per_day)

    blocks: list[StudyBlockOut] = []
    at_risk: list[dict] = []

    for assignment in active:
        needed = max(HOURS_STEP_MINUTES, _hours_to_minutes(assignment.hours_needed))
        remaining = needed
        scheduled = 0
        last_day = assignment.due_date - timedelta(days=config.finish_buffer_days)

        for day in days:
            if day > last_day or remaining == 0:
                break
            assignment_today = 0

            while remaining > 0:
                limit = min(
                    max_block,
                    day_cap - day_used[day],
                    assignment_cap - assignment_today,
                )
                if limit < min_block:
                    break
                slot = next(
                    (i for i in free[day] if _usable_minutes(i) >= min_block), None
                )
                if slot is None:
                    break

                # A remainder below min_block is rounded up to a min_block block.
                # It cannot be merged into an earlier block instead: every block
                # is already as long as its limits allow, and those limits (max
                # block, free time, daily caps) never loosen later in the run.
                length = min(max(remaining, min_block), limit, _usable_minutes(slot))
                block_start, block_end = slot[0], slot[0] + length
                blocks.append(
                    StudyBlockOut(
                        assignment_id=assignment.id,
                        date=day,
                        start_time=_minutes_to_time(block_start),
                        end_time=_minutes_to_time(block_end),
                    )
                )

                # Reserve the break on both sides so the gap also holds when a
                # later assignment is placed in free time before this block.
                free[day] = _snap(
                    _subtract(
                        free[day],
                        block_start - config.break_minutes,
                        block_end + config.break_minutes,
                    ),
                    config.slot_step_minutes,
                )
                day_used[day] += length
                assignment_today += length
                scheduled += length
                remaining = max(0, remaining - length)

        if remaining > 0:
            at_risk.append(
                {
                    "assignment_id": assignment.id,
                    "title": assignment.title,
                    "hours_scheduled": scheduled / 60,
                    "hours_short": remaining / 60,
                }
            )

    blocks.sort(key=lambda b: (b.date, b.start_time))
    return ScheduleResult(blocks=blocks, at_risk=at_risk)
