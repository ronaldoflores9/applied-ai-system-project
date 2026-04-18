
"""Centralized logging and guardrails for PawPal+."""
from __future__ import annotations

import logging
import os
from datetime import date


# ---------------------------------------------------------------------------
# Guardrail constants
# ---------------------------------------------------------------------------

MAX_TASK_DURATION_MINUTES = 480   # 8 hours — no single task should exceed this
MAX_TASK_TITLE_LENGTH     = 120   # prevents unreasonably long task names
MAX_CHAT_MESSAGE_LENGTH   = 2000  # caps user input to the AI assistant
MAX_PETS_PER_OWNER        = 20    # sanity cap on pets
MAX_TASKS_PER_PET         = 100   # sanity cap on tasks


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure the PawPal+ application logger.

    Creates a ``logs/`` directory and writes a dated log file.
    Only WARNING+ messages are echoed to the console to keep the
    Streamlit terminal clean; INFO records go to the file only.

    Returns the ``pawpal`` root logger.
    """
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"pawpal_{date.today().isoformat()}.log")

    logger = logging.getLogger("pawpal")

    # Guard against duplicate handlers on Streamlit reruns
    if logger.handlers:
        return logger

    logger.setLevel(level)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File handler — full INFO stream
    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.INFO)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    # Console handler — warnings and above only
    ch = logging.StreamHandler()
    ch.setLevel(logging.WARNING)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    logger.info("PawPal+ logging initialized — log file: %s", log_file)
    return logger


# ---------------------------------------------------------------------------
# Input guardrails
# ---------------------------------------------------------------------------

class GuardrailError(ValueError):
    """Raised when user input violates a guardrail."""


def validate_task_title(title: str) -> str:
    """Return *title* stripped, or raise GuardrailError."""
    title = title.strip()
    if not title:
        raise GuardrailError("Task title cannot be empty.")
    if len(title) > MAX_TASK_TITLE_LENGTH:
        raise GuardrailError(
            f"Task title is too long ({len(title)} chars). "
            f"Keep it under {MAX_TASK_TITLE_LENGTH} characters."
        )
    return title


def validate_task_duration(minutes: int) -> int:
    """Return *minutes* or raise GuardrailError."""
    if minutes < 1:
        raise GuardrailError("Task duration must be at least 1 minute.")
    if minutes > MAX_TASK_DURATION_MINUTES:
        raise GuardrailError(
            f"Task duration {minutes} min exceeds the maximum allowed "
            f"({MAX_TASK_DURATION_MINUTES} min / 8 hours)."
        )
    return minutes


def validate_time_hint(time_str: str) -> str:
    """Validate and return an 'HH:MM' string, or raise GuardrailError."""
    time_str = time_str.strip()
    if not time_str:
        return time_str  # empty is fine — means flexible
    parts = time_str.split(":")
    if len(parts) != 2:
        raise GuardrailError(f"Time '{time_str}' must be in HH:MM format.")
    try:
        h, m = int(parts[0]), int(parts[1])
    except ValueError:
        raise GuardrailError(f"Time '{time_str}' contains non-numeric characters.")
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise GuardrailError(f"Time '{time_str}' is out of range (00:00–23:59).")
    return f"{h:02d}:{m:02d}"


def validate_chat_message(message: str) -> str:
    """Return *message* stripped, or raise GuardrailError."""
    message = message.strip()
    if not message:
        raise GuardrailError("Message cannot be empty.")
    if len(message) > MAX_CHAT_MESSAGE_LENGTH:
        raise GuardrailError(
            f"Message is too long ({len(message)} chars). "
            f"Please keep it under {MAX_CHAT_MESSAGE_LENGTH} characters."
        )
    return message
