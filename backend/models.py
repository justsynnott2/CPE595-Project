"""Database tables. Fixed-value fields are enums so the ML data stays clean."""
import enum
from datetime import date, time

from sqlalchemy import Date, Float, ForeignKey, Integer, String, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class AssignmentType(str, enum.Enum):
    homework = "Homework"
    lab = "Lab"
    reading = "Reading"
    exam = "Exam"
    project = "Project"


class Difficulty(str, enum.Enum):
    easy = "Easy"
    medium = "Medium"
    hard = "Hard"


class Status(str, enum.Enum):
    not_started = "Not Started"
    in_progress = "In Progress"
    done = "Done"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String)

    assignments: Mapped[list["Assignment"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    commitments: Mapped[list["Commitment"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    study_blocks: Mapped[list["StudyBlock"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Assignment(Base):
    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    course: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    type: Mapped[str] = mapped_column(String)          # AssignmentType value
    difficulty: Mapped[str] = mapped_column(String)    # Difficulty value
    due_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String, default=Status.not_started.value)
    ai_prediction_hrs: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_hrs: Mapped[float | None] = mapped_column(Float, nullable=True)

    user: Mapped["User"] = relationship(back_populates="assignments")
    study_blocks: Mapped[list["StudyBlock"]] = relationship(
        back_populates="assignment", cascade="all, delete-orphan"
    )


class Commitment(Base):
    """Recurring weekly item (class, work). day_of_week: 0=Mon ... 6=Sun."""
    __tablename__ = "commitments"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String)
    day_of_week: Mapped[int] = mapped_column(Integer)
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)

    user: Mapped["User"] = relationship(back_populates="commitments")


class StudyBlock(Base):
    __tablename__ = "study_blocks"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("assignments.id"))
    date: Mapped[date] = mapped_column(Date)
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)

    user: Mapped["User"] = relationship(back_populates="study_blocks")
    assignment: Mapped["Assignment"] = relationship(back_populates="study_blocks")

