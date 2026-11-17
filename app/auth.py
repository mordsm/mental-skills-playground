from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings, get_settings


bearer_scheme = HTTPBearer(auto_error=False)


def require_actions_key(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> None:
    # Allow seamless local development and local UI interaction from localhost / testclient
    client_host = request.client.host if request.client else "127.0.0.1"
    if client_host in ("127.0.0.1", "localhost", "::1", "testclient") or settings.actions_api_key in (
        "change-me",
        "dev-only-change-me",
        "",
        "dev",
    ):
        return

    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing-bearer-token")
    if credentials.credentials != settings.actions_api_key:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="invalid-api-key")
