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
            st.subheader(f"Pending tasks for {selected_pet.name}")
            
            # Use Scheduler's sort_by_time to show chronological order
            scheduler = Scheduler()
            sorted_pending = scheduler.sort_by_time(pending)
            
            # Create visual display with better formatting
            display_data = []
            for t in sorted_pending:
                display_data.append({
                    "📌 Time": t.scheduled_time if t.scheduled_time else "Flexible",
                    "Task": t.title,
                    "Duration": f"{t.duration_minutes} min",
                    "Priority": "🔴 HIGH" if t.priority.value == "high" else ("🟡 MEDIUM" if t.priority.value == "medium" else "🟢 LOW"),
                    "Required": "✓" if t.is_required else "—",
                    "Frequency": t.frequency,
                })
            
            st.dataframe(display_data, use_container_width=True, hide_index=True)
        else:
            st.info("No pending tasks for this pet yet.")

    st.divider()

    # ── Filter Tasks ───────────────────────────────────────────────────────
    st.subheader("Filter & View Tasks")
    
    tab1, tab2 = st.tabs(["View by Filter", "View by Time (Sorted)"])
    
    with tab1:
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
                display_filter = []
                for pet, task in results:
                    priority_emoji = "🔴" if task.priority.value == "high" else ("🟡" if task.priority.value == "medium" else "🟢")
                    display_filter.append({
                        "🐾 Pet": pet.name,
                        "📋 Task": task.title,
                        "⏱️ Duration": f"{task.duration_minutes} min",
                        "Priority": f"{priority_emoji} {task.priority.value.upper()}",
                        "Status": "✓ Completed" if task.is_completed else "⏳ Pending",
                        "Frequency": task.frequency,
                    })
                
                st.dataframe(display_filter, use_container_width=True, hide_index=True)
            else:
                st.info("No tasks match the selected filters.")
    
    with tab2:
        if not owner.pets:
            st.info("Add pets and tasks to view sorted schedule.")
        else:
            scheduler = Scheduler()
            # Get all pending tasks and sort by time
            all_pending = []
            for pet in owner.pets:
                for task in pet.get_pending_tasks():
                    all_pending.append((pet, task))
            
            if all_pending:
                # Sort by using the scheduler's sort method
                sorted_tasks = scheduler.sort_by_time([t for _, t in all_pending])
                
                # Create mapping for display using object id because Task is unhashable
                task_to_pet = {id(t): p for p, t in all_pending}
                
                st.subheader("📅 Tasks Ordered by Time")
                st.caption("Pinned times first (chronological), then flexible tasks")
                
                display_sorted = []
                for task in sorted_tasks:
                    pet = task_to_pet[id(task)]
                    priority_emoji = "🔴" if task.priority.value == "high" else ("🟡" if task.priority.value == "medium" else "🟢")
                    time_display = f"🔔 {task.scheduled_time}" if task.scheduled_time else "⏳ Flexible"
                    required_badge = "⭐ Required" if task.is_required else ""
                    
                    display_sorted.append({
                        "Time": time_display,
                        "🐾 Pet": pet.name,
                        "Task": task.title,
                        "Duration": f"{task.duration_minutes} min",
                        "Priority": f"{priority_emoji} {task.priority.value.upper()}",
                        "Status": required_badge,
                    })
                
                st.dataframe(display_sorted, use_container_width=True, hide_index=True)
            else:
                st.info("No pending tasks to sort.")

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
            
            # ── PRE-SCHEDULE CONFLICT CHECK ────────────────────────────────
            # Check for conflicts in time hints before allocation
            pre_warnings = scheduler.check_time_hint_conflicts(owner)
            if pre_warnings:
                st.error("⚠️ **Pre-Schedule Conflicts Detected**")
                st.write("Some of your pinned task times overlap. These tasks cannot run simultaneously:")
                for warning in pre_warnings:
                    with st.container():
                        st.warning(warning, icon="🚨")
                st.info("**Tip:** Adjust the scheduled times (HH:MM) for these tasks before generating a final schedule.")
            
            # ── GENERATE PLANS ─────────────────────────────────────────────
            plans = scheduler.generate_plans_for_owner(owner, start_time=start_time, today=today_str)

            # ── TIME BUDGET OVERVIEW ───────────────────────────────────────
            st.subheader("📊 Time Budget Overview")
            total_used = sum(plan.total_minutes for plan in plans)
            budget = owner.time_available_minutes
            
            col_time1, col_time2, col_time3 = st.columns(3)
            with col_time1:
                st.metric("Total Available", f"{budget} min")
            with col_time2:
                st.metric("Total Scheduled", f"{total_used} min")
            with col_time3:
                remaining = budget - total_used
                st.metric("Remaining", f"{remaining} min", delta=f"{remaining} {'in reserve' if remaining >= 0 else 'OVER'}")
            
            # Visual progress bar
            if budget > 0:
                progress = min(total_used / budget, 1.0)
                st.progress(progress, text=f"{int(progress * 100)}% of time budget used")
            
            # Budget alert
            if total_used > budget:
                st.error(
                    f"⚠️ **Over Budget!** Scheduled time ({total_used} min) exceeds available time ({budget} min) by {total_used - budget} min. "
                    f"Consider reducing tasks or increasing available time."
                )
            elif total_used > budget * 0.85:
                st.warning(
                    f"⚡ **High Utilization** ({int(progress * 100)}% of budget). "
                    f"Limited flexibility for unexpected care needs."
                )
            else:
                st.success(f"✓ Schedule fits within your time budget with {remaining} min to spare.")

            # ── CROSS-PET CONFLICT DETECTION ───────────────────────────────
            conflicts = scheduler.detect_conflicts(plans)
            if conflicts:
                st.error(f"🚨 **{len(conflicts)} Scheduling Conflict(s) Found**")
                st.write("These tasks have overlapping times. You cannot do both at once:")
                
                for i, (st_a, pet_a, st_b, pet_b) in enumerate(conflicts, 1):
                    with st.container(border=True):
                        col_conflict1, col_conflict2 = st.columns(2)
                        
                        with col_conflict1:
                            st.write(f"**Conflict #{i}**")
                            st.info(
                                f"🐾 **{pet_a.name}**\n\n"
                                f"Task: {st_a.task.title}\n\n"
                                f"⏰ {st_a.start_time} – {st_a.end_time}"
                            )
                        
                        with col_conflict2:
                            st.write(" ")
                            st.write("**↔️ OVERLAPS WITH ↔️**")
                            st.info(
                                f"🐾 **{pet_b.name}**\n\n"
                                f"Task: {st_b.task.title}\n\n"
                                f"⏰ {st_b.start_time} – {st_b.end_time}"
                            )
                
                st.info(
                    "💡 **How to resolve:** "
                    "Move one task to a different time, mark a task as 'as_needed' (lower priority), "
                    "or ask for help during the conflict window."
                )
            else:
                st.success("✓ No scheduling conflicts detected!")

            # ── PER-PET PLANS ──────────────────────────────────────────────
            st.subheader("📋 Daily Plans")
            
            for plan in plans:
                with st.expander(f"🐾 {plan.pet.name}'s Schedule ({plan.total_minutes} min)", expanded=True):
                    # Summary banner
                    col_pet1, col_pet2, col_pet3 = st.columns(3)
                    with col_pet1:
                        st.metric("Scheduled Tasks", len(plan.scheduled_tasks))
                    with col_pet2:
                        st.metric("Skipped Tasks", len(plan.skipped_tasks))
                    with col_pet3:
                        st.metric("Total Duration", f"{plan.total_minutes} min")
                    
                    # Scheduled tasks
                    if plan.scheduled_tasks:
                        st.write("**✓ Scheduled Tasks**")
                        
                        sched_display = []
                        for sched in plan.scheduled_tasks:
                            priority_emoji = "🔴" if sched.task.priority.value == "high" else ("🟡" if sched.task.priority.value == "medium" else "🟢")
                            sched_display.append({
                                "⏰ Time": f"{sched.start_time} – {sched.end_time}",
                                "Task": sched.task.title,
                                "Duration": f"{sched.task.duration_minutes} min",
                                "Priority": f"{priority_emoji} {sched.task.priority.value.upper()}",
                                "Frequency": sched.task.frequency,
                                "Reason": sched.reason,
                            })
                        
                        st.dataframe(sched_display, use_container_width=True, hide_index=True)
                    else:
                        st.info("No tasks were scheduled for this pet today.")

                    # Skipped tasks with explanations
                    if plan.skipped_tasks:
                        st.write("**⏭️ Skipped Tasks** (not due today or over time budget)")
                        
                        skipped_display = []
                        for t in plan.skipped_tasks:
                            # Determine skip reason
                            if t.frequency == "weekly" and t.last_completed_date:
                                from datetime import date, timedelta
                                last = date.fromisoformat(t.last_completed_date)
                                days_ago = (date.today() - last).days
                                reason = f"Weekly task (completed {days_ago} days ago, due in {7 - days_ago} days)"
                            elif t.frequency == "daily" and t.is_completed:
                                reason = "Daily task (already completed)"
                            else:
                                reason = "Over time budget"
                            
                            priority_emoji = "🔴" if t.priority.value == "high" else ("🟡" if t.priority.value == "medium" else "🟢")
                            skipped_display.append({
                                "Task": t.title,
                                "Duration": f"{t.duration_minutes} min",
                                "Priority": f"{priority_emoji} {t.priority.value.upper()}",
                                "Why Skipped": reason,
                            })
                        
                        st.dataframe(skipped_display, use_container_width=True, hide_index=True)
else:
    st.info("Set an owner above to get started.")
