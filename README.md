# Mental Skills Playground

Mental Skills Playground is a separate product/backend for training meta-cognitive and
meta-emotional skills through short, controlled, game-like practice sessions.

Compass remains the manager of day-to-day projects, tasks, approvals, mail, finance, and
agent orchestration. This project owns the mental training product. Compass may later
call this backend as an external specialist service, but it should not own the core
training logic.

## Product Role

The product is a "gym for mental muscles":

```text
DISCOVER -> TRAIN -> RETEST -> TRANSFER -> LEARN
```

The MVP focuses on:

- `PAUSE`
- `FRUSTRATION_TOLERANCE`
- `AROUSAL_REGULATION`

It is not therapy, diagnosis, or a generic wellbeing chatbot. It should feel like a
coherent training world with safe, low-intensity simulations and longitudinal learning.

## Run Locally

```powershell
cd C:\workspace\mental-skills-playground
uv sync
Copy-Item .env.example .env
uv run uvicorn app.main:app --reload --port 8010
```

Local URLs:

```text
http://localhost:8010/api/health
http://localhost:8010/docs
```

## GPT Actions

The appropriate Custom GPT should refer to this project as:

```text
Mental Skills Playground
```

Use this backend, not Compass, as the action server for mental-skills training flows.
Compass can integrate with it later through explicit API calls.

The GPT-facing API namespace is:

```text
/api/msp/*
```

## Environment

```text
MSP_ACTIONS_API_KEY=change-me
MSP_DATABASE_PATH=data/mental-skills-playground.db
MSP_PUBLIC_BASE_URL=http://localhost:8010
MSP_USER_ID=moshe
```

## Relationship To Compass

```text
Compass = manager/orchestrator for day-to-day systems
Mental Skills Playground = training product for mental skills
```

Future integration should be API-based:

- Compass asks for training status or recommendation.
- Mental Skills Playground owns sessions, progress, exercises, safety state, and skill history.
- Compass does not directly mutate mental-skills internal data except through approved API contracts.