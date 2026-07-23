from __future__ import annotations

from textwrap import dedent

from app.models import (
    CoreTruthDraft,
    EvidenceBoardDraft,
    SuspectCastDraft,
)


def build_evidence_review_prompt(
    core_truth: CoreTruthDraft,
    suspect_cast: SuspectCastDraft,
    evidence_board: EvidenceBoardDraft,
    room_objects: list[str],
) -> str:
    """Legacy diagnostic prompt.

    Production generation no longer depends on an LLM reviewer. The deterministic
    validators and final payload auditor are authoritative. This prompt remains
    available for manual qualitative inspection only.
    """

    objects = "\n".join(
        f"{index}: {name}"
        for index, name in enumerate(room_objects)
    )

    return dedent(
        f"""
        You are a qualitative reviewer for a proof-carrying room mystery.
        Do not rewrite the case and do not invent evidence.

        ROOM OBJECTS:
        {objects}

        LOCKED CORE:
        {core_truth.model_dump_json()}

        LOCKED SUSPECTS:
        {suspect_cast.model_dump_json()}

        EVIDENCE BOARD:
        {evidence_board.model_dump_json()}

        Review only prose quality and physical readability. The Python compiler
        has already enforced the formal proof contract:

        1. Clue 1 visibly establishes the method.
        2. Clue 2 establishes a bounded event order and corroborates the two
           shared departure accounts without pretending that matching testimony
           alone creates physical impossibility.
        3. Clue 3 directly contradicts the killer on the murder object.
        4. Clue 4 independently links the same killer to a different room object
           during or immediately after the attack.
        5. Clue 5 is resolved by visible prior repair or age.
        6. No internal suspect keys, weak modal reasoning, CCTV, DNA,
           fingerprints, unnamed witnesses, or hidden external evidence appear.

        Flag awkward grammar, implausible object interaction, repetitive prose,
        or a player-facing statement that is difficult to understand. Use British
        English and return only the configured review schema.
        """
    ).strip()
