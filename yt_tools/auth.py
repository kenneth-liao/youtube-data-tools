import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from oauthlib.oauth2 import AccessDeniedError
from platformdirs import user_data_path


REQUIRED_SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    "https://www.googleapis.com/auth/yt-analytics-monetary.readonly",
]


class AuthorizationError(Exception):
    """An actionable authorization failure safe to display to the user."""


@dataclass(frozen=True)
class CredentialPaths:
    client_config_file: Path
    token_file: Path


def resolve_credential_paths(
    client_config_file: str | Path | None = None,
    token_file: str | Path | None = None,
) -> CredentialPaths:
    """Resolve canonical credential destinations without searching other locations."""
    data_directory = user_data_path("yt-tools", appauthor=False)
    return CredentialPaths(
        client_config_file=(
            Path(client_config_file)
            if client_config_file
            else data_directory / "client_secret.json"
        ),
        token_file=(Path(token_file) if token_file else data_directory / "token.json"),
    )


def _write_private(path: Path, content: str) -> None:
    parent_existed = path.parent.exists()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not parent_existed:
        path.parent.chmod(0o700)

    descriptor, temporary_name = tempfile.mkstemp(dir=path.parent)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as temporary_file:
            descriptor = -1
            temporary_file.write(content)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_name, path)
        path.chmod(0o600)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        Path(temporary_name).unlink(missing_ok=True)


def load_authorized_credentials(token_file: str | Path) -> Credentials:
    """Load credentials for an authorized channel without repeating consent."""
    token_file = Path(token_file)
    if not token_file.is_file():
        raise AuthorizationError(
            f"No stored authorization found at {token_file}. "
            "Run yt-tools authorize --client-secrets <file>."
        )
    try:
        credentials = Credentials.from_authorized_user_file(str(token_file))
    except (OSError, ValueError, TypeError, AttributeError) as error:
        raise AuthorizationError(
            f"Stored authorization at {token_file} is malformed. "
            "Run yt-tools authorize again."
        ) from error
    if credentials.expired and credentials.refresh_token:
        try:
            credentials.refresh(Request())
        except GoogleAuthError as error:
            raise AuthorizationError(
                "Stored authorization refresh failed. "
                "Run yt-tools authorize again."
            ) from error
        _write_private(token_file, credentials.to_json())
    if not credentials.valid:
        raise AuthorizationError(
            "Stored authorization cannot be refreshed. "
            "Run yt-tools authorize again."
        )
    if not credentials.has_scopes(REQUIRED_SCOPES):
        raise AuthorizationError(
            "Stored authorization lacks the required read-only access. "
            "Run yt-tools authorize again."
        )
    return credentials


def _read_client_config(client_secrets: Path) -> dict:
    if not client_secrets.is_file():
        raise AuthorizationError(
            f"Client-secret file not found at {client_secrets}. "
            "Select a Google OAuth client-secret JSON file."
        )
    try:
        payload = json.loads(client_secrets.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise AuthorizationError(
            f"Client-secret file at {client_secrets} is malformed. "
            "Select a valid Google OAuth client-secret JSON file."
        ) from error

    required_fields = {"client_id", "client_secret", "auth_uri", "token_uri"}
    configurations = [
        payload.get(client_type)
        for client_type in ("installed", "web")
        if isinstance(payload, dict) and isinstance(payload.get(client_type), dict)
    ]
    if len(configurations) != 1 or not required_fields.issubset(configurations[0]):
        raise AuthorizationError(
            f"Client-secret file at {client_secrets} is malformed. "
            "Expected one complete installed or web Google OAuth client configuration."
        )
    return payload


def authorize(
    client_secrets: str | Path,
    client_config_file: str | Path,
    token_file: str | Path,
) -> None:
    """Authorize an owned channel and store the reusable OAuth configuration."""
    client_secrets = Path(client_secrets)
    client_config_file = Path(client_config_file)
    token_file = Path(token_file)

    if client_config_file.resolve() == token_file.resolve():
        raise AuthorizationError(
            "Client configuration and token destinations must be different files."
        )

    payload = _read_client_config(client_secrets)
    _write_private(client_config_file, json.dumps(payload))

    try:
        flow = InstalledAppFlow.from_client_secrets_file(
            str(client_config_file), scopes=REQUIRED_SCOPES
        )
        flow.run_local_server(port=0, access_type="offline", prompt="consent")
    except AccessDeniedError as error:
        raise AuthorizationError(
            "Channel-owner authorization was denied. "
            "Run yt-tools authorize again and grant the requested read-only access."
        ) from error
    except Exception as error:
        raise AuthorizationError(
            "Channel-owner authorization failed before completion. Check the OAuth "
            "client configuration and network, then run yt-tools authorize again."
        ) from error

    if not flow.credentials.refresh_token:
        raise AuthorizationError(
            "Google did not return a refreshable token. "
            "Run yt-tools authorize again and complete consent."
        )
    _write_private(token_file, flow.credentials.to_json())
