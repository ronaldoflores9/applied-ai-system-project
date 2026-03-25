from dataclasses import dataclass, field


@dataclass
class Owner:
    name: str
    time_available_minutes: int
    preferences: list[str] = field(default_factory=list)


@dataclass
class Pet:
    name: str
    species: str
    owner: Owner


@dataclass
class Task:
    title: str
    duration_minutes: int
    priority: str  # "low", "medium", "high"
    category: str = ""
    is_required: bool = False


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


class Scheduler:
    def generate_plan(self, pet: Pet, tasks: list[Task], start_time: str = "08:00") -> DailyPlan:
        pass
