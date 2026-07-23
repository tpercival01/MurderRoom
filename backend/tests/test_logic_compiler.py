"""Compiler and validation tests. No Groq request is made."""

import os

os.environ.setdefault(
    "GROQ_API_KEY",
    "test-key",
)

from app.generator import (
    _compile_blueprint,
    _validate_compiled,
)
from app.models import (
    BlueprintSuspect,
    CaseBlueprintAI,
    ClueKind,
    DeductionKind,
    ObservableClueSeed,
    SuspectKey,
)


ROOMS = [
    "Desk",
    "Monitor",
    "Mug",
    "Lamp",
]


def seed(
    index: int,
    title: str,
    detail: str,
    inference: str,
) -> ObservableClueSeed:
    return ObservableClueSeed(
        room_object_index=index,
        title=title,
        observable_detail=detail,
        inference=inference,
    )


def valid_blueprint() -> CaseBlueprintAI:
    suspects = [
        BlueprintSuspect(
            key=SuspectKey.suspect_1,
            name="Emily Vale",
            relationship_to_victim="Colleague",
            statement=(
                "I remained beside the Desk, sorting the papers "
                "already spread across its surface."
            ),
            alibi_claim=(
                "The unchanged arrangement on the Desk supports "
                "where I said I stayed."
            ),
        ),
        BlueprintSuspect(
            key=SuspectKey.suspect_2,
            name="David Cross",
            relationship_to_victim="Project partner",
            statement=(
                "I repositioned the Lamp beside the victim before "
                "20:10, then stepped away and never looked behind "
                "the Monitor."
            ),
            alibi_claim=(
                "I handled the Lamp during the relevant window, "
                "but I never inspected the rear of the Monitor."
            ),
        ),
        BlueprintSuspect(
            key=SuspectKey.suspect_3,
            name="Sarah Wynn",
            relationship_to_victim="Friend",
            statement=(
                "I stayed with the Mug, turning its chipped handle "
                "away from the edge of the table."
            ),
            alibi_claim=(
                "The Mug remained where and how I said I left it."
            ),
        ),
    ]

    return CaseBlueprintAI(
        title="The Last Adjustment",
        opening_incident=(
            "During a late project review, Eleanor Vale is found "
            "unconscious beside the desk moments after a heavy impact "
            "is heard from inside the photographed room."
        ),
        victim_name="Eleanor Vale",
        killer_key=SuspectKey.suspect_2,
        motive=(
            "David feared Eleanor would expose his deliberate changes "
            "to the project accounts at the morning review."
        ),
        method=(
            "David swung the heavy Lamp into Eleanor's temple, causing "
            "the fatal head injury described in the case."
        ),
        time_of_death="between 20:10 and 20:20",
        suspects=suspects,
        method_clue=seed(
            3,
            "Dent in the Base",
            (
                "The Lamp has a fresh inward dent along the edge "
                "of its heavy base."
            ),
            (
                "The concentrated damage supports the Lamp being "
                "used for a forceful impact."
            ),
        ),
        opportunity_clue=seed(
            3,
            "Changed Position",
            (
                "The Lamp stands beside the victim rather than in "
                "the position described by the other two suspects."
            ),
            (
                "David's own statement places him handling and "
                "repositioning the Lamp during the relevant window."
            ),
        ),
        contradiction_clue=seed(
            1,
            "Cracked Rear Latch",
            (
                "A cracked latch is hidden behind the Monitor stand "
                "and cannot be seen from the front."
            ),
            (
                "David described that cracked rear latch despite "
                "claiming he never looked behind the Monitor."
            ),
        ),
        innocent_1_alibi_clue=seed(
            0,
            "Undisturbed Layout",
            (
                "The Desk papers remain in the exact overlapping "
                "arrangement Emily described."
            ),
            (
                "The unchanged Desk layout supports Emily's account "
                "of remaining there."
            ),
        ),
        innocent_2_alibi_clue=seed(
            2,
            "Turned Handle",
            (
                "The Mug's chipped handle faces inwards, away from "
                "the table edge."
            ),
            (
                "That Mug position supports Sarah's specific account "
                "of turning it."
            ),
        ),
        red_herring_clue=seed(
            0,
            "Dark Smear",
            (
                "A dark smear crosses one corner of the Desk near "
                "where the victim fell."
            ),
            (
                "Its shape looks like a hurried attempt to remove "
                "something from the scene."
            ),
        ),
        opportunity=(
            "David Cross admitted handling and repositioning the Lamp "
            "during the death window, giving him direct access to the "
            "same object supported as the murder method."
        ),
        killer_alibi_flaw=(
            "David denied looking behind the Monitor, but accurately "
            "described the cracked latch hidden behind its stand."
        ),
        red_herring_resolution=(
            "The dark Desk smear came from an old marker stain and "
            "did not result from the attack."
        ),
    )


def test_blueprint_compiles_to_valid_case() -> None:
    core, cast, board = _compile_blueprint(
        valid_blueprint(),
        ROOMS,
    )

    assert len(board.clues) == 5
    assert sum(
        clue.kind == ClueKind.red_herring
        for clue in board.clues
    ) == 1
    assert _validate_compiled(
        core,
        cast,
        board,
        ROOMS,
    ) == []


def test_compiler_does_not_launder_deductions() -> None:
    _, _, board = _compile_blueprint(
        valid_blueprint(),
        ROOMS,
    )

    kinds = {
        deduction.kind
        for clue in board.clues
        for deduction in clue.deductions
    }

    assert DeductionKind.eliminates_suspect not in kinds
    assert DeductionKind.supports_suspect not in kinds
    assert DeductionKind.establishes_timeline not in kinds


def test_red_herring_resolution_is_hidden() -> None:
    blueprint = valid_blueprint()
    _, _, board = _compile_blueprint(
        blueprint,
        ROOMS,
    )

    red_herring = next(
        clue
        for clue in board.clues
        if clue.kind == ClueKind.red_herring
    )

    assert (
        blueprint.red_herring_resolution
        not in red_herring.detail
    )


def test_contradiction_is_independent() -> None:
    _, _, board = _compile_blueprint(
        valid_blueprint(),
        ROOMS,
    )

    opportunity_clue = next(
        clue
        for clue in board.clues
        if any(
            deduction.kind
            == DeductionKind.establishes_opportunity
            for deduction in clue.deductions
        )
    )
    contradiction_clue = next(
        clue
        for clue in board.clues
        if any(
            deduction.kind
            == DeductionKind.contradicts_statement
            for deduction in clue.deductions
        )
    )

    assert opportunity_clue.id if hasattr(
        opportunity_clue,
        "id",
    ) else opportunity_clue is not contradiction_clue
    assert (
        opportunity_clue.room_object_index
        != contradiction_clue.room_object_index
    )
