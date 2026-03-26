from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class Owner:
    name: str
    time_available_minutes: int
    preferences: list[str] = field(default_factory=list)
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Register a pet under this owner."""
        self.pets.append(pet)

    def get_all_tasks(self) -> list[Task]:
        """Return every task across all of this owner's pets."""
        return [task for pet in self.pets for task in pet.tasks]


@dataclass
class Pet:
    name: str
    species: str
    owner: Owner
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Attach a task to this pet's task list."""
        self.tasks.append(task)

    def get_pending_tasks(self) -> list[Task]:
        """Return all tasks that have not yet been completed."""
        return [t for t in self.tasks if not t.is_completed]


@dataclass
class Task:
    title: str
    duration_minutes: int
    priority: Priority
    category: str = ""
    is_required: bool = False
    species: list[str] = field(default_factory=list)  # empty = applies to all species
    frequency: str = "daily"  # "daily", "weekly", "as_needed"
    is_completed: bool = False
    scheduled_time: str = ""          # optional "HH:MM" hint; "" = unscheduled
    last_completed_date: str = ""     # "YYYY-MM-DD"; "" = never completed

    def mark_complete(self) -> None:
        """Mark this task as completed and record today's date."""
        self.is_completed = True
        self.last_completed_date = date.today().isoformat()


@dataclass
class ScheduledTask:
    task: Task
    start_time: str
    end_time: str
    reason: str


@dataclass
class DailyPlan:
    pet: Pet
    scheduled_tasks: list[ScheduledTask] = field(default_factory=list)
    skipped_tasks: list[Task] = field(default_factory=list)
    total_minutes: int = 0
    summary: str = ""

    @property
    def owner(self) -> Owner:
        """Return the owner of the pet this plan belongs to."""
        return self.pet.owner


# ---------------------------------------------------------------------------
# Recurrence helper
# ---------------------------------------------------------------------------

def is_due_today(task: Task, today: str | None = None) -> bool:
    """Return True if *task* should appear in today's schedule.

    Rules:
    - "daily"     → always due
    - "as_needed" → due only when not already completed
    - "weekly"    → due if never completed, or last completed > 6 days ago
    """
    if today is None:
        today = date.today().isoformat()

    if task.frequency == "daily":
        return True

    if task.frequency == "as_needed":
        return not task.is_completed

    if task.frequency == "weekly":
        if not task.last_completed_date:
            return True
        last = date.fromisoformat(task.last_completed_date)
        today_date = date.fromisoformat(today)
        return (today_date - last).days > 6

    return True  # unknown frequency → include by default


class Scheduler:
    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_plan(self, pet: Pet, tasks: list[Task], start_time: str = "08:00",
                      today: str | None = None) -> DailyPlan:
        """Build and return a DailyPlan for a pet from the given task list."""
        due = [t for t in tasks if is_due_today(t, today)]
        filtered = self._filter_by_species(due, pet.species)
        sorted_tasks = self._sort_tasks(filtered)
        scheduled, skipped = self._allocate(sorted_tasks, pet.owner.time_available_minutes, start_time)
        plan = DailyPlan(pet=pet, scheduled_tasks=scheduled, skipped_tasks=skipped)
        plan.total_minutes = sum(st.task.duration_minutes for st in scheduled)
        plan.summary = self._build_summary(plan)
        return plan

    def generate_plans_for_owner(self, owner: Owner, start_time: str = "08:00",
                                 today: str | None = None) -> list[DailyPlan]:
        """Generate a DailyPlan for each pet owned, using that pet's pending tasks."""
        return [
            self.generate_plan(pet, pet.get_pending_tasks(), start_time, today)
            for pet in owner.pets
        ]

    def mark_task_complete(self, pet: Pet, task: Task) -> Task | None:
        """Complete a task and auto-create the next recurring instance.

        For tasks with frequency "daily" or "weekly", this method creates a
        new pending Task with the same settings and appends it to the pet.
        Returns the new task when created, otherwise None.
        """
        if task not in pet.tasks:
            raise ValueError("Task does not belong to this pet")

        if task.is_completed:
            return None

        task.mark_complete()

        if task.frequency not in {"daily", "weekly"}:
            return None

        next_task = Task(
            title=task.title,
            duration_minutes=task.duration_minutes,
            priority=task.priority,
            category=task.category,
            is_required=task.is_required,
            species=list(task.species),
            frequency=task.frequency,
            is_completed=False,
            scheduled_time=task.scheduled_time,
            last_completed_date="",
        )
        pet.add_task(next_task)
        return next_task

    def sort_by_time(self, tasks: list[Task]) -> list[Task]:
        """Order tasks by their explicit time hints.

        Tasks with a valid `scheduled_time` are sorted lexicographically in
        HH:MM order. Tasks without a time hint are pushed to the end using a
        sentinel value, preserving deterministic output for UI rendering.
        """
        return sorted(
            tasks,
            key=lambda task: task.scheduled_time if task.scheduled_time else "99:99",
        )

    def filter_by_status_or_pet(
        self,
        owner: Owner,
        is_completed: bool | None = None,
        pet_name: str | None = None,
    ) -> list[tuple[Pet, Task]]:
        """Return (pet, task) pairs filtered by optional status and pet name.

        This performs a single pass through all tasks owned by `owner` and
        applies AND-style filtering for each supplied criterion.
        - `is_completed=None` disables status filtering.
        - `pet_name=None` disables pet-name filtering.
        """
        results: list[tuple[Pet, Task]] = []
        for pet in owner.pets:
            if pet_name and pet.name != pet_name:
                continue
            for task in pet.tasks:
                if is_completed is not None and task.is_completed != is_completed:
                    continue
                results.append((pet, task))
        return results

    def filter_tasks(
        self,
        owner: Owner,
        pet_name: str | None = None,
        status: str | None = None,   # "pending" | "completed"
        priority: str | None = None,  # "low" | "medium" | "high"
    ) -> list[tuple[Pet, Task]]:
        """Return tasks that satisfy the supplied multi-criteria query.

        Filters are cumulative (logical AND). This helper supports quick
        dashboard views such as "all pending high-priority tasks for Buddy".
        Omit any filter (pass None) to leave that dimension unrestricted.
        """
        results: list[tuple[Pet, Task]] = []
        for pet in owner.pets:
            if pet_name and pet.name != pet_name:
                continue
            for task in pet.tasks:
                if status == "pending" and task.is_completed:
                    continue
                if status == "completed" and not task.is_completed:
                    continue
                if priority and task.priority.value != priority:
                    continue
                results.append((pet, task))
        return results

    def detect_conflicts(self, plans: list[DailyPlan]) -> list[tuple[ScheduledTask, Pet, ScheduledTask, Pet]]:
        """Find all overlapping scheduled windows across one or more plans.

        Each result tuple is `(task_a, pet_a, task_b, pet_b)`. The algorithm
        flattens all scheduled tasks, then checks each unique pair once.
        Overlap is detected with interval logic:
            `start_a < end_b and start_b < end_a`.
        """
        all_items: list[tuple[ScheduledTask, Pet]] = [
            (st, plan.pet)
            for plan in plans
            for st in plan.scheduled_tasks
        ]

        conflicts: list[tuple[ScheduledTask, Pet, ScheduledTask, Pet]] = []
        for i, (st_a, pet_a) in enumerate(all_items):
            for st_b, pet_b in all_items[i + 1:]:
                a_start = self._parse_time(st_a.start_time)
                a_end   = self._parse_time(st_a.end_time)
                b_start = self._parse_time(st_b.start_time)
                b_end   = self._parse_time(st_b.end_time)
                if a_start < b_end and b_start < a_end:
                    conflicts.append((st_a, pet_a, st_b, pet_b))
        return conflicts

    def get_conflict_warnings(self, plans: list[DailyPlan]) -> list[str]:
        """Lightweight wrapper: return human-readable warning strings for every conflict.

        Never raises — always returns a (possibly empty) list of strings so the
        caller can print or display them without risk of crashing.
        """
        warnings: list[str] = []
        for st_a, pet_a, st_b, pet_b in self.detect_conflicts(plans):
            kind = "SAME-PET" if pet_a is pet_b else "CROSS-PET"
            warnings.append(
                f"[{kind} CONFLICT] "
                f"{pet_a.name} / \"{st_a.task.title}\" ({st_a.start_time}–{st_a.end_time})"
                f"  overlaps with  "
                f"{pet_b.name} / \"{st_b.task.title}\" ({st_b.start_time}–{st_b.end_time})"
            )
        return warnings

    def check_time_hint_conflicts(self, owner: Owner) -> list[str]:
        """Validate user-provided time hints before schedule allocation.

        This preflight pass detects overlapping pinned windows by treating each
        hint as an interval `[scheduled_time, scheduled_time + duration)` and
        comparing unique pairs. It is useful because sequential allocation can
        mask original same-pet conflicts by shifting later tasks forward.

        Only incomplete tasks with a non-empty `scheduled_time` are checked.
        Returns human-readable warnings and never raises.
        """
        # Build a flat list of (pet, task) for tasks that have a scheduled_time
        pinned: list[tuple[Pet, Task]] = [
            (pet, task)
            for pet in owner.pets
            for task in pet.tasks
            if task.scheduled_time and not task.is_completed
        ]

        warnings: list[str] = []
        for i, (pet_a, task_a) in enumerate(pinned):
            for pet_b, task_b in pinned[i + 1:]:
                a_start = self._parse_time(task_a.scheduled_time)
                a_end   = a_start + task_a.duration_minutes
                b_start = self._parse_time(task_b.scheduled_time)
                b_end   = b_start + task_b.duration_minutes
                if a_start < b_end and b_start < a_end:
                    kind = "SAME-PET" if pet_a is pet_b else "CROSS-PET"
                    warnings.append(
                        f"[PRE-SCHEDULE {kind} CONFLICT] "
                        f"{pet_a.name} / \"{task_a.title}\" "
                        f"({self._format_time(a_start)}–{self._format_time(a_end)})"
                        f"  overlaps with  "
                        f"{pet_b.name} / \"{task_b.title}\" "
                        f"({self._format_time(b_start)}–{self._format_time(b_end)})"
                    )
        return warnings

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _filter_by_species(self, tasks: list[Task], species: str) -> list[Task]:
        """Remove tasks that do not apply to the given species."""
        return [t for t in tasks if not t.species or species in t.species]

    def _sort_tasks(self, tasks: list[Task]) -> list[Task]:
        """Apply core ranking used by plan generation.

        Sort precedence:
        1. `scheduled_time` (pinned items first)
        2. `is_required` (required before optional)
        3. `priority` (`high`, `medium`, `low`)
        """
        priority_order = {Priority.HIGH: 0, Priority.MEDIUM: 1, Priority.LOW: 2}
        return sorted(
            tasks,
            key=lambda t: (
                t.scheduled_time if t.scheduled_time else "99:99",  # pinned times first
                not t.is_required,
                priority_order.get(t.priority, 99),
            ),
        )

    def _allocate(
        self, tasks: list[Task], budget_minutes: int, start_time: str
    ) -> tuple[list[ScheduledTask], list[Task]]:
        """Greedily place ranked tasks into a fixed minute budget.

        The allocator walks tasks in pre-sorted order, tracking:
        - `elapsed` for budget enforcement
        - `wall` for start/end clock labels

        If a task has a future `scheduled_time` hint, `wall` jumps forward to
        that time; hints in the past are ignored. Tasks that exceed remaining
        budget are collected in `skipped`.
        """
        scheduled: list[ScheduledTask] = []
        skipped: list[Task] = []
        elapsed = 0
        wall = self._parse_time(start_time)

        for task in tasks:
            # Honour explicit scheduled_time hint
            if task.scheduled_time:
                pinned = self._parse_time(task.scheduled_time)
                if pinned >= wall:
                    wall = pinned

            if elapsed + task.duration_minutes <= budget_minutes:
                end_wall = wall + task.duration_minutes
                reason = (
                    f"pinned to {task.scheduled_time}"
                    if task.scheduled_time
                    else "scheduled within available time"
                )
                scheduled.append(ScheduledTask(
                    task=task,
                    start_time=self._format_time(wall),
                    end_time=self._format_time(end_wall),
                    reason=reason,
                ))
                elapsed += task.duration_minutes
                wall = end_wall
            else:
                skipped.append(task)

        return scheduled, skipped

    def _build_summary(self, plan: DailyPlan) -> str:
        """Compose a human-readable summary string for the plan."""
        return (
            f"{plan.pet.name}'s plan: "
            f"{len(plan.scheduled_tasks)} tasks scheduled, "
            f"{len(plan.skipped_tasks)} skipped, "
            f"{plan.total_minutes} minutes total."
        )

    def _parse_time(self, time_str: str) -> int:
        """Convert 'HH:MM' to minutes since midnight."""
        h, m = time_str.split(":")
        return int(h) * 60 + int(m)

    def _format_time(self, minutes: int) -> str:
        """Convert minutes since midnight to 'HH:MM'."""
        return f"{minutes // 60:02d}:{minutes % 60:02d}"
