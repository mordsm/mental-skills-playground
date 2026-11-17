from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth import require_actions_key
from app.schemas.mental_skills import (
    AudioInferenceRequest,
    BiofeedbackRoleplayTurnRequest,
    BiometricTelemetryRequest,
    CompleteSessionRequest,
    GuidedImageryCalibrationRequest,
    InterventionEvaluateRequest,
    RecordSessionEventRequest,
    SaveObservationRequest,
    SaveReflectionRequest,
    StartSessionRequest,
)
from app.services.biometric_engine import BiometricTrainingEngine
from app.services.mental_skills import MentalSkillsService


router = APIRouter(prefix="/api/msp", tags=["mental-skills"], dependencies=[Depends(require_actions_key)])


@router.get("/user/context", operation_id="getMentalSkillsUserContext")
def get_user_context(user_id: str = "moshe") -> dict:
    return MentalSkillsService().user_context(user_id)


@router.get("/user/profile", operation_id="getMentalSkillsUserProfile")
def get_user_profile(user_id: str = "moshe") -> dict:
    return MentalSkillsService().profile(user_id)


@router.get("/skills", operation_id="listMentalSkills")
def list_skills(user_id: str = "moshe") -> dict:
    return MentalSkillsService().list_skills(user_id)


@router.get("/skills/{skill_id}/history", operation_id="getMentalSkillHistory")
def get_skill_history(skill_id: str, user_id: str = "moshe", limit: int = 10) -> dict:
    return MentalSkillsService().skill_history(user_id, skill_id, limit=limit)


@router.get("/training/recommendation", operation_id="getMentalTrainingRecommendation")
def get_training_recommendation(user_id: str = "moshe") -> dict:
    return MentalSkillsService().recommendation(user_id)


@router.post("/sessions/start", operation_id="startMentalTrainingSession")
def start_session(request: StartSessionRequest) -> dict:
    return MentalSkillsService().start_session(request.model_dump(mode="json"))


@router.post("/sessions/{session_id}/event", operation_id="recordMentalTrainingSessionEvent")
def record_session_event(session_id: str, request: RecordSessionEventRequest) -> dict:
    return MentalSkillsService().record_event(session_id, request.model_dump(mode="json"))


@router.post("/sessions/{session_id}/complete", operation_id="completeMentalTrainingSession")
def complete_session(session_id: str, request: CompleteSessionRequest) -> dict:
    return MentalSkillsService().complete_session(session_id, request.model_dump(mode="json"))


@router.post("/observations", operation_id="saveMentalSkillsObservation")
def save_observation(request: SaveObservationRequest) -> dict:
    return MentalSkillsService().save_observation(request.model_dump(mode="json"))


@router.get("/patterns", operation_id="getMentalSkillsPatterns")
def get_patterns(user_id: str = "moshe") -> dict:
    return MentalSkillsService().patterns(user_id)


@router.post("/reflection", operation_id="saveMentalSkillsReflection")
def save_reflection(request: SaveReflectionRequest) -> dict:
    return MentalSkillsService().save_reflection(request.model_dump(mode="json"))


@router.get("/progress", operation_id="getMentalSkillsProgress")
def get_progress(user_id: str = "moshe") -> dict:
    return MentalSkillsService().progress(user_id)


# --- Architecture & Enhancement Plan Endpoints (Subsystems 1–4) ---


@router.get("/biometrics/overview", operation_id="getMentalSkillsBiometricOverview")
def get_biometric_overview(user_id: str = "moshe") -> dict:
    return BiometricTrainingEngine().architecture_telemetry_overview(user_id)


@router.get("/biometrics/baseline", operation_id="getMentalSkillsCircadianBaseline")
def get_circadian_baseline(
    user_id: str = "moshe",
    circadian_slot: str | None = None,
    sleep_deficit_hours: float = 0.0,
    recovery_score: float = 80.0,
) -> dict:
    return BiometricTrainingEngine().compute_rolling_7d_baseline(
        user_id=user_id,
        circadian_slot=circadian_slot,
        sleep_deficit_hours=sleep_deficit_hours,
        recovery_score=recovery_score,
    )


@router.post("/biometrics/telemetry", operation_id="ingestMentalSkillsBiometricTelemetry")
def ingest_biometric_telemetry(request: BiometricTelemetryRequest) -> dict:
    return BiometricTrainingEngine().ingest_biometric_telemetry(request.model_dump(mode="json"))


@router.post("/audio/infer", operation_id="inferMentalSkillsEdgeAudio")
def infer_edge_audio(request: AudioInferenceRequest) -> dict:
    return BiometricTrainingEngine().process_edge_gated_audio(request.model_dump(mode="json"))


@router.post("/interventions/evaluate", operation_id="evaluateMentalSkillsInterventionHierarchy")
def evaluate_intervention(request: InterventionEvaluateRequest) -> dict:
    return BiometricTrainingEngine().evaluate_intervention_hierarchy(request.model_dump(mode="json"))


@router.post("/biofeedback/roleplay/turn", operation_id="stepMentalSkillsBiofeedbackRoleplay")
def step_biofeedback_roleplay(request: BiofeedbackRoleplayTurnRequest) -> dict:
    return BiometricTrainingEngine().step_biofeedback_roleplay(request.model_dump(mode="json"))


@router.post("/biofeedback/imagery/calibrate", operation_id="calibrateMentalSkillsGuidedImageryRsa")
def calibrate_guided_imagery_rsa(request: GuidedImageryCalibrationRequest) -> dict:
    return BiometricTrainingEngine().calibrate_guided_imagery_rsa(request.model_dump(mode="json"))


