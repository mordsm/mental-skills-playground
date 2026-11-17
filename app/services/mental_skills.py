from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.database import db, json_dump, json_load, resource_id, utc_now


MVP_SKILLS: list[dict[str, Any]] = [
    {
        "skill_id": "PAUSE",
        "display_name": "Pause",
        "description": "Create space between stimulus and response.",
        "default_min_difficulty": 1,
        "default_max_difficulty": 2,
    },
    {
        "skill_id": "FRUSTRATION_TOLERANCE",
        "display_name": "Frustration tolerance",
        "description": "Stay stable when something does not work, is delayed, or goes wrong.",
        "default_min_difficulty": 1,
        "default_max_difficulty": 2,
    },
    {
        "skill_id": "AROUSAL_REGULATION",
        "display_name": "Arousal regulation",
        "description": "Notice and reduce physical or emotional activation.",
        "default_min_difficulty": 1,
        "default_max_difficulty": 2,
    },
]

MVP_EXERCISES: list[dict[str, Any]] = [
    {
        "exercise_id": "pause_wait_three_seconds",
        "skill_id": "PAUSE",
        "mode": "TRAINING_MODE",
        "challenge_type": "waiting",
        "min_difficulty": 1,
        "max_difficulty": 2,
        "micro_skill": "wait_three_seconds",
        "templates": {
            "baseline": "מגיעה הודעה שמרגישה טיפה לא הוגנת או מעצבנת. מה הדחף האוטומטי הראשון שלך?",
            "retest": "מגיעה הודעה דומה. נסה לעצור בדיוק 3 שניות של שקט מוחלט לפני שאתה בוחר כיצד להגיב.",
        },
        "safety_tags": ["low_intensity", "stop_available"],
    },
    {
        "exercise_id": "pause_procrastination_urge",
        "skill_id": "PAUSE",
        "mode": "TRAINING_MODE",
        "challenge_type": "urge_surfing",
        "min_difficulty": 1,
        "max_difficulty": 2,
        "micro_skill": "ten_second_posture_reset",
        "templates": {
            "baseline": "אתה מתחיל משימה מורכבת ומיד עולה דחף לפתוח לשונית חדשה או לבדוק את הטלפון. מה קורה בגוף ובמחשבה?",
            "retest": "הדחף מופיע שוב. הנח ידיים על הברכיים, קח 10 שניות של איפוס יציבה ונשימה אחת מלאה, ואז בחר אם להמשיך.",
        },
        "safety_tags": ["low_intensity", "stop_available"],
    },
    {
        "exercise_id": "frustration_changed_instruction",
        "skill_id": "FRUSTRATION_TOLERANCE",
        "mode": "TRAINING_MODE",
        "challenge_type": "changed_instructions",
        "min_difficulty": 1,
        "max_difficulty": 2,
        "micro_skill": "reset_and_continue",
        "templates": {
            "baseline": "התחלת משימה לפי הנחיה מסוימת, ופתאום ההנחיה משתנה או שצריך לעשות הכל מהתחלה. מה התגובה הראשונית?",
            "retest": "ההנחיה השתנתה שוב. נסה נשיפת שחרור איטית אחת (Exhale Reset), אמור לעצמך 'זה חלק מהתהליך', ובחר בצעד הבא.",
        },
        "safety_tags": ["low_intensity", "stop_available"],
    },
    {
        "exercise_id": "frustration_technical_glitch",
        "skill_id": "FRUSTRATION_TOLERANCE",
        "mode": "TRAINING_MODE",
        "challenge_type": "unexpected_error",
        "min_difficulty": 1,
        "max_difficulty": 3,
        "micro_skill": "hands_off_keyboard",
        "templates": {
            "baseline": "סקריפט או מערכת שעבדה מקודם נתקעת וזורקת שגיאה אדומה. מה האימפולס המיידי?",
            "retest": "שגיאה מופיעה שוב. הרם ידיים מהמקלדת למשך 5 שניות, קרא רק את השורה האחרונה של הודעת השגיאה, ונסח השערה אחת רגועה.",
        },
        "safety_tags": ["low_intensity", "stop_available"],
    },
    {
        "exercise_id": "arousal_notice_exhale",
        "skill_id": "AROUSAL_REGULATION",
        "mode": "TRAINING_MODE",
        "challenge_type": "body_signal",
        "min_difficulty": 1,
        "max_difficulty": 2,
        "micro_skill": "slow_exhale_notice_change",
        "templates": {
            "baseline": "עצור לרגע ובדוק: מה קורה בגוף שלך כרגע? (כתפיים מכווצות? נשימה קצרה? מתח בלסת?)",
            "retest": "בצע נשיפה איטית וממושכת דרך הפה, כאילו אתה מכבה נר לאט. מה השתנה בתחושת הגוף, אפילו מעט?",
        },
        "safety_tags": ["low_intensity", "stop_available"],
    },
    {
        "exercise_id": "arousal_box_breathing",
        "skill_id": "AROUSAL_REGULATION",
        "mode": "TRAINING_MODE",
        "challenge_type": "calm_down_protocol",
        "min_difficulty": 1,
        "max_difficulty": 3,
        "micro_skill": "box_breathing_4x4",
        "templates": {
            "baseline": "אתה מרגיש אי-שקט או קצב לב מעט מוגבר לפני משימה או שיחה. כמה רמת העוררות מ-1 עד 5?",
            "retest": "בצע מחזור אחד של נשימת ריבוע: שאיפה ל-4 שניות, עצירה ל-4, נשיפה ל-4, עצירה ל-4. דרג כעת את רמת העוררות.",
        },
        "safety_tags": ["low_intensity", "stop_available"],
    },
]


class MentalSkillsService:
    def ensure_seed_data(self, user_id: str = "moshe") -> None:
        now = utc_now()
        with db() as conn:
            conn.execute(
                """
                insert or ignore into msp_users
                (user_id, display_name, timezone, coach_style, identity_method, created_at, updated_at)
                values (?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, user_id, "Asia/Jerusalem", "curious_playful", "single_user_mvp", now, now),
            )
            for skill in MVP_SKILLS:
                conn.execute(
                    """
                    insert or ignore into msp_skills
                    (skill_id, display_name, description, status, default_min_difficulty,
                     default_max_difficulty, created_at)
                    values (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        skill["skill_id"],
                        skill["display_name"],
                        skill["description"],
                        "active",
                        skill["default_min_difficulty"],
                        skill["default_max_difficulty"],
                        now,
                    ),
                )
                conn.execute(
                    """
                    insert or ignore into msp_user_skill_state
                    (user_id, skill_id, current_training_level, confidence, sessions_count,
                     recent_performance_json, trend, last_trained_at, preferred_exercises_json,
                     ineffective_exercises_json, known_triggers_json, effective_regulation_methods_json)
                    values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (user_id, skill["skill_id"], 1, 0.0, 0, "[]", "not_enough_data", None, "[]", "[]", "[]", "[]"),
                )
            for exercise in MVP_EXERCISES:
                conn.execute(
                    """
                    insert or replace into msp_exercises
                    (exercise_id, skill_id, mode, challenge_type, min_difficulty, max_difficulty,
                     micro_skill, templates_json, safety_tags_json, status)
                    values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        exercise["exercise_id"],
                        exercise["skill_id"],
                        exercise["mode"],
                        exercise["challenge_type"],
                        exercise["min_difficulty"],
                        exercise["max_difficulty"],
                        exercise["micro_skill"],
                        json_dump(exercise["templates"]),
                        json_dump(exercise["safety_tags"]),
                        "active",
                    ),
                )

    def user_context(self, user_id: str) -> dict[str, Any]:
        self.ensure_seed_data(user_id)
        recommendation = self.recommendation(user_id)
        history = self.skill_history(user_id, recommendation["recommended_skill_id"], limit=3)
        return {
            "success": True,
            "user_id": user_id,
            "current_focus": recommendation["recommended_skill_id"],
            "recommended_skill_id": recommendation["recommended_skill_id"],
            "recommended_exercise_id": recommendation["recommended_exercise_id"],
            "difficulty": recommendation["difficulty"],
            "recent_summary": self._recent_summary(user_id),
            "skill_history": history["history"],
            "safety_notes": ["MVP uses only low-intensity drills.", "Stop immediately if the user asks to stop."],
        }

    def profile(self, user_id: str) -> dict[str, Any]:
        self.ensure_seed_data(user_id)
        with db() as conn:
            row = conn.execute("select * from msp_users where user_id = ?", (user_id,)).fetchone()
        return dict(row) | {"success": True}

    def list_skills(self, user_id: str = "moshe") -> dict[str, Any]:
        self.ensure_seed_data(user_id)
        with db() as conn:
            rows = conn.execute("select * from msp_skills where status = 'active' order by skill_id").fetchall()
        return {"success": True, "skills": [dict(row) for row in rows]}

    def recommendation(self, user_id: str) -> dict[str, Any]:
        self.ensure_seed_data(user_id)
        with db() as conn:
            rows = conn.execute(
                """
                select * from msp_user_skill_state
                where user_id = ?
                order by sessions_count asc,
                         last_trained_at is not null asc,
                         last_trained_at asc,
                         case skill_id
                             when 'PAUSE' then 1
                             when 'FRUSTRATION_TOLERANCE' then 2
                             when 'AROUSAL_REGULATION' then 3
                             else 99
                         end asc
                """,
                (user_id,),
            ).fetchall()
        chosen = rows[0]
        difficulty = min(2, max(1, int(chosen["current_training_level"])))
        exercise = self._exercise_for(chosen["skill_id"], difficulty)
        return {
            "success": True,
            "user_id": user_id,
            "recommended_skill_id": chosen["skill_id"],
            "recommended_exercise_id": exercise["exercise_id"] if exercise else None,
            "difficulty": difficulty,
            "reason": "Fewest completed sessions; capped at low-intensity MVP difficulty.",
        }

    def start_session(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.ensure_seed_data(payload["user_id"])
        existing = self._session_by_idempotency(payload["idempotency_key"])
        if existing:
            return existing
        exercise_id = payload.get("exercise_id") or self._exercise_for(payload["skill_id"], payload["difficulty"])["exercise_id"]
        session_id = resource_id("msp_session")
        with db() as conn:
            conn.execute(
                """
                insert into msp_training_sessions
                (session_id, user_id, skill_id, exercise_id, mode, difficulty, status,
                 started_at, completed_at, summary, safety_state, idempotency_key)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    payload["user_id"],
                    payload["skill_id"],
                    exercise_id,
                    payload.get("mode", "TRAINING_MODE"),
                    payload.get("difficulty", 1),
                    "active",
                    utc_now(),
                    None,
                    "",
                    "ok",
                    payload["idempotency_key"],
                ),
            )
        return self._session(session_id) | {"already_existed": False}

    def record_event(self, session_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        existing = self._event_by_idempotency(payload["idempotency_key"])
        if existing:
            return existing
        session = self._session(session_id)
        if not session:
            return {"success": False, "error": "session_not_found"}
        safety_state = "stopped" if payload["event_type"] == "user_stop" else session["safety_state"]
        event_id = resource_id("msp_event")
        with db() as conn:
            conn.execute(
                """
                insert into msp_training_events
                (event_id, session_id, user_id, event_type, occurred_at, payload_json, idempotency_key)
                values (?, ?, ?, ?, ?, ?, ?)
                """,
                (event_id, session_id, session["user_id"], payload["event_type"], payload["occurred_at"], json_dump(payload.get("payload", {})), payload["idempotency_key"]),
            )
            if safety_state != session["safety_state"]:
                conn.execute("update msp_training_sessions set safety_state = ?, status = ? where session_id = ?", (safety_state, "stopped", session_id))
        return {"success": True, "event_id": event_id, "session_id": session_id, "safety_state": safety_state, "already_existed": False}

    def complete_session(self, session_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        existing = self._idempotent_response(payload["idempotency_key"], "msp.complete_session")
        if existing:
            return existing
        session = self._session(session_id)
        if not session:
            return {"success": False, "error": "session_not_found"}
        now = utc_now()
        safety_state = payload.get("safety_state") or session["safety_state"]
        status = "completed" if safety_state == "ok" else "completed_with_safety_note"
        with db() as conn:
            conn.execute(
                """
                update msp_training_sessions
                set status = ?, completed_at = ?, summary = ?, safety_state = ?
                where session_id = ?
                """,
                (status, now, payload["summary"], safety_state, session_id),
            )
        self._update_skill_state(session["user_id"], session["skill_id"], session["difficulty"], safety_state, payload["user_noticed_change"], now)
        response = self._session(session_id) | {"success": True}
        self._remember_idempotent_response(payload["idempotency_key"], "msp.complete_session", response)
        return response

    def skill_history(self, user_id: str, skill_id: str, limit: int = 10) -> dict[str, Any]:
        self.ensure_seed_data(user_id)
        with db() as conn:
            state = conn.execute("select * from msp_user_skill_state where user_id = ? and skill_id = ?", (user_id, skill_id)).fetchone()
            sessions = conn.execute(
                "select * from msp_training_sessions where user_id = ? and skill_id = ? order by started_at desc limit ?",
                (user_id, skill_id, limit),
            ).fetchall()
        return {"success": True, "user_id": user_id, "skill_id": skill_id, "state": self._state_row(state) if state else None, "history": [self._session_row(row) for row in sessions]}

    def progress(self, user_id: str) -> dict[str, Any]:
        self.ensure_seed_data(user_id)
        with db() as conn:
            rows = conn.execute("select * from msp_user_skill_state where user_id = ? order by skill_id", (user_id,)).fetchall()
        return {"success": True, "user_id": user_id, "skills": [self._state_row(row) for row in rows]}

    def patterns(self, user_id: str) -> dict[str, Any]:
        patterns = []
        for state in self.progress(user_id)["skills"]:
            if state["sessions_count"]:
                patterns.append({"skill_id": state["skill_id"], "pattern": f"{state['sessions_count']} completed session(s); trend is {state['trend']}.", "evidence_level": "early"})
        return {"success": True, "user_id": user_id, "patterns": patterns}

    def save_observation(self, payload: dict[str, Any]) -> dict[str, Any]:
        existing = self._idempotent_response(payload["idempotency_key"], "msp.save_observation")
        if existing:
            return existing
        observation_id = resource_id("msp_observation")
        occurred_at = payload.get("occurred_at") or datetime.now(timezone.utc).isoformat()
        with db() as conn:
            conn.execute(
                """
                insert into msp_observations
                (observation_id, user_id, skill_id, occurred_at, source, content, tags_json, idempotency_key)
                values (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (observation_id, payload["user_id"], payload.get("skill_id"), occurred_at, payload.get("source", "gpt"), payload["content"], json_dump(payload.get("tags", [])), payload["idempotency_key"]),
            )
        response = {"success": True, "observation_id": observation_id, "already_existed": False}
        self._remember_idempotent_response(payload["idempotency_key"], "msp.save_observation", response)
        return response

    def save_reflection(self, payload: dict[str, Any]) -> dict[str, Any]:
        existing = self._idempotent_response(payload["idempotency_key"], "msp.save_reflection")
        if existing:
            return existing
        reflection_id = resource_id("msp_reflection")
        with db() as conn:
            conn.execute(
                """
                insert into msp_reflections
                (reflection_id, user_id, session_id, skill_id, created_at, content, insight_tags_json, idempotency_key)
                values (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (reflection_id, payload["user_id"], payload.get("session_id"), payload.get("skill_id"), utc_now(), payload["content"], json_dump(payload.get("insight_tags", [])), payload["idempotency_key"]),
            )
        response = {"success": True, "reflection_id": reflection_id, "already_existed": False}
        self._remember_idempotent_response(payload["idempotency_key"], "msp.save_reflection", response)
        return response

    def _update_skill_state(self, user_id: str, skill_id: str, difficulty: int, safety_state: str, noticed_change: bool, now: str) -> None:
        with db() as conn:
            row = conn.execute("select * from msp_user_skill_state where user_id = ? and skill_id = ?", (user_id, skill_id)).fetchone()
            recent = json_load(row["recent_performance_json"], []) if row else []
            recent = ([{"safety_state": safety_state, "user_noticed_change": noticed_change, "difficulty": difficulty}] + recent)[:5]
            trend = "reduce_difficulty" if safety_state in {"stopped", "overload"} else "collecting_evidence"
            level = 1 if safety_state in {"stopped", "overload"} else min(2, difficulty)
            confidence = min(1.0, 0.2 + 0.1 * (int(row["sessions_count"]) + 1 if row else 1))
            conn.execute(
                """
                update msp_user_skill_state
                set current_training_level = ?, confidence = ?, sessions_count = sessions_count + 1,
                    recent_performance_json = ?, trend = ?, last_trained_at = ?
                where user_id = ? and skill_id = ?
                """,
                (level, confidence, json_dump(recent), trend, now, user_id, skill_id),
            )

    def _exercise_for(self, skill_id: str, difficulty: int) -> dict[str, Any] | None:
        with db() as conn:
            row = conn.execute(
                "select * from msp_exercises where skill_id = ? and min_difficulty <= ? and max_difficulty >= ? and status = 'active' order by exercise_id limit 1",
                (skill_id, difficulty, difficulty),
            ).fetchone()
        return self._exercise_row(row) if row else None

    def _recent_summary(self, user_id: str) -> str:
        with db() as conn:
            row = conn.execute("select summary from msp_training_sessions where user_id = ? and summary != '' order by completed_at desc limit 1", (user_id,)).fetchone()
        return row["summary"] if row else ""

    def _session(self, session_id: str) -> dict[str, Any] | None:
        with db() as conn:
            row = conn.execute("select * from msp_training_sessions where session_id = ?", (session_id,)).fetchone()
        return self._session_row(row) if row else None

    def _session_by_idempotency(self, key: str) -> dict[str, Any] | None:
        with db() as conn:
            row = conn.execute("select * from msp_training_sessions where idempotency_key = ?", (key,)).fetchone()
        return (self._session_row(row) | {"already_existed": True}) if row else None

    def _event_by_idempotency(self, key: str) -> dict[str, Any] | None:
        with db() as conn:
            row = conn.execute("select * from msp_training_events where idempotency_key = ?", (key,)).fetchone()
        if not row:
            return None
        return {"success": True, "event_id": row["event_id"], "session_id": row["session_id"], "safety_state": "stopped" if row["event_type"] == "user_stop" else "ok", "already_existed": True}

    def _idempotent_response(self, key: str, endpoint: str) -> dict[str, Any] | None:
        with db() as conn:
            row = conn.execute("select response_json from idempotency_keys where key = ? and endpoint = ?", (key, endpoint)).fetchone()
        return json_load(row["response_json"], None) if row else None

    def _remember_idempotent_response(self, key: str, endpoint: str, response: dict[str, Any]) -> None:
        with db() as conn:
            conn.execute("insert or ignore into idempotency_keys (key, endpoint, response_json, created_at) values (?, ?, ?, ?)", (key, endpoint, json_dump(response), utc_now()))

    def _exercise_row(self, row: Any) -> dict[str, Any]:
        return {
            "exercise_id": row["exercise_id"],
            "skill_id": row["skill_id"],
            "mode": row["mode"],
            "challenge_type": row["challenge_type"],
            "min_difficulty": row["min_difficulty"],
            "max_difficulty": row["max_difficulty"],
            "micro_skill": row["micro_skill"],
            "templates": json_load(row["templates_json"], {}),
            "safety_tags": json_load(row["safety_tags_json"], []),
            "status": row["status"],
        }

    def _state_row(self, row: Any) -> dict[str, Any]:
        return {
            "user_id": row["user_id"],
            "skill_id": row["skill_id"],
            "current_training_level": row["current_training_level"],
            "confidence": row["confidence"],
            "sessions_count": row["sessions_count"],
            "recent_performance": json_load(row["recent_performance_json"], []),
            "trend": row["trend"],
            "last_trained_at": row["last_trained_at"],
            "preferred_exercises": json_load(row["preferred_exercises_json"], []),
            "ineffective_exercises": json_load(row["ineffective_exercises_json"], []),
            "known_triggers": json_load(row["known_triggers_json"], []),
            "effective_regulation_methods": json_load(row["effective_regulation_methods_json"], []),
        }

    def _session_row(self, row: Any) -> dict[str, Any]:
        return {
            "success": True,
            "session_id": row["session_id"],
            "user_id": row["user_id"],
            "skill_id": row["skill_id"],
            "exercise_id": row["exercise_id"],
            "mode": row["mode"],
            "difficulty": row["difficulty"],
            "status": row["status"],
            "started_at": row["started_at"],
            "completed_at": row["completed_at"],
            "summary": row["summary"],
            "safety_state": row["safety_state"],
        }

