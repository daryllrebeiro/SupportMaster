"""Minimal HTTPS JSON transport for injected production integrations."""

from __future__ import annotations

from collections.abc import Mapping
import json
from typing import Any, Protocol
from urllib.error import HTTPError
from urllib.parse import urlencode, urljoin, urlparse
from urllib.request import Request, urlopen


class JsonHttpTransport(Protocol):
    def request(
        self,
        method: str,
        path: str,
        payload: Mapping[str, Any] | None = None,
    ) -> tuple[int, dict[str, Any]]:
        ...


class UrllibJsonTransport:
    """HTTPS-only JSON transport with bounded response sizes."""

    def __init__(
        self,
        base_url: str,
        *,
        bearer_token: str | None = None,
        timeout_seconds: int = 20,
        max_response_bytes: int = 2_000_000,
        allow_http_localhost: bool = False,
    ) -> None:
        parsed = urlparse(base_url)
        if parsed.scheme not in {"https", "http"} or not parsed.netloc:
            raise ValueError("Integration base_url must be an absolute HTTP(S) URL.")
        if parsed.scheme == "http" and not (
            allow_http_localhost and parsed.hostname in {"localhost", "127.0.0.1"}
        ):
            raise ValueError("Production integration transport requires HTTPS.")
        self.base_url = base_url.rstrip("/") + "/"
        self.bearer_token = bearer_token
        self.timeout_seconds = timeout_seconds
        self.max_response_bytes = max_response_bytes

    def request(
        self,
        method: str,
        path: str,
        payload: Mapping[str, Any] | None = None,
    ) -> tuple[int, dict[str, Any]]:
        if not path.startswith("/"):
            raise ValueError("Integration paths must be absolute and relative to base_url.")
        method = method.upper()
        url = urljoin(self.base_url, path.lstrip("/"))
        body: bytes | None = None
        if method == "GET" and payload:
            url = f"{url}?{urlencode(payload)}"
        elif payload is not None:
            body = json.dumps(dict(payload)).encode("utf-8")
        headers = {"Accept": "application/json"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        request = Request(url, data=body, headers=headers, method=method)
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read(self.max_response_bytes + 1)
                if len(raw) > self.max_response_bytes:
                    raise ValueError("Integration response exceeds the configured limit.")
                return int(response.status), json.loads(raw.decode("utf-8") or "{}")
        except HTTPError as error:
            raw = error.read(self.max_response_bytes + 1)
            if len(raw) > self.max_response_bytes:
                raw = b"{}"
            try:
                payload = json.loads(raw.decode("utf-8") or "{}")
            except json.JSONDecodeError:
                payload = {"error": raw.decode("utf-8", errors="replace")[:1000]}
            return int(error.code), payload
