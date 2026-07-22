from __future__ import annotations

import re

from app.models import (
    ClueKind,
    CoreTruthDraft,
    DeductionKind,
    EvidenceBoardDraft,
    SuspectCastDraft,
    SuspectKey,
    SuspectReferenceKey,
)


BANNED_EVIDENCE_TERMS = {
    "fingerprint",
    "dna",
    "cctv",
    "camera footage",
    "video recording",
    "microscopic",
    "forensic analysis",
    "unnamed witness",
    "witness observed",
}

BANNED_REASONING_PHRASES = {
    "clock imprint",
    "dated around",
    "still holding",
    "was not near",
    "only the killer could",
    "regularly maintained",
    "no relevance",
    "unrelated to the murder",
    "unrelated to the incident",
    "shows the killer was near",
    "proves the killer was near",
    "meaning the killer was near",
    "shows the killer was present",
    "proves the killer was present",
}

BANNED_EXTERNAL_LOCATIONS = {
    "break room",
    "study",
    "kitchen",
    "garden",
    "hallway",
    "corridor",
    "car park",
    "bedroom",
    "bathroom",
}

BANNED_CORE_METHOD_TERMS = {
    "poison",
    "sedative",
    "toxin",
    "cyanide",
    "allergic reaction",
    "electrocution",
    "electrical surge",
    "live feed",
}

STOP_WORDS = {
    "a", "an", "and", "at", "before", "by", "for", "from", "i",
    "in", "is", "it", "of", "on", "the", "then", "to", "was",
    "with", "after", "that", "this", "their", "they",
}


def _content_words(text: str) -> set[str]:
    words: set[str] = set()

    for raw_word in re.findall(r"[a-z0-9']+", text.casefold()):
        word = (
            raw_word[:-2]
            if raw_word.endswith("'s")
            else raw_word
        )

        if len(word) > 2 and word not in STOP_WORDS:
            words.add(word)

    return words


def _has_shared_detail(left: str, right: str) -> bool:
    return len(
        _content_words(left).intersection(_content_words(right))
    ) >= 2


def validate_core_truth(
    draft: CoreTruthDraft,
    room_objects: list[str],
) -> list[str]:
    issues: list[str] = []

    primary_object = room_objects[
        draft.primary_room_object_index
    ].casefold()
    contradiction_object = room_objects[
        draft.contradiction_room_object_index
    ].casefold()

    method_text = draft.method.casefold()
    denial_text = draft.killer_denial.casefold()
    hidden_text = draft.hidden_detail.casefold()
    revealed_text = draft.killer_revealed_detail.casefold()
    flaw_text = draft.killer_alibi_flaw.casefold()

    if primary_object not in method_text:
        issues.append(
            "The method does not mention its primary room object."
        )

    if contradiction_object not in denial_text:
        issues.append(
            "The killer denial does not mention the locked "
            "contradiction object."
        )

    if contradiction_object not in hidden_text:
        issues.append(
            "The hidden detail does not mention the locked "
            "contradiction object."
        )

    if contradiction_object not in flaw_text:
        issues.append(
            "The killer alibi flaw does not mention the locked "
            "contradiction object."
        )

    if not _has_shared_detail(
        draft.hidden_detail,
        draft.killer_revealed_detail,
    ):
        issues.append(
            "The killer's revealed detail does not match the "
            "locked hidden detail."
        )

    if not _has_shared_detail(
        draft.hidden_detail,
        draft.killer_alibi_flaw,
    ):
        issues.append(
            "The killer alibi flaw does not explain the locked "
            "hidden detail."
        )

    if not _has_shared_detail(
        draft.killer_denial,
        draft.killer_alibi_flaw,
    ):
        issues.append(
            "The killer alibi flaw does not directly address the "
            "killer's denial."
        )

    combined = " ".join(
        [
            draft.opening_incident,
            draft.method,
            draft.killer_alibi,
            draft.killer_alibi_flaw,
        ]
    ).casefold()

    for banned_term in BANNED_CORE_METHOD_TERMS:
        if banned_term in combined:
            issues.append(
                "Core truth uses unsupported reasoning: "
                f"{banned_term}."
            )

    for banned_term in BANNED_EVIDENCE_TERMS:
        if banned_term in combined:
            issues.append(
                f"Core truth uses prohibited evidence: {banned_term}."
            )

    for banned_phrase in BANNED_REASONING_PHRASES:
        if banned_phrase in flaw_text:
            issues.append(
                "Core truth uses weak alibi reasoning: "
                f"{banned_phrase}."
            )

    for location in BANNED_EXTERNAL_LOCATIONS:
        if location in combined:
            issues.append(
                "Core truth introduces an external location: "
                f"{location}."
            )

    for key in SuspectKey:
        if key.value in combined:
            issues.append(
                "Narrative fields expose an internal suspect key."
            )
            break

    if not re.fullmatch(
        r"(?:[01]\d|2[0-3]):[0-5]\d",
        draft.time_of_death.strip(),
    ):
        issues.append(
            "Time of death must be one exact 24-hour time."
        )

    if draft.killer_alibi.strip() == draft.killer_alibi_flaw.strip():
        issues.append(
            "The killer alibi and its flaw must be different."
        )

    return issues

def validate_suspect_cast(
    suspect_cast: SuspectCastDraft,
    core_truth: CoreTruthDraft,
    room_objects: list[str],
) -> list[str]:
    issues: list[str] = []

    killer = next(
        suspect
        for suspect in suspect_cast.suspects
        if suspect.key == core_truth.killer_key
    )

    if killer.alibi_claim.strip() != core_truth.killer_alibi.strip():
        issues.append(
            "The killer alibi does not match the locked core truth."
        )

    if (
        killer.alibi_evidence_fact.strip()
        != core_truth.killer_alibi_flaw.strip()
    ):
        issues.append(
            "The killer evidence fact does not match the locked flaw."
        )

    alibi_indexes = {
        suspect.alibi_room_object_index
        for suspect in suspect_cast.suspects
    }

    if len(alibi_indexes) != 3:
        issues.append(
            "Each suspect must use a different alibi room object."
        )

    if core_truth.primary_room_object_index in alibi_indexes:
        issues.append(
            "The primary murder object must be reserved for the "
            "method clue, not a suspect alibi."
        )

    for suspect in suspect_cast.suspects:
        fact = suspect.alibi_evidence_fact.casefold()
        room_object = room_objects[
            suspect.alibi_room_object_index
        ].casefold()

        for banned_term in BANNED_EVIDENCE_TERMS:
            if banned_term in fact:
                issues.append(
                    f"{suspect.key.value} uses prohibited evidence: "
                    f"{banned_term}."
                )

        for banned_phrase in BANNED_REASONING_PHRASES:
            if banned_phrase in fact:
                issues.append(
                    f"{suspect.key.value} uses weak reasoning: "
                    f"{banned_phrase}."
                )

        if room_object not in fact:
            issues.append(
                f"{suspect.key.value} evidence does not mention "
                f"its indexed room object."
            )

        if suspect.key != core_truth.killer_key:
            account = (
                f"{suspect.statement} {suspect.alibi_claim}"
            )
            if not _has_shared_detail(
                account,
                suspect.alibi_evidence_fact,
            ):
                issues.append(
                    f"{suspect.key.value} evidence does not "
                    "corroborate a specific detail from their account."
                )

    return issues


def validate_evidence_board(
    board: EvidenceBoardDraft,
    core_truth: CoreTruthDraft,
    suspect_cast: SuspectCastDraft,
    room_objects: list[str],
) -> list[str]:
    issues: list[str] = []
    killer_key = core_truth.killer_key
    innocent_keys = {
        suspect.key
        for suspect in suspect_cast.suspects
        if suspect.key != killer_key
    }
    suspect_by_key = {
        suspect.key: suspect
        for suspect in suspect_cast.suspects
    }
    primary_object_index = core_truth.primary_room_object_index
    primary_object = room_objects[primary_object_index].casefold()
    killer = suspect_by_key[killer_key]
    killer_object_index = killer.alibi_room_object_index
    killer_object = room_objects[killer_object_index].casefold()
    death_times = re.findall(
        r"\b\d{1,2}:\d{2}\b",
        core_truth.time_of_death,
    )

    corroborated: set[SuspectKey] = set()
    contradicted: set[SuspectKey] = set()
    opportunity_for: set[SuspectKey] = set()
    method_clues: set[int] = set()
    timeline_clues: set[int] = set()
    contradiction_clues: set[int] = set()
    opportunity_clues: set[int] = set()

    for clue_index, clue in enumerate(board.clues):
        detail = clue.detail.casefold()
        room_object = room_objects[
            clue.room_object_index
        ].casefold()

        if room_object not in detail:
            issues.append(
                f"clue_{clue_index + 1} does not mention "
                "its indexed room object."
            )

        for banned_term in BANNED_EVIDENCE_TERMS:
            if banned_term in detail:
                issues.append(
                    f"clue_{clue_index + 1} uses prohibited evidence: "
                    f"{banned_term}."
                )

        for banned_phrase in BANNED_REASONING_PHRASES:
            if banned_phrase in detail:
                issues.append(
                    f"clue_{clue_index + 1} uses weak reasoning: "
                    f"{banned_phrase}."
                )

        if clue.kind == ClueKind.red_herring:
            continue

        for deduction in clue.deductions:
            related = deduction.related_suspect_key

            if deduction.kind == DeductionKind.establishes_method:
                method_clues.add(clue_index)

                if clue.room_object_index != primary_object_index:
                    issues.append(
                        f"clue_{clue_index + 1} establishes method "
                        "using the wrong room object."
                    )

                if primary_object not in detail:
                    issues.append(
                        f"clue_{clue_index + 1} method detail does "
                        "not mention the primary room object."
                    )

            elif deduction.kind == DeductionKind.establishes_timeline:
                timeline_clues.add(clue_index)

                missing_times = [
                    time_value
                    for time_value in death_times
                    if time_value not in clue.detail
                ]

                if missing_times:
                    issues.append(
                        f"clue_{clue_index + 1} timeline detail "
                        "does not include every locked death time."
                    )

            elif deduction.kind == DeductionKind.corroborates_alibi:
                key = SuspectKey(related.value)

                if key == killer_key:
                    issues.append(
                        "The killer must not receive a corroboratesAlibi "
                        "deduction."
                    )
                else:
                    corroborated.add(key)
                    locked_suspect = suspect_by_key[key]
                    locked_fact = locked_suspect.alibi_evidence_fact

                    if (
                        clue.room_object_index
                        != locked_suspect.alibi_room_object_index
                    ):
                        issues.append(
                            f"clue_{clue_index + 1} corroborates "
                            f"{key.value} using the wrong room object."
                        )

                    if not _has_shared_detail(
                        clue.detail,
                        locked_fact,
                    ):
                        issues.append(
                            f"clue_{clue_index + 1} does not "
                            f"corroborate {key.value}'s locked fact."
                        )

            elif deduction.kind == DeductionKind.eliminates_suspect:
                key = SuspectKey(related.value)

                if key == killer_key:
                    issues.append(
                        "No clue may eliminate the true killer."
                    )
                else:
                    corroborated.add(key)

            elif deduction.kind == DeductionKind.contradicts_statement:
                key = SuspectKey(related.value)
                contradicted.add(key)
                contradiction_clues.add(clue_index)

                if key == killer_key:
                    if clue.room_object_index != killer_object_index:
                        issues.append(
                            f"clue_{clue_index + 1} contradicts the "
                            "killer using the wrong room object."
                        )

                    if not _has_shared_detail(
                        clue.detail,
                        core_truth.killer_alibi_flaw,
                    ):
                        issues.append(
                            f"clue_{clue_index + 1} does not expose "
                            "the locked killer alibi flaw."
                        )

            elif deduction.kind == DeductionKind.establishes_opportunity:
                key = SuspectKey(related.value)
                opportunity_for.add(key)
                opportunity_clues.add(clue_index)

                if key != killer_key:
                    issues.append(
                        "Opportunity must be assigned to the killer."
                    )

                if clue.room_object_index != primary_object_index:
                    issues.append(
                        f"clue_{clue_index + 1} establishes opportunity "
                        "using the wrong room object."
                    )

                if primary_object not in detail:
                    issues.append(
                        f"clue_{clue_index + 1} opportunity detail "
                        "does not mention the primary room object."
                    )

                if killer_object not in detail:
                    issues.append(
                        f"clue_{clue_index + 1} opportunity detail "
                        "does not mention the killer alibi room object."
                    )

                if not _has_shared_detail(
                    clue.detail,
                    core_truth.killer_alibi_flaw,
                ):
                    issues.append(
                        f"clue_{clue_index + 1} opportunity is not "
                        "grounded in the locked killer flaw."
                    )

    missing_innocents = innocent_keys - corroborated
    if missing_innocents:
        names = ", ".join(
            sorted(key.value for key in missing_innocents)
        )
        issues.append(
            f"Missing innocent corroboration for: {names}."
        )

    if killer_key not in contradicted:
        issues.append(
            "No clue contradicts the killer's statement."
        )

    if killer_key not in opportunity_for:
        issues.append(
            "No clue establishes the killer's opportunity."
        )

    if not method_clues:
        issues.append(
            "No clue establishes the murder method."
        )

    if not timeline_clues:
        issues.append(
            "No clue establishes the timeline."
        )

    if contradiction_clues and opportunity_clues:
        if (
            contradiction_clues == opportunity_clues
            and len(contradiction_clues) == 1
        ):
            issues.append(
                "The killer contradiction and opportunity must not "
                "both depend on a single clue."
            )

    opportunity_text = board.opportunity.casefold()

    if not board.opportunity.strip():
        issues.append(
            "The evidence board must explain opportunity."
        )
    else:
        if primary_object not in opportunity_text:
            issues.append(
                "The case-level opportunity does not mention the "
                "primary room object."
            )

        if killer_object not in opportunity_text:
            issues.append(
                "The case-level opportunity does not mention the "
                "killer alibi room object."
            )

        if not _has_shared_detail(
            board.opportunity,
            core_truth.killer_alibi_flaw,
        ):
            issues.append(
                "The case-level opportunity is not grounded in the "
                "locked killer flaw."
            )

    return issues
