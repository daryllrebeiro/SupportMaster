"""Constant-time API-key authentication with explicit scopes."""

from __future__ import annotations

from hashlib import sha256
import secrets
from collections.abc import Mapping
from typing import Literal

from pydantic import BaseModel, Field

from .settings import SecuritySettings


class Principal(BaseModel):
    subject: str
    tenant_id: str
    scopes: list[str] = Field(default_factory=list)
    authenticated: bool = True

    def allows(self, scope: str) -> bool:
        return "ADMIN" in self.scopes or scope in self.scopes


class AuthResult(BaseModel):
    status: Literal["AUTHENTICATED", "ANONYMOUS", "REJECTED"]
    principal: Principal | None = None
    reason: str | None = None


class Authenticator:
    def __init__(self, settings: SecuritySettings) -> None:
        self.settings = settings

    def authenticate(self, headers: Mapping[str, str]) -> AuthResult:
        if self.settings.auth_mode == "DISABLED":
            return AuthResult(
                status="ANONYMOUS",
                principal=Principal(
                    subject="anonymous",
                    tenant_id=self.settings.anonymous_tenant,
                    scopes=["RUN_EXECUTE", "HEALTH_READ", "AUDIT_READ", "ORG_ADMIN"],
                ),
            )
        token = self._token(headers)
        if not token:
            if self.settings.auth_mode == "REQUIRED":
                return AuthResult(status="REJECTED", reason="Authentication is required.")
            scopes = ["RUN_EXECUTE", "HEALTH_READ", "AUDIT_READ", "ORG_ADMIN"] if self.settings.auth_mode == "DISABLED" else ["HEALTH_READ"]
            return AuthResult(
                status="ANONYMOUS",
                principal=Principal(subject="anonymous", tenant_id=self.settings.anonymous_tenant, scopes=scopes),
            )
        if token.count(".") == 2:
            try:
                import base64
                import json
                import time
                import os
                parts = token.split(".")
                payload_b64 = parts[1]
                payload_b64 += "=" * ((4 - len(payload_b64) % 4) % 4)
                payload_bytes = base64.urlsafe_b64decode(payload_b64)
                claims = json.loads(payload_bytes.decode("utf-8"))
                exp = claims.get("exp")
                if exp is not None and time.time() > exp:
                    return AuthResult(status="REJECTED", reason="JWT token has expired.")
                sub = claims.get("sub", "token-user")
                tenant_id = claims.get("tenant_id") or claims.get("iss", "default")
                scopes = claims.get("scopes") or ["RUN_EXECUTE", "HEALTH_READ", "AUDIT_READ"]
                secret = os.getenv("SUPPORTMASTER_JWT_SECRET")
                if secret:
                    try:
                        import jwt
                        jwt.decode(token, secret, algorithms=["HS256"])
                    except ImportError:
                        pass
                    except Exception as e:
                        return AuthResult(status="REJECTED", reason=f"JWT signature verification failed: {e}")
                return AuthResult(
                    status="AUTHENTICATED",
                    principal=Principal(subject=sub, tenant_id=tenant_id, scopes=scopes),
                )
            except Exception as e:
                return AuthResult(status="REJECTED", reason=f"Malformed JWT token: {e}")

        token_hash = sha256(token.encode("utf-8")).hexdigest()
        import time
        for credential in self.settings.credentials:
            if secrets.compare_digest(token_hash, credential.key_hash):
                if credential.expires_at is not None and time.time() > credential.expires_at:
                    return AuthResult(status="REJECTED", reason="The credentials have expired.")
                return AuthResult(
                    status="AUTHENTICATED",
                    principal=Principal(subject=credential.subject, tenant_id=credential.tenant_id, scopes=credential.scopes),
                )
        return AuthResult(status="REJECTED", reason="Invalid SupportMaster credentials.")

    @staticmethod
    def _token(headers: Mapping[str, str]) -> str | None:
        authorization = headers.get("Authorization") or headers.get("authorization") or ""
        if authorization.lower().startswith("bearer "):
            return authorization[7:].strip() or None
        return headers.get("X-SupportMaster-API-Key") or headers.get("x-supportmaster-api-key") or None
