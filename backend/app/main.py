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
from app.planner import build_case_plan
from app.payload_audit import audit_payload


app = FastAPI(
    title="Murder Room API",
    version="0.4.0",
)


def _raise_generation_error(error: MysteryGenerationError) -> None:
    status_code = error.status_code or 502
    headers = None

    if error.retry_after_seconds is not None:
        headers = {
            "Retry-After": str(error.retry_after_seconds),
        }

    raise HTTPException(
        status_code=status_code,
        detail=str(error),
        headers=headers,
    ) from error


@app.get("/health")
def health() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "ok",
        "model": settings.groq_model,
        "version": app.version,
        "architecture": "proof-carrying-compiler",
    }


@app.post("/generate-mystery", response_model=MysteryDraft)
def generate_mystery(request: GenerateMysteryRequest) -> MysteryDraft:
    try:
        return generate_mystery_draft(
            request.room_objects,
            request.difficulty,
            request.seed,
        )
    except MysteryGenerationError as error:
        _raise_generation_error(error)


@app.post("/generate-case", response_model=MysteryCasePayload)
def generate_case(request: GenerateMysteryRequest) -> MysteryCasePayload:
    mystery = generate_mystery(request)
    payload = to_case_payload(mystery, request.room_objects)
    issues = audit_payload(payload.model_dump(mode="json"))
    if issues:
        _raise_generation_error(
            MysteryGenerationError(
                "Final payload audit failed: " + "; ".join(issues[:20])
            )
        )
    return payload


@app.post("/debug/plan")
def debug_plan(request: GenerateMysteryRequest) -> dict[str, object]:
    plan = build_case_plan(
        request.room_objects,
        request.difficulty,
        request.seed,
    )
    return {
        "seed": plan.seed,
        "killerKey": plan.killer_key.value,
        "methodStyle": plan.method_style.value,
        "methodObject": request.room_objects[plan.method_index],
        "timelineObject": request.room_objects[plan.timeline_index],
        "identityObject": request.room_objects[plan.identity_index],
        "redHerringObject": request.room_objects[plan.red_herring_index],
        "departureTime": plan.departure_time,
        "discoveryTime": plan.discovery_time,
    }


@app.post("/debug/generate-draft", response_model=MysteryDraft)
def generate_draft(request: GenerateMysteryRequest) -> MysteryDraft:
    return generate_mystery(request)


@app.post("/debug/generate-core", response_model=CoreTruthDraft)
def generate_core(request: GenerateMysteryRequest) -> CoreTruthDraft:
    try:
        return generate_core_truth(
            request.room_objects,
            request.difficulty,
            request.seed,
        )
    except MysteryGenerationError as error:
        _raise_generation_error(error)


@app.post("/debug/generate-suspects", response_model=SuspectCastDraft)
def generate_suspects(request: GenerateSuspectRequest) -> SuspectCastDraft:
    try:
        return generate_suspect_cast(
            request.core_truth,
            request.room_objects,
            request.difficulty,
            request.seed,
        )
    except MysteryGenerationError as error:
        _raise_generation_error(error)


@app.post("/debug/generate-evidence", response_model=EvidenceBoardDraft)
def generate_evidence(request: GenerateEvidenceRequest) -> EvidenceBoardDraft:
    try:
        return generate_evidence_board(
            request.core_truth,
            request.suspect_cast,
            request.room_objects,
            request.difficulty,
            request.seed,
        )
    except MysteryGenerationError as error:
        _raise_generation_error(error)
