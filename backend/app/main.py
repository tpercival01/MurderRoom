from fastapi import FastAPI, HTTPException

from app.assembly import to_case_payload
from app.config import get_settings
from app.generator import (
    MysteryGenerationError,
    generate_core_truth,
    generate_evidence_board,
    generate_mystery_draft,
    generate_suspect_cast,
)
from app.models import (
    CoreTruthDraft,
    EvidenceBoardDraft,
    GenerateEvidenceRequest,
    GenerateMysteryRequest,
    GenerateSuspectRequest,
    MysteryCasePayload,
    MysteryDraft,
    SuspectCastDraft,
)


app = FastAPI(
    title="Murder Room API",
    version="0.2.1",
)


def _raise_generation_error(
    error: MysteryGenerationError,
) -> None:
    raise HTTPException(
        status_code=502,
        detail=str(error),
    ) from error


@app.get("/health")
def health() -> dict[str, str]:
    settings = get_settings()

    return {
        "status": "ok",
        "model": settings.groq_model,
        "version": app.version,
    }


@app.post(
    "/generate-mystery",
    response_model=MysteryDraft,
)
def generate_mystery(
    request: GenerateMysteryRequest,
) -> MysteryDraft:
    try:
        return generate_mystery_draft(
            request.room_objects,
            request.difficulty,
        )
    except MysteryGenerationError as error:
        _raise_generation_error(error)


@app.post(
    "/generate-case",
    response_model=MysteryCasePayload,
)
def generate_case(
    request: GenerateMysteryRequest,
) -> MysteryCasePayload:
    mystery = generate_mystery(request)

    return to_case_payload(
        mystery,
        request.room_objects,
    )


@app.post(
    "/debug/generate-draft",
    response_model=MysteryDraft,
)
def generate_draft(
    request: GenerateMysteryRequest,
) -> MysteryDraft:
    return generate_mystery(request)


@app.post(
    "/debug/generate-core",
    response_model=CoreTruthDraft,
)
def generate_core(
    request: GenerateMysteryRequest,
) -> CoreTruthDraft:
    try:
        return generate_core_truth(
            request.room_objects,
            request.difficulty,
        )
    except MysteryGenerationError as error:
        _raise_generation_error(error)


@app.post(
    "/debug/generate-suspects",
    response_model=SuspectCastDraft,
)
def generate_suspects(
    request: GenerateSuspectRequest,
) -> SuspectCastDraft:
    try:
        return generate_suspect_cast(
            request.core_truth,
            request.room_objects,
            request.difficulty,
        )
    except MysteryGenerationError as error:
        _raise_generation_error(error)


@app.post(
    "/debug/generate-evidence",
    response_model=EvidenceBoardDraft,
)
def generate_evidence(
    request: GenerateEvidenceRequest,
) -> EvidenceBoardDraft:
    try:
        return generate_evidence_board(
            request.core_truth,
            request.suspect_cast,
            request.room_objects,
            request.difficulty,
        )
    except MysteryGenerationError as error:
        _raise_generation_error(error)
