"""Compatibility tests for the current deterministic proof compiler.

This file replaces the removed CaseBlueprintAI/_compile_blueprint tests.
No Groq request is made.
"""

from app.models import (
    ClueKind,
    DeductionKind,
    Difficulty,
    NarrativeSeedAI,
    NarrativeSuspectAI,
    SuspectKey,
    SuspectReferenceKey
)
from app.planner import ProofStyle, build_case_plan, compile_case
from app.validation import (
    validate_core_truth,
    validate_evidence_board,
    validate_suspect_cast,
)


ROOM_OBJECTS = ["Desk", "Monitor", "Mug", "Lamp"]


def narrative() -> NarrativeSeedAI:
    return NarrativeSeedAI(
        title="The Quiet Account",
        setting_description=(
            "a book-lined private study prepared for an evening board meeting"
        ),
        victim_name="Alistair Wren",
        victim_role="the founder of a family investment firm",
        suspects=[
            NarrativeSuspectAI(
                key=SuspectKey.suspect_1,
                name="Mara Ellison",
                relationship_to_victim="his estranged daughter",
            ),
            NarrativeSuspectAI(
                key=SuspectKey.suspect_2,
                name="Leonard Pike",
                relationship_to_victim="his long-serving solicitor",
            ),
            NarrativeSuspectAI(
                key=SuspectKey.suspect_3,
                name="Iris Bell",
                relationship_to_victim="his chief financial officer",
            ),
        ],
        motive_detail=(
            "the victim was about to expose falsified company accounts that "
            "would have ended the killer's career"
        ),
    )


def compile_sample():
    plan = build_case_plan(
        ROOM_OBJECTS,
        Difficulty.standard,
        4172,
    )
    return compile_case(narrative(), plan)


def test_compiler_produces_a_valid_case() -> None:
    core, cast, board = compile_sample()

    assert validate_core_truth(core, ROOM_OBJECTS) == []
    assert validate_suspect_cast(cast, core, ROOM_OBJECTS) == []
    assert validate_evidence_board(board, core, cast, ROOM_OBJECTS) == []


def test_compiler_produces_exactly_one_red_herring() -> None:
    _, _, board = compile_sample()

    assert len(board.clues) == 5
    assert sum(
        clue.kind == ClueKind.red_herring
        for clue in board.clues
    ) == 1


def test_red_herring_contains_no_deductions() -> None:
    _, _, board = compile_sample()

    red_herring = next(
        clue
        for clue in board.clues
        if clue.kind == ClueKind.red_herring
    )

    assert red_herring.deductions == []


def test_killer_links_are_independent() -> None:
    _, _, board = compile_sample()

    opportunity_clue = next(
        clue
        for clue in board.clues
        if any(
            deduction.kind == DeductionKind.establishes_opportunity
            for deduction in clue.deductions
        )
    )
    supporting_clues = [
        clue
        for clue in board.clues
        if any(
            deduction.kind == DeductionKind.supports_suspect
            for deduction in clue.deductions
        )
    ]

    assert supporting_clues
    assert any(
        clue.room_object_index != opportunity_clue.room_object_index
        for clue in supporting_clues
    )

def test_seed_parity_selects_proof_style() -> None:
    even_plan = build_case_plan(
        ROOM_OBJECTS,
        Difficulty.standard,
        1002,
    )
    odd_plan = build_case_plan(
        ROOM_OBJECTS,
        Difficulty.standard,
        1001,
    )

    assert even_plan.proof_style == ProofStyle.shared_alibi
    assert odd_plan.proof_style == ProofStyle.split_corroboration

def test_split_corroboration_has_one_killer_clue() -> None:
    plan = build_case_plan(
        ROOM_OBJECTS,
        Difficulty.standard,
        1001,
    )
    core, cast, board = compile_case(narrative(), plan)

    innocent_keys = [
        suspect.key
        for suspect in cast.suspects
        if suspect.key != core.killer_key
    ]
    killer_ref = SuspectReferenceKey(core.killer_key.value)
    innocent_1_ref = SuspectReferenceKey(innocent_keys[0].value)
    innocent_2_ref = SuspectReferenceKey(innocent_keys[1].value)

    clue_2_pairs = {
        (deduction.kind, deduction.related_suspect_key)
        for deduction in board.clue_2.deductions
    }
    clue_3_pairs = {
        (deduction.kind, deduction.related_suspect_key)
        for deduction in board.clue_3.deductions
    }
    clue_4_pairs = {
        (deduction.kind, deduction.related_suspect_key)
        for deduction in board.clue_4.deductions
    }

    assert plan.proof_style == ProofStyle.split_corroboration
    assert clue_2_pairs == {
        (DeductionKind.establishes_timeline, SuspectReferenceKey.none),
        (DeductionKind.corroborates_alibi, innocent_1_ref),
    }
    assert clue_3_pairs == {
        (DeductionKind.contradicts_statement, killer_ref),
        (DeductionKind.establishes_opportunity, killer_ref),
        (DeductionKind.supports_suspect, killer_ref),
    }
    assert clue_4_pairs == {
        (DeductionKind.corroborates_alibi, innocent_2_ref),
    }