# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## Features

PawPal+ includes a scheduling engine with practical planning algorithms designed for real pet-care routines:

- **Chronological sorting by time** (`sort_by_time`): tasks with pinned times (`HH:MM`) are ordered earliest-first using lexicographic string comparison; flexible tasks receive the sentinel key `"99:99"` and sort to the end — O(n log n).
- **Multi-factor task ranking** (`_sort_tasks`): the plan builder ranks tasks by a three-key tuple — pinned time → `is_required` flag → priority level (`high` / `medium` / `low`) — so critical, time-anchored work is always scheduled first.
- **Greedy time-budgeted allocation** (`_allocate`): tasks are placed into the day in ranked order, advancing a running clock; each task is scheduled only if its duration fits within the owner's remaining minute budget; overflow tasks are recorded as skipped — O(n) single pass.
- **Daily / weekly / as-needed recurrence** (`is_due_today`): date arithmetic determines whether each task is due today; `daily` tasks are always eligible, `weekly` tasks re-appear after >6 elapsed days, and `as_needed` tasks are eligible until completed.
- **Auto-creation of next recurring instance** (`mark_task_complete`): completing a `daily` or `weekly` task automatically appends a fresh pending copy to the pet's task list, preserving all original properties and the `last_completed_date` needed for the 7-day boundary check.
- **Species-aware task filtering** (`_filter_by_species`): tasks carry an optional species list; an empty list means "all species," so each pet only receives tasks that match its species — ensures cats don't get dog-specific tasks.
- **Pre-schedule conflict detection** (`check_time_hint_conflicts`): before plan generation, pinned-time tasks are compared pairwise as time intervals; overlapping pairs are reported as `SAME-PET` or `CROSS-PET` warnings so intent conflicts are caught early.
- **Post-schedule overlap detection** (`detect_conflicts` / `get_conflict_warnings`): after allocation, all scheduled windows are cross-checked with an O(n²) interval-overlap algorithm (`a_start < b_end and b_start < a_end`) and surfaced as human-readable warnings.
- **Multi-criteria dashboard filtering** (`filter_tasks`): users can simultaneously filter by pet name, completion status, and priority in a single O(n) pass; all three dimensions are optional AND-combined.
- **Multi-pet planning** (`generate_plans_for_owner`): generates an independent daily plan for every pet an owner has, each respecting the full time budget, then aggregates conflict detection across all plans.
- **Explainable plan output**: every `ScheduledTask` records a human-readable `reason` string — e.g., `"pinned to 08:00"` vs. `"scheduled within available time"` — plus per-pet summaries of scheduled and skipped tasks.

## Testing PawPal+

### Run the test suite

```bash
python -m pytest tests/test_pawpal.py -v
```

### 📸 Demo

<a href="/course_images/ai110/image.png" target="_blank"><img src='/course_images/ai110/image.png' title='PawPal App' width='' alt='PawPal App' class='center-block' /></a>

<a href="/course_images/ai110/image-1.png" target="_blank"><img src='/course_images/ai110/image-1.png' title='PawPal App' width='' alt='PawPal App' class='center-block' /></a>

<a href="/course_images/ai110/image-2.png" target="_blank"><img src='/course_images/ai110/image-2.png' title='PawPal App' width='' alt='PawPal App' class='center-block' /></a>

<a href="/course_images/ai110/image-3.png" target="_blank"><img src='/course_images/ai110/image-3.png' title='PawPal App' width='' alt='PawPal App' class='center-block' /></a>

<a href="/course_images/ai110/image-4.png" target="_blank"><img src='/course_images/ai110/image-4.png' title='PawPal App' width='' alt='PawPal App' class='center-block' /></a>

<a href="/course_images/ai110/image-5.png" target="_blank"><img src='/course_images/ai110/image-5.png' title='PawPal App' width='' alt='PawPal App' class='center-block' /></a>

### Test Coverage

The test suite includes **25 comprehensive tests** covering critical functionality and edge cases:

1. **Sorting Correctness** (2 tests)
   - Verifies tasks are ordered chronologically by scheduled time
   - Confirms unscheduled tasks sort to the end

2. **Recurrence Logic** (3 tests)
   - Daily tasks auto-create the next pending instance on completion
   - Weekly tasks preserve all properties when recurring
   - As-needed tasks don't auto-recur (one-time completion)

3. **Conflict Detection** (3 tests)
   - Same-pet overlapping times are flagged
   - Cross-pet scheduling conflicts are detected
   - Adjacent time windows (no gap) don't trigger false positives

4. **Core Functionality** (6 tests)
   - Task lifecycle (marking complete, status changes)
   - Owner and pet management
   - Pre-schedule conflict warnings
   - Time-hint overlap validation

5. **Edge Cases & Robustness** (11 tests)
   - Zero time budget (graceful handling of no available time)
   - Exact time budget fit (tasks fitting perfectly within limits)
   - Weekly recurrence boundaries (6-day vs 7-day completion thresholds)
   - Large task count sorting (20+ tasks with mixed properties)
   - Time parsing edge cases (midnight 00:00, end-of-day 23:59)
   - Invalid pet-task mappings (error handling)
   - Multi-criteria filtering with all-None parameters
   - Multi-pet time allocation and budget overflow detection
   - Multi-species task filtering

### Confidence Level

**★★★★★ (5/5 stars)**

The system demonstrates exceptional reliability across all dimensions:

✅ **All 25 tests passing** (100% pass rate)
✅ **Core algorithm validated** – Greedy allocation, sorting, recurrence all proven
✅ **Edge cases thoroughly tested** – Zero budget, time boundaries, large datasets
✅ **Error handling verified** – Invalid inputs caught with appropriate errors
✅ **Multi-pet & multi-task complexity** – Cross-pet conflicts, species filtering, time parsing all robust

**The system is production-ready for typical pet care scheduling scenarios.**
