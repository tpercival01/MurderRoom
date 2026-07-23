from __future__ import annotations

import json

import pytest

from app.assembly import assemble_mystery, to_case_payload
from app.models import (
    ClueKind,
    DeductionKind,
    Difficulty,
    NarrativeSeedAI,
    NarrativeSuspectAI,
    SuspectKey,
)
from app.planner import build_case_plan, compile_case
from app.validation import (
    validate_core_truth,
    validate_evidence_board,
    validate_suspect_cast,
)


ROOMS = ["cup", "lamp", "book", "chair"]


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


def compile_sample(seed: int = 4172):
    plan = build_case_plan(ROOMS, Difficulty.standard, seed)
    core, cast, board = compile_case(narrative(), plan)
    return plan, core, cast, board


def test_sample_room_has_strong_affordance_plan() -> None:
    plan, _, _, _ = compile_sample()
    assert ROOMS[plan.method_index] == "lamp"
    assert ROOMS[plan.timeline_index] == "chair"
    assert ROOMS[plan.identity_index] == "book"
    assert ROOMS[plan.red_herring_index] == "cup"


def test_compiled_case_passes_all_semantic_validators() -> None:
    _, core, cast, board = compile_sample()
    assert validate_core_truth(core, ROOMS) == []
    assert validate_suspect_cast(cast, core, ROOMS) == []
    assert validate_evidence_board(board, core, cast, ROOMS) == []


def test_case_has_exact_proof_contract() -> None:
    _, core, cast, board = compile_sample()
    killer = core.killer_key
    innocent_keys = {suspect.key for suspect in cast.suspects if suspect.key != killer}

    assert len(board.clues) == 5
    assert [clue.kind for clue in board.clues] == [
        ClueKind.evidence,
        ClueKind.evidence,
        ClueKind.evidence,
        ClueKind.evidence,
        ClueKind.red_herring,
    ]
    assert {clue.room_object_index for clue in board.clues} == {0, 1, 2, 3}

    support_clues = []
    corroborated = set()
    for index, clue in enumerate(board.clues):
        for deduction in clue.deductions:
            if deduction.kind == DeductionKind.supports_suspect:
                support_clues.append((index, deduction.related_suspect_key.value))
            if deduction.kind == DeductionKind.corroborates_alibi:
                corroborated.add(deduction.related_suspect_key.value)

    assert support_clues == [(2, killer.value), (3, killer.value)]
    assert corroborated == {key.value for key in innocent_keys}


def test_output_contains_no_internal_suspect_keys_or_weak_reasoning() -> None:
    _, core, cast, board = compile_sample()
    mystery = assemble_mystery(core, cast, board)
    payload = to_case_payload(mystery, ROOMS)
    encoded = payload.model_dump_json().casefold()

    for forbidden in (
        "suspect_1",
        "suspect_2",
        "suspect_3",
        "may have",
        "possibly",
        "just a coincidence",
        "likely caused by",
    ):
        assert forbidden not in encoded


def test_two_killer_links_are_independent_and_specific() -> None:
    plan, core, cast, board = compile_sample()
    killer_name = next(
        suspect.name for suspect in cast.suspects if suspect.key == core.killer_key
    )

    assert board.clue_3.room_object_index == plan.method_index
    assert board.clue_4.room_object_index == plan.identity_index
    assert board.clue_3.room_object_index != board.clue_4.room_object_index
    assert killer_name in board.clue_3.detail
    assert killer_name in board.clue_4.detail
    assert core.killer_denial not in board.clue_3.detail
    assert ROOMS[plan.method_index] in board.opportunity
    assert ROOMS[plan.identity_index] in board.opportunity


def test_red_herring_is_observable_but_does_not_reveal_resolution() -> None:
    _, _, _, board = compile_sample()
    detail = board.clue_5.detail.casefold()
    assert board.clue_5.kind == ClueKind.red_herring
    assert board.clue_5.deductions == []
    assert any(word in detail for word in ("glue", "tape", "varnish", "film", "stitch"))
    for forbidden in (
        "earlier repair",
        "older repair",
        "predates the attack",
        "before the attack",
        "unrelated to the murder",
        "irrelevant",
    ):
        assert forbidden not in detail


@pytest.mark.parametrize(
    "objects",
    [
        ["knife", "curtain", "desk", "mirror"],
        ["pillow", "clock", "notebook", "table"],
        ["bottle", "sofa", "painting", "cabinet"],
        ["plant pot", "television", "rug", "shelf"],
    ],
)
def test_planner_compiles_other_common_room_combinations(objects: list[str]) -> None:
    plan = build_case_plan(objects, Difficulty.brutal, 9917)
    core, cast, board = compile_case(narrative(), plan)
    assert validate_core_truth(core, objects) == []
    assert validate_suspect_cast(cast, core, objects) == []
    assert validate_evidence_board(board, core, cast, objects) == []
    assert {clue.room_object_index for clue in board.clues} == {0, 1, 2, 3}


def test_final_uuid_payload_passes_external_auditor() -> None:
    from app.payload_audit import audit_payload

    _, core, cast, board = compile_sample()
    payload = to_case_payload(assemble_mystery(core, cast, board), ROOMS)
    assert audit_payload(payload.model_dump(mode="json")) == []


def test_full_generation_pipeline_with_stubbed_groq(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import generator
    from app.config import get_settings
    from app.payload_audit import audit_payload

    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    get_settings.cache_clear()
    monkeypatch.setattr(
        generator,
        "call_structured_model",
        lambda prompt, model_class, max_tokens: narrative(),
    )

    mystery = generator.generate_mystery_draft(
        ROOMS,
        Difficulty.standard,
        4172,
    )
    payload = to_case_payload(mystery, ROOMS)
    assert audit_payload(payload.model_dump(mode="json")) == []
    assert mystery.solution.killer_key == SuspectKey.suspect_3

    get_settings.cache_clear()


def test_player_clues_present_observations_not_solved_deductions() -> None:
    _, _, _, board = compile_sample()
    encoded = " ".join(clue.detail for clue in board.clues).casefold()
    for forbidden in (
        "this directly contradicts",
        "this independently places",
        "the attack therefore",
        "therefore had the only",
    ):
        assert forbidden not in encoded


def test_motive_and_opening_are_compiler_sanitised() -> None:
    seeded = narrative().model_copy(
        update={
            "setting_description": (
                "A book-lined private study prepared for an evening board meeting"
            ),
            "motive_detail": (
                "because the victim was about to expose falsified company accounts"
            ),
        }
    )
    # Direct compilation defensively sanitises even if provider validation
    # should normally reject the leading word.
    plan = build_case_plan(ROOMS, Difficulty.standard, 4172)
    core, _, _ = compile_case(
        seeded.model_copy(
            update={
                "motive_detail": (
                    "the victim was about to expose falsified company accounts"
                )
            }
        ),
        plan,
    )
    assert "because because" not in core.motive.casefold()
    assert " found dead in A " not in core.opening_incident


def test_generic_narrative_title_is_rejected() -> None:
    from app.planner import narrative_seed_issues

    seeded = narrative().model_copy(
        update={"title": "The Mysterious Office Death"}
    )
    assert "The title is generic. Create a specific, evocative title." in (
        narrative_seed_issues(seeded)
    )
