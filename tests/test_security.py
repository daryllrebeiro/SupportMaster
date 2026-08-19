import unittest

from supportmaster.security import Authenticator, load_security_settings
from supportmaster.persistence import SQLiteRunStore, TenantAccessError
from supportmaster.workflow_state import SupportMasterState
import tempfile
from pathlib import Path


class SecurityTests(unittest.TestCase):
    def test_required_auth_rejects_missing_and_invalid_credentials(self) -> None:
        settings = load_security_settings({
            "SUPPORTMASTER_AUTH_MODE": "REQUIRED",
            "SUPPORTMASTER_API_KEYS": "secret-a|alice|tenant-a|RUN_EXECUTE,HEALTH_READ",
        })
        authenticator = Authenticator(settings)
        self.assertEqual(authenticator.authenticate({}).status, "REJECTED")
        self.assertEqual(authenticator.authenticate({"Authorization": "Bearer wrong"}).status, "REJECTED")

    def test_authenticated_principal_is_tenant_and_scope_bound(self) -> None:
        settings = load_security_settings({
            "SUPPORTMASTER_AUTH_MODE": "REQUIRED",
            "SUPPORTMASTER_API_KEYS": "secret-a|alice|tenant-a|RUN_EXECUTE,HEALTH_READ",
        })
        result = Authenticator(settings).authenticate({"Authorization": "Bearer secret-a"})
        assert result.principal is not None
        self.assertEqual(result.status, "AUTHENTICATED")
        self.assertEqual(result.principal.tenant_id, "tenant-a")
        self.assertTrue(result.principal.allows("RUN_EXECUTE"))
        self.assertTrue(result.principal.allows("HEALTH_READ"))
        self.assertFalse(result.principal.allows("ADMIN"))

    def test_optional_mode_allows_scoped_anonymous_health_only(self) -> None:
        settings = load_security_settings({"SUPPORTMASTER_AUTH_MODE": "OPTIONAL"})
        result = Authenticator(settings).authenticate({})
        assert result.principal is not None
        self.assertEqual(result.status, "ANONYMOUS")
        self.assertTrue(result.principal.allows("HEALTH_READ"))
        self.assertFalse(result.principal.allows("RUN_EXECUTE"))

    def test_required_mode_without_keys_fails_startup_configuration(self) -> None:
        with self.assertRaises(ValueError):
            load_security_settings({"SUPPORTMASTER_AUTH_MODE": "REQUIRED"})

    def test_tenant_context_survives_durable_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = SQLiteRunStore(Path(directory) / "runs.db")
            store.create_run(SupportMasterState(run_id="run-secure", tenant_id="tenant-a", initiated_by="alice"))
            state = store.load_state("run-secure")
            self.assertEqual(state.tenant_id, "tenant-a")
            self.assertEqual(state.initiated_by, "alice")
            with self.assertRaises(TenantAccessError):
                store.load_state_for_tenant("run-secure", "tenant-b")

    def test_expiry_aware_authentication(self) -> None:
        import time
        settings_active = load_security_settings({
            "SUPPORTMASTER_AUTH_MODE": "REQUIRED",
            "SUPPORTMASTER_API_KEYS": f"secret-a|alice|tenant-a|RUN_EXECUTE|{int(time.time() + 3600)}",
        })
        authenticator_active = Authenticator(settings_active)
        self.assertEqual(authenticator_active.authenticate({"Authorization": "Bearer secret-a"}).status, "AUTHENTICATED")

        settings_expired = load_security_settings({
            "SUPPORTMASTER_AUTH_MODE": "REQUIRED",
            "SUPPORTMASTER_API_KEYS": f"secret-b|bob|tenant-b|RUN_EXECUTE|{int(time.time() - 10)}",
        })
        authenticator_expired = Authenticator(settings_expired)
        result = authenticator_expired.authenticate({"Authorization": "Bearer secret-b"})
        self.assertEqual(result.status, "REJECTED")
        self.assertEqual(result.reason, "The credentials have expired.")


if __name__ == "__main__":
    unittest.main()
