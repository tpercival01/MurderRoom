from __future__ import annotations

import json
import logging
import re
from textwrap import dedent
from typing import Type, TypeVar

from pydantic import BaseModel, ValidationError

from app.assembly import assemble_mystery
from app.config import get_settings
from app.models import (
    CoreTruthDraft,
    Difficulty,
    EvidenceBoardDraft,
    MysteryDraft,
    NarrativeSeedAI,
    SuspectCastDraft,
    SuspectKey,
)
from app.planner import (
    CasePlan,
    PlanError,
    build_case_plan,
    compile_case,
    narrative_seed_issues,
)
from app.validation import (
    validate_core_truth,
    validate_evidence_board,
    validate_suspect_cast,
)

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class MysteryGenerationError(RuntimeError):
    """Raised when a valid mystery cannot be produced."""

    def __init__(
        self,
        message: str,
        *,
        retryable: bool = True,
        status_code: int | None = None,
        retry_after_seconds: int | None = None,
    ) -> None:
        super().__init__(message)
        self.retryable = retryable
        self.status_code = status_code
        self.retry_after_seconds = retry_after_seconds


def _parse_json_object(raw_content: str, model_class: Type[T]) -> T:
    cleaned = raw_content.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as error:
        start = cleaned.find("{")
        if start < 0:
            raise ValueError("Provider response contained no JSON object.") from error
        try:
            payload, _ = json.JSONDecoder().raw_decode(cleaned[start:])
        except json.JSONDecodeError as inner:
            raise ValueError("Provider returned malformed or truncated JSON.") from inner

    if not isinstance(payload, dict):
        raise ValueError("Provider JSON must be an object.")
    return model_class.model_validate(payload)


def _strict_schema_model(model_name: str) -> bool:
    return model_name in {
        "openai/gpt-oss-20b",
        "openai/gpt-oss-120b",
    }


def _best_effort_schema_model(model_name: str) -> bool:
    return model_name in {
        "meta-llama/llama-4-scout-17b-16e-instruct",
        "openai/gpt-oss-safeguard-20b",
    }



def _retry_after_seconds(error: Exception) -> int | None:
    """Read Retry-After from OpenAI-compatible provider errors."""
    header_sources = [
        getattr(error, "headers", None),
        getattr(getattr(error, "response", None), "headers", None),
    ]
    for headers in header_sources:
        if not headers:
            continue
        raw = headers.get("retry-after") or headers.get("Retry-After")
        if raw is None:
            continue
        try:
            return max(1, int(float(str(raw))))
        except (TypeError, ValueError):
            continue
    return None

def call_structured_model(
    prompt: str,
    model_class: Type[T],
    *,
    max_tokens: int,
) -> T:
    """Call Groq once and validate the response against the same Pydantic model.

    The OpenAI import and settings construction are lazy. Pure planner tests can
    therefore run without an API key or the OpenAI package installed.
    """

    try:
        from openai import OpenAI
    except ImportError as error:
        raise MysteryGenerationError(
            "The backend requires the 'openai' package for Groq's "
            "OpenAI-compatible endpoint.",
            retryable=False,
        ) from error

    settings = get_settings()
    client = OpenAI(
        api_key=settings.groq_api_key,
        base_url=settings.groq_base_url,
        timeout=settings.request_timeout_seconds,
    )
    schema = model_class.model_json_schema()

    messages = [
        {"role": "system", "content": prompt},
        {
            "role": "user",
            "content": (
                "Return exactly one complete JSON object matching the supplied "
                "schema. Do not include Markdown, comments, or extra prose."
            ),
        },
    ]
    options: dict = {
        "model": settings.groq_model,
        "messages": messages,
        "temperature": settings.generation_temperature,
        "max_completion_tokens": max_tokens,
    }

    if _strict_schema_model(settings.groq_model):
        options["reasoning_effort"] = settings.generation_reasoning_effort
        options["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": model_class.__name__,
                "strict": True,
                "schema": schema,
            },
        }
    elif _best_effort_schema_model(settings.groq_model):
        options["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": model_class.__name__,
                "strict": False,
                "schema": schema,
            },
        }
    else:
        options["response_format"] = {"type": "json_object"}
        messages[1]["content"] += (
            "\nThe required JSON Schema is:\n"
            + json.dumps(schema, separators=(",", ":"))
        )

    try:
        completion = client.chat.completions.create(**options)
        content = completion.choices[0].message.content
        if not content:
            raise ValueError("Groq returned an empty completion.")
        return _parse_json_object(content, model_class)
    except Exception as error:
        status_code = getattr(error, "status_code", None)
        if status_code is not None:
            retry_after = _retry_after_seconds(error)
            retryable = (
                status_code in {408, 409}
                or status_code >= 500
                or (
                    status_code == 400
                    and _best_effort_schema_model(settings.groq_model)
                )
            )
            # A 429 must escape immediately. Retrying the same whole case
            # consumes each small amount of quota as it becomes available.
            if status_code == 429:
                retryable = False

            raise MysteryGenerationError(
                f"Groq request failed with HTTP {status_code}: {error}",
                retryable=retryable,
                status_code=status_code,
                retry_after_seconds=retry_after,
            ) from error
        raise MysteryGenerationError(
            f"Groq request failed before a response was received: {error}",
            retryable=True,
        ) from error


def _narrative_prompt(
    plan: CasePlan,
    feedback: list[str] | None,
) -> str:
    objects = "\n".join(
        f"{index}: {name}"
        for index, name in enumerate(plan.room_objects)
    )
    killer_key = plan.killer_key.value
    feedback_text = ""
    if feedback:
        feedback_text = (
            "\nPREVIOUS NARRATIVE VALIDATION FAILURES:\n- "
            + "\n- ".join(feedback[:12])
            + "\nCorrect every failure in the replacement object."
        )

    return dedent(
        f"""
        You are the narrative casting layer for a British room-based murder
        mystery game. Python has already constructed and proved the complete
        evidence logic. You must provide only original narrative metadata.

        CASE NONCE: {plan.seed}
        DIFFICULTY: {plan.difficulty.value}
        PHOTOGRAPHED ROOM OBJECTS:
        {objects}

        LOCKED MURDERER KEY: {killer_key}

        Generate:
        - one evocative title that is specific to this case;
        - one concise setting description for the photographed room;
        - a named adult victim and a plausible social or professional role;
        - exactly three named adult suspects, using suspect_1, suspect_2 and
          suspect_3 once each;
        - each suspect's relationship to the victim;
        - one motive_detail clause explaining the pressure that drove the locked
          murderer to kill. The clause will be inserted after the word "because".

        Do not generate clues, evidence, alibis, statements, methods, times,
        deductions, IDs, police records, CCTV, witnesses, fingerprints, DNA, or
        additional rooms. Python owns all of those facts.

        Quality rules:
        1. Use British English.
        2. Use natural, distinctive names. Avoid John Smith, Jane Doe, Emily
           Wilson, James Davis, Sarah Taylor and Richard Langley.
        3. Do not expose the strings suspect_1, suspect_2 or suspect_3 anywhere
           except the required key fields.
        4. Do not call the case "Mansion Murder", "Murder Mystery", "The Murder"
           or any similarly generic title.
        5. Each relationship_to_victim must be a short role phrase such as
           "estranged daughter" or "business partner", without a leading pronoun.
        6. The setting must describe one room only and must be compatible with all
           four supplied objects. Write it as a lower-case noun phrase beginning
           with "a", "an" or "the".
        7. The motive_detail must name a concrete secret, loss, betrayal or threat
           and must grammatically follow the word "because". Do not begin it with
           "because" and do not end it with a full stop.
        8. Do not mention which suspect is the killer in prose. The locked key is
           for internal consistency only.
        {feedback_text}
        """
    ).strip()


def _validate_compiled(
    core: CoreTruthDraft,
    cast: SuspectCastDraft,
    evidence: EvidenceBoardDraft,
    room_objects: list[str],
) -> list[str]:
    issues: list[str] = []
    issues.extend(validate_core_truth(core, room_objects))
    issues.extend(validate_suspect_cast(cast, core, room_objects))
    issues.extend(validate_evidence_board(evidence, core, cast, room_objects))
    return issues


def _generate_all(
    room_objects: list[str],
    difficulty: Difficulty,
    seed: int | None = None,
) -> tuple[CoreTruthDraft, SuspectCastDraft, EvidenceBoardDraft]:
    plan = build_case_plan(room_objects, difficulty, seed)
    settings = get_settings()
    feedback: list[str] | None = None
    last_issues: list[str] = []

    for attempt in range(1, settings.generation_max_retries + 1):
        try:
            narrative = call_structured_model(
                _narrative_prompt(plan, feedback),
                NarrativeSeedAI,
                max_tokens=settings.narrative_max_tokens,
            )
        except (MysteryGenerationError, ValidationError, ValueError) as error:
            if isinstance(error, MysteryGenerationError) and not error.retryable:
                raise
            feedback = [f"Narrative response failed validation: {error}"]
            last_issues = feedback
            logger.warning("Narrative attempt %s failed: %s", attempt, error)
            continue

        seed_issues = narrative_seed_issues(narrative)
        if seed_issues:
            feedback = seed_issues
            last_issues = seed_issues
            continue

        try:
            compiled = compile_case(narrative, plan)
        except (PlanError, ValidationError, ValueError) as error:
            feedback = [f"Deterministic compilation failed: {error}"]
            last_issues = feedback
            continue

        issues = _validate_compiled(*compiled, room_objects)
        if not issues:
            return compiled

        # A compiled failure indicates a programmer invariant, not a creative
        # failure. Retrying Groq cannot repair deterministic templates.
        raise MysteryGenerationError(
            "The proof compiler produced an invalid case: " + "; ".join(issues[:20])
        )

    raise MysteryGenerationError(
        "Unable to obtain valid narrative metadata from Groq. "
        + "; ".join(last_issues[:12])
    )


def generate_core_truth(
    room_objects: list[str],
    difficulty: Difficulty = Difficulty.standard,
    seed: int | None = None,
) -> CoreTruthDraft:
    return _generate_all(room_objects, difficulty, seed)[0]


def generate_suspect_cast(
    core_truth: CoreTruthDraft,
    room_objects: list[str],
    difficulty: Difficulty = Difficulty.standard,
    seed: int | None = None,
) -> SuspectCastDraft:
    # Retained for endpoint compatibility. Production generation is atomic.
    return _generate_all(room_objects, difficulty, seed)[1]


def generate_evidence_board(
    core_truth: CoreTruthDraft,
    suspect_cast: SuspectCastDraft,
    room_objects: list[str],
    difficulty: Difficulty = Difficulty.standard,
    seed: int | None = None,
) -> EvidenceBoardDraft:
    # Retained for endpoint compatibility. Production generation is atomic.
    return _generate_all(room_objects, difficulty, seed)[2]


def generate_mystery_draft(
    room_objects: list[str],
    difficulty: Difficulty = Difficulty.standard,
    seed: int | None = None,
) -> MysteryDraft:
    core, cast, evidence = _generate_all(room_objects, difficulty, seed)
    return assemble_mystery(core, cast, evidence)
