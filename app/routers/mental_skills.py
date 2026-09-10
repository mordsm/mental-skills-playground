from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth import require_actions_key
from app.schemas.mental_skills import (
    CompleteSessionRequest,
    RecordSessionEventRequest,
    SaveObservationRequest,
    SaveReflectionRequest,
    StartSessionRequest,
)
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

