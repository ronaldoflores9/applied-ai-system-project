# PawPal+ — Reflection

## What this project taught me about AI and problem-solving

**Design before implementation is not optional.** The most consequential decision in this project was spending time on UML and system design before writing a single line of scheduling logic. When I started implementing, the class boundaries were clear, the data flow was mapped, and I never had to stop and ask "where does this logic live?" That clarity paid dividends when integrating the AI agent — I could wire Gemini's tool calls directly to well-defined Python methods rather than spaghetti functions.

**AI is most useful as a thinking partner, not a code generator.** The most valuable AI interactions in this project were the ones where I asked it to *evaluate trade-offs* or *propose alternatives* before committing to an approach. When I asked for the urgency scoring algorithm, I got three candidates with complexity and integration analysis — not just one answer. That forced me to make a real decision with understood trade-offs instead of accepting the first suggestion.

**You have to verify AI output against your own mental model.** At one point, an AI-suggested implementation of the urgency formula produced scores where a fresh HIGH-priority task outranked an overdue LOW-priority task — the opposite of what I wanted. I caught this by tracing through a concrete numerical example before accepting the code. Without that verification step, a subtle scoring inversion would have shipped silently.

**Guardrails are part of the feature, not an afterthought.** Adding explicit input validation (`validate_task_title`, `validate_time_hint`, etc.) and capping the agentic loop at 10 iterations felt like minor housekeeping at first. In practice, these guardrails prevented UI crashes, made error messages actionable, and gave me confidence that the AI assistant wouldn't spiral on a malformed input. Building observability (structured log files) alongside the features rather than at the end made debugging significantly faster.

The core lesson: **good AI-assisted engineering looks the same as good engineering** — clear requirements, honest trade-off analysis, testable components, and verified outputs. AI compresses the time between idea and working code, but it cannot substitute for the judgment that decides which idea is worth building in the first place.
