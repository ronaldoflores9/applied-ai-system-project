"""PawPal+ AI Assistant — Agentic Workflow via Google Gemini tool use.

This module wires the existing Scheduler into an agentic Gemini loop.
Gemini autonomously decides which scheduling tools to call (and in what
order) to answer the user's natural-language request before returning
a final text response.

Supported tools
---------------
generate_schedule       Build today's full schedule for all pets.
get_task_recommendation Find the best task for a spare window of time.
check_conflicts         Detect overlapping tasks in today's schedule.
get_pet_tasks           List tasks for one or all pets.
get_owner_summary       Return owner profile and high-level stats.
"""
from __future__ import annotations

import logging
import os
from datetime import date

from dotenv import load_dotenv
load_dotenv()

from google import genai
from google.genai import types

from pawpal_system import Owner, Scheduler, is_due_today

logger = logging.getLogger("pawpal.ai")

MODEL_NAME = "gemini-2.5-flash"
FALLBACK_MODELS = ("gemini-2.0-flash",)

# ---------------------------------------------------------------------------
# Tool declarations
# ---------------------------------------------------------------------------

TOOLS = [
    types.Tool(function_declarations=[
        types.FunctionDeclaration(
            name="generate_schedule",
            description=(
                "Generate an optimized daily schedule for all of the owner's pets. "
                "Returns each pet's scheduled and skipped tasks with start/end times "
                "and the reason each task was included or excluded."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "start_time": types.Schema(
                        type=types.Type.STRING,
                        description="Schedule start time in HH:MM format (default '08:00').",
                    ),
                    "date": types.Schema(
                        type=types.Type.STRING,
                        description="Target date in YYYY-MM-DD format (default today).",
                    ),
                },
            ),
        ),
        types.FunctionDeclaration(
            name="get_task_recommendation",
            description=(
                "Find the single most urgent task that fits inside a free time window. "
                "Useful when the owner has an unexpected gap and wants to know what to do next."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "free_minutes": types.Schema(
                        type=types.Type.INTEGER,
                        description="Number of free minutes available right now.",
                    ),
                    "current_time": types.Schema(
                        type=types.Type.STRING,
                        description="Current wall-clock time in HH:MM format.",
                    ),
                },
                required=["free_minutes", "current_time"],
            ),
        ),
        types.FunctionDeclaration(
            name="check_conflicts",
            description=(
                "Generate today's schedule and check for overlapping task windows. "
                "Returns the number of conflicts and human-readable descriptions."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={},
            ),
        ),
        types.FunctionDeclaration(
            name="get_pet_tasks",
            description=(
                "Retrieve the task list for a specific pet, or all pets when "
                "pet_name is 'all'. Shows title, duration, priority, frequency, "
                "and completion status."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "pet_name": types.Schema(
                        type=types.Type.STRING,
                        description="Pet name (case-sensitive) or 'all' for every pet.",
                    ),
                },
                required=["pet_name"],
            ),
        ),
        types.FunctionDeclaration(
            name="get_owner_summary",
            description=(
                "Return a summary of the owner's profile: name, daily time budget, "
                "number of pets, total tasks, and pending vs completed counts."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={},
            ),
        ),
    ])
]


# ---------------------------------------------------------------------------
# Assistant class
# ---------------------------------------------------------------------------

class PawPalAIAssistant:
    """Agentic Gemini assistant that interacts with the PawPal+ Scheduler."""

    def __init__(self, owner: Owner, scheduler: Scheduler) -> None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "GEMINI_API_KEY is not set. Add it to your .env file:\n"
                "  GEMINI_API_KEY='AIza...'"
            )
        self.client    = genai.Client(api_key=api_key)
        self.owner     = owner
        self.scheduler = scheduler
        self.model_name = MODEL_NAME
        logger.info("PawPalAIAssistant initialised for owner '%s'", owner.name)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process_message(
        self,
        user_message: str,
        chat_history: list[dict],
    ) -> tuple[str, list[dict]]:
        """Process *user_message* through the agentic Gemini tool-use loop."""
        logger.info("User message received (len=%d)", len(user_message))

        # Build contents list from prior history + new user turn
        contents: list[types.Content] = []
        for turn in chat_history:
            role = "user" if turn["role"] == "user" else "model"
            contents.append(types.Content(
                role=role,
                parts=[types.Part(text=turn["content"])],
            ))
        contents.append(types.Content(
            role="user",
            parts=[types.Part(text=user_message)],
        ))

        config = types.GenerateContentConfig(
            tools=TOOLS,
            system_instruction=self._build_system_prompt(),
        )

        # ── Agentic tool-use loop ─────────────────────────────────────
        final_text = ""

        try:
            response = self._generate_content(contents, config)
        except Exception as exc:
            logger.error("Gemini API error: %s", exc, exc_info=True)
            err = str(exc)
            if "429" in err or "RESOURCE_EXHAUSTED" in err:
                return (
                    "**Quota exceeded.** Your free-tier limit for this API key is used up. "
                    "Please generate a new key at [aistudio.google.com](https://aistudio.google.com) "
                    "and update `.env`.",
                    chat_history,
                )
            return (f"API error: `{exc}`", chat_history)

        for iteration in range(10):  # guardrail: max 10 tool-call rounds
            logger.info("Agentic loop iteration %d", iteration + 1)

            # Collect function calls from this response
            fn_calls = []
            if response.candidates:
                for part in response.candidates[0].content.parts:
                    fc = getattr(part, "function_call", None)
                    if fc and getattr(fc, "name", None):
                        fn_calls.append(fc)

            if not fn_calls:
                # No tool calls — this is the final answer
                try:
                    final_text = response.text
                except Exception:
                    final_text = " ".join(
                        p.text
                        for p in response.candidates[0].content.parts
                        if hasattr(p, "text") and p.text
                    )
                break

            # Execute tools and build response parts
            fn_response_parts: list[types.Part] = []
            for fc in fn_calls:
                tool_name = fc.name
                tool_args = dict(fc.args) if fc.args else {}
                logger.info("Tool call: %s(%s)", tool_name, tool_args)

                result = self._execute_tool(tool_name, tool_args)
                logger.info("Tool result for %s: %s", tool_name, str(result)[:200])

                fn_response_parts.append(types.Part(
                    function_response=types.FunctionResponse(
                        name=tool_name,
                        response={"result": result},
                    )
                ))

            # Append assistant's function-call turn and our results to contents
            contents.append(response.candidates[0].content)
            contents.append(types.Content(role="user", parts=fn_response_parts))

            try:
                response = self._generate_content(contents, config)
            except Exception as exc:
                logger.error("Gemini error sending tool results: %s", exc, exc_info=True)
                final_text = f"Error after tool call: `{exc}`"
                break
        else:
            logger.warning("Agentic loop hit iteration cap")
            final_text = "I ran into a processing loop. Please try a simpler question."

        if not final_text:
            final_text = "I wasn't able to produce a response. Please try again."

        updated_history = chat_history + [
            {"role": "user",      "content": user_message},
            {"role": "assistant", "content": final_text},
        ]
        return final_text, updated_history

    # ------------------------------------------------------------------
    # System prompt
    # ------------------------------------------------------------------

    def _build_system_prompt(self) -> str:
        today = date.today().isoformat()
        pets  = ", ".join(p.name for p in self.owner.pets) or "none yet"
        return (
            f"You are PawPal+, an intelligent pet care scheduling assistant.\n"
            f"You are helping {self.owner.name}, who has "
            f"{self.owner.time_available_minutes} minutes available today.\n"
            f"Their pets: {pets}.\n"
            f"Today's date: {today}.\n\n"
            "Use the available tools to answer scheduling questions accurately. "
            "Be proactive: when a user asks to generate a schedule, also check "
            "for conflicts automatically. When recommending a task, explain the "
            "urgency score and why that task ranks highest. Keep responses concise "
            "and friendly."
        )

    # ------------------------------------------------------------------
    # Tool dispatch
    # ------------------------------------------------------------------

    def _generate_content(
        self,
        contents: list[types.Content],
        config: types.GenerateContentConfig,
    ):
        """Call Gemini with automatic model fallback on quota exhaustion."""
        models = [self.model_name, *[m for m in FALLBACK_MODELS if m != self.model_name]]
        last_exc: Exception | None = None

        for model in models:
            try:
                response = self.client.models.generate_content(
                    model=model,
                    contents=contents,
                    config=config,
                )
                if model != self.model_name:
                    logger.warning(
                        "Primary model '%s' unavailable; falling back to '%s'",
                        self.model_name,
                        model,
                    )
                    self.model_name = model
                return response
            except Exception as exc:
                last_exc = exc
                if self._is_quota_error(exc):
                    logger.warning("Quota-limited on model '%s'; trying fallback", model)
                    continue
                raise

        # Every model candidate failed (typically quota exhausted for all).
        if last_exc is not None:
            raise last_exc
        raise RuntimeError("Gemini call failed before attempting any model")

    def _is_quota_error(self, exc: Exception) -> bool:
        msg = str(exc).lower()
        return "resource_exhausted" in msg or "quota" in msg or "429" in msg

    def _execute_tool(self, tool_name: str, tool_input: dict) -> dict:
        handlers = {
            "generate_schedule":       self._tool_generate_schedule,
            "get_task_recommendation": self._tool_get_recommendation,
            "check_conflicts":         self._tool_check_conflicts,
            "get_pet_tasks":           self._tool_get_pet_tasks,
            "get_owner_summary":       self._tool_get_owner_summary,
        }
        handler = handlers.get(tool_name)
        if handler is None:
            return {"error": f"Unknown tool '{tool_name}'"}
        try:
            return handler(tool_input)
        except Exception as exc:
            logger.error("Tool '%s' error: %s", tool_name, exc, exc_info=True)
            return {"error": str(exc)}

    # ------------------------------------------------------------------
    # Tool implementations
    # ------------------------------------------------------------------

    def _tool_generate_schedule(self, inp: dict) -> dict:
        start_time = inp.get("start_time", "08:00")
        today      = inp.get("date", date.today().isoformat())
        plans = self.scheduler.generate_plans_for_owner(
            self.owner, start_time=start_time, today=today
        )
        result: dict = {}
        for plan in plans:
            result[plan.pet.name] = {
                "total_minutes": plan.total_minutes,
                "summary":       plan.summary,
                "scheduled": [
                    {"task": st.task.title, "start": st.start_time,
                     "end": st.end_time, "reason": st.reason}
                    for st in plan.scheduled_tasks
                ],
                "skipped": [
                    {"task": t.title, "priority": t.priority.value}
                    for t in plan.skipped_tasks
                ],
            }
        return result

    def _tool_get_recommendation(self, inp: dict) -> dict:
        result = self.scheduler.recommend_next(
            self.owner,
            available_minutes=int(inp["free_minutes"]),
            current_time=inp["current_time"],
            today=inp.get("date", date.today().isoformat()),
        )
        if result is None:
            return {"found": False, "message": "No pending task fits the available window."}
        rec_pet, rec_task, rec_score = result
        return {
            "found": True, "pet": rec_pet.name, "task": rec_task.title,
            "duration": rec_task.duration_minutes, "priority": rec_task.priority.value,
            "frequency": rec_task.frequency, "required": rec_task.is_required,
            "score": round(rec_score, 2), "category": rec_task.category,
        }

    def _tool_check_conflicts(self, _inp: dict) -> dict:
        plans    = self.scheduler.generate_plans_for_owner(self.owner)
        warnings = self.scheduler.get_conflict_warnings(plans)
        return {"conflict_count": len(self.scheduler.detect_conflicts(plans)), "warnings": warnings}

    def _tool_get_pet_tasks(self, inp: dict) -> dict:
        pet_name = inp.get("pet_name", "all")
        today    = date.today().isoformat()
        targets  = self.owner.pets if pet_name.lower() == "all" else [
            p for p in self.owner.pets if p.name == pet_name
        ]
        if not targets:
            return {"error": f"No pet named '{pet_name}' found."}
        return {
            pet.name: [
                {"title": t.title, "duration": t.duration_minutes,
                 "priority": t.priority.value, "frequency": t.frequency,
                 "required": t.is_required, "completed": t.is_completed,
                 "due_today": is_due_today(t, today), "pinned_time": t.scheduled_time or None}
                for t in pet.tasks
            ]
            for pet in targets
        }

    def _tool_get_owner_summary(self, _inp: dict) -> dict:
        total     = sum(len(p.tasks) for p in self.owner.pets)
        pending   = sum(sum(1 for t in p.tasks if not t.is_completed) for p in self.owner.pets)
        return {
            "owner": self.owner.name,
            "time_budget_minutes": self.owner.time_available_minutes,
            "pet_count": len(self.owner.pets),
            "pets": [{"name": p.name, "species": p.species, "task_count": len(p.tasks)}
                     for p in self.owner.pets],
            "total_tasks": total, "pending_tasks": pending, "completed_tasks": total - pending,
        }
