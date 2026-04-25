from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from enum import Enum

logger = logging.getLogger("pawpal.scheduler")


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
        logger.info("Generating plan for '%s' (%s tasks)", pet.name, len(tasks))
        due = [t for t in tasks if is_due_today(t, today)]
        filtered = self._filter_by_species(due, pet.species)
        sorted_tasks = self._sort_tasks(filtered)
        scheduled, skipped = self._allocate(sorted_tasks, pet.owner.time_available_minutes, start_time)
        plan = DailyPlan(pet=pet, scheduled_tasks=scheduled, skipped_tasks=skipped)
        plan.total_minutes = sum(st.task.duration_minutes for st in scheduled)
        plan.summary = self._build_summary(plan)
        logger.info(
            "Plan for '%s': %d scheduled, %d skipped, %d min total",
            pet.name, len(scheduled), len(skipped), plan.total_minutes,
        )
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
        logger.info("Task '%s' marked complete for pet '%s'", task.title, pet.name)

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
            last_completed_date=task.last_completed_date,
        )
        pet.add_task(next_task)
        return next_task

    def sort_by_priority_then_time(self, tasks: list[Task]) -> list[Task]:
        """Order tasks by priority first (High → Medium → Low), then by time.

        Within each priority tier, tasks with a pinned scheduled_time are
        ordered chronologically (lexicographic "HH:MM" comparison); flexible
        tasks sort to the end of their tier using the sentinel "99:99".

        This produces a plan that always completes the most important work
        first, regardless of when it was originally scheduled.

        Example ordering for a mixed list:
            🔴 HIGH  / "08:00"  → first
            🔴 HIGH  / "09:30"  → second
            🔴 HIGH  / flexible → third
            🟡 MEDIUM / "07:00" → fourth (high priority beats earlier time)
            🟢 LOW   / flexible → last
        """
        priority_order = {Priority.HIGH: 0, Priority.MEDIUM: 1, Priority.LOW: 2}
        return sorted(
            tasks,
            key=lambda t: (
                priority_order.get(t.priority, 99),
                t.scheduled_time if t.scheduled_time else "99:99",
            ),
        )

    def sort_by_time(self, tasks: list[Task]) -> list[Task]:
        """Order tasks by their explicit time hints.

        Uses Python's sorted() with a lambda as the key function.
        The lambda extracts each task's scheduled_time string ("HH:MM").
        Because "HH:MM" strings sort correctly in lexicographic order
        (e.g. "06:45" < "07:30" < "08:00"), no time parsing is needed.
        Tasks without a time hint receive the sentinel "99:99" so they
        sort to the end, preserving deterministic output for UI rendering.

        Example:
            key=lambda task: task.scheduled_time or "99:99"
            "06:45" → sorts first
            "08:00" → sorts after "07:30"
            ""      → becomes "99:99", sorts last
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
        """Detect overlapping scheduled windows across one or more plans.

        Args:
            plans: Daily plans whose ScheduledTask windows should be compared.

        Returns:
            A list of conflict tuples in the form
            (scheduled_task_a, pet_a, scheduled_task_b, pet_b).

        Notes:
            Uses pairwise interval overlap logic:
            start_a < end_b and start_b < end_a.
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
        logger.info("Conflict detection complete: %d conflict(s) found", len(conflicts))
        return conflicts

    def get_conflict_warnings(self, plans: list[DailyPlan]) -> list[str]:
        """Build user-facing warning messages from detected scheduling conflicts.

        Args:
            plans: Daily plans to scan for overlaps.

        Returns:
            A list of warning strings. The list is empty when no conflicts are
            found.

        Notes:
            This method is intentionally lightweight and non-throwing so callers
            can safely print warnings without interrupting the app flow.
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

    def resolve_conflicts(
        self, owner: Owner, plans: list[DailyPlan] | None = None
    ) -> list[tuple[Task, str, str]]:
        """Auto-resolve scheduling conflicts by shifting the later task forward.

        When *plans* are supplied the sweep-line uses the actual scheduled
        windows from the generated plans, so it can fix both pinned-time
        and unpinned cross-pet conflicts.  Without *plans* only tasks that
        already have a ``scheduled_time`` hint are considered.

        Algorithm (sweep-line):
        1. Collect tasks sorted by their start time (from plans or from
           scheduled_time hints).
        2. Walk through them tracking ``wall`` — the earliest free minute.
        3. If a task's start overlaps ``wall``, push its ``scheduled_time``
           forward to ``wall`` and record the change.
        4. Advance ``wall`` to the end of the task in either case.

        Args:
            owner: Owner whose pets' tasks will be adjusted in-place.
            plans: Optional generated plans; when provided, all conflicts
                   (pinned and unpinned) are resolved using the scheduled
                   windows.  When omitted, only pinned tasks are considered.

        Returns:
            A list of (task, old_time, new_time) triples for every task whose
            scheduled_time was changed, so the UI can display a diff.
        """
        if plans is not None:
            all_items: list[tuple[Task, str]] = sorted(
                [
                    (st.task, st.start_time)
                    for plan in plans
                    for st in plan.scheduled_tasks
                ],
                key=lambda x: self._parse_time(x[1]),
            )
        else:
            all_items = sorted(
                [
                    (task, task.scheduled_time)
                    for pet in owner.pets
                    for task in pet.tasks
                    if task.scheduled_time and not task.is_completed
                ],
                key=lambda x: self._parse_time(x[1]),
            )

        changes: list[tuple[Task, str, str]] = []
        wall = 0  # minutes since midnight — tracks the next free slot

        for task, current_time in all_items:
            start = self._parse_time(current_time)
            if start < wall:
                old_time = task.scheduled_time if task.scheduled_time else current_time
                task.scheduled_time = self._format_time(wall)
                changes.append((task, old_time, task.scheduled_time))
                start = wall
            wall = start + task.duration_minutes

        return changes

    def check_time_hint_conflicts(self, owner: Owner) -> list[str]:
        """Check pinned task time hints for overlaps before allocation.

        Args:
            owner: Owner whose pets and incomplete pinned tasks are validated.

        Returns:
            A list of warning strings describing pre-schedule conflicts.

        Notes:
            This preflight check treats each pinned task as the interval
            [scheduled_time, scheduled_time + duration). It helps surface intent
            conflicts that greedy allocation might otherwise mask by shifting
            later tasks forward.
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
    # Weighted urgency scoring & smart recommendation
    # ------------------------------------------------------------------

    def score_task(self, task: Task, today: str | None = None) -> float:
        """Compute a composite urgency score for a single task.

        The score is a weighted sum of four independent signals:

        1. **Priority weight** (1–3): LOW=1, MEDIUM=2, HIGH=3.
        2. **Required multiplier** (×2 if is_required, ×1 otherwise):
           Required tasks are double-weighted because skipping them is not
           an option.
        3. **Recency penalty** (0.0–1.0): For *weekly* tasks the penalty
           grows linearly from 0 on the day of completion to 1.0 on day 7+,
           rewarding tasks that are almost overdue. Daily and as_needed tasks
           receive a flat recency contribution of 0.5.
        4. **Overdue bonus** (+2.0): Applied when a weekly task has not been
           completed in more than 7 days to ensure overdue items surface at
           the top regardless of priority.

        Final formula:
            score = (priority_weight * required_mult) + recency_penalty + overdue_bonus

        Returns a non-negative float; higher means more urgent.
        """
        if today is None:
            today = date.today().isoformat()

        priority_weight = {Priority.LOW: 1, Priority.MEDIUM: 2, Priority.HIGH: 3}.get(task.priority, 1)
        required_mult = 2.0 if task.is_required else 1.0

        recency_penalty = 0.5  # default for daily / as_needed
        overdue_bonus = 0.0

        if task.frequency == "weekly":
            if not task.last_completed_date:
                recency_penalty = 1.0
            else:
                days_elapsed = (date.fromisoformat(today) - date.fromisoformat(task.last_completed_date)).days
                recency_penalty = min(days_elapsed / 7.0, 1.0)
                if days_elapsed > 7:
                    overdue_bonus = 2.0

        return (priority_weight * required_mult) + recency_penalty + overdue_bonus

    def recommend_next(
        self,
        owner: Owner,
        available_minutes: int,
        current_time: str = "08:00",
        today: str | None = None,
    ) -> tuple[Pet, Task, float] | None:
        """Return the single most urgent pending task that fits a free window.

        This answers the question: *"I have N free minutes right now — what
        should I do next?"*  It is useful when the owner has an unplanned gap
        and wants an instant recommendation without regenerating the full plan.

        Algorithm:
        1. Collect every pending, due task across all pets (species-filtered).
        2. Exclude tasks already pinned to a future time (they belong to the
           fixed schedule, not the free window).
        3. Score each candidate with :meth:`score_task`.
        4. Among tasks whose ``duration_minutes ≤ available_minutes``, return
           the (pet, task, score) triple with the highest score.
           Ties are broken by shorter duration (prefer finishing something
           quickly when urgency is equal).

        Returns ``None`` when no eligible task fits the available window.
        """
        if today is None:
            today = date.today().isoformat()

        current_minutes = self._parse_time(current_time)

        candidates: list[tuple[Pet, Task, float]] = []
        for pet in owner.pets:
            due_tasks = [t for t in pet.get_pending_tasks() if is_due_today(t, today)]
            species_tasks = self._filter_by_species(due_tasks, pet.species)
            for task in species_tasks:
                # Skip tasks that are pinned to a future time slot
                if task.scheduled_time:
                    pinned = self._parse_time(task.scheduled_time)
                    if pinned > current_minutes:
                        continue
                if task.duration_minutes <= available_minutes:
                    candidates.append((pet, task, self.score_task(task, today)))

        if not candidates:
            logger.info("recommend_next: no eligible tasks found for %d min window", available_minutes)
            return None

        best = max(candidates, key=lambda x: (x[2], -x[1].duration_minutes))
        logger.info(
            "recommend_next: '%s' (pet=%s, score=%.2f) for %d-min window",
            best[1].title, best[0].name, best[2], available_minutes,
        )
        return best

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
