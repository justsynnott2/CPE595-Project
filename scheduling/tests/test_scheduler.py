"""Tests for the greedy study schedule generator."""
import random
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scheduling.scheduler import (
    AssignmentInput,
    CommitmentInput,
    SchedulerConfig,
    generate_schedule,
)

MONDAY = date(2026, 11, 9)
MONDAY_9AM = datetime(2026, 11, 9, 9, 0)


def assignment(id, due_offset, hours, status="Not Started"):
    """Build an assignment due due_offset days after MONDAY."""
    return AssignmentInput(
        id=id,
        title=f"A{id}",
        due_date=MONDAY + timedelta(days=due_offset),
        hours_needed=hours,
        status=status,
    )


def block_all_day(day_of_week):
    return CommitmentInput(day_of_week, time(9, 0), time(22, 0))


def minutes(clock):
    return clock.hour * 60 + clock.minute


def block_hours(block):
    return (minutes(block.end_time) - minutes(block.start_time)) / 60


def hours_by_assignment(result):
    totals = {}
    for block in result.blocks:
        totals[block.assignment_id] = totals.get(block.assignment_id, 0) + block_hours(block)
    return totals


def busy_week_result():
    """A realistic mix of classes and assignments used by the invariant tests."""
    commitments = [
        CommitmentInput(0, time(10, 0), time(11, 15)),
        CommitmentInput(2, time(10, 0), time(11, 15)),
        CommitmentInput(1, time(13, 0), time(15, 30)),
        CommitmentInput(3, time(13, 0), time(15, 30)),
        CommitmentInput(4, time(18, 0), time(21, 0)),
    ]
    assignments = [
        assignment(1, 2, 3.0),
        assignment(2, 4, 6.25),
        assignment(3, 4, 1.75),
        assignment(4, 7, 9.5),
        assignment(5, 10, 12.0),
    ]
    return generate_schedule(assignments, commitments, MONDAY_9AM), commitments, assignments


def test_single_assignment_fits_and_totals_match():
    result = generate_schedule([assignment(1, 4, 3.0)], [], MONDAY_9AM)

    assert hours_by_assignment(result) == {1: 3.0}
    assert result.at_risk == []


def test_no_block_overlaps_a_commitment_or_another_block():
    result, commitments, _ = busy_week_result()

    assert result.blocks
    for block in result.blocks:
        for commitment in commitments:
            if commitment.day_of_week == block.date.weekday():
                assert (
                    block.end_time <= commitment.start_time
                    or block.start_time >= commitment.end_time
                )

    for first, second in zip(result.blocks, result.blocks[1:]):
        if first.date == second.date:
            gap = minutes(second.start_time) - minutes(first.end_time)
            assert gap >= SchedulerConfig().break_minutes


def test_blocks_stay_inside_the_day_and_before_the_due_date():
    result, _, assignments = busy_week_result()
    config = SchedulerConfig()
    due_dates = {a.id: a.due_date for a in assignments}

    for block in result.blocks:
        assert config.day_start <= block.start_time < block.end_time <= config.day_end
        assert block.date < due_dates[block.assignment_id]
        assert config.min_block_hrs <= block_hours(block) <= config.max_block_hrs
        assert minutes(block.start_time) % config.slot_step_minutes == 0


def test_daily_and_per_assignment_caps_are_respected():
    result, _, _ = busy_week_result()
    config = SchedulerConfig()
    per_day = {}
    per_assignment_day = {}

    for block in result.blocks:
        per_day[block.date] = per_day.get(block.date, 0) + block_hours(block)
        key = (block.assignment_id, block.date)
        per_assignment_day[key] = per_assignment_day.get(key, 0) + block_hours(block)

    assert max(per_day.values()) <= config.max_hours_per_day
    assert max(per_assignment_day.values()) <= config.max_hours_per_assignment_per_day


def test_per_assignment_cap_spreads_work_across_days():
    result = generate_schedule([assignment(1, 4, 5.0)], [], MONDAY_9AM)

    assert [block_hours(b) for b in result.blocks] == [2.0, 2.0, 1.0]
    assert [b.date for b in result.blocks] == [MONDAY + timedelta(days=d) for d in range(3)]


def test_earlier_deadline_is_scheduled_first_when_time_is_scarce():
    # Only Monday 09:00-11:00 is free, and the later deadline is listed first.
    commitments = [CommitmentInput(0, time(11, 0), time(22, 0))]
    commitments += [block_all_day(day) for day in range(1, 7)]
    later = assignment(1, 2, 2.0)
    earlier = assignment(2, 1, 2.0)

    result = generate_schedule([later, earlier], commitments, MONDAY_9AM)

    assert hours_by_assignment(result) == {2: 2.0}
    assert result.at_risk == [
        {"assignment_id": 1, "title": "A1", "hours_scheduled": 0.0, "hours_short": 2.0}
    ]


def test_assignment_due_today_is_at_risk_with_nothing_scheduled():
    result = generate_schedule([assignment(1, 0, 3.0)], [], MONDAY_9AM)

    assert result.blocks == []
    assert result.at_risk == [
        {"assignment_id": 1, "title": "A1", "hours_scheduled": 0.0, "hours_short": 3.0}
    ]


def test_assignment_due_tomorrow_with_too_little_time_is_partly_scheduled():
    late_evening = datetime(2026, 11, 9, 21, 0)

    result = generate_schedule([assignment(1, 1, 3.0)], [], late_evening)

    assert hours_by_assignment(result) == {1: 1.0}
    assert result.at_risk == [
        {"assignment_id": 1, "title": "A1", "hours_scheduled": 1.0, "hours_short": 2.0}
    ]


def test_week_fully_blocked_puts_everything_at_risk():
    commitments = [block_all_day(day) for day in range(7)]
    assignments = [assignment(1, 3, 2.0), assignment(2, 5, 4.5)]

    result = generate_schedule(assignments, commitments, MONDAY_9AM)

    assert result.blocks == []
    assert {r["assignment_id"]: r["hours_short"] for r in result.at_risk} == {1: 2.0, 2: 4.5}


def test_done_and_zero_hour_assignments_are_ignored():
    assignments = [assignment(1, 4, 3.0, status="Done"), assignment(2, 4, 0.0)]

    result = generate_schedule(assignments, [], MONDAY_9AM)

    assert result.blocks == []
    assert result.at_risk == []


def test_first_day_respects_the_start_time():
    start = datetime(2026, 11, 9, 14, 7)

    result = generate_schedule([assignment(1, 4, 2.0)], [], start)

    assert result.blocks[0].date == MONDAY
    assert result.blocks[0].start_time == time(14, 15)


def test_same_inputs_always_produce_the_same_output():
    _, commitments, assignments = busy_week_result()
    first = generate_schedule(assignments, commitments, MONDAY_9AM)

    shuffled = assignments[:]
    random.Random(595).shuffle(shuffled)
    second = generate_schedule(shuffled, commitments, MONDAY_9AM)

    assert first == second


def test_remainder_below_min_block_becomes_a_min_block():
    # 2.25 hours is a 2.0 block plus a 0.25 remainder, which cannot merge.
    result = generate_schedule([assignment(1, 4, 2.25)], [], MONDAY_9AM)

    assert [block_hours(b) for b in result.blocks] == [2.0, 0.5]
    assert result.at_risk == []


def test_hours_are_rounded_to_quarter_hours():
    result = generate_schedule([assignment(1, 4, 1.1)], [], MONDAY_9AM)

    assert hours_by_assignment(result) == {1: 1.0}


def test_overnight_commitment_blocks_the_rest_of_the_day():
    commitments = [CommitmentInput(0, time(9, 0), time(20, 0)),
                   CommitmentInput(0, time(20, 0), time(1, 0))]

    result = generate_schedule([assignment(1, 2, 1.0)], commitments, MONDAY_9AM)

    assert result.blocks[0].date == MONDAY + timedelta(days=1)
