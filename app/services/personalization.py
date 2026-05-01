from app.models.caller import CallerProfile
from app.models.questions import QuestionSet


_BASE_SYSTEM_PROMPT = """You are K2, a warm and engaging personal voice assistant. \
You are having a real phone conversation — keep responses concise and natural. \
This is voice, not text: avoid lists, bullet points, or long paragraphs. \
Listen actively and refer back to what the caller shares before moving on."""

def build_first_message(caller: CallerProfile) -> str:
    if not caller.is_known:
        return (
            "Hey there! Thanks for calling. I don't think we've spoken before — "
            "who am I speaking with today?"
        )

    name = caller.display_name()

    if caller.call_count == 0:
        return (
            f"Hey {name}! So great to hear from you — first time calling! "
            f"So, what are you building?"
        )

    ordinal = _ordinal(caller.call_count + 1)
    return (
        f"Hey {name}! Good to hear from you again — this is your {ordinal} call! "
        f"What's the project?"
    )


def build_system_prompt(caller: CallerProfile, question_set: QuestionSet) -> str:
    parts = [_BASE_SYSTEM_PROMPT]

    if caller.is_known:
        parts.append(f"\nCALLER CONTEXT:\n- Name: {caller.name}")
        if caller.nickname:
            parts.append(f"- Goes by: {caller.nickname}")
        if caller.notes:
            parts.append(f"- Background: {caller.notes}")
        parts.append(f"- Previous calls: {caller.call_count}")
        if caller.vibe_prompt:
            parts.append(
                f"\nVIBE CODING FOCUS:\n{caller.vibe_prompt}\n"
                "Use this as the lens for your opening question — don't recite it, "
                "but let it shape how you ask about what they're building and why."
            )

    if question_set.intro_prompt:
        parts.append(f"\n{question_set.intro_prompt}")

    if question_set.questions:
        parts.append(
            "\nCONVERSATION QUESTIONS — work through these naturally, not robotically. "
            "Respond to what the caller says before moving to the next question:\n"
            + question_set.formatted_list()
            + "\n\nWrap up warmly when the conversation feels complete."
        )

    return "\n".join(parts)


def build_dynamic_variables(caller: CallerProfile) -> dict[str, str]:
    return {
        "caller_name": caller.display_name(),
        "call_count": str(caller.call_count),
        "is_known": "true" if caller.is_known else "false",
    }


def _ordinal(n: int) -> str:
    suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10 if n % 100 not in (11, 12, 13) else 0, "th")
    return f"{n}{suffix}"
