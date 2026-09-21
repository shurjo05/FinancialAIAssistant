"""Conversation-memory helpers.

The full thread is persisted, but only a bounded recent window is ever sent to
the LLM — enough for Jo to follow "that one" / "what about February", without
letting a long thread bloat the context (cost) or drift the model. Numbers are
never replayed from history; Jo re-calls the data tools each turn, so grounding
is untouched by memory.
"""

# Recent turns sent to the model (≈6 exchanges). The UI nudges "start a new chat"
# for a fresh topic, which is the real context reset.
MAX_CONTEXT_MESSAGES = 12
# Per-message hard cap when building context, so one giant pasted turn can't blow
# the budget.
MAX_MESSAGE_CHARS = 2000
# Longest question we accept (mirrored as a schema constraint on the endpoints).
MAX_QUESTION_CHARS = 500


def build_context(messages: list[dict]) -> list[dict]:
    """Trim persisted history to the bounded window sent to the model.

    `messages` is oldest→newest, each `{"role": "user"|"assistant", "content": str}`,
    and must EXCLUDE the new question being asked.
    """
    recent = messages[-MAX_CONTEXT_MESSAGES:]
    return [
        {"role": m["role"], "content": (m["content"] or "")[:MAX_MESSAGE_CHARS]}
        for m in recent
    ]
