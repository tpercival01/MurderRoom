from uuid import uuid4

from app.models import (
    CoreTruthDraft,
    EvidenceBoardDraft,
    MysteryCasePayload,
    MysteryCluePayload,
    MysteryDeductionPayload,
    MysteryDraft,
    MysteryPersonPayload,
    MysterySolutionPayload,
    RoomObjectPayload,
    SolutionDraft,
    SuspectCastDraft,
    SuspectReferenceKey,
)


def assemble_mystery(
    core_truth: CoreTruthDraft,
    suspect_cast: SuspectCastDraft,
    evidence_board: EvidenceBoardDraft,
) -> MysteryDraft:
    return MysteryDraft(
        title=core_truth.title,
        opening_incident=core_truth.opening_incident,
        victim_name=core_truth.victim_name,
        suspects=suspect_cast.suspects,
        clues=evidence_board.clues,
        solution=SolutionDraft(
            killer_key=core_truth.killer_key,
            motive=core_truth.motive,
            method=core_truth.method,
            time_of_death=core_truth.time_of_death,
            opportunity=evidence_board.opportunity,
        ),
    )


def to_case_payload(
    mystery: MysteryDraft,
    room_object_names: list[str],
) -> MysteryCasePayload:
    room_objects = [
        RoomObjectPayload(
            id=uuid4(),
            name=name,
            isConfirmed=True,
        )
        for name in room_object_names
    ]

    suspect_ids = {
        suspect.key.value: uuid4()
        for suspect in mystery.suspects
    }

    suspects = [
        MysteryPersonPayload(
            id=suspect_ids[suspect.key.value],
            name=suspect.name,
            role="Suspect",
            relationshipToVictim=(
                suspect.relationship_to_victim
            ),
            statement=suspect.statement,
            alibiClaim=suspect.alibi_claim,
        )
        for suspect in mystery.suspects
    ]

    clues = []

    for clue in mystery.clues:
        deductions = []

        for deduction in clue.deductions:
            related_id = None

            if (
                deduction.related_suspect_key
                != SuspectReferenceKey.none
            ):
                related_id = suspect_ids[
                    deduction.related_suspect_key.value
                ]

            deductions.append(
                MysteryDeductionPayload(
                    kind=deduction.kind,
                    relatedSuspectID=related_id,
                )
            )

        clues.append(
            MysteryCluePayload(
                id=uuid4(),
                title=clue.title,
                detail=clue.detail,
                roomObjectID=room_objects[
                    clue.room_object_index
                ].id,
                kind=clue.kind,
                deductions=deductions,
            )
        )

    killer_id = suspect_ids[
        mystery.solution.killer_key.value
    ]

    return MysteryCasePayload(
        id=uuid4(),
        title=mystery.title,
        openingIncident=mystery.opening_incident,
        victim=MysteryPersonPayload(
            id=uuid4(),
            name=mystery.victim_name,
            role="Victim",
            relationshipToVictim="Victim",
            statement="",
            alibiClaim="",
        ),
        suspects=suspects,
        roomObjects=room_objects,
        clues=clues,
        solution=MysterySolutionPayload(
            killerID=killer_id,
            motive=mystery.solution.motive,
            method=mystery.solution.method,
            timeOfDeath=mystery.solution.time_of_death,
            opportunity=mystery.solution.opportunity,
        ),
    )
