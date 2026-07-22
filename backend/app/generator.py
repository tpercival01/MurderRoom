from __future__ import annotations

import json
import random
import logging
import re
from textwrap import dedent
from typing import Optional, Type

from openai import OpenAI

from app.assembly import assemble_mystery
from app.config import get_settings
from app.models import (
    CoreTruthAIResponse,
    CoreTruthDraft,
    Difficulty,
    EvidenceBoardDraft,
    EvidenceBoardReview,
    MysteryDraft,
    SuspectCastDraft,
)
from app.reviewer import build_evidence_review_prompt
from app.validation import (
    validate_core_truth,
    validate_evidence_board,
    validate_suspect_cast,
)


logger = logging.getLogger(__name__)
settings = get_settings()

client = OpenAI(
    api_key=settings.groq_api_key,
    base_url=settings.groq_base_url,
)


class MysteryGenerationError(RuntimeError):
    """Raised when a valid mystery phase cannot be produced."""


def _is_retryable(error: Exception) -> bool:
    status_code = getattr(error, "status_code", None)

    if status_code is None:
        return True

    return status_code == 429 or status_code >= 500


def _parse_json_object(
    raw_content: str,
    model_class: Type,
):
    """Extract and validate one model object from provider text."""
    cleaned = raw_content.strip()

    if cleaned.startswith("```"):
        lines = cleaned.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        cleaned = "\n".join(lines).strip()

    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError:
        # Defensive fallback for a provider adding prose around an
        # otherwise valid JSON object.
        object_start = cleaned.find("{")

        if object_start == -1:
            raise ValueError(
                "Provider response contains no JSON object. "
                f"Response excerpt: {cleaned[:500]!r}"
            )

        try:
            payload, _ = json.JSONDecoder().raw_decode(
                cleaned[object_start:]
            )
        except json.JSONDecodeError as error:
            raise ValueError(
                "Provider returned malformed or truncated JSON. "
                f"Response excerpt: {cleaned[:500]!r}"
            ) from error

    if not isinstance(payload, dict):
        raise ValueError(
            "Provider JSON must be an object, not "
            f"{type(payload).__name__}."
        )

    # Some non-schema models wrap the result in {"result": {...}}.
    if len(payload) == 1:
        only_key, only_value = next(iter(payload.items()))

        if (
            isinstance(only_value, dict)
            and only_key.casefold()
            in {
                "result",
                "data",
                model_class.__name__.casefold(),
            }
        ):
            payload = only_value

    allowed_fields = set(model_class.model_fields)
    unexpected_fields = set(payload) - allowed_fields

    if unexpected_fields:
        logger.info(
            "Ignoring unexpected %s fields: %s",
            model_class.__name__,
            sorted(unexpected_fields),
        )
        payload = {
            key: value
            for key, value in payload.items()
            if key in allowed_fields
        }

    try:
        return model_class.model_validate(payload)
    except Exception as error:
        raise ValueError(
            f"Provider JSON did not match {model_class.__name__}: "
            f"{error}. Response excerpt: {cleaned[:800]!r}"
        ) from error


def call_structured_model(
    prompt: str,
    model_class: Type,
    *,
    max_tokens: int,
    attempts: Optional[int] = None,
):
    schema = model_class.model_json_schema()
    attempt_count = attempts or settings.generation_max_retries
    last_error: Optional[Exception] = None

    for attempt in range(1, attempt_count + 1):
        try:
            user_instruction = (
                "Return one complete JSON object only. "
                "Do not use Markdown or explanatory prose."
            )

            request_options = {
                "model": settings.groq_model,
                "messages": [
                    {
                        "role": "system",
                        "content": prompt,
                    },
                ],
                "temperature": settings.generation_temperature,
                "max_completion_tokens": max_tokens,
            }

            if settings.groq_model.startswith("openai/gpt-oss"):
                request_options["reasoning_effort"] = (
                    settings.generation_reasoning_effort
                )
                request_options["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": model_class.__name__,
                        "strict": True,
                        "schema": schema,
                    },
                }
            else:
                # JSON Object Mode guarantees JSON syntax, but it does
                # not send the model our schema. Include the exact
                # Pydantic schema in the instruction, then validate the
                # result locally.
                compact_schema = json.dumps(
                    schema,
                    separators=(",", ":"),
                )
                user_instruction += (
                    "\nThe JSON must conform exactly to this schema:"
                    f"\n{compact_schema}"
                )
                request_options["response_format"] = {
                    "type": "json_object",
                }

            request_options["messages"].append(
                {
                    "role": "user",
                    "content": user_instruction,
                }
            )

            response = client.chat.completions.create(
                **request_options,
            )

            raw_content = response.choices[0].message.content

            if not raw_content:
                raise ValueError(
                    "Groq returned an empty response."
                )

            return _parse_json_object(
                raw_content,
                model_class,
            )

        except Exception as error:
            last_error = error
            logger.warning(
                "%s generation attempt %s failed: %s",
                model_class.__name__,
                attempt,
                error,
            )

            if not _is_retryable(error):
                break

    detail = (
        repr(last_error)
        if last_error is not None
        else "Unknown generation error"
    )

    raise MysteryGenerationError(
        f"{model_class.__name__} generation failed. "
        f"Last error: {detail}"
    ) from last_error


def _difficulty_guidance(difficulty: Difficulty) -> str:
    if difficulty == Difficulty.easy:
        return (
            "EASY: make the killer contradiction direct. The player "
            "should combine the contradiction with one method clue."
        )

    if difficulty == Difficulty.brutal:
        return (
            "BRUTAL: no single clue may identify the killer. Separate "
            "the alibi contradiction, opportunity and method across "
            "different clues, and make the red herring credible."
        )

    return (
        "STANDARD: require at least two clues to identify the killer. "
        "Keep the logic clear after the player compares them."
    )


def _feedback_prompt(
    base_prompt: str,
    issues: list[str],
    phase_name: str,
) -> str:
    if not issues:
        return base_prompt

    feedback = "\n".join(f"- {issue}" for issue in issues)

    return (
        base_prompt
        + "\n\nTHE PREVIOUS "
        + phase_name.upper()
        + " WAS REJECTED:\n"
        + feedback
        + "\nGenerate a different result that fixes every issue."
    )


def generate_core_truth(
    room_objects: list[str],
    difficulty: Difficulty = Difficulty.standard,
) -> CoreTruthDraft:
    objects = "\n".join(
        f"{index}: {name}"
        for index, name in enumerate(room_objects)
    )

    primary_room_object_index = random.randrange(
        len(room_objects)
    )
    primary_room_object = room_objects[
        primary_room_object_index
    ]

    contradiction_candidates = [
        index
        for index in range(len(room_objects))
        if index != primary_room_object_index
    ]
    contradiction_room_object_index = random.choice(
        contradiction_candidates
    )
    contradiction_room_object = room_objects[
        contradiction_room_object_index
    ]

    base_prompt = dedent(
        f"""
        Create only the locked foundation for a fair, fictional
        one-room murder mystery.

        The mystery takes place entirely inside the photographed room.
        Every important physical object must be one of these four:

        {objects}

        PRIMARY METHOD OBJECT:
        {primary_room_object}

        CONTRADICTION OBJECT:
        {contradiction_room_object}

        DIFFICULTY:
        {_difficulty_guidance(difficulty)}

        REQUIRED LOGIC:

        1. The method must use the exact primary method object,
           "{primary_room_object}", as an ordinary real object.
        2. The method must be physically plausible and leave a visible
           trace that a player could observe without laboratory work.
        3. killer_denial must clearly say the killer did not approach,
           inspect or handle the contradiction object,
           "{contradiction_room_object}".
        4. hidden_detail must describe one plausible physical detail
           on, under, inside or behind "{contradiction_room_object}".
           It must not be visible from normal viewing distance.
        5. killer_revealed_detail must accidentally reveal knowledge
           of that exact hidden detail while preserving the denial.
        6. The revealed detail must closely repeat the distinctive
           words used in hidden_detail.
        7. The contradiction comes from impossible knowledge. The
           hidden detail itself does not prove who made it or who was
           present during the murder.

        HARD LIMITS:

        - Use exactly one victim and one killer key.
        - Use a 24-hour time such as "20:15".
        - Keep all events and claims inside this single room.
        - Do not invent another room, corridor, garden, kitchen,
          study, break room, witness or external location.
        - Do not use poison, sedatives, toxins, allergies,
          electrocution, electrical surges or invisible chemicals.
        - Do not use CCTV, recordings, live feeds, fingerprints,
          DNA, forensic analysis, laboratory tests or confessions.
        - Do not invent machinery, detachable crushing panels,
          implausible traps or impossible object behaviour.
        - Do not put suspect_1, suspect_2 or suspect_3 inside prose.
        - Use grounded contemporary fiction, British English and
          concise iPhone-friendly wording.
        - Return only the required JSON object.
        - Do not generate suspects, clues, an alibi flaw or indexes.
        """
    ).strip()

    issues: list[str] = []
    last_generation_error: Optional[
        MysteryGenerationError
    ] = None

    for _ in range(settings.generation_max_retries):
        try:
            generated = call_structured_model(
                _feedback_prompt(
                    base_prompt,
                    issues,
                    "core truth",
                ),
                CoreTruthAIResponse,
                max_tokens=settings.core_max_tokens,
                attempts=1,
            )
        except MysteryGenerationError as error:
            status_code = getattr(
                error.__cause__,
                "status_code",
                None,
            )

            # Authentication and quota failures cannot be fixed by
            # immediately asking the same provider again.
            if status_code in {401, 403, 429}:
                raise

            last_generation_error = error
            issues = [
                "The provider returned malformed or incomplete JSON."
            ]
            continue

        killer_denial = generated.killer_denial.strip()
        revealed_detail = (
            generated.killer_revealed_detail.strip()
        )
        hidden_detail = generated.hidden_detail.strip()

        killer_alibi = " ".join(
            [
                killer_denial,
                revealed_detail,
            ]
        )

        # Python owns the deduction wording. The model supplies the
        # facts, but it cannot replace impossible-knowledge logic with
        # an unrelated claim about presence.
        killer_alibi_flaw = (
            f"{revealed_detail} This reveals knowledge of "
            f"{hidden_detail} That detail cannot be observed without "
            f"approaching, inspecting or handling the "
            f"{contradiction_room_object}, directly contradicting "
            f"the denial: {killer_denial}"
        )

        draft = CoreTruthDraft(
            title=generated.title,
            opening_incident=generated.opening_incident,
            victim_name=generated.victim_name,
            killer_key=generated.killer_key,
            motive=generated.motive,
            method=generated.method,
            time_of_death=generated.time_of_death,
            killer_denial=killer_denial,
            hidden_detail=hidden_detail,
            killer_revealed_detail=revealed_detail,
            killer_alibi=killer_alibi,
            killer_alibi_flaw=killer_alibi_flaw,
            primary_room_object_index=(
                primary_room_object_index
            ),
            contradiction_room_object_index=(
                contradiction_room_object_index
            ),
        )

        issues = validate_core_truth(
            draft,
            room_objects,
        )

        if not issues:
            return draft

    if (
        last_generation_error is not None
        and issues == [
            "The provider returned malformed or incomplete JSON."
        ]
    ):
        raise last_generation_error

    if issues:
        raise MysteryGenerationError(
            "Core truth failed deterministic validation: "
            + ", ".join(issues)
        )

    if last_generation_error is not None:
        raise last_generation_error

    raise MysteryGenerationError(
        "Core truth generation failed without a result."
    )

def generate_suspect_cast(
    core_truth: CoreTruthDraft,
    room_objects: list[str],
    difficulty: Difficulty = Difficulty.standard,
) -> SuspectCastDraft:
    objects = "\n".join(
        f"{index}: {name}"
        for index, name in enumerate(room_objects)
    )

    base_prompt = dedent(
        f"""
        Create exactly three suspects around this locked truth.

        ROOM OBJECTS:
        {objects}

        LOCKED CORE:
        {core_truth.model_dump_json()}

        DIFFICULTY:
        {_difficulty_guidance(difficulty)}

        HARD RULES:

        1. Use suspect_1, suspect_2 and suspect_3 exactly once.
        2. The locked killer key is the killer, but prose must not
           reveal that.
        3. The killer's alibi_claim and alibi_evidence_fact must
           exactly reproduce the locked alibi and flaw.
        4. Each innocent statement must include one distinctive,
           observable detail about their indexed room object.
        5. Each innocent alibi_evidence_fact must corroborate that
           exact detail. It need not prove absolute innocence.
        6. Do not infer continuous behaviour from object temperature,
           position, stains or condition.
        7. Do not invent timestamps in stains, rings, dents, dust or
           handwriting.
        8. Do not use fingerprints, DNA, CCTV, recordings, hidden
           logs, external rooms, unnamed witnesses or forensic work.
        9. No innocent should admit handling the murder object during
           the death window.
        10. Statements and alibis must be concise for an iPhone screen.
        11. Use British English and return only the schema.
        """
    ).strip()

    issues: list[str] = []

    for _ in range(settings.generation_max_retries):
        cast = call_structured_model(
            _feedback_prompt(base_prompt, issues, "suspect cast"),
            SuspectCastDraft,
            max_tokens=settings.suspect_max_tokens,
            attempts=1,
        )

        issues = validate_suspect_cast(
            cast,
            core_truth,
            room_objects,
        )

        if not issues:
            return cast

    raise MysteryGenerationError(
        "Suspect cast failed deterministic validation: "
        + ", ".join(issues)
    )


def review_evidence_board(
    core_truth: CoreTruthDraft,
    suspect_cast: SuspectCastDraft,
    evidence_board: EvidenceBoardDraft,
    room_objects: list[str],
) -> EvidenceBoardReview:
    return call_structured_model(
        build_evidence_review_prompt(
            core_truth,
            suspect_cast,
            evidence_board,
            room_objects,
        ),
        EvidenceBoardReview,
        max_tokens=settings.review_max_tokens,
        attempts=1,
    )



def _evidence_blueprint(
    core_truth: CoreTruthDraft,
    suspect_cast: SuspectCastDraft,
    room_objects: list[str],
) -> str:
    killer = next(
        suspect
        for suspect in suspect_cast.suspects
        if suspect.key == core_truth.killer_key
    )
    innocents = [
        suspect
        for suspect in suspect_cast.suspects
        if suspect.key != core_truth.killer_key
    ]

    first_innocent = innocents[0]
    second_innocent = innocents[1]
    killer_object = room_objects[
        killer.alibi_room_object_index
    ]
    primary_object = room_objects[
        core_truth.primary_room_object_index
    ]
    death_times = ", ".join(
        re.findall(
            r"\b\d{1,2}:\d{2}\b",
            core_truth.time_of_death,
        )
    )

    return dedent(
        f"""
        MANDATORY CLUE BLUEPRINT:

        clue_1
        - room_object_index: {first_innocent.alibi_room_object_index}
        - detail must literally name "{room_objects[first_innocent.alibi_room_object_index]}"
        - one deduction: corroboratesAlibi for {first_innocent.key.value}
        - paraphrase this locked fact without inventing anything:
          {first_innocent.alibi_evidence_fact}

        clue_2
        - room_object_index: {killer.alibi_room_object_index}
        - detail must literally name "{killer_object}"
        - deductions: contradictsStatement for {killer.key.value}
          and establishesTimeline with related key "none"
        - directly expose this locked flaw:
          {core_truth.killer_alibi_flaw}
        - explicitly include every locked death time: {death_times}

        clue_3
        - room_object_index: {core_truth.primary_room_object_index}
        - detail must literally name both "{primary_object}" and
          "{killer_object}"
        - deductions: establishesMethod with related key "none"
          and establishesOpportunity for {killer.key.value}
        - show the observable method on the {primary_object}
        - connect the killer's presence established by the
          {killer_object} evidence to physical reach of the
          {primary_object}
        - do not invent duties, ownership, access permissions,
          extra rooms or extra objects

        clue_4
        - room_object_index: {second_innocent.alibi_room_object_index}
        - detail must literally name "{room_objects[second_innocent.alibi_room_object_index]}"
        - one deduction: corroboratesAlibi for {second_innocent.key.value}
        - paraphrase this locked fact without inventing anything:
          {second_innocent.alibi_evidence_fact}

        clue_5
        - kind: redHerring
        - deductions: []
        - detail must literally name its indexed supplied room object
        - make it plausibly suspicious without claiming it is
          irrelevant or proving any deduction

        CASE-LEVEL OPPORTUNITY:
        - opportunity must literally name both "{killer_object}" and
          "{primary_object}"
        - it must explain how the locked {killer_object} evidence places
          {killer.name} within reach of the {primary_object}
        - it must not introduce any fact absent from the locked core or
          suspect cast
        """
    ).strip()

def generate_evidence_board(
    core_truth: CoreTruthDraft,
    suspect_cast: SuspectCastDraft,
    room_objects: list[str],
    difficulty: Difficulty = Difficulty.standard,
) -> EvidenceBoardDraft:
    objects = "\n".join(
        f"{index}: {name}"
        for index, name in enumerate(room_objects)
    )

    base_prompt = dedent(
        f"""
        Create the five-clue evidence board for this locked case.

        ROOM OBJECTS:
        {objects}

        LOCKED CORE:
        {core_truth.model_dump_json()}

        LOCKED SUSPECTS:
        {suspect_cast.model_dump_json()}

        DIFFICULTY:
        {_difficulty_guidance(difficulty)}

        {_evidence_blueprint(
            core_truth,
            suspect_cast,
            room_objects,
        )}

        HARD STRUCTURE:

        1. Fill clue_1 through clue_5 with five different clues.
        2. Exactly one clue is redHerring and has no deductions.
        3. Use all four room objects.
        4. Every clue detail must literally name the supplied room
           object selected by its room_object_index.
        5. Follow the mandatory clue blueprint exactly. Do not move
           deduction roles to different clue slots.
        6. Each innocent receives a corroboratesAlibi deduction tied
           to their locked alibi_evidence_fact.
        7. Use eliminatesSuspect only for genuine impossibility.
        8. The killer receives contradictsStatement and
           establishesOpportunity deductions, but never
           corroboratesAlibi or eliminatesSuspect.
        9. Include establishesMethod and establishesTimeline.
        10. establishesMethod and establishesTimeline use "none".
        11. All other deduction kinds identify the relevant suspect.
        12. The contradiction and opportunity must not both depend
            on one clue.
        13. At least two clues must be combined to solve the case.

        FAIRNESS:

        1. Treat the locked alibi_evidence_fact values as the complete
           factual source. Paraphrase them without inventing extra
           times, ownership, access or behaviour.
        2. Timeline evidence must support the stated death time or
           window, not merely place somebody in the room.
        3. Method evidence must support the exact locked method using
           observable features of the primary room object.
        4. Opportunity must follow from the locked killer flaw and
           physical proximity to the primary room object. Do not
           invent job duties or special access.
        5. No DNA, fingerprints, CCTV, recordings, microscopic work,
           unnamed witnesses or hidden external evidence.
        6. No timestamps inferred from temperature, stains, dust,
           scratches, condensation or handwriting.
        7. The red herring must sound relevant. Never call it
           irrelevant, unrelated or meaningless.
        8. Use British English and concise iPhone-friendly prose.

        KEY MAPPING:

        - corroboratesAlibi: the innocent suspect's key
        - eliminatesSuspect: the genuinely eliminated suspect's key
        - supportsSuspect: the suspect supported
        - contradictsStatement: the contradicted suspect
        - establishesOpportunity: the killer
        - establishesMethod: "none"
        - establishesTimeline: "none"

        Return only the schema.
        """
    ).strip()

    issues: list[str] = []

    for _ in range(settings.generation_max_retries):
        board = call_structured_model(
            _feedback_prompt(base_prompt, issues, "evidence board"),
            EvidenceBoardDraft,
            max_tokens=settings.evidence_max_tokens,
            attempts=1,
        )

        issues = validate_evidence_board(
            board,
            core_truth,
            suspect_cast,
            room_objects,
        )

        if issues:
            continue

        review = review_evidence_board(
            core_truth,
            suspect_cast,
            board,
            room_objects,
        )

        if review.passes:
            return board

        issues = review.issues or [
            "The semantic reviewer rejected the evidence board."
        ]

    raise MysteryGenerationError(
        "Evidence board failed validation: "
        + ", ".join(issues)
    )


def generate_mystery_draft(
    room_objects: list[str],
    difficulty: Difficulty = Difficulty.standard,
) -> MysteryDraft:
    core_truth = generate_core_truth(
        room_objects,
        difficulty,
    )
    suspect_cast = generate_suspect_cast(
        core_truth,
        room_objects,
        difficulty,
    )
    evidence_board = generate_evidence_board(
        core_truth,
        suspect_cast,
        room_objects,
        difficulty,
    )

    return assemble_mystery(
        core_truth,
        suspect_cast,
        evidence_board,
    )
