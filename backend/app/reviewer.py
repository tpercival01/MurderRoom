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
    objects = "\n".join(
        f"{index}: {name}"
        for index, name in enumerate(room_objects)
    )

    return dedent(
        f"""
        You are the final adversarial logic reviewer for a
        room-based deduction game.

        ROOM OBJECTS:
        {objects}

        LOCKED CORE:
        {core_truth.model_dump_json()}

        LOCKED SUSPECTS:
        {suspect_cast.model_dump_json()}

        EVIDENCE BOARD:
        {evidence_board.model_dump_json()}

        Pass only when all of these are true:

        1. Each innocent has a clue that fairly corroborates one
           specific locked detail. It need not prove physical
           impossibility.
        2. The killer's exact locked alibi is directly contradicted.
        3. The timeline clue genuinely supports the stated death
           time or window. Presence alone is not a death time.
        4. Method evidence is observable and supports the exact
           locked method without laboratory assumptions.
        5. Opportunity explicitly connects the killer's revealed
           knowledge of the locked hidden detail to physical reach of
           the primary murder object. The contradiction object and
           primary object must both be named. Do not accept invented
           duties, access, ownership or rooms.
        6. Every deduction label says no more than its clue proves.
        7. No timestamps are inferred from stains, temperature,
           dust, scratches or condensation.
        8. No CCTV, recordings, fingerprints, DNA, microscopic
           analysis, hidden external evidence or unnamed witnesses.
        9. The red herring is plausible and does not call itself
           irrelevant.
        10. The combined clues leave the locked killer as the single
            fair answer.

        Use British English. Return only the review schema.
        """
    ).strip()
