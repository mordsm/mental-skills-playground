from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_subsystem_1_multimodal_sensor_fusion_and_exertion_gate() -> None:
    # 1. Acute sympathetic surge at rest (< 1.2 METs) triggers surge & edge audio ring-buffer
    surge_resp = client.post(
        "/api/msp/biometrics/telemetry",
        json={
            "user_id": "test_user_arch",
            "hr_bpm": 98.0,
            "hrv_rmssd_ms": 27.0,
            "hrv_sdnn_ms": 33.0,
            "ppg_sqi": 0.94,
            "skin_temp_c": 32.8,
            "eda_microsiemens": 6.2,
            "accel_x_g": 0.01,
            "accel_y_g": 0.02,
            "accel_z_g": 1.00,
            "sleep_deficit_hours": 1.0,
            "recovery_score": 78.0,
        },
    )
    assert surge_resp.status_code == 200
    surge_data = surge_resp.json()
    assert surge_data["exertion_gate"]["exertion_gated"] is False
    assert surge_data["exertion_gate"]["estimated_mets"] <= 1.2
    assert surge_data["autonomic_evaluation"]["hrv_drop_pct"] > 20.0
    assert surge_data["autonomic_evaluation"]["sympathetic_surge"] is True
    assert surge_data["edge_audio_ring_buffer_trigger"] is True

    # 2. Physical exertion (> 1.2 METs) suppresses stress alerts (False-Positive Suppression)
    exertion_resp = client.post(
        "/api/msp/biometrics/telemetry",
        json={
            "user_id": "test_user_arch",
            "hr_bpm": 124.0,
            "hrv_rmssd_ms": 24.0,
            "hrv_sdnn_ms": 29.0,
            "ppg_sqi": 0.89,
            "skin_temp_c": 34.2,
            "eda_microsiemens": 7.5,
            "accel_x_g": 0.40,
            "accel_y_g": 0.32,
            "accel_z_g": 1.20,
        },
    )
    assert exertion_resp.status_code == 200
    exertion_data = exertion_resp.json()
    assert exertion_data["exertion_gate"]["estimated_mets"] > 1.2
    assert exertion_data["exertion_gate"]["exertion_gated"] is True
    assert exertion_data["autonomic_evaluation"]["sympathetic_surge"] is False
    assert exertion_data["edge_audio_ring_buffer_trigger"] is False


def test_subsystem_2_edge_gated_audio_and_privacy_protection() -> None:
    # 1. Without sympathetic surge (>20% HRV drop), microphone stays in dormant ring-buffer
    dormant_resp = client.post(
        "/api/msp/audio/infer",
        json={
            "user_id": "test_user_arch",
            "sympathetic_surge_active": False,
            "hrv_drop_pct": 8.0,
            "exertion_gated": False,
            "capture_window_seconds": 6.0,
        },
    )
    assert dormant_resp.status_code == 200
    dormant = dormant_resp.json()
    assert dormant["capture_activated"] is False
    assert dormant["ring_buffer_state"] == "DORMANT_LOCAL_RING_BUFFER"
    assert dormant["privacy_guarantee"]["raw_buffer_purged"] is True
    assert dormant["privacy_guarantee"]["raw_bytes_retained"] == 0

    # 2. Passive withdrawal / insult response (low volume + flattened F0 variability)
    withdrawal_resp = client.post(
        "/api/msp/audio/infer",
        json={
            "user_id": "test_user_arch",
            "sympathetic_surge_active": True,
            "hrv_drop_pct": 26.0,
            "exertion_gated": False,
            "capture_window_seconds": 6.5,
            "jitter_pct": 1.35,
            "pitch_f0_hz": 120.0,
            "pitch_variability_hz": 7.0,
            "volume_db_envelope": -32.0,
            "speech_rate_wpm": 85.0,
            "pause_ratio": 0.50,
        },
    )
    assert withdrawal_resp.status_code == 200
    withdrawal = withdrawal_resp.json()
    assert withdrawal["capture_activated"] is True
    assert withdrawal["affective_state"] == "PASSIVE_WITHDRAWAL_INSULT_RESPONSE"
    assert withdrawal["privacy_guarantee"]["raw_buffer_purged"] is True
    assert withdrawal["privacy_guarantee"]["raw_bytes_retained"] == 0

    # 3. Outward verbal escalation (loud volume + high pitch variability / fast rate)
    escalation_resp = client.post(
        "/api/msp/audio/infer",
        json={
            "user_id": "test_user_arch",
            "sympathetic_surge_active": True,
            "hrv_drop_pct": 31.0,
            "exertion_gated": False,
            "capture_window_seconds": 8.0,
            "jitter_pct": 2.4,
            "pitch_f0_hz": 218.0,
            "pitch_variability_hz": 45.0,
            "volume_db_envelope": -11.0,
            "speech_rate_wpm": 180.0,
            "pause_ratio": 0.15,
        },
    )
    assert escalation_resp.status_code == 200
    escalation = escalation_resp.json()
    assert escalation["capture_activated"] is True
    assert escalation["affective_state"] == "OUTWARD_VERBAL_ESCALATION"
    assert escalation["privacy_guarantee"]["raw_buffer_purged"] is True


def test_subsystem_3_realtime_intervention_hierarchy() -> None:
    # Level 1 — Somatic Grounding (Micro-Haptics) on early physiological drift
    l1_resp = client.post(
        "/api/msp/interventions/evaluate",
        json={
            "user_id": "test_user_arch",
            "hrv_drop_pct": 15.0,
            "sympathetic_surge": False,
            "sustained_arousal_seconds": 8.0,
            "exertion_gated": False,
        },
    )
    assert l1_resp.status_code == 200
    l1 = l1_resp.json()
    assert l1["intervention_level"] == 1
    assert l1["level_name"] == "SOMATIC_GROUNDING_MICRO_HAPTICS"
    assert l1["haptic_pattern"] == "subtle_double_pulse"
    assert l1["zero_visual_cognitive_distraction"] is True

    # Level 2 — Contextual Micro-Prompt timed during conversational pauses
    l2_resp = client.post(
        "/api/msp/interventions/evaluate",
        json={
            "user_id": "test_user_arch",
            "hrv_drop_pct": 28.0,
            "sympathetic_surge": True,
            "sustained_arousal_seconds": 35.0,
            "exertion_gated": False,
            "affective_state": "OUTWARD_VERBAL_ESCALATION",
            "conversational_pause_detected": True,
        },
    )
    assert l2_resp.status_code == 200
    l2 = l2_resp.json()
    assert l2["intervention_level"] == 2
    assert l2["level_name"] == "CONTEXTUAL_MICRO_PROMPT"
    assert l2["timed_for_conversational_pause"] is True

    # Level 3 — Post-Event Recovery & Debrief (3–5 minutes post-incident)
    l3_resp = client.post(
        "/api/msp/interventions/evaluate",
        json={
            "user_id": "test_user_arch",
            "hrv_drop_pct": 9.0,
            "sympathetic_surge": False,
            "minutes_post_incident": 4.0,
            "autonomic_recovery_begun": True,
        },
    )
    assert l3_resp.status_code == 200
    l3 = l3_resp.json()
    assert l3["intervention_level"] == 3
    assert l3["level_name"] == "POST_EVENT_RECOVERY_DEBRIEF"
    assert len(l3["debrief_questions"]) == 3


def test_subsystem_4_closed_loop_biofeedback_dda_and_rsa_imagery() -> None:
    # 1. High physiological stability scales DDA difficulty up
    up_resp = client.post(
        "/api/msp/biofeedback/roleplay/turn",
        json={
            "user_id": "test_user_arch",
            "scenario_type": "boundary_negotiation",
            "current_difficulty": 1,
            "user_response": "אני מבין את הצורך, אך אוכל להתחייב ליום שלישי.",
            "hr_bpm": 68.0,
            "hrv_rmssd_ms": 48.0,
            "eda_microsiemens": 1.8,
            "affective_state": "REGULATED_CALM_SPEECH",
        },
    )
    assert up_resp.status_code == 200
    up_data = up_resp.json()
    assert up_data["next_difficulty"] == 2
    assert up_data["dda_transition"] == "SCALED_UP_ON_STABILITY"

    # 2. Acute autonomic overload scales DDA difficulty down
    down_resp = client.post(
        "/api/msp/biofeedback/roleplay/turn",
        json={
            "user_id": "test_user_arch",
            "scenario_type": "interpersonal_conflict",
            "current_difficulty": 3,
            "user_response": "עזוב, אני לא יכול לדבר על זה עכשיו.",
            "hr_bpm": 108.0,
            "hrv_rmssd_ms": 20.0,
            "eda_microsiemens": 7.8,
            "affective_state": "PASSIVE_WITHDRAWAL_INSULT_RESPONSE",
        },
    )
    assert down_resp.status_code == 200
    down_data = down_resp.json()
    assert down_data["next_difficulty"] == 2
    assert down_data["dda_transition"] == "SCALED_DOWN_FOR_REGULATION"

    # 3. 0.1 Hz (6 breaths/min) RSA Guided Imagery calibration
    rsa_resp = client.post(
        "/api/msp/biofeedback/imagery/calibrate",
        json={
            "user_id": "test_user_arch",
            "initial_hr_bpm": 95.0,
            "current_hr_bpm": 70.0,
            "initial_hrv_rmssd_ms": 26.0,
            "current_hrv_rmssd_ms": 45.0,
            "respiration_rate_bpm": 6.0,
            "elapsed_seconds": 120.0,
        },
    )
    assert rsa_resp.status_code == 200
    rsa_data = rsa_resp.json()
    assert rsa_data["pacing_protocol"]["target_resonance_frequency_hz"] == 0.1
    assert rsa_data["pacing_protocol"]["target_breaths_per_minute"] == 6.0
    assert rsa_data["rsa_coherence_score"] == 100.0
    assert rsa_data["autonomic_recovery_score"] >= 80.0
    assert rsa_data["equilibrium_reached"] is True
