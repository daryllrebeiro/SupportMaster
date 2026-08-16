"""Fail-closed API-key configuration for deployed operator surfaces."""

from __future__ import annotations

import os
from hashlib import sha256
from typing import Literal

from pydantic import BaseModel, Field


class ApiKeyCredential(BaseModel):
    key_hash: str
    subject: str
    tenant_id: str = "default"
    scopes: list[str] = Field(default_factory=list)


class SecuritySettings(BaseModel):
    auth_mode: Literal["DISABLED", "OPTIONAL", "REQUIRED"] = "DISABLED"
    credentials: list[ApiKeyCredential] = Field(default_factory=list)
    anonymous_tenant: str = "default"


def _credential(raw: str, index: int) -> ApiKeyCredential:
    # Format: secret|subject|tenant|scope1,scope2
    parts = raw.split("|", 3)
    secret = parts[0].strip()
    if not secret:
        raise ValueError("SUPPORTMASTER_API_KEYS contains an empty secret.")
    subject = parts[1].strip() if len(parts) > 1 and parts[1].strip() else f"api-key-{index + 1}"
    tenant = parts[2].strip() if len(parts) > 2 and parts[2].strip() else "default"
    scopes = [item.strip() for item in parts[3].split(",") if item.strip()] if len(parts) > 3 else ["RUN_EXECUTE", "HEALTH_READ", "AUDIT_READ"]
    return ApiKeyCredential(key_hash=sha256(secret.encode("utf-8")).hexdigest(), subject=subject, tenant_id=tenant, scopes=scopes)


def load_security_settings(environ: dict[str, str] | None = None) -> SecuritySettings:
    values = dict(environ or os.environ)
    mode = values.get("SUPPORTMASTER_AUTH_MODE", "DISABLED").strip().upper() or "DISABLED"
    if mode not in {"DISABLED", "OPTIONAL", "REQUIRED"}:
        raise ValueError("SUPPORTMASTER_AUTH_MODE must be DISABLED, OPTIONAL, or REQUIRED.")
    raw_keys = values.get("SUPPORTMASTER_API_KEYS", "")
    credentials = [_credential(item, index) for index, item in enumerate(raw_keys.split(";") if raw_keys else [])]
    if mode == "REQUIRED" and not credentials:
        raise ValueError("REQUIRED authentication needs SUPPORTMASTER_API_KEYS.")
    tenant = values.get("SUPPORTMASTER_ANONYMOUS_TENANT", "default").strip() or "default"
    return SecuritySettings(auth_mode=mode, credentials=credentials, anonymous_tenant=tenant)
