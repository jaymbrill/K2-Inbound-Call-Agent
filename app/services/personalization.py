from app.models.caller import CallerProfile
from app.models.questions import QuestionSet


_BASE_SYSTEM_PROMPT = """You are K2, a warm and engaging personal voice assistant. \
You are having a real phone conversation — keep responses concise and natural. \
This is voice, not text: avoid lists, bullet points, or long paragraphs. \
Listen actively and refer back to what the caller shares before moving on."""

_OFFSITE_CONTEXT = (
    "we have a K2 offsite next week where we're doing a live vibe-coding demonstration — "
    "showing how you can build a real app using AI in a short amount of time. "
    "We want the demo to actually solve a problem that matters, so we're reaching out "
    "to a few people to source ideas."
)


def build_first_message(caller: CallerProfile) -> str:
    if not caller.is_known:
        return (
            "Hey there! Thanks for calling. I don't think we've spoken before — "
            "who am I speaking with today?"
        )

    name = caller.display_name()
    return (
        f"Hey {name}! Great to connect. So the reason I'm reaching out — {_OFFSITE_CONTEXT} "
        f"I'd love to pick your brain for a few minutes if you have time. "
        f"Ready to jump in?"
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
                f"\nPERSONALIZED ANGLE FOR THIS CALLER:\n{caller.vibe_prompt}\n"
                "After your opening context about the offsite demo, use this angle to make "
                "a natural, personalized bridge into the first question — reference why you "
                "thought of them specifically. Don't read this verbatim; weave it in naturally."
            )

    parts.append(
        "\nCONFIRMATION HANDLING:\n"
        "Your opening message ended with 'Ready to jump in?' — the caller's first response "
        "will likely be a simple yes or affirmation (yes, sure, go ahead, yep, absolutely, etc.). "
        "If it sounds anything like agreement, do NOT acknowledge it or say 'great!' — "
        "just flow directly into the personalized bridge and first question. "
        "If they seem hesitant or say no, be warm and offer to call back at a better time."
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
