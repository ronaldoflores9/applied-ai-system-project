import streamlit as st
from datetime import date

from pawpal_system import Owner, Pet, Task, Priority, Scheduler

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

# ── Shared style helpers ────────────────────────────────────────────────────────

def _priority_badge(pval: str) -> str:
    """Return an HTML badge for a priority value string."""
    cfg = {
        "high":   ("#ff4b4b", "white",  "🔴 HIGH"),
        "medium": ("#f0a500", "white",  "🟡 MEDIUM"),
        "low":    ("#21c354", "white",  "🟢 LOW"),
    }
    bg, fg, label = cfg.get(pval, ("#888", "white", pval.upper()))
    return (
        f'<span style="background:{bg};color:{fg};padding:2px 8px;'
        f'border-radius:4px;font-size:0.8em;font-weight:bold;">{label}</span>'
    )

def _status_pill(is_completed: bool) -> str:
    if is_completed:
        return '<span style="background:#21c354;color:white;padding:2px 8px;border-radius:12px;font-size:0.8em;">✅ Done</span>'
    return '<span style="background:#4a90d9;color:white;padding:2px 8px;border-radius:12px;font-size:0.8em;">⏳ Pending</span>'

def _freq_badge(freq: str) -> str:
    icons = {"daily": "🔁 Daily", "weekly": "📅 Weekly", "as_needed": "🎯 As Needed"}
    label = icons.get(freq, freq)
    return f'<span style="background:#555;color:#eee;padding:1px 7px;border-radius:4px;font-size:0.78em;">{label}</span>'

def _task_emoji(title: str, category: str = "") -> str:
    """Guess a fitting emoji from the task title or category keywords."""
    text = (title + " " + category).lower()
    if any(k in text for k in ("walk", "run", "hike", "exercise")):
        return "🦮"
    if any(k in text for k in ("feed", "food", "meal", "treat", "water")):
        return "🍖"
    if any(k in text for k in ("med", "pill", "drug", "inject", "vaccine")):
        return "💊"
    if any(k in text for k in ("groom", "bath", "brush", "nail", "trim")):
        return "✂️"
    if any(k in text for k in ("play", "toy", "enrich", "game")):
        return "🎾"
    if any(k in text for k in ("vet", "check", "appoint", "clinic")):
        return "🏥"
    if any(k in text for k in ("train", "lesson", "obedien")):
        return "🎓"
    if any(k in text for k in ("sleep", "rest", "nap", "bed")):
        return "😴"
    if any(k in text for k in ("litter", "clean", "sanitize", "scoop")):
        return "🧹"
    return "🐾"

def _species_emoji(species: str) -> str:
    return {"dog": "🐕", "cat": "🐈"}.get(species.lower(), "🐾")

def _priority_border(pval: str) -> str:
    return {"high": "#ff4b4b", "medium": "#f0a500", "low": "#21c354"}.get(pval, "#888")

def _priority_bg(pval: str) -> str:
    return {"high": "#2d1515", "medium": "#2d2010", "low": "#0f2d18"}.get(pval, "#1e1e1e")

# ── Hero header ────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div style="background:linear-gradient(135deg,#1a1a2e 0%,#16213e 60%,#0f3460 100%);
                border-radius:12px;padding:28px 32px 20px;margin-bottom:24px;
                border:1px solid #0f3460;">
      <h1 style="margin:0;color:#e0e0ff;font-size:2.2em;">🐾 PawPal+</h1>
      <p style="margin:6px 0 0;color:#8899bb;font-size:1em;">
        Smart pet-care scheduling · Priority-aware · Conflict-safe
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Session state ──────────────────────────────────────────────────────────────
if "owner" not in st.session_state:
    st.session_state.owner = None
if "plans" not in st.session_state:
    st.session_state.plans = None

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — Owner setup
# ══════════════════════════════════════════════════════════════════════════════
with st.expander("👤 Owner Setup", expanded=st.session_state.owner is None):
    owner_name    = st.text_input("Owner name", value="Jordan")
    time_available = st.number_input(
        "Time available today (minutes)", min_value=30, max_value=480, value=120
    )
    if st.button("💾 Save Owner", use_container_width=True):
        st.session_state.owner = Owner(
            name=owner_name, time_available_minutes=int(time_available)
        )
        st.success(f"✓ Owner **{owner_name}** saved with **{time_available} min** available.")

# ── Owner dashboard card ───────────────────────────────────────────────────────
if st.session_state.owner:
    owner: Owner = st.session_state.owner
    pet_count = len(owner.pets)
    task_count = sum(len(p.tasks) for p in owner.pets)
    st.markdown(
        f"""
        <div style="background:#1a2035;border:1px solid #2a4070;border-radius:10px;
                    padding:14px 20px;margin-bottom:8px;display:flex;gap:32px;
                    align-items:center;">
          <div>
            <div style="color:#8899bb;font-size:0.75em;text-transform:uppercase;">Owner</div>
            <div style="color:#e0e0ff;font-size:1.1em;font-weight:bold;">{owner.name}</div>
          </div>
          <div>
            <div style="color:#8899bb;font-size:0.75em;text-transform:uppercase;">Time Budget</div>
            <div style="color:#21c354;font-size:1.1em;font-weight:bold;">{owner.time_available_minutes} min</div>
          </div>
          <div>
            <div style="color:#8899bb;font-size:0.75em;text-transform:uppercase;">Pets</div>
            <div style="color:#e0e0ff;font-size:1.1em;font-weight:bold;">{pet_count}</div>
          </div>
          <div>
            <div style="color:#8899bb;font-size:0.75em;text-transform:uppercase;">Total Tasks</div>
            <div style="color:#e0e0ff;font-size:1.1em;font-weight:bold;">{task_count}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

if st.session_state.owner:
    owner: Owner = st.session_state.owner

    st.divider()

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 2 — Add a Pet
    # ══════════════════════════════════════════════════════════════════════════
    st.subheader("🐾 Add a Pet")
    col_pn, col_sp, col_btn = st.columns([2, 2, 1])
    with col_pn:
        pet_name = st.text_input("Pet name", value="Mochi")
    with col_sp:
        species = st.selectbox("Species", ["dog", "cat", "other"])
    with col_btn:
        st.write("")
        st.write("")
        if st.button("➕ Add", use_container_width=True):
            new_pet = Pet(name=pet_name, species=species, owner=owner)
            owner.add_pet(new_pet)
            st.success(f"Added **{pet_name}** ({species}).")

    # Pet profile cards
    if owner.pets:
        cols = st.columns(min(len(owner.pets), 4))
        for i, pet in enumerate(owner.pets):
            pending_n  = len(pet.get_pending_tasks())
            completed_n = sum(1 for t in pet.tasks if t.is_completed)
            with cols[i % 4]:
                st.markdown(
                    f"""
                    <div style="background:#1a2035;border:1px solid #2a4070;border-radius:10px;
                                padding:14px;text-align:center;margin-bottom:4px;">
                      <div style="font-size:2em;">{_species_emoji(pet.species)}</div>
                      <div style="color:#e0e0ff;font-weight:bold;font-size:1em;">{pet.name}</div>
                      <div style="color:#8899bb;font-size:0.78em;">{pet.species}</div>
                      <hr style="border-color:#2a4070;margin:8px 0;">
                      <div style="display:flex;justify-content:space-around;">
                        <div>
                          <div style="color:#4a90d9;font-size:1.1em;font-weight:bold;">{pending_n}</div>
                          <div style="color:#8899bb;font-size:0.7em;">Pending</div>
                        </div>
                        <div>
                          <div style="color:#21c354;font-size:1.1em;font-weight:bold;">{completed_n}</div>
                          <div style="color:#8899bb;font-size:0.7em;">Done</div>
                        </div>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    st.divider()

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 3 — Add a Task
    # ══════════════════════════════════════════════════════════════════════════
    st.subheader("📋 Add a Task to a Pet")

    if not owner.pets:
        st.warning("Add a pet first before scheduling tasks.")
    else:
        pet_names        = [p.name for p in owner.pets]
        selected_pet_name = st.selectbox("Select pet", pet_names)
        selected_pet      = next(p for p in owner.pets if p.name == selected_pet_name)

        col1, col2, col3 = st.columns(3)
        with col1:
            task_title = st.text_input("Task title", value="Morning walk")
        with col2:
            duration = st.number_input("Duration (min)", min_value=1, max_value=240, value=20)
        with col3:
            priority_str = st.selectbox("Priority", ["low", "medium", "high"], index=2)

        col4, col5, col6 = st.columns(3)
        with col4:
            is_required = st.checkbox("Required task?")
        with col5:
            frequency = st.selectbox("Frequency", ["daily", "weekly", "as_needed"])
        with col6:
            scheduled_time = st.text_input("Pinned time (HH:MM, optional)", value="")

        if st.button("➕ Add Task", use_container_width=True):
            new_task = Task(
                title=task_title,
                duration_minutes=int(duration),
                priority=Priority(priority_str),
                is_required=is_required,
                frequency=frequency,
                scheduled_time=scheduled_time.strip(),
            )
            selected_pet.add_task(new_task)
            st.success(f"Task **{task_title}** added to {selected_pet.name}.")

        # ── Interactive task list ──────────────────────────────────────────
        all_tasks = selected_pet.tasks  # show pending + completed
        if all_tasks:
            st.markdown(
                f"##### Tasks — {_species_emoji(selected_pet.species)} {selected_pet.name}"
            )
            scheduler = Scheduler()
            sorted_tasks = scheduler.sort_by_time(
                [t for t in all_tasks if not t.is_completed]
            ) + [t for t in all_tasks if t.is_completed]

            for idx, t in enumerate(sorted_tasks):
                emoji  = _task_emoji(t.title, t.category)
                pval   = t.priority.value
                p_icon = "🔴" if pval == "high" else "🟡" if pval == "medium" else "🟢"
                uid    = f"{id(selected_pet)}_{id(t)}"

                if t.is_completed:
                    # Completed — read-only muted row
                    st.markdown(
                        f'<div style="background:#111a27;border-left:4px solid #333;'
                        f'border-radius:6px;padding:8px 14px;margin-bottom:4px;'
                        f'color:#556;opacity:0.7;">'
                        f"✅ <s>{emoji} {t.title}</s> &nbsp;"
                        f'<small>{p_icon} {pval.upper()} | {t.duration_minutes} min</small>'
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    # Pending — editable row
                    col_info, col_time, col_done = st.columns([4, 2, 1])
                    with col_info:
                        st.markdown(
                            f'<div style="padding:6px 0;color:#e0e0ff;">'
                            f"{p_icon} <strong>{emoji} {t.title}</strong>"
                            f'<br/><small style="color:#8899bb;">'
                            f"⏱️ {t.duration_minutes} min &nbsp;|&nbsp; 🔁 {t.frequency}"
                            f"{'&nbsp;|&nbsp; ⭐ Required' if t.is_required else ''}</small>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                    with col_time:
                        new_time = st.text_input(
                            "Time (HH:MM)",
                            value=t.scheduled_time,
                            placeholder="e.g. 09:30",
                            key=f"time_{uid}",
                            label_visibility="collapsed",
                        )
                        t.scheduled_time = new_time.strip()
                    with col_done:
                        if st.button("✅", key=f"done_{uid}", help="Mark as done"):
                            t.mark_complete()
                            st.session_state.plans = None
                            st.rerun()
        else:
            st.info("No tasks for this pet yet.")

    st.divider()

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 4 — Filter & View
    # ══════════════════════════════════════════════════════════════════════════
    st.subheader("🔍 Filter & View Tasks")
    tab1, tab2, tab3 = st.tabs(["View by Filter", "📅 Time (Sorted)", "🔴 Priority View"])

    with tab1:
        if not owner.pets:
            st.info("Add pets and tasks to use filters.")
        else:
            fc1, fc2, fc3 = st.columns(3)
            with fc1:
                filter_pet = st.selectbox("Pet", ["All"] + [p.name for p in owner.pets], key="filter_pet")
            with fc2:
                filter_status = st.selectbox("Status", ["All", "pending", "completed"], key="filter_status")
            with fc3:
                filter_priority = st.selectbox("Priority", ["All", "high", "medium", "low"], key="filter_priority")

            scheduler = Scheduler()
            results = scheduler.filter_tasks(
                owner,
                pet_name=None if filter_pet == "All" else filter_pet,
                status=None if filter_status == "All" else filter_status,
                priority=None if filter_priority == "All" else filter_priority,
            )

            if results:
                st.caption(f"{len(results)} task(s) matched")
                rows = []
                for pet, task in results:
                    emoji = _task_emoji(task.title, task.category)
                    rows.append({
                        "🐾 Pet":      f"{_species_emoji(pet.species)} {pet.name}",
                        "Task":        f"{emoji} {task.title}",
                        "Min":         task.duration_minutes,
                        "Priority":    f"{'🔴' if task.priority.value=='high' else '🟡' if task.priority.value=='medium' else '🟢'} {task.priority.value.upper()}",
                        "Status":      "✅ Done" if task.is_completed else "⏳ Pending",
                        "Frequency":   task.frequency,
                        "Required":    "⭐" if task.is_required else "—",
                    })
                st.dataframe(rows, use_container_width=True, hide_index=True)
            else:
                st.info("No tasks match the selected filters.")

    with tab2:
        if not owner.pets:
            st.info("Add pets and tasks to view sorted schedule.")
        else:
            scheduler = Scheduler()
            all_pending = [(pet, task) for pet in owner.pets for task in pet.get_pending_tasks()]
            if all_pending:
                task_to_pet   = {id(t): p for p, t in all_pending}
                sorted_tasks  = scheduler.sort_by_time([t for _, t in all_pending])
                st.caption("Pinned times first (chronological), then flexible tasks")
                rows = []
                for task in sorted_tasks:
                    pet   = task_to_pet[id(task)]
                    emoji = _task_emoji(task.title, task.category)
                    rows.append({
                        "Time":      f"🔔 {task.scheduled_time}" if task.scheduled_time else "⏳ Flexible",
                        "🐾 Pet":   f"{_species_emoji(pet.species)} {pet.name}",
                        "Task":      f"{emoji} {task.title}",
                        "Min":       task.duration_minutes,
                        "Priority":  f"{'🔴' if task.priority.value=='high' else '🟡' if task.priority.value=='medium' else '🟢'} {task.priority.value.upper()}",
                        "Required":  "⭐ Yes" if task.is_required else "—",
                    })
                st.dataframe(rows, use_container_width=True, hide_index=True)
            else:
                st.info("No pending tasks to sort.")

    with tab3:
        if not owner.pets:
            st.info("Add pets and tasks to use the priority view.")
        else:
            scheduler   = Scheduler()
            all_pending = [(pet, task) for pet in owner.pets for task in pet.get_pending_tasks()]
            if not all_pending:
                st.info("No pending tasks.")
            else:
                task_to_pet     = {id(t): p for p, t in all_pending}
                priority_sorted = scheduler.sort_by_priority_then_time([t for _, t in all_pending])

                st.caption("Tasks ranked **High → Medium → Low**, then by time within each tier.")
                st.markdown(
                    "**Legend:** &nbsp;"
                    '<span style="background:#ff4b4b;color:white;padding:2px 8px;border-radius:4px;font-weight:bold;font-size:0.85em;">🔴 HIGH</span>'
                    "&nbsp;"
                    '<span style="background:#f0a500;color:white;padding:2px 8px;border-radius:4px;font-weight:bold;font-size:0.85em;">🟡 MEDIUM</span>'
                    "&nbsp;"
                    '<span style="background:#21c354;color:white;padding:2px 8px;border-radius:4px;font-weight:bold;font-size:0.85em;">🟢 LOW</span>',
                    unsafe_allow_html=True,
                )
                st.write("")

                for rank, task in enumerate(priority_sorted, start=1):
                    pet    = task_to_pet[id(task)]
                    pval   = task.priority.value
                    emoji  = _task_emoji(task.title, task.category)
                    border = _priority_border(pval)
                    bg     = _priority_bg(pval)
                    badge  = _priority_badge(pval)
                    freq   = _freq_badge(task.frequency)
                    time_s = f"🔔 {task.scheduled_time}" if task.scheduled_time else "⏳ Flexible"
                    req_s  = "&nbsp;⭐ <em>Required</em>" if task.is_required else ""
                    st.markdown(
                        f'<div style="background:{bg};border-left:5px solid {border};'
                        f'border-radius:6px;padding:10px 14px;margin-bottom:6px;color:#e0e0ff;">'
                        f"<strong>#{rank} &nbsp;{emoji} {task.title}</strong>"
                        f"&nbsp; {badge} &nbsp;{freq}{req_s}<br/>"
                        f'<small style="color:#8899bb;">🐾 {_species_emoji(pet.species)} {pet.name}'
                        f"&nbsp;|&nbsp; {time_s} &nbsp;|&nbsp; ⏱️ {task.duration_minutes} min</small>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

    st.divider()

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 5 — Smart Recommendation
    # ══════════════════════════════════════════════════════════════════════════
    st.subheader("💡 Smart Recommendation")
    st.caption("Got an unexpected free window? Find out what to do next.")

    rec_col1, rec_col2, rec_col3 = st.columns(3)
    with rec_col1:
        free_minutes = st.number_input("Free minutes", min_value=5, max_value=240, value=30)
    with rec_col2:
        current_time = st.text_input("Current time (HH:MM)", value=date.today().strftime("%H:%M") if True else "09:00")
    with rec_col3:
        rec_today = st.text_input("Today's date", value=date.today().isoformat(), key="rec_today")

    if st.button("🔍 Recommend a Task", use_container_width=True):
        scheduler = Scheduler()
        result = scheduler.recommend_next(
            owner,
            available_minutes=int(free_minutes),
            current_time=current_time,
            today=rec_today,
        )
        if result:
            rec_pet, rec_task, rec_score = result
            pval  = rec_task.priority.value
            emoji = _task_emoji(rec_task.title, rec_task.category)
            st.markdown(
                f"""
                <div style="background:{_priority_bg(pval)};border:2px solid {_priority_border(pval)};
                            border-radius:10px;padding:18px 22px;margin-top:8px;color:#e0e0ff;">
                  <div style="font-size:0.75em;color:#8899bb;text-transform:uppercase;margin-bottom:4px;">
                    Best match for {free_minutes} free minutes
                  </div>
                  <div style="font-size:1.4em;font-weight:bold;">
                    {emoji} {rec_task.title}
                  </div>
                  <div style="margin:6px 0;">
                    {_priority_badge(pval)} &nbsp; {_freq_badge(rec_task.frequency)}
                    {"&nbsp; ⭐ <strong>Required</strong>" if rec_task.is_required else ""}
                  </div>
                  <div style="color:#8899bb;font-size:0.88em;">
                    🐾 {_species_emoji(rec_pet.species)} {rec_pet.name}
                    &nbsp;|&nbsp; ⏱️ {rec_task.duration_minutes} min
                    &nbsp;|&nbsp; 📊 Urgency score: <strong style="color:#e0e0ff;">{rec_score:.1f}</strong>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.info("No tasks fit the available window, or all pending tasks are pinned to a future time.")

    st.divider()

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 6 — Generate Schedule
    # ══════════════════════════════════════════════════════════════════════════
    st.subheader("🗓️ Build Today's Schedule")

    g_col1, g_col2 = st.columns(2)
    with g_col1:
        start_time = st.text_input("Start time (HH:MM)", value="08:00")
    with g_col2:
        today_str = st.text_input("Date (YYYY-MM-DD)", value=date.today().isoformat())

    if st.button("⚡ Generate Schedule", use_container_width=True):
        if not owner.pets:
            st.warning("Add at least one pet before generating a schedule.")
        else:
            scheduler = Scheduler()
            pre_warnings = scheduler.check_time_hint_conflicts(owner)
            st.session_state.plans = scheduler.generate_plans_for_owner(
                owner, start_time=start_time, today=today_str
            )
            st.session_state.pre_warnings = pre_warnings

    # ── Results (persist across reruns via session_state) ──────────────────
    if st.session_state.plans:
        plans     = st.session_state.plans
        scheduler = Scheduler()

        # Pre-schedule warnings
        for w in st.session_state.get("pre_warnings", []):
            st.warning(w, icon="🚨")

        # Time budget
        st.markdown("#### 📊 Time Budget Overview")
        total_used = sum(plan.total_minutes for plan in plans)
        budget     = owner.time_available_minutes
        remaining  = budget - total_used
        progress   = min(total_used / budget, 1.0) if budget > 0 else 0

        m1, m2, m3 = st.columns(3)
        m1.metric("Available", f"{budget} min")
        m2.metric("Scheduled", f"{total_used} min")
        m3.metric("Remaining", f"{remaining} min",
                  delta=f"{remaining} {'in reserve' if remaining >= 0 else 'OVER BUDGET'}")
        st.progress(progress, text=f"{int(progress * 100)}% of daily budget used")

        if total_used > budget:
            st.error(f"⚠️ Over budget by {total_used - budget} min.")
        elif total_used > budget * 0.85:
            st.warning(f"⚡ High utilization ({int(progress*100)}%). Little buffer for surprises.")
        else:
            st.success(f"✓ Schedule fits within budget with {remaining} min to spare.")

        # Conflict detection
        conflicts = scheduler.detect_conflicts(plans)
        if conflicts:
            st.error(f"🚨 **{len(conflicts)} Scheduling Conflict(s) Found**")
            for i, (st_a, pet_a, st_b, pet_b) in enumerate(conflicts, 1):
                with st.container(border=True):
                    ca, cb = st.columns(2)
                    with ca:
                        st.markdown(
                            f"**Conflict #{i}**<br/>"
                            f"🐾 **{pet_a.name}**<br/>"
                            f"{_task_emoji(st_a.task.title)} {st_a.task.title}<br/>"
                            f"⏰ {st_a.start_time} – {st_a.end_time}",
                            unsafe_allow_html=True,
                        )
                    with cb:
                        st.markdown(
                            f"↔️ **OVERLAPS WITH**<br/>"
                            f"🐾 **{pet_b.name}**<br/>"
                            f"{_task_emoji(st_b.task.title)} {st_b.task.title}<br/>"
                            f"⏰ {st_b.start_time} – {st_b.end_time}",
                            unsafe_allow_html=True,
                        )

            # Auto-resolve button — lives OUTSIDE generate block so it survives reruns
            if st.button("🔧 Auto-Resolve Conflicts", use_container_width=True):
                changes = scheduler.resolve_conflicts(owner)
                if changes:
                    for task, old_t, new_t in changes:
                        emoji = _task_emoji(task.title, task.category)
                        st.markdown(
                            f'<div style="background:#1a2035;border-left:4px solid #f0a500;'
                            f'border-radius:6px;padding:8px 14px;margin-bottom:4px;color:#e0e0ff;">'
                            f"{emoji} <strong>{task.title}</strong>"
                            f'&nbsp;<span style="color:#ff4b4b;text-decoration:line-through;">{old_t}</span>'
                            f'&nbsp;→&nbsp;<span style="color:#21c354;">{new_t}</span></div>',
                            unsafe_allow_html=True,
                        )
                    # Rebuild plan immediately with the fixed times
                    st.session_state.plans = Scheduler().generate_plans_for_owner(
                        owner, start_time=start_time, today=today_str
                    )
                    st.success(f"✓ Resolved {len(changes)} conflict(s). Schedule rebuilt.")
                    st.rerun()
                else:
                    st.info("No pinned-time conflicts to resolve.")
        else:
            st.success("✓ No scheduling conflicts detected!")

        # Per-pet plans
        st.markdown("#### 📋 Daily Plans")
        for plan in plans:
            pet_emoji = _species_emoji(plan.pet.species)
            with st.expander(
                f"{pet_emoji} {plan.pet.name}'s Schedule — {plan.total_minutes} min scheduled",
                expanded=True,
            ):
                pm1, pm2, pm3 = st.columns(3)
                pm1.metric("Scheduled", len(plan.scheduled_tasks))
                pm2.metric("Skipped",   len(plan.skipped_tasks))
                pm3.metric("Duration",  f"{plan.total_minutes} min")

                if plan.scheduled_tasks:
                    st.markdown("**✅ Scheduled Tasks**")
                    sched_rows = []
                    for sched in plan.scheduled_tasks:
                        t    = sched.task
                        pval = t.priority.value
                        sched_rows.append({
                            "⏰ Time":   f"{sched.start_time} – {sched.end_time}",
                            "Task":      f"{_task_emoji(t.title, t.category)} {t.title}",
                            "Min":       t.duration_minutes,
                            "Priority":  f"{'🔴' if pval=='high' else '🟡' if pval=='medium' else '🟢'} {pval.upper()}",
                            "Frequency": t.frequency,
                            "Required":  "⭐" if t.is_required else "—",
                            "Reason":    sched.reason,
                        })
                    st.dataframe(sched_rows, use_container_width=True, hide_index=True)
                else:
                    st.info("No tasks were scheduled for this pet today.")

                if plan.skipped_tasks:
                    st.markdown("**⏭️ Skipped Tasks**")
                    skip_rows = []
                    for t in plan.skipped_tasks:
                        pval = t.priority.value
                        if t.frequency == "weekly" and t.last_completed_date:
                            days_ago = (date.today() - date.fromisoformat(t.last_completed_date)).days
                            why = f"Weekly — completed {days_ago}d ago (due in {7 - days_ago}d)"
                        elif t.frequency == "daily" and t.is_completed:
                            why = "Daily — already completed today"
                        else:
                            why = "Over time budget"
                        skip_rows.append({
                            "Task":        f"{_task_emoji(t.title, t.category)} {t.title}",
                            "Min":         t.duration_minutes,
                            "Priority":    f"{'🔴' if pval=='high' else '🟡' if pval=='medium' else '🟢'} {pval.upper()}",
                            "Why Skipped": why,
                        })
                    st.dataframe(skip_rows, use_container_width=True, hide_index=True)

else:
    st.markdown(
        """
        <div style="background:#1a2035;border:1px solid #2a4070;border-radius:10px;
                    padding:24px;text-align:center;color:#8899bb;">
          <div style="font-size:2em;margin-bottom:8px;">👤</div>
          <strong style="color:#e0e0ff;">Set an owner above to get started.</strong><br/>
          Enter your name and daily time budget, then click <em>Save Owner</em>.
        </div>
        """,
        unsafe_allow_html=True,
    )
