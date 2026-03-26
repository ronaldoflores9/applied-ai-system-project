from pawpal_system import Owner, Pet, Task, Priority, Scheduler


def make_owner():
    return Owner(name="Maria", time_available_minutes=60)


def make_pet(owner):
    return Pet(name="Buddy", species="dog", owner=owner)


def make_task():
    return Task(title="Walk", duration_minutes=30, priority=Priority.HIGH)


def test_mark_complete_changes_task_status():
    task = make_task()
    assert task.is_completed is False
    task.mark_complete()
    assert task.is_completed is True


def test_add_task_increases_pet_task_count():
    owner = make_owner()
    pet = make_pet(owner)
    assert len(pet.tasks) == 0
    pet.add_task(make_task())
    assert len(pet.tasks) == 1


def test_mark_task_complete_creates_next_instance_for_daily_task():
    owner = make_owner()
    pet = make_pet(owner)
    task = Task(
        title="Feed",
        duration_minutes=10,
        priority=Priority.HIGH,
        frequency="daily",
        scheduled_time="07:30",
    )
    pet.add_task(task)
    scheduler = Scheduler()

    next_task = scheduler.mark_task_complete(pet, task)

    assert task.is_completed is True
    assert next_task is not None
    assert next_task is not task
    assert next_task.title == task.title
    assert next_task.frequency == "daily"
    assert next_task.is_completed is False
    assert len(pet.tasks) == 2


def test_mark_task_complete_does_not_create_new_for_as_needed():
    owner = make_owner()
    pet = make_pet(owner)
    task = Task(
        title="As needed grooming",
        duration_minutes=15,
        priority=Priority.MEDIUM,
        frequency="as_needed",
    )
    pet.add_task(task)
    scheduler = Scheduler()

    next_task = scheduler.mark_task_complete(pet, task)

    assert task.is_completed is True
    assert next_task is None
    assert len(pet.tasks) == 1
