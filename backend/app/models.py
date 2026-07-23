from __future__ import annotations

from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _clean_room_objects(values: list[str]) -> list[str]:
    cleaned = [" ".join(value.strip().split()) for value in values]

    if len(cleaned) != 4:
        raise ValueError("Exactly four room objects are required.")
    if any(not value for value in cleaned):
        raise ValueError("All four room objects must have names.")
    if len({value.casefold() for value in cleaned}) != 4:
        raise ValueError("Room objects must be distinct.")

    return cleaned


class Difficulty(str, Enum):
    easy = "easy"
    standard = "standard"
    brutal = "brutal"


class SuspectKey(str, Enum):
    suspect_1 = "suspect_1"
    suspect_2 = "suspect_2"
    suspect_3 = "suspect_3"


class SuspectReferenceKey(str, Enum):
    none = "none"
    suspect_1 = "suspect_1"
    suspect_2 = "suspect_2"
    suspect_3 = "suspect_3"


class ClueKind(str, Enum):
    evidence = "evidence"
    red_herring = "redHerring"


class DeductionKind(str, Enum):
    eliminates_suspect = "eliminatesSuspect"
    supports_suspect = "supportsSuspect"
    corroborates_alibi = "corroboratesAlibi"
    establishes_method = "establishesMethod"
    establishes_timeline = "establishesTimeline"
    establishes_opportunity = "establishesOpportunity"
    contradicts_statement = "contradictsStatement"


# MARK: - Requests


class GenerateMysteryRequest(StrictModel):
    room_objects: list[str] = Field(min_length=4, max_length=4)
    difficulty: Difficulty = Difficulty.standard
    seed: Optional[int] = Field(default=None, ge=0, le=2_147_483_647)

    _validate_objects = field_validator("room_objects")(_clean_room_objects)


class GenerateSuspectRequest(StrictModel):
    room_objects: list[str]
    core_truth: "CoreTruthDraft"
    difficulty: Difficulty = Difficulty.standard
    seed: Optional[int] = Field(default=None, ge=0, le=2_147_483_647)

    _validate_objects = field_validator("room_objects")(_clean_room_objects)


class GenerateEvidenceRequest(StrictModel):
    room_objects: list[str]
    core_truth: "CoreTruthDraft"
    suspect_cast: "SuspectCastDraft"
    difficulty: Difficulty = Difficulty.standard
    seed: Optional[int] = Field(default=None, ge=0, le=2_147_483_647)

    _validate_objects = field_validator("room_objects")(_clean_room_objects)


# MARK: - Groq narrative seed


class NarrativeSuspectAI(StrictModel):
    key: SuspectKey
    name: str = Field(min_length=4, max_length=60)
    relationship_to_victim: str = Field(min_length=4, max_length=120)


class NarrativeSeedAI(StrictModel):
    """Creative metadata produced by Groq.

    No logical claim is generated here. Python owns the chronology, statements,
    alibis, evidence, deductions, murderer references, and final solution graph.
    """

    title: str = Field(min_length=5, max_length=100)
    setting_description: str = Field(min_length=20, max_length=260)
    victim_name: str = Field(min_length=4, max_length=60)
    victim_role: str = Field(min_length=4, max_length=100)
    suspects: list[NarrativeSuspectAI]
    motive_detail: str = Field(min_length=20, max_length=280)

    @field_validator("suspects")
    @classmethod
    def validate_suspects(
        cls,
        values: list[NarrativeSuspectAI],
    ) -> list[NarrativeSuspectAI]:
        if len(values) != 3:
            raise ValueError("Exactly three suspects are required.")
        if {value.key for value in values} != set(SuspectKey):
            raise ValueError("Each suspect key must appear exactly once.")
        names = {value.name.casefold().strip() for value in values}
        if len(names) != 3:
            raise ValueError("Suspect names must be distinct.")
        return values

    @model_validator(mode="after")
    def validate_distinct_people(self) -> "NarrativeSeedAI":
        suspect_names = {item.name.casefold().strip() for item in self.suspects}
        if self.victim_name.casefold().strip() in suspect_names:
            raise ValueError("The victim name must differ from every suspect name.")
        return self


# MARK: - Internal compiled mystery


class CoreTruthDraft(StrictModel):
    title: str
    opening_incident: str
    victim_name: str

    killer_key: SuspectKey
    motive: str
    method: str
    method_evidence: str
    time_of_death: str

    killer_denial: str
    hidden_detail: str
    killer_revealed_detail: str

    killer_alibi: str
    killer_alibi_flaw: str

    primary_room_object_index: int = Field(ge=0, le=3)
    contradiction_room_object_index: int = Field(ge=0, le=3)


class SuspectDraft(StrictModel):
    key: SuspectKey
    name: str
    relationship_to_victim: str
    statement: str
    alibi_claim: str
    alibi_room_object_index: int = Field(ge=0, le=3)
    alibi_evidence_fact: str


class SuspectCastDraft(StrictModel):
    suspects: list[SuspectDraft]

    @field_validator("suspects")
    @classmethod
    def validate_suspects(
        cls,
        values: list[SuspectDraft],
    ) -> list[SuspectDraft]:
        if len(values) != 3:
            raise ValueError("A mystery must contain exactly three suspects.")
        if {suspect.key for suspect in values} != set(SuspectKey):
            raise ValueError("Each suspect key must appear exactly once.")
        return values


class DeductionDraft(StrictModel):
    kind: DeductionKind
    related_suspect_key: SuspectReferenceKey

    @model_validator(mode="after")
    def validate_reference_kind(self) -> "DeductionDraft":
        no_suspect_kinds = {
            DeductionKind.establishes_method,
            DeductionKind.establishes_timeline,
        }
        if (
            self.kind in no_suspect_kinds
            and self.related_suspect_key != SuspectReferenceKey.none
        ):
            raise ValueError(
                f"{self.kind.value} must use related_suspect_key 'none'."
            )
        if (
            self.kind not in no_suspect_kinds
            and self.related_suspect_key == SuspectReferenceKey.none
        ):
            raise ValueError(f"{self.kind.value} must identify a suspect.")
        return self


class ClueDraft(StrictModel):
    title: str
    detail: str
    room_object_index: int = Field(ge=0, le=3)
    kind: ClueKind
    deductions: list[DeductionDraft]

    @model_validator(mode="after")
    def validate_clue(self) -> "ClueDraft":
        if len(self.deductions) > 5:
            raise ValueError("A clue may contain at most five deductions.")
        if self.kind == ClueKind.red_herring and self.deductions:
            raise ValueError("A red herring must have no deductions.")
        if self.kind == ClueKind.evidence and not self.deductions:
            raise ValueError("An evidence clue must contain a deduction.")
        return self


class EvidenceBoardDraft(StrictModel):
    opportunity: str
    clue_1: ClueDraft
    clue_2: ClueDraft
    clue_3: ClueDraft
    clue_4: ClueDraft
    clue_5: ClueDraft

    @property
    def clues(self) -> list[ClueDraft]:
        return [self.clue_1, self.clue_2, self.clue_3, self.clue_4, self.clue_5]

    @model_validator(mode="after")
    def validate_evidence_board(self) -> "EvidenceBoardDraft":
        if sum(clue.kind == ClueKind.red_herring for clue in self.clues) != 1:
            raise ValueError("A mystery must contain exactly one red herring.")
        if {clue.room_object_index for clue in self.clues} != {0, 1, 2, 3}:
            raise ValueError("Every room object must be used by at least one clue.")
        return self


class EvidenceBoardReview(StrictModel):
    passes: bool
    innocent_alibis_are_fairly_corroborated: bool
    killer_alibi_is_directly_contradicted: bool
    timeline_is_actually_established: bool
    method_is_supported_by_observable_evidence: bool
    opportunity_is_specific_and_supported: bool
    deduction_labels_are_supported: bool
    evidence_is_physically_plausible: bool
    no_important_facts_are_invented: bool
    red_herring_is_fair: bool
    issues: list[str]


class SolutionDraft(StrictModel):
    killer_key: SuspectKey
    motive: str
    method: str
    time_of_death: str
    opportunity: str


class MysteryDraft(StrictModel):
    title: str
    opening_incident: str
    victim_name: str
    suspects: list[SuspectDraft]
    clues: list[ClueDraft]
    solution: SolutionDraft

    @field_validator("suspects")
    @classmethod
    def validate_suspect_count(cls, values: list[SuspectDraft]) -> list[SuspectDraft]:
        if len(values) != 3:
            raise ValueError("A mystery must contain exactly three suspects.")
        return values

    @field_validator("clues")
    @classmethod
    def validate_clue_count(cls, values: list[ClueDraft]) -> list[ClueDraft]:
        if len(values) != 5:
            raise ValueError("A mystery must contain exactly five clues.")
        return values


# MARK: - iPhone-facing payloads


class MysteryPersonPayload(StrictModel):
    id: UUID
    name: str
    role: str
    relationshipToVictim: str
    statement: str
    alibiClaim: str


class RoomObjectPayload(StrictModel):
    id: UUID
    name: str
    isConfirmed: bool


class MysteryDeductionPayload(StrictModel):
    kind: DeductionKind
    relatedSuspectID: Optional[UUID]


class MysteryCluePayload(StrictModel):
    id: UUID
    title: str
    detail: str
    roomObjectID: UUID
    kind: ClueKind
    deductions: list[MysteryDeductionPayload]


class MysterySolutionPayload(StrictModel):
    killerID: UUID
    motive: str
    method: str
    timeOfDeath: str
    opportunity: str


class MysteryCasePayload(StrictModel):
    id: UUID
    title: str
    openingIncident: str
    victim: MysteryPersonPayload
    suspects: list[MysteryPersonPayload]
    roomObjects: list[RoomObjectPayload]
    clues: list[MysteryCluePayload]
    solution: MysterySolutionPayload
