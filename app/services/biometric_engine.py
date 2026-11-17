from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Any

from app.database import db, init_db, json_dump, json_load, resource_id, utc_now


EXERTION_METS_THRESHOLD = 1.2
SYMPATHETIC_SURGE_HRV_DROP_PCT = 20.0
EARLY_DRIFT_HRV_DROP_PCT = 10.0
RESONANCE_FREQUENCY_HZ = 0.1
RESONANCE_BREATHS_PER_MIN = 6.0


DEFAULT_CIRCADIAN_BASELINES: dict[str, dict[str, float]] = {
    "morning": {"hr_p50": 68.0, "rmssd_p50": 46.0, "rmssd_p25": 38.0, "sdnn_p50": 54.0, "eda_p75": 2.4, "skin_temp_p50": 33.3},
    "afternoon": {"hr_p50": 72.0, "rmssd_p50": 42.0, "rmssd_p25": 35.0, "sdnn_p50": 50.0, "eda_p75": 2.6, "skin_temp_p50": 33.5},
    "evening": {"hr_p50": 70.0, "rmssd_p50": 44.0, "rmssd_p25": 36.0, "sdnn_p50": 52.0, "eda_p75": 2.3, "skin_temp_p50": 33.6},
    "night": {"hr_p50": 60.0, "rmssd_p50": 54.0, "rmssd_p25": 44.0, "sdnn_p50": 62.0, "eda_p75": 1.8, "skin_temp_p50": 33.8},
}


ROLEPLAY_SCENARIOS: dict[str, dict[str, Any]] = {
    "boundary_negotiation": {
        "scenario_id": "boundary_negotiation",
        "title_he": "משא ומתן על גבולות עבודה וזמן",
        "skill_id": "PAUSE",
        "prompts_by_aggression": {
            1: "אולי תוכל בכל זאת להכניס את המשימה הזו להיום? זה יעזור לנו מאוד.",
            2: "אני מבין שאתה עמוס, אבל כולם בצוות נותנים כתף עכשיו. למה זה מתעכב אצלך?",
            3: "תקשיב, זה לא מקובל שאתה דוחה את זה למחר. אנחנו צריכים תוצאה עכשיו בלי תירוצים!",
        },
    },
    "interpersonal_conflict": {
        "scenario_id": "interpersonal_conflict",
        "title_he": "עימות בין-אישי או ביקורת לא הוגנת",
        "skill_id": "AROUSAL_REGULATION",
        "prompts_by_aggression": {
            1: "נראה לי שפספסת כמה פרטים במסמך שהצגת קודם.",
            2: "שוב העלית הצעה שלא בדקת עד הסוף? חבל על הזמן של כולנו בחדר.",
            3: "זה פשוט לא רציני מה שהבאת כאן. איך אפשר לסמוך על הנתונים האלה בכלל?!",
        },
    },
    "unfair_criticism": {
        "scenario_id": "unfair_criticism",
        "title_he": "ביקורת לא הוגנת או עקיצה בישיבה",
        "skill_id": "AROUSAL_REGULATION",
        "prompts_by_aggression": {
            1: "נראה לי שפספסת כמה פרטים במסמך שהצגת קודם.",
            2: "שוב העלית הצעה שלא בדקת עד הסוף? חבל על הזמן של כולנו בחדר.",
            3: "זה פשוט לא רציני מה שהבאת כאן. איך אפשר לסמוך על הנתונים האלה בכלל?!",
        },
    },
    "social_friction": {
        "scenario_id": "social_friction",
        "title_he": "חיכוך חברתי או שינוי דרישות חד",
        "skill_id": "FRUSTRATION_TOLERANCE",
        "prompts_by_aggression": {
            1: "שינינו כיוון קל בדרישות הלקוח, נצטרך לעדכן את החלק הראשון.",
            2: "תמחק את מה שבנית בשעתיים האחרונות, החלטנו ללכת על ארכיטקטורה אחרת לגמרי.",
            3: "לא מעניין אותי כמה שעות השקעת בזה — הכל מבוטל ותגיש גרסה חדשה בעוד שעה!",
        },
    },
    "abrupt_pivot": {
        "scenario_id": "abrupt_pivot",
        "title_he": "שינוי דרישות חד באמצע ביצוע",
        "skill_id": "FRUSTRATION_TOLERANCE",
        "prompts_by_aggression": {
            1: "שינינו כיוון קל בדרישות הלקוח, נצטרך לעדכן את החלק הראשון.",
            2: "תמחק את מה שבנית בשעתיים האחרונות, החלטנו ללכת על ארכיטקטורה אחרת לגמרי.",
            3: "לא מעניין אותי כמה שעות השקעת בזה — הכל מבוטל ותגיש גרסה חדשה בעוד שעה!",
        },
    },
}


def resolve_circadian_slot(hour: int | None = None) -> str:
    if hour is None:
        hour = datetime.now(timezone.utc).hour
    if 6 <= hour < 12:
        return "morning"
    if 12 <= hour < 18:
        return "afternoon"
    if 18 <= hour < 23:
        return "evening"
    return "night"


def _percentile(sorted_vals: list[float], q: float) -> float:
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    pos = (len(sorted_vals) - 1) * q
    lower = int(math.floor(pos))
    upper = int(math.ceil(pos))
    if lower == upper:
        return sorted_vals[lower]
    weight = pos - lower
    return sorted_vals[lower] * (1.0 - weight) + sorted_vals[upper] * weight


class BiometricTrainingEngine:
    def __init__(self) -> None:
        # Ensure all 4 new SQLite tables exist even if server started before schema migration
        init_db()

    # ------------------------------------------------------------------
    # 1. Multimodal Sensor Fusion
    # ------------------------------------------------------------------
    def compute_rolling_7d_baseline(
        self,
        user_id: str,
        circadian_slot: str | None = None,
        sleep_deficit_hours: float = 0.0,
        recovery_score: float = 80.0,
    ) -> dict[str, Any]:
        slot = circadian_slot or resolve_circadian_slot()
        cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        with db() as conn:
            rows = conn.execute(
                """
                select hr_bpm, hrv_rmssd_ms, hrv_sdnn_ms, eda_microsiemens, skin_temp_c
                from msp_biometric_samples
                where user_id = ? and circadian_slot = ? and exertion_gated = 0 and recorded_at >= ?
                order by recorded_at desc
                limit 200
                """,
                (user_id, slot, cutoff),
            ).fetchall()

        defaults = DEFAULT_CIRCADIAN_BASELINES.get(slot, DEFAULT_CIRCADIAN_BASELINES["morning"])
        valid_rmssd_rows = [r for r in rows if float(r["hrv_rmssd_ms"]) >= 18.0]
        if len(valid_rmssd_rows) >= 3:
            rmssd_vals = sorted(float(r["hrv_rmssd_ms"]) for r in valid_rmssd_rows)
            hr_vals = sorted(float(r["hr_bpm"]) for r in valid_rmssd_rows)
            sdnn_vals = sorted(float(r["hrv_sdnn_ms"]) for r in valid_rmssd_rows)
            eda_vals = sorted(float(r["eda_microsiemens"]) for r in valid_rmssd_rows if r["eda_microsiemens"] is not None)
            raw_rmssd_p50 = _percentile(rmssd_vals, 0.50)
            raw_rmssd_p25 = _percentile(rmssd_vals, 0.25)
            raw_hr_p50 = _percentile(hr_vals, 0.50)
            raw_sdnn_p50 = _percentile(sdnn_vals, 0.50)
            raw_eda_p75 = _percentile(eda_vals, 0.75) if eda_vals else defaults["eda_p75"]
            window_source = "rolling_7d_percentiles"
        else:
            raw_rmssd_p50 = defaults["rmssd_p50"]
            raw_rmssd_p25 = defaults["rmssd_p25"]
            raw_hr_p50 = defaults["hr_p50"]
            raw_sdnn_p50 = defaults["sdnn_p50"]
            raw_eda_p75 = defaults["eda_p75"]
            window_source = "circadian_seed_plus_rolling_7d"

        sleep_factor = max(0.82, 1.0 - (0.025 * max(0.0, sleep_deficit_hours)))
        recovery_factor = 0.90 + (0.20 * (min(100.0, max(0.0, recovery_score)) / 100.0))
        combined_modifier = round(sleep_factor * recovery_factor, 3)

        adjusted_rmssd_baseline = round(raw_rmssd_p50 * combined_modifier, 2)
        adjusted_hr_baseline = round(raw_hr_p50 / combined_modifier, 2)

        return {
            "circadian_slot": slot,
            "window_source": window_source,
            "samples_in_7d_window": len(rows),
            "raw_rmssd_p50_ms": round(raw_rmssd_p50, 2),
            "raw_rmssd_p25_ms": round(raw_rmssd_p25, 2),
            "adjusted_rmssd_baseline_ms": adjusted_rmssd_baseline,
            "adjusted_hrv_rmssd_baseline_ms": adjusted_rmssd_baseline,
            "adjusted_hr_baseline_bpm": adjusted_hr_baseline,
            "sdnn_p50_ms": round(raw_sdnn_p50, 2),
            "eda_p75_microsiemens": round(raw_eda_p75, 2),
            "sleep_deficit_hours": sleep_deficit_hours,
            "recovery_score": recovery_score,
            "circadian_recovery_modifier": combined_modifier,
        }

    def ingest_biometric_telemetry(self, payload: dict[str, Any]) -> dict[str, Any]:
        user_id = payload.get("user_id", "moshe")
        hr_bpm = float(payload.get("hr_bpm", 72.0))
        hrv_rmssd_ms = float(payload.get("hrv_rmssd_ms", 42.0))
        hrv_sdnn_ms = float(payload.get("hrv_sdnn_ms", 50.0))
        ppg_sqi = float(payload.get("ppg_sqi", 0.92))
        skin_temp_c = float(payload.get("skin_temp_c", 33.4))
        eda_microsiemens = payload.get("eda_microsiemens")
        if eda_microsiemens is not None:
            eda_microsiemens = float(eda_microsiemens)

        ax = float(payload.get("accel_x_g", 0.02))
        ay = float(payload.get("accel_y_g", 0.03))
        az = float(payload.get("accel_z_g", 0.98))
        vector_mag = round(math.sqrt(ax * ax + ay * ay + az * az), 4)
        dynamic_g = abs(vector_mag - 1.0)

        explicit_mets = payload.get("estimated_mets")
        if explicit_mets is not None:
            estimated_mets = round(float(explicit_mets), 2)
        else:
            estimated_mets = round(1.0 + (dynamic_g * 4.5), 2)

        exertion_gated = estimated_mets > EXERTION_METS_THRESHOLD

        sleep_deficit = float(payload.get("sleep_deficit_hours", 0.5))
        recovery_score = float(payload.get("recovery_score", 78.0))
        slot = resolve_circadian_slot(payload.get("hour_of_day"))

        baseline = self.compute_rolling_7d_baseline(
            user_id=user_id,
            circadian_slot=slot,
            sleep_deficit_hours=sleep_deficit,
            recovery_score=recovery_score,
        )
        base_rmssd = baseline["adjusted_rmssd_baseline_ms"]
        base_hr = baseline["adjusted_hr_baseline_bpm"]
        base_eda = baseline["eda_p75_microsiemens"]

        hrv_drop_pct = round(max(0.0, ((base_rmssd - hrv_rmssd_ms) / max(1.0, base_rmssd)) * 100.0), 2)
        hr_elevation_bpm = round(hr_bpm - base_hr, 2)
        eda_elevated = (eda_microsiemens is not None) and (eda_microsiemens > base_eda)

        autonomic_arousal_elevated = (hr_elevation_bpm >= 6.0) or eda_elevated or (hrv_drop_pct >= 25.0)
        sympathetic_surge = (
            (not exertion_gated)
            and (ppg_sqi >= 0.5)
            and (hrv_drop_pct > SYMPATHETIC_SURGE_HRV_DROP_PCT)
            and autonomic_arousal_elevated
        )
        early_physiological_drift = (
            (not exertion_gated)
            and (not sympathetic_surge)
            and (ppg_sqi >= 0.5)
            and (hrv_drop_pct >= EARLY_DRIFT_HRV_DROP_PCT or eda_elevated)
        )

        if exertion_gated:
            arousal_state = "EXERTION_GATED_SUPPRESSED"
        elif sympathetic_surge:
            arousal_state = "ACUTE_SYMPATHETIC_SURGE"
        elif early_physiological_drift:
            arousal_state = "EARLY_PHYSIOLOGICAL_DRIFT"
        else:
            arousal_state = "HOMEOSTATIC_BASELINE"

        sample_id = resource_id("msp_bio")
        now = utc_now()
        telemetry_block = {
            "hr_bpm": hr_bpm,
            "hrv_rmssd_ms": hrv_rmssd_ms,
            "hrv_sdnn_ms": hrv_sdnn_ms,
            "ppg_sqi": ppg_sqi,
            "skin_temp_c": skin_temp_c,
            "eda_microsiemens": eda_microsiemens,
        }
        gate_block = {
            "accel_x_g": ax,
            "accel_y_g": ay,
            "accel_z_g": az,
            "vector_magnitude_g": vector_mag,
            "estimated_mets": estimated_mets,
            "mets_threshold": EXERTION_METS_THRESHOLD,
            "exertion_gated": exertion_gated,
            "false_positive_suppressed": exertion_gated,
            "suppression_reason": "physical_motion_exceeds_1.2_mets" if exertion_gated else None,
        }
        autonomic_block = {
            "hrv_drop_pct": hrv_drop_pct,
            "hr_elevation_bpm": hr_elevation_bpm,
            "eda_elevated": eda_elevated,
            "early_physiological_drift": early_physiological_drift,
            "sympathetic_surge": sympathetic_surge,
            "arousal_state": arousal_state,
            "edge_audio_ring_buffer_trigger": sympathetic_surge,
        }
        evaluation = {
            "sample_id": sample_id,
            "user_id": user_id,
            "recorded_at": now,
            "telemetry": telemetry_block,
            "biometrics": telemetry_block,
            "exertion_gate": gate_block,
            "motion_and_exertion_gate": gate_block,
            "circadian_baseline": baseline,
            "autonomic_evaluation": autonomic_block,
            "autonomic_assessment": autonomic_block,
            "edge_audio_ring_buffer_trigger": sympathetic_surge,
        }

        with db() as conn:
            conn.execute(
                """
                insert into msp_biometric_samples
                (sample_id, user_id, recorded_at, circadian_slot, hr_bpm, hrv_rmssd_ms, hrv_sdnn_ms,
                 ppg_sqi, skin_temp_c, eda_microsiemens, accel_x_g, accel_y_g, accel_z_g,
                 vector_magnitude_g, estimated_mets, sleep_deficit_hours, recovery_score,
                 exertion_gated, hrv_drop_pct, sympathetic_surge, arousal_state, evaluation_json)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sample_id,
                    user_id,
                    now,
                    slot,
                    hr_bpm,
                    hrv_rmssd_ms,
                    hrv_sdnn_ms,
                    ppg_sqi,
                    skin_temp_c,
                    eda_microsiemens,
                    ax,
                    ay,
                    az,
                    vector_mag,
                    estimated_mets,
                    sleep_deficit,
                    recovery_score,
                    1 if exertion_gated else 0,
                    hrv_drop_pct,
                    1 if sympathetic_surge else 0,
                    arousal_state,
                    json_dump(evaluation),
                ),
            )

        return {"success": True} | evaluation

    # ------------------------------------------------------------------
    # 2. Tiered Audio Inference & Privacy Protection
    # ------------------------------------------------------------------
    def process_edge_gated_audio(self, payload: dict[str, Any]) -> dict[str, Any]:
        user_id = payload.get("user_id", "moshe")
        sample_id = payload.get("sample_id")
        hrv_drop_pct = float(payload.get("hrv_drop_pct", 0.0))
        exertion_gated = bool(payload.get("exertion_gated", False))
        sympathetic_surge = bool(payload.get("sympathetic_surge_active", False))

        if sample_id:
            with db() as conn:
                row = conn.execute(
                    "select sympathetic_surge, exertion_gated, hrv_drop_pct from msp_biometric_samples where sample_id = ?",
                    (sample_id,),
                ).fetchone()
            if row:
                sympathetic_surge = bool(row["sympathetic_surge"])
                exertion_gated = bool(row["exertion_gated"])
                hrv_drop_pct = float(row["hrv_drop_pct"])

        gate_passed = (not exertion_gated) and (sympathetic_surge or hrv_drop_pct > SYMPATHETIC_SURGE_HRV_DROP_PCT)
        purge_ts = utc_now()

        if not gate_passed:
            return {
                "success": True,
                "ring_buffer_state": "DORMANT_LOCAL_RING_BUFFER",
                "sympathetic_gate_passed": False,
                "capture_activated": False,
                "affective_state": "DORMANT_GATE_CLOSED",
                "description_he": "המיקרופון במצב טבעת רדומה (לא זוהה זינוק סימפתטי חד מעל 20%).",
                "extracted_features": {"conversational_pause_detected": False},
                "reason": "Edge privacy gate blocked capture: no acute sympathetic surge (>20% HRV drop without physical exertion).",
                "privacy_guarantee": {
                    "continuous_recording": False,
                    "raw_audio_transmitted": False,
                    "raw_buffer_purged": True,
                    "raw_bytes_retained": 0,
                    "purge_timestamp_utc": purge_ts,
                },
            }

        requested_dur = float(payload.get("capture_window_seconds") or payload.get("capture_duration_seconds") or 6.0)
        capture_duration = min(10.0, max(5.0, requested_dur))

        simulated_buffer = bytearray(min(160000, max(1024, int(payload.get("raw_pcm_frame_count", 96000)))))
        pause_ratio_val = round(float(payload.get("pause_ratio", 0.22)), 3)
        features = {
            "jitter_pct": round(float(payload.get("jitter_pct", 0.8)), 3),
            "pitch_f0_hz": round(float(payload.get("pitch_f0_hz", 135.0)), 2),
            "pitch_variability_hz": round(float(payload.get("pitch_variability_hz", 18.0)), 2),
            "volume_db_envelope": round(float(payload.get("volume_db_envelope", -22.0)), 2),
            "speech_rate_wpm": round(float(payload.get("speech_rate_wpm", 130.0)), 1),
            "pause_ratio": pause_ratio_val,
            "conversational_pause_detected": bool(payload.get("conversational_pause_detected", pause_ratio_val >= 0.12)),
        }
        for i in range(len(simulated_buffer)):
            simulated_buffer[i] = 0
        del simulated_buffer

        vol = features["volume_db_envelope"]
        pitch_var = features["pitch_variability_hz"]
        wpm = features["speech_rate_wpm"]
        jitter = features["jitter_pct"]
        pause_ratio = features["pause_ratio"]

        if wpm < 30.0 or pause_ratio >= 0.80:
            affective_state = "SILENT_SOMATIC_AROUSAL"
            confidence = 0.86
            description_he = "עוררות סימפתטית גבוהה בשתיקה / קיפאון רגעי."
        elif vol <= -26.0 and pitch_var <= 22.0 and wpm <= 135.0:
            affective_state = "PASSIVE_WITHDRAWAL_INSULT_RESPONSE"
            confidence = 0.89
            description_he = "נסיגה פסיבית / תגובת פגיעה והשתבללות (עוצמת קול נמוכה ומנעד שטוח)."
        elif vol >= -16.0 or wpm >= 165.0 or (vol > -24.0 and (pitch_var >= 28.0 or jitter >= 1.8)):
            affective_state = "OUTWARD_VERBAL_ESCALATION"
            confidence = 0.91
            description_he = "הסלמה מילולית החוצה (עלייה בעוצמת הקול, תנודות גובה צליל וקצב דיבור מהיר)."
        else:
            affective_state = "REGULATED_CALM_SPEECH"
            confidence = 0.82
            description_he = "דיבור מווסת ויציב למרות העוררות הגופנית."

        inference_id = resource_id("msp_audio")
        purge_ts = utc_now()
        with db() as conn:
            conn.execute(
                """
                insert into msp_audio_inferences
                (inference_id, user_id, sample_id, occurred_at, capture_duration_seconds,
                 sympathetic_gate_passed, features_json, affective_state, confidence,
                 raw_buffer_purged, raw_bytes_retained, purge_timestamp_utc)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    inference_id,
                    user_id,
                    sample_id,
                    purge_ts,
                    capture_duration,
                    1,
                    json_dump(features),
                    affective_state,
                    confidence,
                    1,
                    0,
                    purge_ts,
                ),
            )

        return {
            "success": True,
            "inference_id": inference_id,
            "user_id": user_id,
            "sample_id": sample_id,
            "ring_buffer_state": "CAPTURED_EXTRACTED_AND_PURGED",
            "sympathetic_gate_passed": True,
            "capture_activated": True,
            "capture_duration_seconds": capture_duration,
            "extracted_features": features,
            "on_device_features": features,
            "affective_state": affective_state,
            "description_he": description_he,
            "confidence": confidence,
            "affective_classification": {
                "affective_state": affective_state,
                "confidence": confidence,
                "description_he": description_he,
            },
            "privacy_guarantee": {
                "continuous_recording": False,
                "raw_audio_transmitted": False,
                "raw_buffer_purged": True,
                "raw_bytes_retained": 0,
                "purge_timestamp_utc": purge_ts,
            },
        }

    # ------------------------------------------------------------------
    # 3. Real-Time Intervention Hierarchy
    # ------------------------------------------------------------------
    def evaluate_intervention_hierarchy(self, payload: dict[str, Any]) -> dict[str, Any]:
        user_id = payload.get("user_id", "moshe")
        sample_id = payload.get("sample_id")
        inference_id = payload.get("inference_id")
        hrv_drop_pct = float(payload.get("hrv_drop_pct", 0.0))
        exertion_gated = bool(payload.get("exertion_gated", False))
        sympathetic_surge = bool(payload.get("sympathetic_surge", False))
        affective_state = payload.get("affective_state", "REGULATED_CALM_SPEECH")
        conversational_pause = bool(payload.get("conversational_pause_detected", True))

        post_incident_sec = payload.get("post_incident_elapsed_seconds")
        minutes_post_incident = float(payload.get("minutes_post_incident", 0.0))
        if post_incident_sec is None and minutes_post_incident > 0:
            post_incident_sec = minutes_post_incident * 60.0

        hrv_recovering = bool(payload.get("hrv_recovering", False) or payload.get("autonomic_recovery_begun", False))

        if sample_id:
            with db() as conn:
                s_row = conn.execute(
                    "select hrv_drop_pct, exertion_gated, sympathetic_surge from msp_biometric_samples where sample_id = ?",
                    (sample_id,),
                ).fetchone()
            if s_row:
                hrv_drop_pct = float(s_row["hrv_drop_pct"])
                exertion_gated = bool(s_row["exertion_gated"])
                sympathetic_surge = bool(s_row["sympathetic_surge"])

        if inference_id:
            with db() as conn:
                a_row = conn.execute(
                    "select affective_state, features_json from msp_audio_inferences where inference_id = ?",
                    (inference_id,),
                ).fetchone()
            if a_row:
                affective_state = a_row["affective_state"]
                feats = json_load(a_row["features_json"], {})
                conversational_pause = bool(feats.get("conversational_pause_detected", True))

        if exertion_gated:
            return {
                "success": True,
                "intervention_triggered": False,
                "level": 0,
                "intervention_level": 0,
                "level_name": "SUPPRESSED_BY_EXERTION_GATE",
                "modality": "NONE",
                "haptic_pattern": None,
                "prompt_text_he": "סינון מאמץ גופני פעיל (>1.2 METs) — התראות דחק מושתקות.",
                "reason": "Physical exertion > 1.2 METs detected; stress interventions suppressed.",
            }

        # Level 3 — Post-Event Recovery & Debrief (3-5 minutes post-incident once autonomic recovery begins)
        if post_incident_sec is not None and float(post_incident_sec) >= 180.0 and hrv_recovering:
            level = 3
            level_name = "POST_EVENT_RECOVERY_DEBRIEF"
            modality = "structured_cognitive_checkin"
            haptic_pattern = None
            prompt_text_he = "המערכת האוטונומית שלך חוזרת לאיזון. בוא נבצע צ'ק-אין קוגניטיבי של 60 שניות."
            debrief_questions = [
                "מה היה הרגע שבו הרגשת את העוררות עולה?",
                "האם הצלחת ליצור רווח (Pause) לפני התגובה?",
                "מה תיקח מהאירוע הזה לפעם הבאה?",
            ]
            trigger_reason = f"Post-incident recovery window ({int(float(post_incident_sec))}s elapsed, autonomic baseline recovering)."
            action_payload = {
                "title_he": "רמה 3 — התאוששות ותחקור קצר לאחר האירוע",
                "prompt_he": prompt_text_he,
                "questions_he": debrief_questions,
                "target_skill_id": "PAUSE",
            }
        # Level 2 — Contextual Micro-Prompt (Audio/Visual)
        elif (sympathetic_surge or hrv_drop_pct > SYMPATHETIC_SURGE_HRV_DROP_PCT) and affective_state in {
            "OUTWARD_VERBAL_ESCALATION",
            "PASSIVE_WITHDRAWAL_INSULT_RESPONSE",
        }:
            level = 2
            level_name = "CONTEXTUAL_MICRO_PROMPT"
            modality = "minimalist_chip_and_earpiece_whisper"
            haptic_pattern = "single_soft_tap"
            debrief_questions = None
            trigger_reason = f"Sustained sympathetic arousal (HRV drop {hrv_drop_pct}%) with {affective_state}."
            if affective_state == "OUTWARD_VERBAL_ESCALATION":
                chip_he = "עצור 3 שניות · הנמך עוצמת קול ב-20%"
                audio_cue_he = "נשיפה איטית. דבר לאט ובטון נמוך."
                target_skill = "PAUSE"
            else:
                chip_he = "זקוף כתפיים · קול יציב וברור"
                audio_cue_he = "שמור על נוכחות. משפט אחד קצר וברור."
                target_skill = "AROUSAL_REGULATION"
            prompt_text_he = f"{chip_he} ({audio_cue_he})"
            action_payload = {
                "title_he": "רמה 2 — מיקרו-תזכורת הקשרית בזמן אמת",
                "screen_chip_he": chip_he,
                "earpiece_cue_he": audio_cue_he,
                "delivery_timing": "DELIVERED_NOW_IN_CONVERSATIONAL_PAUSE" if conversational_pause else "QUEUED_FOR_NEXT_CONVERSATIONAL_PAUSE",
                "conversational_pause_detected": conversational_pause,
                "target_skill_id": target_skill,
            }
        # Level 1 — Somatic Grounding (Micro-Haptics)
        elif hrv_drop_pct >= EARLY_DRIFT_HRV_DROP_PCT or sympathetic_surge:
            level = 1
            level_name = "SOMATIC_GROUNDING_MICRO_HAPTICS"
            modality = "smartwatch_micro_haptics"
            haptic_pattern = "subtle_double_pulse"
            debrief_questions = None
            prompt_text_he = "שחרר מתח בכתפיים / נשיפה איטית (רטט כפול עדין בשעון ללא היסח דעת)."
            trigger_reason = f"Early physiological drift detected (HRV drop {hrv_drop_pct}%)."
            action_payload = {
                "title_he": "רמה 1 — קרקוע סומטי (מיקרו-רטט בשעון)",
                "haptic_pattern": haptic_pattern,
                "pulse_intervals_ms": [120, 100, 120],
                "anchor_cue_he": "שחרר מתח בכתפיים / נשיפה איטית",
                "anchor_cue_en": "release tension / exhale",
                "visual_distraction": False,
                "cognitive_distraction": False,
                "target_skill_id": "AROUSAL_REGULATION",
            }
        else:
            return {
                "success": True,
                "intervention_triggered": False,
                "level": 0,
                "intervention_level": 0,
                "level_name": "NO_INTERVENTION_NEEDED",
                "modality": "NONE",
                "haptic_pattern": None,
                "prompt_text_he": "המדדים האוטונומיים בטווח הבסיס האישי — אין צורך בהתערבות.",
                "reason": "Autonomic state within personal circadian baseline.",
            }

        intervention_id = resource_id("msp_intv")
        now = utc_now()
        with db() as conn:
            conn.execute(
                """
                insert into msp_interventions
                (intervention_id, user_id, sample_id, inference_id, occurred_at,
                 level, level_name, modality, trigger_reason, action_payload_json)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    intervention_id,
                    user_id,
                    sample_id,
                    inference_id,
                    now,
                    level,
                    level_name,
                    modality,
                    trigger_reason,
                    json_dump(action_payload),
                ),
            )

        return {
            "success": True,
            "intervention_triggered": True,
            "intervention_id": intervention_id,
            "level": level,
            "intervention_level": level,
            "level_name": level_name,
            "modality": modality,
            "haptic_pattern": haptic_pattern,
            "zero_visual_cognitive_distraction": level == 1,
            "timed_for_conversational_pause": conversational_pause if level == 2 else False,
            "prompt_text_he": prompt_text_he,
            "debrief_questions": debrief_questions,
            "trigger_reason": trigger_reason,
            "action": action_payload,
        }

    # ------------------------------------------------------------------
    # 4. Closed-Loop Biofeedback Simulation & Guided Imagery
    # ------------------------------------------------------------------
    def step_biofeedback_roleplay(self, payload: dict[str, Any]) -> dict[str, Any]:
        user_id = payload.get("user_id", "moshe")
        scenario_id = payload.get("scenario_type") or payload.get("scenario_id") or "boundary_negotiation"
        scenario = ROLEPLAY_SCENARIOS.get(scenario_id, ROLEPLAY_SCENARIOS["boundary_negotiation"])
        hr_bpm = float(payload.get("hr_bpm", 76.0))
        hrv_rmssd_ms = float(payload.get("hrv_rmssd_ms", 38.0))
        eda_microsiemens = float(payload.get("eda_microsiemens", 2.4))
        hrv_drop_pct = float(payload.get("hrv_drop_pct", max(0.0, ((44.0 - hrv_rmssd_ms) / 44.0) * 100.0)))
        user_utterance = (payload.get("user_response") or payload.get("user_utterance") or "").strip()

        sim_id = payload.get("simulation_id")
        current_aggression = int(payload.get("current_difficulty") or 2)
        turns: list[dict[str, Any]] = []

        if sim_id:
            with db() as conn:
                row = conn.execute(
                    "select * from msp_biofeedback_simulations where simulation_id = ?",
                    (sim_id,),
                ).fetchone()
            if row:
                current_aggression = int(row["adversary_aggression_level"])
                turns = json_load(row["turns_json"], [])

        stability_score = round(
            max(
                0.0,
                min(
                    100.0,
                    (min(100.0, (hrv_rmssd_ms / 45.0) * 100.0) * 0.55)
                    + (max(0.0, 100.0 - max(0.0, hr_bpm - 65.0) * 2.2) * 0.45),
                ),
            ),
            1,
        )

        if hrv_drop_pct > 22.0 or hr_bpm > 98.0 or hrv_rmssd_ms < 24.0:
            new_aggression = max(1, current_aggression - 1)
            dda_state = "SCALED_DOWN_FOR_REGULATION"
            dda_explanation_he = "זוהתה הצפה אוטונומית חיה — רמת הלחץ של היריב הורדה אוטומטית (DDA) כדי לאפשר ייצוב נשימתי."
        elif hrv_drop_pct < 12.0 and hrv_rmssd_ms >= 36.0 and hr_bpm <= 84.0:
            new_aggression = min(3, current_aggression + 1)
            dda_state = "SCALED_UP_ON_STABILITY"
            dda_explanation_he = "שמרת על יציבות פיזיולוגית מרשימה (HRV יציב) — רמת האתגר והלחץ בתרחיש הועלתה (DDA) לחיזוק החוסן."
        else:
            new_aggression = current_aggression
            dda_state = "MAINTAINED_LEVEL"
            dda_explanation_he = "עוררות מתונה — רמת הקושי של התרחיש נשמרת יציבה."

        adversary_reply = scenario["prompts_by_aggression"].get(new_aggression, scenario["prompts_by_aggression"][2])
        now = utc_now()
        turn_entry = {
            "turn_index": len(turns) + 1,
            "occurred_at": now,
            "user_utterance": user_utterance,
            "biometrics": {
                "hr_bpm": hr_bpm,
                "hrv_rmssd_ms": hrv_rmssd_ms,
                "eda_microsiemens": eda_microsiemens,
                "hrv_drop_pct": hrv_drop_pct,
            },
            "dda_state": dda_state,
            "adversary_aggression_level": new_aggression,
            "adversary_response_he": adversary_reply,
        }
        turns.append(turn_entry)

        if not sim_id:
            sim_id = resource_id("msp_sim")
            with db() as conn:
                conn.execute(
                    """
                    insert into msp_biofeedback_simulations
                    (simulation_id, user_id, simulation_type, scenario_id, started_at, updated_at,
                     adversary_aggression_level, dda_state, rsa_target_hz, rsa_breaths_per_min,
                     time_to_equilibrium_seconds, autonomic_recovery_score, turns_json, status)
                    values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        sim_id,
                        user_id,
                        "BIOMETRIC_ROLEPLAY_DDA",
                        scenario["scenario_id"],
                        now,
                        now,
                        new_aggression,
                        dda_state,
                        RESONANCE_FREQUENCY_HZ,
                        RESONANCE_BREATHS_PER_MIN,
                        None,
                        None,
                        json_dump(turns),
                        "active",
                    ),
                )
        else:
            with db() as conn:
                conn.execute(
                    """
                    update msp_biofeedback_simulations
                    set updated_at = ?, adversary_aggression_level = ?, dda_state = ?, turns_json = ?
                    where simulation_id = ?
                    """,
                    (now, new_aggression, dda_state, json_dump(turns), sim_id),
                )

        return {
            "success": True,
            "simulation_id": sim_id,
            "scenario_id": scenario["scenario_id"],
            "scenario_title_he": scenario["title_he"],
            "skill_id": scenario["skill_id"],
            "previous_difficulty": current_aggression,
            "next_difficulty": new_aggression,
            "dda_transition": dda_state,
            "physiological_stability_score": stability_score,
            "adversary_prompt_he": adversary_reply,
            "adversary_response_he": adversary_reply,
            "coaching_feedback_he": dda_explanation_he,
            "dda": {
                "previous_aggression_level": current_aggression,
                "current_aggression_level": new_aggression,
                "dda_state": dda_state,
                "explanation_he": dda_explanation_he,
            },
            "turns_count": len(turns),
        }

    def calibrate_guided_imagery_rsa(self, payload: dict[str, Any]) -> dict[str, Any]:
        user_id = payload.get("user_id", "moshe")
        protocol_id = payload.get("protocol_id") or "rsa_4_6"
        initial_hr = float(payload.get("initial_hr_bpm", 92.0))
        initial_rmssd = float(payload.get("initial_hrv_rmssd_ms", 24.0))
        current_hr = float(payload.get("current_hr_bpm", 71.0))
        current_rmssd = float(payload.get("current_hrv_rmssd_ms", 44.0))
        elapsed_sec = float(payload.get("elapsed_seconds", 120.0))

        protocols_meta: dict[str, dict[str, Any]] = {
            "4_7_8": {
                "protocol_id": "4_7_8",
                "protocol_name_he": "נשימת 4-7-8 (ד\"ר אנדרו וייל)",
                "target_bpm": 3.16,
                "target_hz": 0.0526,
                "inhale_seconds": 4.0,
                "hold_seconds": 7.0,
                "exhale_seconds": 8.0,
                "hold_empty_seconds": 0.0,
                "guidance_he": (
                    "מחזור 4-7-8 (19 שניות למחזור, ~3.16 נשימות בדקה): "
                    "שאיפה שקטה דרך האף למשך 4 שניות ➔ החזקת אוויר בריאות מלאות ל-7 שניות (העלאת גירוי הוואגוס) "
                    "➔ נשיפה איטית וממושכת דרך הפה למשך 8 שניות שמשחררת מתח מהכתפיים והלסת."
                ),
            },
            "rsa_4_6": {
                "protocol_id": "rsa_4_6",
                "protocol_name_he": "תהודת לב-נשימה 0.1 Hz RSA (4/6)",
                "target_bpm": RESONANCE_BREATHS_PER_MIN,
                "target_hz": RESONANCE_FREQUENCY_HZ,
                "inhale_seconds": 4.0,
                "hold_seconds": 0.0,
                "exhale_seconds": 6.0,
                "hold_empty_seconds": 0.0,
                "guidance_he": (
                    "דמיין גל אור יציב הנע בקצב של 6 נשימות בדקה (0.1 Hz): "
                    "שאיפה שקטה דרך האף למשך 4 שניות... ונשיפה ארוכה ורכה למשך 6 שניות שמרפה את הכתפיים והלסת."
                ),
            },
            "box_4_4_4_4": {
                "protocol_id": "box_4_4_4_4",
                "protocol_name_he": "נשימת קופסה (Box Breathing 4-4-4-4)",
                "target_bpm": 3.75,
                "target_hz": 0.0625,
                "inhale_seconds": 4.0,
                "hold_seconds": 4.0,
                "exhale_seconds": 4.0,
                "hold_empty_seconds": 4.0,
                "guidance_he": (
                    "מחזור נשימת קופסה 4-4-4-4 (16 שניות למחזור, 3.75 נשימות בדקה): "
                    "שאיפה מהאף ל-4 שניות ➔ החזקת אוויר מלא ל-4 שניות ➔ נשיפה מבוקרת ל-4 שניות ➔ החזקת ריאות ריקות ל-4 שניות."
                ),
            },
            "sigh_3_1_6": {
                "protocol_id": "sigh_3_1_6",
                "protocol_name_he": "אנחה פיזיולוגית (Physiological Sigh 3-1-6)",
                "target_bpm": 6.0,
                "target_hz": 0.1,
                "inhale_seconds": 3.0,
                "hold_seconds": 1.0,
                "exhale_seconds": 6.0,
                "hold_empty_seconds": 0.0,
                "guidance_he": (
                    "מחזור אנחה פיזיולוגית 3-1-6 (10 שניות למחזור): "
                    "שאיפה כפולה מהאף (שאיפה מלאה + לגימת אוויר קצרה נוספת, 3 שניות) ➔ עצירה של שנייה ➔ נשיפה איטית וארוכה דרך הפה ל-6 שניות."
                ),
            },
        }
        pmeta = protocols_meta.get(protocol_id, protocols_meta["rsa_4_6"])
        target_bpm = float(pmeta["target_bpm"])
        target_hz = float(pmeta["target_hz"])
        resp_rate = float(payload.get("respiration_rate_bpm") or target_bpm)

        resp_hz = round(resp_rate / 60.0, 4)
        freq_deviation = abs(resp_rate - target_bpm)
        rsa_coherence_score = round(max(0.0, min(100.0, 100.0 - (freq_deviation * 14.0))), 1)

        hr_reduction = max(0.0, initial_hr - current_hr)
        rmssd_gain = max(0.0, current_rmssd - initial_rmssd)

        recovery_score = round(
            min(
                100.0,
                (0.45 * rsa_coherence_score)
                + (0.35 * min(100.0, (rmssd_gain / max(5.0, initial_rmssd * 0.5)) * 100.0))
                + (0.20 * min(100.0, (hr_reduction / 15.0) * 100.0)),
            ),
            1,
        )
        equilibrium_reached = (current_rmssd >= 38.0) and (current_hr <= 76.0) and (rsa_coherence_score >= 70.0)
        time_to_equilibrium_sec = round(elapsed_sec, 1) if equilibrium_reached else round(elapsed_sec * (100.0 / max(25.0, recovery_score)), 1)

        sim_id = payload.get("simulation_id") or resource_id("msp_rsa")
        now = utc_now()
        imagery_script_he = pmeta["guidance_he"]

        with db() as conn:
            conn.execute(
                """
                insert or replace into msp_biofeedback_simulations
                (simulation_id, user_id, simulation_type, scenario_id, started_at, updated_at,
                 adversary_aggression_level, dda_state, rsa_target_hz, rsa_breaths_per_min,
                 time_to_equilibrium_seconds, autonomic_recovery_score, turns_json, status)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sim_id,
                    user_id,
                    "RSA_GUIDED_IMAGERY",
                    pmeta["protocol_id"],
                    now,
                    now,
                    1,
                    "RESONANCE_PACING",
                    target_hz,
                    target_bpm,
                    time_to_equilibrium_sec,
                    recovery_score,
                    json_dump(
                        [
                            {
                                "protocol_id": pmeta["protocol_id"],
                                "initial_hr_bpm": initial_hr,
                                "current_hr_bpm": current_hr,
                                "initial_hrv_rmssd_ms": initial_rmssd,
                                "current_hrv_rmssd_ms": current_rmssd,
                                "respiration_rate_bpm": resp_rate,
                                "rsa_coherence_score": rsa_coherence_score,
                            }
                        ]
                    ),
                    "completed" if equilibrium_reached else "calibrating",
                ),
            )

        pacing_protocol = {
            "protocol_id": pmeta["protocol_id"],
            "protocol_name_he": pmeta["protocol_name_he"],
            "target_resonance_frequency_hz": target_hz,
            "target_frequency_hz": target_hz,
            "target_breaths_per_minute": target_bpm,
            "inhale_seconds": pmeta["inhale_seconds"],
            "hold_seconds": pmeta["hold_seconds"],
            "exhale_seconds": pmeta["exhale_seconds"],
            "hold_empty_seconds": pmeta["hold_empty_seconds"],
            "measured_frequency_hz": resp_hz,
            "measured_breaths_per_minute": resp_rate,
            "rsa_coherence_score": rsa_coherence_score,
            "guidance_he": imagery_script_he,
        }

        return {
            "success": True,
            "simulation_id": sim_id,
            "user_id": user_id,
            "rsa_coherence_score": rsa_coherence_score,
            "autonomic_recovery_score": recovery_score,
            "time_to_equilibrium_seconds": time_to_equilibrium_sec,
            "equilibrium_reached": equilibrium_reached,
            "pacing_protocol": pacing_protocol,
            "rsa_pacing": pacing_protocol,
            "autonomic_recovery": {
                "hr_reduction_bpm": round(hr_reduction, 1),
                "hrv_rmssd_gain_ms": round(rmssd_gain, 1),
                "equilibrium_reached": equilibrium_reached,
                "time_to_equilibrium_seconds": time_to_equilibrium_sec,
                "autonomic_recovery_score": recovery_score,
            },
            "guided_imagery_prompt_he": imagery_script_he,
        }

    def architecture_telemetry_overview(self, user_id: str = "moshe") -> dict[str, Any]:
        with db() as conn:
            samples = conn.execute(
                "select * from msp_biometric_samples where user_id = ? order by recorded_at desc limit 5",
                (user_id,),
            ).fetchall()
            inferences = conn.execute(
                "select * from msp_audio_inferences where user_id = ? order by occurred_at desc limit 5",
                (user_id,),
            ).fetchall()
            interventions = conn.execute(
                "select * from msp_interventions where user_id = ? order by occurred_at desc limit 5",
                (user_id,),
            ).fetchall()
            sims = conn.execute(
                "select * from msp_biofeedback_simulations where user_id = ? order by updated_at desc limit 5",
                (user_id,),
            ).fetchall()

        return {
            "success": True,
            "user_id": user_id,
            "circadian_baseline": self.compute_rolling_7d_baseline(user_id, resolve_circadian_slot()),
            "recent_biometric_samples": [dict(r) for r in samples],
            "recent_audio_inferences": [dict(r) for r in inferences],
            "recent_interventions": [
                dict(r) | {"action": json_load(r["action_payload_json"], {})} for r in interventions
            ],
            "recent_simulations": [dict(r) for r in sims],
            "available_roleplay_scenarios": list(ROLEPLAY_SCENARIOS.values()),
        }
