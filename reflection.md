# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

The initial UML design for PawPal+ includes 6 classes organized around the core concept of generating a personalized daily care schedule for a pet.

| Class             | Responsibilities                                                                                                       |
| ----------------- | ---------------------------------------------------------------------------------------------------------------------- |
| **Owner**         | Stores the owner's name, available time (in minutes), and scheduling preferences                                       |
| **Pet**           | Represents the animal being cared for — holds its name, species, and a reference to its owner                          |
| **Task**          | Defines a single care activity with a title, duration, priority, category, and whether it's required                   |
| **ScheduledTask** | Wraps a `Task` with a concrete start/end time and a reason for its placement in the schedule                           |
| **DailyPlan**     | Aggregates the full schedule for a pet — holds the list of scheduled and skipped tasks, total time used, and a summary |
| **Scheduler**     | The logic class — takes a pet and a list of tasks and produces a `DailyPlan` via `generate_plan()`                     |

Key relationships:

- An `Owner` owns one `Pet`
- A `Task` becomes a `ScheduledTask` when placed in the plan
- A `DailyPlan` contains many `ScheduledTask`s and tracks skipped `Task`s
- The `Scheduler` uses the `Pet` (and its owner's constraints) to produce the `DailyPlan`

The design separates data (Owner, Pet, Task) from scheduling logic (Scheduler) and output structure (ScheduledTask, DailyPlan), following a clean single-responsibility pattern.

**b. Design changes**

Yes, the design evolved after reviewing AI feedback on the initial skeleton. The following changes were made:

1. **Converted classes to Python dataclasses** — `Owner`, `Pet`, `Task`, `ScheduledTask`, and `DailyPlan` were refactored from manual `__init__` methods to `@dataclass` decorators. This eliminated boilerplate and made the field definitions cleaner and easier to read. `field(default_factory=list)` was used for mutable defaults like `preferences`, `scheduled_tasks`, and `skipped_tasks`.

2. **Added a `Priority` enum** — The `priority` field on `Task` was originally a plain string (`"low"`, `"medium"`, `"high"`) with no validation. AI feedback flagged this as a potential source of silent bugs when sorting. A `Priority(str, Enum)` class was added to enforce valid values at the type level.

3. **Split `Scheduler.generate_plan()` into private helper stubs** — AI feedback identified that putting all scheduling logic into one method would become a bottleneck and be hard to test. The method was decomposed into `_sort_tasks()` and `_allocate()` stubs to keep responsibilities separated and make future testing easier.

4. **Added `Task.species` field** — The original `Task` had no way to indicate which pet species it applied to. AI feedback flagged that the scheduler had no basis to filter tasks by pet type. A `species: list[str]` field was added; an empty list means the task applies to all species, and `_filter_by_species()` in the `Scheduler` handles the filtering.

5. **Added `DailyPlan.owner` property** — The original design required chaining `plan.pet.owner` to access owner constraints. A `@property` was added to `DailyPlan` to expose the owner directly, making the relationship explicit and access cleaner.

6. **Added time parsing helpers to `Scheduler`** — `start_time` was a plain string with no parsing logic anywhere. AI feedback flagged this as a likely source of bugs. Two private methods, `_parse_time()` and `_format_time()`, were added to centralize all `"HH:MM"` arithmetic in one place.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

**Tradeoff: Keep explicit pairwise overlap checks (readability) instead of a denser "more Pythonic" one-liner**

I reviewed `detect_conflicts()` with Copilot and asked how it could be simplified for readability or performance. One suggestion was to compress the nested loops into a compact expression (for example, using `itertools.combinations` plus inline overlap checks in one statement). That version is shorter and arguably more Pythonic, but it is harder for a beginner to step through and debug.

I decided to keep the current explicit loop version because this project prioritizes clarity over micro-optimizations. The current implementation makes each step obvious: flatten scheduled tasks, compare each unique pair once, parse intervals, then apply overlap logic.

The performance tradeoff is that conflict detection is still $O(n^2)$ in the number of scheduled items. For this assignment-sized scheduler, that cost is acceptable. If this system grew to many pets and many tasks, a sweep-line or sorted-interval approach could reduce comparisons while keeping warnings non-blocking.

---

## 3. AI Collaboration

**a. How you used AI**

I used artificial intelligence for various aspects of the project. Initially, I used it to brainstorm the UML design and determine the correct approach for its development. Additionally, I used it for debugging, refactoring, and implementing code, specifically when I had an idea of what the algorithm was supposed to do but wasn’t sure how to implement it. The prompts I found most useful were those that asked about the function of a particular concept or part of the code.

**b. Judgment and verification**

One instance where I rejected the AI’s suggestions was during algorithm development and proposal: when I selected one and asked the AI to implement it, the algorithm didn’t meet the requirements I was looking for. I evaluated and verified these by comparing what I wanted to achieve with my code against what the AI was actually doing. Finally, what I did was suggest another algorithm and began comparing and testing it to see if it worked correctly.

---

## 4. Testing and Verification

**a. What you tested**

I tested the behaviors that most directly affect schedule quality and user trust:

1. **Task lifecycle basics**: adding tasks to pets, marking tasks complete, and verifying status transitions.
2. **Recurrence logic**: ensuring `daily` and `weekly` tasks create the next pending instance when completed, while `as_needed` tasks do not auto-recur.
3. **Sorting correctness**: confirming tasks are ordered chronologically by pinned `HH:MM` time and that flexible tasks appear after pinned tasks.
4. **Conflict detection**: validating overlap detection for same-pet and cross-pet schedules, while ensuring adjacent intervals are not falsely flagged.
5. **Time-budget allocation**: checking zero-budget behavior, exact-fit schedules, and skipped-task behavior when time is exceeded.
6. **Filtering behavior**: verifying task filtering by pet, status, and priority, including all-filters-off cases.
7. **Error handling and edge cases**: invalid pet-task mappings, time boundaries (for example `00:00` and `23:59`), and larger mixed task sets.

These tests were important because they allowed us to verify how the system performed under normal conditions and in edge cases. This also reduces the risk of regression during refactoring, ensures that conflict warnings are reliable, and confirms that the application behaves predictably when inputs are imperfect.

**b. Confidence**

I am highly confident that my scheduler works correctly for the core behaviors in this project. The full test suite passes and covers recurrence, sorting, conflict detection, filtering, and budget allocation across normal and edge-case scenarios. I also verified that invalid task-to-pet operations fail safely, which improves reliability when data is inconsistent. If I had more time, I would add stress tests with many pets and hundreds of tasks to measure performance and ensure the UI remains responsive. I would also add stricter input-validation tests for malformed times and invalid dates submitted through the Streamlit interface. Finally, I would test long-term recurrence behavior over simulated weeks to confirm that due-date logic remains accurate over time.

---

## 5. Reflection

**a. What went well**

The part of the project I’m most satisfied with is learning how to use UML. Not just because I learned how to use it on this project, but because I see it as a tool I can use for my future projects. In my opinion, using this tool, specifically Mermaid.js, makes developing class diagrams and flowcharts much more interesting, technical, and enjoyable.

**b. What you would improve**

If I’d had more time, I would have redesigned the scheduling system so that it could generate schedules for multiple pets at once, rather than creating a schedule for each one individually. This would make the scheduling system much more comprehensive and user-friendly. As for the UI, I would have improved it and tweaked it a bit to better match the theme.

**c. Key takeaway**

An important lesson I learned about designing systems and working with AI on this project is that effective implementation requires a solid system design. This AI-supported design makes everything more efficient by establishing a clear structure and meeting the specific goals we set out to achieve. Using UML first before jumping straight into implementation helped me break the problem down into parts and gradually solve them while identifying clear and concise characteristics, rather than making assumptions and then having to make too many adjustments along the way. This process improved both the quality of my application and my confidence in the final system.
