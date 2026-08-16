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
        token_hash = sha256(token.encode("utf-8")).hexdigest()
        for credential in self.settings.credentials:
            if secrets.compare_digest(token_hash, credential.key_hash):
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
