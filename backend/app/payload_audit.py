from __future__ import annotations

import json
import re
from typing import Any


WEAK_PHRASES = {
    "may have",
    "might have",
    "possibly",
    "perhaps",
    "likely caused by",
    "just a coincidence",
    "suggests they may",
    "could have been used",
}
INTERNAL_RE = re.compile(r"\bsuspect[_ ]?[123]\b", re.IGNORECASE)
GENERIC_TITLES = {
    "the mysterious death",
    "the mysterious murder",
    "the mysterious office death",
    "the office murder",
    "the office death",
}
PLAYER_CONCLUSION_PHRASES = {
    "this directly contradicts",
    "this independently places",
    "the attack therefore",
}
RED_HERRING_RESOLUTION_PHRASES = {
    "earlier repair",
    "older repair",
    "predates the attack",
    "before the attack",
    "unrelated to the murder",
    "irrelevant",
}


def _all_player_text(payload: dict[str, Any]) -> list[tuple[str, str]]:
    fields: list[tuple[str, str]] = []
    fields.append(("title", str(payload.get("title", ""))))
    fields.append(("openingIncident", str(payload.get("openingIncident", ""))))

    for index, suspect in enumerate(payload.get("suspects", [])):
        fields.extend(
            [
                (f"suspects[{index}].name", str(suspect.get("name", ""))),
                (f"suspects[{index}].statement", str(suspect.get("statement", ""))),
                (f"suspects[{index}].alibiClaim", str(suspect.get("alibiClaim", ""))),
            ]
        )

    for index, clue in enumerate(payload.get("clues", [])):
        fields.extend(
            [
                (f"clues[{index}].title", str(clue.get("title", ""))),
                (f"clues[{index}].detail", str(clue.get("detail", ""))),
            ]
        )

    solution = payload.get("solution", {})
    for key in ("motive", "method", "timeOfDeath", "opportunity"):
        fields.append((f"solution.{key}", str(solution.get(key, ""))))
    return fields


def audit_payload(payload: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    suspects = payload.get("suspects", [])
    objects = payload.get("roomObjects", [])
    clues = payload.get("clues", [])
    solution = payload.get("solution", {})

    title_text = str(payload.get("title", "")).casefold().strip()
    if title_text in GENERIC_TITLES:
        issues.append("The case title is placeholder-level.")

    if len(suspects) != 3:
        issues.append(f"Expected 3 suspects; received {len(suspects)}.")
    if len(objects) != 4:
        issues.append(f"Expected 4 room objects; received {len(objects)}.")
    if len(clues) != 5:
        issues.append(f"Expected 5 clues; received {len(clues)}.")

    suspect_ids = {str(suspect.get("id")) for suspect in suspects}
    object_by_id = {str(obj.get("id")): str(obj.get("name", "")) for obj in objects}
    killer_id = str(solution.get("killerID"))
    killer = next((suspect for suspect in suspects if str(suspect.get("id")) == killer_id), None)

    if killer_id not in suspect_ids:
        issues.append("solution.killerID does not reference a returned suspect.")

    red_herrings = [clue for clue in clues if clue.get("kind") == "redHerring"]
    if len(red_herrings) != 1:
        issues.append(f"Expected exactly 1 red herring; received {len(red_herrings)}.")
    for clue in red_herrings:
        if clue.get("deductions"):
            issues.append("The red herring carries deductions.")

    deduction_locations: dict[str, list[tuple[int, str | None]]] = {}
    used_object_ids: set[str] = set()
    for index, clue in enumerate(clues):
        object_id = str(clue.get("roomObjectID"))
        used_object_ids.add(object_id)
        object_name = object_by_id.get(object_id)
        if object_name is None:
            issues.append(f"clues[{index}] references an unknown roomObjectID.")
        elif object_name.casefold() not in str(clue.get("detail", "")).casefold():
            issues.append(
                f"clues[{index}] does not name its linked object {object_name!r}."
            )

        detail_text = str(clue.get("detail", "")).casefold()
        for phrase in PLAYER_CONCLUSION_PHRASES:
            if phrase in detail_text:
                issues.append(
                    f"clues[{index}] explains its deduction to the player: {phrase!r}."
                )
        if clue.get("kind") == "redHerring":
            for phrase in RED_HERRING_RESOLUTION_PHRASES:
                if phrase in detail_text:
                    issues.append(
                        f"clues[{index}] reveals the red-herring resolution: {phrase!r}."
                    )

        for deduction in clue.get("deductions", []):
            kind = str(deduction.get("kind"))
            related = deduction.get("relatedSuspectID")
            related_text = str(related) if related is not None else None
            deduction_locations.setdefault(kind, []).append((index, related_text))
            if related_text is not None and related_text not in suspect_ids:
                issues.append(
                    f"clues[{index}] deduction {kind} references an unknown suspect."
                )

    if used_object_ids != set(object_by_id):
        issues.append("The five clues do not collectively use all four room objects.")

    for required in (
        "establishesMethod",
        "establishesTimeline",
        "establishesOpportunity",
        "contradictsStatement",
    ):
        if required not in deduction_locations:
            issues.append(f"No clue provides {required}.")

    support = deduction_locations.get("supportsSuspect", [])
    killer_support_locations = {
        index for index, suspect_id in support if suspect_id == killer_id
    }
    if len(killer_support_locations) < 2:
        issues.append(
            "The killer is not supported by two independent clue locations."
        )
    if any(suspect_id != killer_id for _, suspect_id in support):
        issues.append("A supportsSuspect deduction points to an innocent suspect.")

    contradiction_refs = {
        suspect_id
        for _, suspect_id in deduction_locations.get("contradictsStatement", [])
    }
    opportunity_refs = {
        suspect_id
        for _, suspect_id in deduction_locations.get("establishesOpportunity", [])
    }
    if killer_id not in contradiction_refs:
        issues.append("No contradiction deduction references the solution killer.")
    if killer_id not in opportunity_refs:
        issues.append("No opportunity deduction references the solution killer.")

    if killer is not None:
        killer_name = str(killer.get("name", ""))
        opportunity = str(solution.get("opportunity", ""))
        if killer_name.casefold() not in opportunity.casefold():
            issues.append("The opportunity explanation does not name the killer.")

    for path, text in _all_player_text(payload):
        lowered = text.casefold()
        if INTERNAL_RE.search(text):
            issues.append(f"{path} exposes an internal suspect key.")
        for phrase in WEAK_PHRASES:
            if phrase in lowered:
                issues.append(f"{path} uses weak reasoning phrase {phrase!r}.")

    return issues

