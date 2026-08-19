import base64
import json
import time
import unittest
import io
import os
import tempfile
from pathlib import Path
from supportmaster.connectors import JiraConnector, ZendeskConnector
from supportmaster.security.auth import Authenticator
from supportmaster.security.settings import SecuritySettings
from supportmaster.web import SupportMasterHandler
from supportmaster.persistence import SQLiteRunStore


class MockSupportMasterHandler(SupportMasterHandler):
    def __init__(self, path, method="GET", body=b"", headers=None):
        self.path = path
        self.command = method
        self.rfile = io.BytesIO(body)
        self.wfile = io.BytesIO()
        self.headers = headers or {}
        self.response_code = None
        self.response_headers = {}

    def send_response(self, code, message=None):
        self.response_code = code

    def send_header(self, keyword, value):
        self.response_headers[keyword] = value

    def end_headers(self):
        pass

    def log_message(self, format, *args):
        pass



def make_mock_jwt(payload: dict) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode("utf-8")).decode("utf-8").rstrip("=")
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8").rstrip("=")
    signature_b64 = base64.urlsafe_b64encode(b"sig").decode("utf-8").rstrip("=")
    return f"{header_b64}.{payload_b64}.{signature_b64}"


class ConnectorsAndJwtTests(unittest.TestCase):
    def test_jira_connector_mapping(self) -> None:
        payload = {
            "issue": {
                "key": "FIN-123",
                "fields": {
                    "summary": "SSO Callback fails",
                    "description": "Details here",
                    "priority": {"name": "High"},
                    "reporter": {"emailAddress": "test@example.org"},
                    "project": {"key": "FIN"},
                    "status": {"name": "To Do"}
                }
            }
        }
        mapped = JiraConnector.map_payload(payload)
        self.assertEqual(mapped["external_id"], "FIN-123")
        self.assertEqual(mapped["title"], "Jira key: FIN-123 | SSO Callback fails")
        self.assertEqual(mapped["description"], "Details here")
        self.assertEqual(mapped["priority"], "High")
        self.assertEqual(mapped["reporter"], "test@example.org")
        self.assertEqual(mapped["metadata"]["jira_project"], "FIN")

    def test_zendesk_connector_mapping(self) -> None:
        payload = {
            "ticket": {
                "id": 999,
                "subject": "Crash on launch",
                "description": "Log here",
                "priority": "normal",
                "requester": {"email": "user@example.org"},
                "status": "new",
                "tags": ["mobile", "crash"]
            }
        }
        mapped = ZendeskConnector.map_payload(payload)
        self.assertEqual(mapped["external_id"], "999")
        self.assertEqual(mapped["title"], "Zendesk ticket #999 | Crash on launch")
        self.assertEqual(mapped["description"], "Log here")
        self.assertEqual(mapped["priority"], "normal")
        self.assertEqual(mapped["reporter"], "user@example.org")
        self.assertEqual(mapped["metadata"]["zendesk_status"], "new")

    def test_jwt_authenticator(self) -> None:
        settings = SecuritySettings(auth_mode="REQUIRED")
        authenticator = Authenticator(settings)

        # 1. Valid token
        payload = {
            "sub": "alice",
            "tenant_id": "tenant-x",
            "scopes": ["RUN_EXECUTE", "AUDIT_READ"],
            "exp": time.time() + 3600
        }
        token = make_mock_jwt(payload)
        headers = {"Authorization": f"Bearer {token}"}
        result = authenticator.authenticate(headers)
        self.assertEqual(result.status, "AUTHENTICATED")
        self.assertEqual(result.principal.subject, "alice")
        self.assertEqual(result.principal.tenant_id, "tenant-x")
        self.assertTrue(result.principal.allows("AUDIT_READ"))

        # 2. Expired token
        expired_payload = {
            "sub": "bob",
            "tenant_id": "tenant-y",
            "scopes": ["RUN_EXECUTE"],
            "exp": time.time() - 60
        }
        expired_token = make_mock_jwt(expired_payload)
        expired_headers = {"Authorization": f"Bearer {expired_token}"}
        expired_result = authenticator.authenticate(expired_headers)
        self.assertEqual(expired_result.status, "REJECTED")
        self.assertIn("expired", expired_result.reason.lower())


    def test_web_connectors_endpoints(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(temp_dir.name) / "test_run.db"
        old_run_db = os.environ.get("SUPPORTMASTER_RUN_DB")
        os.environ["SUPPORTMASTER_RUN_DB"] = str(db_path)
        
        try:
            # Seed the database
            store = SQLiteRunStore(db_path)
            
            # Setup payload
            payload = {
                "issue": {
                    "key": "FIN-123",
                    "fields": {
                        "summary": "SSO Callback fails",
                        "description": "Details here",
                        "priority": {"name": "High"},
                        "reporter": {"emailAddress": "test@example.org"},
                        "project": {"key": "FIN"},
                        "status": {"name": "To Do"}
                    }
                }
            }
            body = json.dumps(payload).encode("utf-8")
            headers = {
                "X-SupportMaster-API-Key": "secret",
                "Content-Length": str(len(body))
            }
            
            # Request handler
            handler = MockSupportMasterHandler(
                "/api/connectors/jira",
                method="POST",
                body=body,
                headers=headers
            )
            
            # Patch authenticate to return a dummy principal
            from supportmaster.security.auth import AuthResult, Principal
            from unittest.mock import patch
            principal = Principal(subject="operator", tenant_id="demo-acme", scopes=["RUN_EXECUTE", "AUDIT_READ"])
            auth_res = AuthResult(status="AUTHENTICATED", principal=principal)
            
            with patch("supportmaster.web.AUTHENTICATOR.authenticate", return_value=auth_res):
                handler.do_POST()
                
            self.assertEqual(handler.response_code, 201)
            res = json.loads(handler.wfile.getvalue().decode("utf-8"))
            self.assertEqual(res["status"], "CREATED")
            self.assertEqual(res["case"]["external_id"], "FIN-123")
            
        finally:
            os.environ["SUPPORTMASTER_RUN_DB"] = old_run_db or ""
            temp_dir.cleanup()


if __name__ == "__main__":
    unittest.main()
