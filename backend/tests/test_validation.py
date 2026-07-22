import json
import unittest
from pathlib import Path

from app.assembly import assemble_mystery, to_case_payload
from app.models import (
    CoreTruthDraft,
    EvidenceBoardDraft,
    SuspectCastDraft,
)
from app.validation import (
    validate_core_truth,
    validate_evidence_board,
    validate_suspect_cast,
)


FIXTURES = Path(__file__).parent / "fixtures"
ROOM_OBJECTS = ["Desk", "Monitor", "Mug", "Lamp"]


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


class ValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.core = CoreTruthDraft.model_validate(
            load("accepted_core_truth_01.json")
        )
        self.cast = SuspectCastDraft.model_validate(
            load("accepted_suspect_cast_01.json")
        )
        self.board = EvidenceBoardDraft.model_validate(
            load("accepted_evidence_board_01.json")
        )

    def test_accepted_core_passes(self) -> None:
        self.assertEqual(
            validate_core_truth(self.core, ROOM_OBJECTS),
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
            mystery.solution.killer_key.value,
            "suspect_2",
        )

    def test_case_payload_maps_ids(self) -> None:
        mystery = assemble_mystery(
            self.core,
            self.cast,
            self.board,
        )
        payload = to_case_payload(mystery, ROOM_OBJECTS)

        self.assertEqual(len(payload.roomObjects), 4)
        self.assertEqual(len(payload.suspects), 3)
        self.assertEqual(len(payload.clues), 5)
        self.assertIn(
            payload.solution.killerID,
            {suspect.id for suspect in payload.suspects},
        )

    def test_historical_bad_board_is_rejected(self) -> None:
        bad_board = EvidenceBoardDraft.model_validate(
            load("rejected_evidence_board_01.json")
        )

        issues = validate_evidence_board(
            bad_board,
            self.core,
            self.cast,
            ROOM_OBJECTS,
        )

        self.assertTrue(issues)


    def test_timeline_requires_every_locked_time(self) -> None:
        data = load("accepted_evidence_board_01.json")
        data["clue_2"]["detail"] = (
            "The monitor shows a local account edit after the victim "
            "was last seen, but gives no usable death-window times."
        )
        board = EvidenceBoardDraft.model_validate(data)

        issues = validate_evidence_board(
            board,
            self.core,
            self.cast,
            ROOM_OBJECTS,
        )

        self.assertTrue(
            any("every locked death time" in issue for issue in issues)
        )

    def test_opportunity_must_bridge_both_objects(self) -> None:
        data = load("accepted_evidence_board_01.json")
        data["clue_3"]["detail"] = (
            "The lamp sits outside its clean dust outline, and its "
            "cord has been pulled into a tightened loop."
        )
        board = EvidenceBoardDraft.model_validate(data)

        issues = validate_evidence_board(
            board,
            self.core,
            self.cast,
            ROOM_OBJECTS,
        )

        self.assertTrue(
            any(
                "killer alibi room object" in issue
                or "locked killer flaw" in issue
                for issue in issues
            )
        )

    def test_suspect_alibi_objects_cover_non_murder_objects(self) -> None:
        data = load("accepted_suspect_cast_01.json")
        data["suspects"][0]["alibi_room_object_index"] = 1
        cast = SuspectCastDraft.model_validate(data)

        issues = validate_suspect_cast(
            cast,
            self.core,
            ROOM_OBJECTS,
        )

        self.assertTrue(
            any("different alibi room object" in issue for issue in issues)
        )


if __name__ == "__main__":
    unittest.main()
