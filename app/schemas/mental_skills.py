from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


MspMode = Literal["TRAINING_MODE", "FIELD_MODE"]
MspEventType = Literal[
    "baseline_response",
    "reflection",
    "micro_skill",
    "retest_response",
    "debrief",
    "user_stop",
    "cooldown",
]


class StartSessionRequest(BaseModel):
    idempotency_key: str
    user_id: str = "moshe"
    skill_id: str
    exercise_id: str | None = None
    mode: MspMode = "TRAINING_MODE"
    difficulty: int = Field(default=1, ge=1, le=2)


class RecordSessionEventRequest(BaseModel):
    idempotency_key: str
    event_type: MspEventType
    occurred_at: datetime
    payload: dict[str, Any] = Field(default_factory=dict)


class CompleteSessionRequest(BaseModel):
    idempotency_key: str
    summary: str
    user_noticed_change: bool = False
    safety_state: str = "ok"


class SaveObservationRequest(BaseModel):
    idempotency_key: str
    user_id: str = "moshe"
    content: str
    skill_id: str | None = None
    occurred_at: datetime | None = None
    source: str = "gpt"
    tags: list[str] = Field(default_factory=list)


class SaveReflectionRequest(BaseModel):
    idempotency_key: str
    user_id: str = "moshe"
    content: str
    session_id: str | None = None
    skill_id: str | None = None
    insight_tags: list[str] = Field(default_factory=list)


class BiometricTelemetryRequest(BaseModel):
    user_id: str = "moshe"
    hr_bpm: float = Field(default=72.0, ge=30.0, le=220.0)
    hrv_rmssd_ms: float = Field(default=42.0, ge=5.0, le=250.0)
    hrv_sdnn_ms: float = Field(default=50.0, ge=5.0, le=300.0)
    ppg_sqi: float = Field(default=0.92, ge=0.0, le=1.0, description="Photoplethysmography signal quality index")
    skin_temp_c: float = Field(default=33.4, ge=25.0, le=42.0)
    eda_microsiemens: float | None = Field(default=1.8, ge=0.0, le=50.0)
    accel_x_g: float = Field(default=0.02)
    accel_y_g: float = Field(default=0.03)
    accel_z_g: float = Field(default=0.98)
    estimated_mets: float | None = Field(default=None, ge=0.8, le=20.0)
    sleep_deficit_hours: float = Field(default=0.5, ge=0.0, le=24.0)
    recovery_score: float = Field(default=78.0, ge=0.0, le=100.0)
    hour_of_day: int | None = Field(default=None, ge=0, le=23)


class AudioInferenceRequest(BaseModel):
    user_id: str = "moshe"
    sample_id: str | None = None
    sympathetic_surge_active: bool = False
    hrv_drop_pct: float = 0.0
    exertion_gated: bool = False
    capture_duration_seconds: float = Field(default=6.0, ge=1.0, le=15.0)
    capture_window_seconds: float | None = Field(default=None, ge=1.0, le=15.0)
    raw_pcm_frame_count: int = Field(default=96000, ge=0, description="Simulated in-memory ring-buffer frames to purge immediately")
    jitter_pct: float = Field(default=0.8, ge=0.0, le=15.0)
    pitch_f0_hz: float = Field(default=135.0, ge=50.0, le=500.0)
    pitch_variability_hz: float = Field(default=18.0, ge=0.0, le=150.0)
    volume_db_envelope: float = Field(default=-22.0, ge=-80.0, le=0.0)
    speech_rate_wpm: float = Field(default=130.0, ge=0.0, le=320.0)
    pause_ratio: float = Field(default=0.22, ge=0.0, le=1.0)
    conversational_pause_detected: bool = True


class InterventionEvaluateRequest(BaseModel):
    user_id: str = "moshe"
    sample_id: str | None = None
    inference_id: str | None = None
    hrv_drop_pct: float = 0.0
    exertion_gated: bool = False
    sympathetic_surge: bool = False
    sustained_arousal_seconds: float = 0.0
    affective_state: str = "REGULATED_CALM_SPEECH"
    conversational_pause_detected: bool = True
    post_incident_elapsed_seconds: float | None = None
    minutes_post_incident: float = 0.0
    hrv_recovering: bool = False
    autonomic_recovery_begun: bool = False


class BiofeedbackRoleplayTurnRequest(BaseModel):
    user_id: str = "moshe"
    simulation_id: str | None = None
    scenario_id: str = "boundary_negotiation"
    scenario_type: str | None = None
    current_difficulty: int | None = None
    user_utterance: str = ""
    user_response: str | None = None
    hr_bpm: float = 76.0
    hrv_rmssd_ms: float = 38.0
    eda_microsiemens: float = 2.4
    hrv_drop_pct: float = 12.0
    affective_state: str = "REGULATED_CALM_SPEECH"


class GuidedImageryCalibrationRequest(BaseModel):
    user_id: str = "moshe"
    simulation_id: str | None = None
    protocol_id: str | None = Field(default=None, description="Selected breathing protocol: 4_7_8, rsa_4_6, box_4_4_4_4, sigh_3_1_6")
    initial_hr_bpm: float = 92.0
    initial_hrv_rmssd_ms: float = 24.0
    current_hr_bpm: float = 71.0
    current_hrv_rmssd_ms: float = 44.0
    respiration_rate_bpm: float = Field(default=6.0, ge=2.0, le=30.0, description="Target breaths/min for protocol")
    elapsed_seconds: float = Field(default=120.0, ge=1.0, le=3600.0)

