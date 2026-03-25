class Owner:
    def __init__(self, name: str, time_available_minutes: int, preferences: list[str] = None):
        self.name = name
        self.time_available_minutes = time_available_minutes
        self.preferences = preferences or []


class Pet:
    def __init__(self, name: str, species: str, owner: Owner):
        self.name = name
        self.species = species
        self.owner = owner


class Task:
    def __init__(self, title: str, duration_minutes: int, priority: str, category: str = "", is_required: bool = False):
        self.title = title
        self.duration_minutes = duration_minutes
        self.priority = priority  # "low", "medium", "high"
        self.category = category
        self.is_required = is_required


class ScheduledTask:
    def __init__(self, task: Task, start_time: str, end_time: str, reason: str):
        self.task = task
        self.start_time = start_time
        self.end_time = end_time
        self.reason = reason


class DailyPlan:
    def __init__(self, pet: Pet, scheduled_tasks: list[ScheduledTask], skipped_tasks: list[Task], total_minutes: int, summary: str):
        self.pet = pet
        self.scheduled_tasks = scheduled_tasks
        self.skipped_tasks = skipped_tasks
        self.total_minutes = total_minutes
        self.summary = summary


class Scheduler:
    def generate_plan(self, pet: Pet, tasks: list[Task], start_time: str = "08:00") -> DailyPlan:
        pass
