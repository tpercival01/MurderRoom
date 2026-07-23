from __future__ import annotations

import re

from app.models import (
    ClueKind,
    CoreTruthDraft,
    DeductionKind,
    EvidenceBoardDraft,
    SuspectCastDraft,
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
    "phone record",
    "mobile record",
    "unnamed witness",
    "hidden passage",
}

BANNED_PLAYER_CONCLUSION_PHRASES = {
    "this directly contradicts",
    "this independently places",
    "the attack therefore",
    "proving it was",
    "showing it was",
    "therefore had the only",
}

BANNED_RED_HERRING_RESOLUTION_PHRASES = {
    "earlier repair",
    "older repair",
    "predates the attack",
    "before the attack",
    "before the evening",
    "not fresh damage",
    "unrelated to the murder",
    "irrelevant",
}

BANNED_WEAK_PHRASES = {
    "may have",
    "might have",
    "possibly",
    "perhaps",
    "suggests they may",
    "just a coincidence",
    "probably unrelated",
    "likely caused by",
    "could have been used",
}

_INTERNAL_REFERENCE_RE = re.compile(r"\bsuspect[_ ]?[123]\b", re.IGNORECASE)


def _mentions_object(text: str, object_name: str) -> bool:
    text_cf = text.casefold()
    name_cf = object_name.casefold().strip()
    if name_cf in text_cf:
        return True
    tokens = [token for token in re.findall(r"[a-z0-9]+", name_cf) if len(token) > 2]
    return bool(tokens) and tokens[-1] in text_cf


def _text_issues(text: str, label: str, *, minimum: int = 12) -> list[str]:
    issues: list[str] = []
    stripped = text.strip()
    lowered = stripped.casefold()

    if len(stripped) < minimum:
        issues.append(f"{label} is too short to carry a fair deduction.")
    if _INTERNAL_REFERENCE_RE.search(stripped):
        issues.append(f"{label} exposes an internal suspect key.")
    for term in BANNED_EVIDENCE_TERMS:
        if term in lowered:
            issues.append(f"{label} uses prohibited external evidence: {term}.")
    for phrase in BANNED_WEAK_PHRASES:
        if phrase in lowered:
            issues.append(f"{label} uses weak or unsupported reasoning: {phrase}.")
    return issues


def validate_core_truth(
    draft: CoreTruthDraft,
    room_objects: list[str],
) -> list[str]:
    issues: list[str] = []
    method_object = room_objects[draft.primary_room_object_index]
    contradiction_object = room_objects[draft.contradiction_room_object_index]

    if not _mentions_object(draft.method_evidence, method_object):
        issues.append("Method evidence must name its photographed method object.")
    if not _mentions_object(draft.method, method_object):
        issues.append("The solution method must name its photographed method object.")
    if not _mentions_object(draft.hidden_detail, contradiction_object):
        issues.append("The killer contradiction must name its photographed object.")
    if "after " not in draft.time_of_death.casefold() or "before " not in draft.time_of_death.casefold():
        issues.append("Time of death must be expressed as a bounded after/before window.")
    if draft.killer_alibi.strip() == draft.killer_alibi_flaw.strip():
        issues.append("The killer alibi and its physical flaw must differ.")

    title_text = draft.title.casefold().strip()
    if (
        title_text in {
            "the mysterious death",
            "the mysterious murder",
            "the mysterious office death",
            "the office murder",
            "the office death",
        }
        or re.fullmatch(
            r"(?:the\s+)?mysterious\s+(?:office\s+)?(?:death|murder)",
            title_text,
        )
    ):
        issues.append("The case title is placeholder-level.")

    if "because because" in draft.motive.casefold():
        issues.append("The motive repeats the word 'because'.")

    if " found dead in A " in draft.opening_incident:
        issues.append("The opening incident contains a capitalised article fragment.")

    for label, text in {
        "title": draft.title,
        "opening incident": draft.opening_incident,
        "motive": draft.motive,
        "method": draft.method,
        "method evidence": draft.method_evidence,
        "killer denial": draft.killer_denial,
        "killer contradiction": draft.hidden_detail,
        "killer alibi": draft.killer_alibi,
        "killer alibi flaw": draft.killer_alibi_flaw,
    }.items():
        issues.extend(_text_issues(text, label, minimum=5 if label == "title" else 12))

    return issues


def validate_suspect_cast(
    suspect_cast: SuspectCastDraft,
    core_truth: CoreTruthDraft,
    room_objects: list[str],
) -> list[str]:
    issues: list[str] = []
    suspects_by_key = {suspect.key: suspect for suspect in suspect_cast.suspects}

    if len(suspects_by_key) != 3:
        return ["The cast must contain three distinct suspect keys."]

    killer = suspects_by_key[core_truth.killer_key]
    if killer.statement.strip() != core_truth.killer_denial.strip():
        issues.append("The killer statement must exactly match the locked denial.")
    if killer.alibi_claim.strip() != core_truth.killer_alibi.strip():
        issues.append("The killer alibi must exactly match the locked alibi.")

    names = [suspect.name.casefold().strip() for suspect in suspect_cast.suspects]
    if len(set(names)) != 3:
        issues.append("Suspect names must be distinct.")

    innocent_names = [
        suspect.name
        for suspect in suspect_cast.suspects
        if suspect.key != core_truth.killer_key
    ]
    killer_name = killer.name

    for suspect in suspect_cast.suspects:
        object_name = room_objects[suspect.alibi_room_object_index]
        if not _mentions_object(suspect.alibi_evidence_fact, object_name):
            issues.append(
                f"{suspect.name}'s evidence must name the indexed object {object_name!r}."
            )
        issues.extend(_text_issues(suspect.statement, f"{suspect.name} statement"))
        issues.extend(_text_issues(suspect.alibi_claim, f"{suspect.name} alibi"))
        issues.extend(_text_issues(
            suspect.alibi_evidence_fact,
            f"{suspect.name} alibi evidence",
        ))

    for innocent_name in innocent_names:
        innocent = next(
            suspect for suspect in suspect_cast.suspects if suspect.name == innocent_name
        )
        other_name = next(name for name in innocent_names if name != innocent_name)
        if other_name.casefold() not in innocent.statement.casefold():
            issues.append(
                f"{innocent_name}'s shared alibi statement must name {other_name}."
            )

    if not any(
        killer_name.casefold() in suspect.statement.casefold()
        for suspect in suspect_cast.suspects
        if suspect.key != core_truth.killer_key
    ):
        issues.append("At least one innocent statement must place the killer in the room.")

    return issues


def _deduction_pairs(board: EvidenceBoardDraft, clue_index: int) -> set[tuple[DeductionKind, SuspectReferenceKey]]:
    clue = board.clues[clue_index]
    return {
        (deduction.kind, deduction.related_suspect_key)
        for deduction in clue.deductions
    }


def validate_evidence_board(
    board: EvidenceBoardDraft,
    core_truth: CoreTruthDraft,
    suspect_cast: SuspectCastDraft,
    room_objects: list[str],
) -> list[str]:
    issues: list[str] = []
    clues = board.clues

    if len(clues) != 5:
        return ["The evidence board must contain exactly five clues."]
    if sum(clue.kind == ClueKind.red_herring for clue in clues) != 1:
        issues.append("The evidence board must contain exactly one red herring.")
    if {clue.room_object_index for clue in clues} != {0, 1, 2, 3}:
        issues.append("All four photographed room objects must be used.")

    for index, clue in enumerate(clues, start=1):
        object_name = room_objects[clue.room_object_index]
        if not _mentions_object(clue.detail, object_name):
            issues.append(f"Clue {index} must name its indexed object {object_name!r}.")
        issues.extend(_text_issues(clue.title, f"clue {index} title", minimum=3))
        issues.extend(_text_issues(clue.detail, f"clue {index} detail"))

        lowered_detail = clue.detail.casefold()
        for phrase in BANNED_PLAYER_CONCLUSION_PHRASES:
            if phrase in lowered_detail:
                issues.append(
                    f"Clue {index} explains its deduction to the player: {phrase}."
                )

        if clue.kind == ClueKind.red_herring:
            for phrase in BANNED_RED_HERRING_RESOLUTION_PHRASES:
                if phrase in lowered_detail:
                    issues.append(
                        f"The red herring reveals its resolution: {phrase}."
                    )

    killer_ref = SuspectReferenceKey(core_truth.killer_key.value)
    innocent_refs = {
        SuspectReferenceKey(suspect.key.value)
        for suspect in suspect_cast.suspects
        if suspect.key != core_truth.killer_key
    }

    clue_1_expected = {
        (DeductionKind.establishes_method, SuspectReferenceKey.none),
    }
    clue_2_expected = {
        (DeductionKind.establishes_timeline, SuspectReferenceKey.none),
        *{
            (kind, ref)
            for ref in innocent_refs
            for kind in (
                DeductionKind.corroborates_alibi,
            )
        },
    }
    clue_3_expected = {
        (DeductionKind.contradicts_statement, killer_ref),
        (DeductionKind.establishes_opportunity, killer_ref),
        (DeductionKind.supports_suspect, killer_ref),
    }
    clue_4_expected = {
        (DeductionKind.supports_suspect, killer_ref),
    }

    expected_sets = [clue_1_expected, clue_2_expected, clue_3_expected, clue_4_expected]
    for index, expected in enumerate(expected_sets):
        actual = _deduction_pairs(board, index)
        if actual != expected:
            issues.append(
                f"Clue {index + 1} has an invalid proof contract: "
                f"expected {sorted((k.value, r.value) for k, r in expected)}, "
                f"got {sorted((k.value, r.value) for k, r in actual)}."
            )

    if clues[4].kind != ClueKind.red_herring or clues[4].deductions:
        issues.append("Clue 5 must be the resolved red herring with no deductions.")
    if any(clue.kind != ClueKind.evidence for clue in clues[:4]):
        issues.append("Clues 1 to 4 must be evidence clues.")
    if clues[0].room_object_index != core_truth.primary_room_object_index:
        issues.append("Clue 1 must use the locked method object.")
    if clues[2].room_object_index != core_truth.contradiction_room_object_index:
        issues.append("Clue 3 must use the locked contradiction object.")
    if clues[2].room_object_index == clues[3].room_object_index:
        issues.append("The two killer-specific clues must use independent objects.")

    support_locations: dict[SuspectReferenceKey, set[int]] = {}
    for index, clue in enumerate(clues):
        for deduction in clue.deductions:
            if deduction.kind == DeductionKind.supports_suspect:
                support_locations.setdefault(deduction.related_suspect_key, set()).add(index)

    if support_locations.get(killer_ref, set()) != {2, 3}:
        issues.append("The killer must be supported by exactly two independent clues.")
    if any(ref != killer_ref for ref in support_locations):
        issues.append("No innocent suspect may receive a supportsSuspect deduction.")

    suspects_by_key = {suspect.key: suspect for suspect in suspect_cast.suspects}
    killer_name = suspects_by_key[core_truth.killer_key].name
    if killer_name.casefold() not in board.opportunity.casefold():
        issues.append("The opportunity explanation must name the killer.")
    for object_index in {
        core_truth.primary_room_object_index,
        clues[3].room_object_index,
    }:
        if not _mentions_object(board.opportunity, room_objects[object_index]):
            issues.append("The opportunity explanation must name both killer-link objects.")
    for suspect in suspect_cast.suspects:
        if suspect.key != core_truth.killer_key and suspect.name.casefold() not in board.opportunity.casefold():
            issues.append(
                f"The opportunity explanation must account for innocent suspect {suspect.name}."
            )

    issues.extend(_text_issues(board.opportunity, "solution opportunity"))
    return issues
