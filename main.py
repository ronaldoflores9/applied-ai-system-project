from pawpal_system import Owner, Pet, Task, Priority, Scheduler

# --- Setup ---
owner = Owner(name="Jordan", time_available_minutes=120)

mochi = Pet(name="Mochi", species="dog", owner=owner)
mochi.add_task(Task("Morning walk",      duration_minutes=30, priority=Priority.HIGH,   is_required=True,  frequency="daily",  scheduled_time="08:00"))
mochi.add_task(Task("Breakfast feeding", duration_minutes=10, priority=Priority.HIGH,   frequency="daily",  scheduled_time="07:30"))
mochi.add_task(Task("Fetch / playtime",  duration_minutes=20, priority=Priority.MEDIUM, frequency="daily"))
mochi.add_task(Task("Medication",        duration_minutes=5,  priority=Priority.HIGH,   frequency="daily",  scheduled_time="06:45"))
mochi.add_task(Task("Brush coat",        duration_minutes=15, priority=Priority.LOW,    frequency="weekly"))
# Deliberate same-pet conflict: Vet appointment overlaps Morning walk (both at 08:00)
mochi.add_task(Task("Vet appointment",   duration_minutes=20, priority=Priority.HIGH,   frequency="as_needed", scheduled_time="08:00"))

luna = Pet(name="Luna", species="cat", owner=owner)
luna.add_task(Task("Breakfast feeding",  duration_minutes=5,  priority=Priority.HIGH,   is_required=True,  frequency="daily",  species=["cat"], scheduled_time="07:30"))
luna.add_task(Task("Litter box clean",   duration_minutes=10, priority=Priority.HIGH,   frequency="daily",  species=["cat"]))
luna.add_task(Task("Interactive play",   duration_minutes=15, priority=Priority.MEDIUM, frequency="daily"))
luna.add_task(Task("Eye drops",          duration_minutes=5,  priority=Priority.HIGH,   frequency="daily",  scheduled_time="06:30"))
luna.add_task(Task("Nail trim",          duration_minutes=20, priority=Priority.LOW,    frequency="weekly"))

owner.add_pet(mochi)
owner.add_pet(luna)

scheduler = Scheduler()

# --- Pre-schedule conflict check (catches same-pet overlaps before allocation) ---
print("=" * 60)
print("  Pre-Schedule Conflict Check")
print("=" * 60)
pre_warnings = scheduler.check_time_hint_conflicts(owner)
if pre_warnings:
    for w in pre_warnings:
        print(f"  WARNING: {w}")
else:
    print("  No pre-schedule conflicts found.")

# Mark one recurring task complete through Scheduler.
# This also creates the next pending occurrence for daily/weekly tasks.
next_occurrence = scheduler.mark_task_complete(mochi, mochi.tasks[2])

# --- Feature 3: Recurring tasks — only due tasks are scheduled ---
today = "2026-03-25"
plans = scheduler.generate_plans_for_owner(owner, start_time="07:30", today=today)

# --- Display per-pet plans ---
print("=" * 60)
print(f"  Today's Schedule  —  Owner: {owner.name}  ({today})")
print("=" * 60)

if next_occurrence:
    print(
        f"Created next recurring task for {mochi.name}: "
        f"{next_occurrence.title} ({next_occurrence.frequency})"
    )

for plan in plans:
    print(f"\n[ {plan.pet.name} ({plan.pet.species}) ]")
    print(f"  Time budget : {owner.time_available_minutes} min")
    print(f"  Time used   : {plan.total_minutes} min")

    if plan.scheduled_tasks:
        print("\n  Scheduled tasks:")
        for st in plan.scheduled_tasks:
            flag = " *" if st.task.is_required else ""
            pin  = f" [pinned {st.task.scheduled_time}]" if st.task.scheduled_time else ""
            print(f"    {st.start_time} - {st.end_time}  {st.task.title}{flag}{pin}  ({st.task.priority.value}, {st.task.frequency})")

    if plan.skipped_tasks:
        print("\n  Skipped tasks (over time budget or not due today):")
        for t in plan.skipped_tasks:
            print(f"    - {t.title} ({t.duration_minutes} min, {t.frequency})")

    print(f"\n  Summary: {plan.summary}")

# --- Feature 5: Shared time budget guard ---
total_used = sum(plan.total_minutes for plan in plans)
print("\n" + "=" * 60)

# --- Sorting demo: tasks intentionally added out of order ---
print("  Sorting demo: Mochi tasks sorted by HH:MM scheduled_time")
print("=" * 60)
sorted_mochi = scheduler.sort_by_time(mochi.tasks)
for task in sorted_mochi:
    when = task.scheduled_time if task.scheduled_time else "(no time)"
    print(f"  {when} - {task.title}")

# --- New filtering demo: by completion and pet name ---
print("\n" + "=" * 60)
print("  Filtering demo: completed tasks for Mochi")
print("=" * 60)
completed_mochi = scheduler.filter_by_status_or_pet(owner, is_completed=True, pet_name="Mochi")
for pet, task in completed_mochi:
    print(f"  [{pet.name}] {task.title} - completed={task.is_completed}")

print("\n" + "=" * 60)
print("  Filtering demo: all pending tasks")
print("=" * 60)
pending_tasks = scheduler.filter_by_status_or_pet(owner, is_completed=False)
for pet, task in pending_tasks:
    print(f"  [{pet.name}] {task.title} - completed={task.is_completed}")

print("\n" + "=" * 60)
print(f"  Total time used across all pets: {total_used} / {owner.time_available_minutes} min")
if total_used > owner.time_available_minutes:
    print("  WARNING: Total scheduled time exceeds owner's available time!")
else:
    print("  OK: Within owner's time budget.")

# --- Feature 4: Post-schedule conflict detection (same-pet + cross-pet) ---
print("\n" + "=" * 60)
print("  Post-Schedule Conflict Warnings")
print("=" * 60)
warnings = scheduler.get_conflict_warnings(plans)
if warnings:
    for w in warnings:
        print(f"  WARNING: {w}")
else:
    print("  No post-schedule conflicts found.")

# --- Feature 2: Filter tasks by pet / status / priority ---
print("\n" + "=" * 60)
print("  Filter demo: all HIGH-priority pending tasks")
print("=" * 60)
filtered = scheduler.filter_tasks(owner, status="pending", priority="high")
for pet, task in filtered:
    print(f"  [{pet.name}] {task.title} — {task.priority.value}, {task.frequency}")

print("\n" + "=" * 60)
