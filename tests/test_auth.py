import json
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from google.auth.exceptions import RefreshError
from oauthlib.oauth2 import AccessDeniedError

from yt_tools.auth import (
    REQUIRED_SCOPES,
    AuthorizationError,
    authorize,
    load_authorized_credentials,
    resolve_credential_paths,
)


def client_payload():
    return {
        "installed": {
            "client_id": "client-id",
            "client_secret": "client-secret",
            "auth_uri": "https://accounts.example/auth",
            "token_uri": "https://accounts.example/token",
        }
    }


class TestAuthorization(unittest.TestCase):
    def test_default_paths_use_the_os_user_data_directory(self):
        with patch("yt_tools.auth.user_data_path", return_value=Path("/user-data/yt-tools")) as data_path:
            paths = resolve_credential_paths()

        data_path.assert_called_once_with("yt-tools", appauthor=False)
        self.assertEqual(paths.client_config_file, Path("/user-data/yt-tools/client_secret.json"))
        self.assertEqual(paths.token_file, Path("/user-data/yt-tools/token.json"))

    def test_missing_stored_token_returns_an_actionable_error(self):
        token = Path("/missing/yt-tools/token.json")

        with self.assertRaisesRegex(
            AuthorizationError,
            "No stored authorization.*yt-tools authorize",
        ):
            load_authorized_credentials(token)

    def test_malformed_stored_token_error_does_not_expose_contents(self):
        with tempfile.TemporaryDirectory() as directory:
            token = Path(directory) / "token.json"
            secret = "super-secret-token"
            token.write_text(secret, encoding="utf-8")

            with self.assertRaises(AuthorizationError) as raised:
                load_authorized_credentials(token)

            self.assertIn("malformed", str(raised.exception).lower())
            self.assertIn("authorize", str(raised.exception).lower())
            self.assertNotIn(secret, str(raised.exception))

    def test_structurally_invalid_stored_token_returns_an_actionable_error(self):
        with tempfile.TemporaryDirectory() as directory:
            token = Path(directory) / "token.json"
            token.write_text("[]", encoding="utf-8")

            with self.assertRaisesRegex(AuthorizationError, "malformed.*authorize"):
                load_authorized_credentials(token)

    def test_stored_credentials_missing_required_scopes_require_authorization(self):
        with tempfile.TemporaryDirectory() as directory:
            token = Path(directory) / "token.json"
            token.write_text("{}", encoding="utf-8")
            credentials = MagicMock(valid=True, expired=False, refresh_token=None)
            credentials.has_scopes.return_value = False

            with patch(
                "yt_tools.auth.Credentials.from_authorized_user_file",
                return_value=credentials,
            ), self.assertRaisesRegex(AuthorizationError, "required read-only access.*authorize"):
                load_authorized_credentials(token)

    def test_valid_stored_credentials_are_reused_without_refresh(self):
        with tempfile.TemporaryDirectory() as directory:
            token = Path(directory) / "token.json"
            token.write_text("{}", encoding="utf-8")
            credentials = MagicMock(valid=True, expired=False)

            with patch(
                "yt_tools.auth.Credentials.from_authorized_user_file",
                return_value=credentials,
            ) as load:
                result = load_authorized_credentials(token)

            self.assertIs(result, credentials)
            load.assert_called_once_with(str(token))
            credentials.refresh.assert_not_called()

    def test_nonrefreshable_stored_credentials_require_authorization(self):
        with tempfile.TemporaryDirectory() as directory:
            token = Path(directory) / "token.json"
            token.write_text("{}", encoding="utf-8")
            credentials = MagicMock(valid=False, expired=True, refresh_token=None)

            with patch(
                "yt_tools.auth.Credentials.from_authorized_user_file",
                return_value=credentials,
            ), self.assertRaisesRegex(AuthorizationError, "cannot be refreshed.*authorize"):
                load_authorized_credentials(token)

    def test_failed_refresh_returns_an_actionable_error_without_provider_secrets(self):
        with tempfile.TemporaryDirectory() as directory:
            token = Path(directory) / "token.json"
            token.write_text("{}", encoding="utf-8")
            credentials = MagicMock(valid=False, expired=True, refresh_token="refresh-token")
            credentials.refresh.side_effect = RefreshError("provider leaked secret-value")

            with (
                patch(
                    "yt_tools.auth.Credentials.from_authorized_user_file",
                    return_value=credentials,
                ),
                patch("yt_tools.auth.Request"),
                self.assertRaises(AuthorizationError) as raised,
            ):
                load_authorized_credentials(token)

            self.assertIn("refresh failed", str(raised.exception).lower())
            self.assertIn("authorize", str(raised.exception).lower())
            self.assertNotIn("secret-value", str(raised.exception))

    def test_expired_stored_credentials_refresh_and_persist_without_consent(self):
        with tempfile.TemporaryDirectory() as directory:
            token = Path(directory) / "token.json"
            token.write_text("{}", encoding="utf-8")
            credentials = MagicMock(valid=False, expired=True, refresh_token="refresh-token")
            credentials.refresh.side_effect = lambda request: setattr(credentials, "valid", True)
            credentials.to_json.return_value = json.dumps({"token": "new-token"})
            request = MagicMock()

            with (
                patch(
                    "yt_tools.auth.Credentials.from_authorized_user_file",
                    return_value=credentials,
                ),
                patch("yt_tools.auth.Request", return_value=request),
            ):
                result = load_authorized_credentials(token)

            self.assertIs(result, credentials)
            credentials.refresh.assert_called_once_with(request)
            self.assertEqual(json.loads(token.read_text()), {"token": "new-token"})
            self.assertEqual(stat.S_IMODE(token.stat().st_mode), 0o600)

    def test_incomplete_client_secret_is_rejected_without_replacing_stored_config(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "selected-client.json"
            source.write_text(json.dumps({"installed": {}}), encoding="utf-8")
            client_config = root / "stored-client.json"
            client_config.write_text("existing-config", encoding="utf-8")

            with self.assertRaisesRegex(AuthorizationError, "malformed"):
                authorize(source, client_config, root / "token.json")

            self.assertEqual(client_config.read_text(), "existing-config")

    def test_malformed_client_secret_is_rejected_without_replacing_stored_config(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "selected-client.json"
            source.write_text("secret-value", encoding="utf-8")
            client_config = root / "stored-client.json"
            client_config.write_text("existing-config", encoding="utf-8")

            with self.assertRaises(AuthorizationError) as raised:
                authorize(source, client_config, root / "token.json")

            self.assertIn("malformed", str(raised.exception).lower())
            self.assertNotIn("secret-value", str(raised.exception))
            self.assertEqual(client_config.read_text(), "existing-config")

    def test_authorize_rejects_the_same_destination_for_config_and_token(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "selected-client.json"
            source.write_text(json.dumps(client_payload()), encoding="utf-8")
            destination = root / "credentials.json"

            with self.assertRaisesRegex(AuthorizationError, "must be different"):
                authorize(source, destination, destination)

            self.assertFalse(destination.exists())

    def test_authorize_uses_one_read_only_profile_and_stores_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "selected-client.json"
            client_config = root / "stored" / "client.json"
            token = root / "stored" / "token.json"
            source_payload = client_payload()
            source.write_text(json.dumps(source_payload), encoding="utf-8")
            credentials = MagicMock(refresh_token="refresh-token")
            credentials.to_json.return_value = json.dumps({"refresh_token": "refresh-token"})
            flow = MagicMock(credentials=credentials)

            with patch(
                "yt_tools.auth.InstalledAppFlow.from_client_secrets_file",
                return_value=flow,
            ) as create_flow:
                authorize(source, client_config, token)

            create_flow.assert_called_once_with(str(client_config), scopes=REQUIRED_SCOPES)
            flow.run_local_server.assert_called_once_with(
                port=0,
                access_type="offline",
                prompt="consent",
            )
            self.assertEqual(json.loads(client_config.read_text()), source_payload)
            self.assertEqual(
                json.loads(token.read_text()),
                {"refresh_token": "refresh-token"},
            )

    def test_authorization_without_a_refresh_token_is_not_stored(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "selected-client.json"
            source.write_text(json.dumps(client_payload()), encoding="utf-8")
            flow = MagicMock()
            flow.credentials.refresh_token = None
            token = root / "token.json"

            with (
                patch(
                    "yt_tools.auth.InstalledAppFlow.from_client_secrets_file",
                    return_value=flow,
                ),
                self.assertRaisesRegex(AuthorizationError, "refreshable token.*authorize"),
            ):
                authorize(source, root / "client.json", token)

            self.assertFalse(token.exists())

    def test_denied_consent_returns_an_actionable_error_without_storing_a_token(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "selected-client.json"
            source.write_text(json.dumps(client_payload()), encoding="utf-8")
            token = root / "token.json"
            flow = MagicMock()
            flow.run_local_server.side_effect = AccessDeniedError(
                description="provider leaked secret-value"
            )

            with (
                patch(
                    "yt_tools.auth.InstalledAppFlow.from_client_secrets_file",
                    return_value=flow,
                ),
                self.assertRaises(AuthorizationError) as raised,
            ):
                authorize(source, root / "client.json", token)

            self.assertIn("denied", str(raised.exception).lower())
            self.assertIn("authorize", str(raised.exception).lower())
            self.assertNotIn("secret-value", str(raised.exception))
            self.assertFalse(token.exists())

    def test_authorize_stores_files_with_owner_only_access(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "selected-client.json"
            source.write_text(json.dumps(client_payload()), encoding="utf-8")
            data_dir = root / "new-data-dir"
            client_config = data_dir / "client.json"
            token = data_dir / "token.json"
            credentials = MagicMock(refresh_token="refresh-token")
            credentials.to_json.return_value = "{}"
            flow = MagicMock(credentials=credentials)

            with patch(
                "yt_tools.auth.InstalledAppFlow.from_client_secrets_file",
                return_value=flow,
            ):
                authorize(source, client_config, token)

            self.assertEqual(stat.S_IMODE(data_dir.stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE(client_config.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(token.stat().st_mode), 0o600)


if __name__ == "__main__":
    unittest.main()
