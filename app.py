import streamlit as st
from datetime import date

from pawpal_system import Owner, Pet, Task, Priority, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")

if "owner" not in st.session_state:
    st.session_state.owner = None

st.divider()
st.subheader("Owner Setup")

owner_name = st.text_input("Owner name", value="Jordan")
time_available = st.number_input("Time available today (minutes)", min_value=30, max_value=480, value=120)

if st.button("Set Owner"):
    st.session_state.owner = Owner(name=owner_name, time_available_minutes=int(time_available))
    st.success(f"Owner '{owner_name}' saved with {time_available} minutes available.")

if st.session_state.owner:
    owner: Owner = st.session_state.owner
    st.info(f"Current owner: **{owner.name}** | Time available: {owner.time_available_minutes} min | Pets: {len(owner.pets)}")

    st.divider()

    # ── Add a Pet ──────────────────────────────────────────────────────────
    st.subheader("Add a Pet")
    pet_name = st.text_input("Pet name", value="Mochi")
    species = st.selectbox("Species", ["dog", "cat", "other"])

    if st.button("Add Pet"):
        new_pet = Pet(name=pet_name, species=species, owner=owner)
        owner.add_pet(new_pet)
        st.success(f"Added pet '{pet_name}' ({species}) to {owner.name}'s profile.")

    if owner.pets:
        st.write("Registered pets:", [p.name for p in owner.pets])

    st.divider()

    # ── Schedule a Task ────────────────────────────────────────────────────
    st.subheader("Add a Task to a Pet")

    if not owner.pets:
        st.warning("Add a pet first before scheduling tasks.")
    else:
        pet_names = [p.name for p in owner.pets]
        selected_pet_name = st.selectbox("Select pet", pet_names)
        selected_pet = next(p for p in owner.pets if p.name == selected_pet_name)

        col1, col2, col3 = st.columns(3)
        with col1:
            task_title = st.text_input("Task title", value="Morning walk")
        with col2:
            duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
        with col3:
            priority_str = st.selectbox("Priority", ["low", "medium", "high"], index=2)

        col4, col5, col6 = st.columns(3)
        with col4:
            is_required = st.checkbox("Required task?")
        with col5:
            frequency = st.selectbox("Frequency", ["daily", "weekly", "as_needed"])
        with col6:
            scheduled_time = st.text_input("Scheduled time (HH:MM, optional)", value="")

        if st.button("Add Task"):
            new_task = Task(
                title=task_title,
                duration_minutes=int(duration),
                priority=Priority(priority_str),
                is_required=is_required,
                frequency=frequency,
                scheduled_time=scheduled_time.strip(),
            )
            selected_pet.add_task(new_task)
            st.success(f"Task '{task_title}' added to {selected_pet.name}.")

        # Show pending tasks for the selected pet
        pending = selected_pet.get_pending_tasks()
        if pending:
            st.write(f"Pending tasks for **{selected_pet.name}**:")
            st.table([
                {
                    "title": t.title,
                    "duration (min)": t.duration_minutes,
                    "priority": t.priority.value,
                    "required": t.is_required,
                    "frequency": t.frequency,
                    "scheduled_time": t.scheduled_time or "—",
                }
                for t in pending
            ])
        else:
            st.info("No pending tasks for this pet yet.")

    st.divider()

    # ── Filter Tasks ───────────────────────────────────────────────────────
    st.subheader("Filter Tasks")

    if not owner.pets:
        st.info("Add pets and tasks to use filters.")
    else:
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            filter_pet = st.selectbox("Filter by pet", ["All"] + [p.name for p in owner.pets], key="filter_pet")
        with fc2:
            filter_status = st.selectbox("Filter by status", ["All", "pending", "completed"], key="filter_status")
        with fc3:
            filter_priority = st.selectbox("Filter by priority", ["All", "high", "medium", "low"], key="filter_priority")

        scheduler = Scheduler()
        results = scheduler.filter_tasks(
            owner,
            pet_name=None if filter_pet == "All" else filter_pet,
            status=None if filter_status == "All" else filter_status,
            priority=None if filter_priority == "All" else filter_priority,
        )

        if results:
            st.table([
                {
                    "pet": pet.name,
                    "task": task.title,
                    "priority": task.priority.value,
                    "status": "completed" if task.is_completed else "pending",
                    "frequency": task.frequency,
                    "duration (min)": task.duration_minutes,
                }
                for pet, task in results
            ])
        else:
            st.info("No tasks match the selected filters.")

    st.divider()

    # ── Generate Schedule ──────────────────────────────────────────────────
    st.subheader("Build Schedule")

    start_time = st.text_input("Start time (HH:MM)", value="08:00")
    today_str = st.text_input("Today's date (YYYY-MM-DD)", value=date.today().isoformat())

    if st.button("Generate Schedule"):
        if not owner.pets:
            st.warning("Add at least one pet before generating a schedule.")
        else:
            scheduler = Scheduler()
            plans = scheduler.generate_plans_for_owner(owner, start_time=start_time, today=today_str)

            # ── Shared time budget guard ───────────────────────────────────
            total_used = sum(plan.total_minutes for plan in plans)
            if total_used > owner.time_available_minutes:
                st.warning(
                    f"Total scheduled time across all pets ({total_used} min) "
                    f"exceeds your available {owner.time_available_minutes} min. "
                    "Consider reducing tasks or increasing available time."
                )

            # ── Cross-pet conflict detection ───────────────────────────────
            conflicts = scheduler.detect_conflicts(plans)
            if conflicts:
                st.error(f"**{len(conflicts)} scheduling conflict(s) detected:**")
                for st_a, pet_a, st_b, pet_b in conflicts:
                    st.warning(
                        f"**{pet_a.name}** — {st_a.task.title} ({st_a.start_time}–{st_a.end_time})  "
                        f"overlaps with  "
                        f"**{pet_b.name}** — {st_b.task.title} ({st_b.start_time}–{st_b.end_time})"
                    )

            # ── Per-pet plans ──────────────────────────────────────────────
            for plan in plans:
                st.markdown(f"### {plan.pet.name}'s Plan")
                st.caption(plan.summary)

                if plan.scheduled_tasks:
                    st.write("**Scheduled:**")
                    st.table([
                        {
                            "task": sched.task.title,
                            "start": sched.start_time,
                            "end": sched.end_time,
                            "duration (min)": sched.task.duration_minutes,
                            "priority": sched.task.priority.value,
                            "frequency": sched.task.frequency,
                            "reason": sched.reason,
                        }
                        for sched in plan.scheduled_tasks
                    ])
                else:
                    st.info("No tasks were scheduled.")

                if plan.skipped_tasks:
                    st.write("**Skipped (over time budget or not due today):**")
                    st.table([
                        {
                            "task": t.title,
                            "duration (min)": t.duration_minutes,
                            "priority": t.priority.value,
                            "frequency": t.frequency,
                        }
                        for t in plan.skipped_tasks
                    ])
else:
    st.info("Set an owner above to get started.")
