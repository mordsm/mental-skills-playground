from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

from app.config import get_settings


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect() -> sqlite3.Connection:
    path = Path(get_settings().database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def db() -> Iterator[sqlite3.Connection]:
    conn = connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with db() as conn:
        conn.executescript(
            """
            create table if not exists idempotency_keys (
                key text primary key,
                endpoint text not null,
                response_json text not null,
                created_at text not null
            );

            create table if not exists msp_users (
                user_id text primary key,
                display_name text not null,
                timezone text not null,
                coach_style text not null,
                identity_method text not null,
                created_at text not null,
                updated_at text not null
            );

            create table if not exists msp_skills (
                skill_id text primary key,
                display_name text not null,
                description text not null,
                status text not null,
                default_min_difficulty integer not null,
                default_max_difficulty integer not null,
                created_at text not null
            );

            create table if not exists msp_exercises (
                exercise_id text primary key,
                skill_id text not null,
                mode text not null,
                challenge_type text not null,
                min_difficulty integer not null,
                max_difficulty integer not null,
                micro_skill text not null,
                templates_json text not null,
                safety_tags_json text not null,
                status text not null
            );

            create table if not exists msp_user_skill_state (
                user_id text not null,
                skill_id text not null,
                current_training_level integer not null,
                confidence real not null,
                sessions_count integer not null,
                recent_performance_json text not null,
                trend text not null,
                last_trained_at text,
                preferred_exercises_json text not null,
                ineffective_exercises_json text not null,
                known_triggers_json text not null,
                effective_regulation_methods_json text not null,
                primary key (user_id, skill_id)
            );

            create table if not exists msp_training_sessions (
                session_id text primary key,
                user_id text not null,
                skill_id text not null,
                exercise_id text,
                mode text not null,
                difficulty integer not null,
                status text not null,
                started_at text not null,
                completed_at text,
                summary text not null,
                safety_state text not null,
                idempotency_key text not null unique
            );

            create table if not exists msp_training_events (
                event_id text primary key,
                session_id text not null,
                user_id text not null,
                event_type text not null,
                occurred_at text not null,
                payload_json text not null,
                idempotency_key text not null unique
            );

            create table if not exists msp_observations (
                observation_id text primary key,
                user_id text not null,
                skill_id text,
                occurred_at text not null,
                source text not null,
                content text not null,
                tags_json text not null,
                idempotency_key text not null unique
            );

            create table if not exists msp_reflections (
                reflection_id text primary key,
                user_id text not null,
                session_id text,
                skill_id text,
                created_at text not null,
                content text not null,
                insight_tags_json text not null,
                idempotency_key text not null unique
            );
            """
        )


def json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def json_load(value: str | None, default: Any) -> Any:
    if not value:
        return default
    return json.loads(value)


def resource_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"

