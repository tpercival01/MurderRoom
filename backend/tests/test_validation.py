from __future__ import annotations

import unittest

from pydantic import ValidationError

from app.assembly import assemble_mystery, to_case_payload
from app.models import (
    Difficulty,
    EvidenceBoardDraft,
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


ROOM_OBJECTS = ["Desk", "Monitor", "Mug", "Lamp"]
SEED = 4172


def narrative() -> NarrativeSeedAI:
    """Return deterministic narrative metadata for compiler tests."""

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


def compile_valid_case():
    """Compile one known-valid case without making a Groq request."""

    plan = build_case_plan(
        ROOM_OBJECTS,
        Difficulty.standard,
        SEED,
    )
    core, cast, board = compile_case(narrative(), plan)
    return core, cast, board


class ValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.core, self.cast, self.board = compile_valid_case()

    def test_accepted_core_passes(self) -> None:
        self.assertEqual(
            validate_core_truth(
                self.core,
                ROOM_OBJECTS,
            ),
            [],
        )

    def test_accepted_cast_passes(self) -> None:
        self.assertEqual(
            validate_suspect_cast(
                self.cast,
                self.core,
                ROOM_OBJECTS,
            ),
            [],
        )

    def test_accepted_board_passes(self) -> None:
        self.assertEqual(
            validate_evidence_board(
                self.board,
                self.core,
                self.cast,
                ROOM_OBJECTS,
            ),
            [],
        )

    def test_mystery_assembles(self) -> None:
        mystery = assemble_mystery(
            self.core,
            self.cast,
            self.board,
        )

        self.assertEqual(len(mystery.suspects), 3)
        self.assertEqual(len(mystery.clues), 5)
        self.assertEqual(
            mystery.solution.killer_key,
            self.core.killer_key,
        )

    def test_case_payload_maps_ids(self) -> None:
        mystery = assemble_mystery(
            self.core,
            self.cast,
            self.board,
        )
        payload = to_case_payload(
            mystery,
            ROOM_OBJECTS,
        )

        self.assertEqual(len(payload.roomObjects), 4)
        self.assertEqual(len(payload.suspects), 3)
        self.assertEqual(len(payload.clues), 5)
        self.assertIn(
            payload.solution.killerID,
            {
                suspect.id
                for suspect in payload.suspects
            },
        )

    def test_timeline_requires_locked_details(self) -> None:
        data = self.board.model_dump(mode="python")
        data["clue_2"]["detail"] = (
            "The object shows activity after the victim was last seen, "
            "but provides no usable death-window details."
        )
        board = EvidenceBoardDraft.model_validate(data)

        issues = validate_evidence_board(
            board,
            self.core,
            self.cast,
            ROOM_OBJECTS,
        )

        self.assertTrue(issues)

    def test_opportunity_must_preserve_locked_evidence(self) -> None:
        data = self.board.model_dump(mode="python")
        data["clue_3"]["detail"] = (
            "The object appears slightly displaced from its usual position."
        )
        board = EvidenceBoardDraft.model_validate(data)

        issues = validate_evidence_board(
            board,
            self.core,
            self.cast,
            ROOM_OBJECTS,
        )

        self.assertTrue(issues)

    def test_innocent_suspects_use_non_method_objects(self) -> None:
        innocent_suspects = [
            suspect
            for suspect in self.cast.suspects
            if suspect.key != self.core.killer_key
        ]

        self.assertEqual(len(innocent_suspects), 2)

        for suspect in innocent_suspects:
            self.assertNotEqual(
                suspect.alibi_room_object_index,
                self.core.primary_room_object_index,
            )

    def test_red_herring_cannot_gain_a_deduction(self) -> None:
        data = self.board.model_dump(mode="python")
        data["clue_5"]["deductions"] = [
            data["clue_1"]["deductions"][0]
        ]

        with self.assertRaises(ValidationError):
            EvidenceBoardDraft.model_validate(data)


if __name__ == "__main__":
    unittest.main()
