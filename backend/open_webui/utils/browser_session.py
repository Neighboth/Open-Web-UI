"""Dependency-free helpers for safely scoping Kasm browser sessions."""

from uuid import UUID
from urllib.parse import urlsplit


def get_user_kasm_credentials(user) -> tuple[str | None, str | None]:
    """Read a user's own Kasm account from their settings.

    A user who brings their own Kasm account is isolated from every other user
    of the instance: the container runs as their account, so nobody inherits
    somebody else's Kasm session.  The credentials live in the user's own
    settings, next to the other bring-your-own-key values.

    Returns ``(username, password)`` or ``(None, None)``.
    """
    if not user:
        return None, None

    settings = getattr(user, 'settings', None)
    if settings is None and isinstance(user, dict):
        settings = user.get('settings')

    if hasattr(settings, 'model_dump'):
        try:
            settings = settings.model_dump()
        except Exception:
            settings = {}
    elif not isinstance(settings, dict):
        settings = {}

    direct = settings.get('browserSandboxKasm')
    if not direct:
        ui = settings.get('ui')
        if hasattr(ui, 'model_dump'):
            try:
                ui = ui.model_dump()
            except Exception:
                ui = {}
        if isinstance(ui, dict):
            direct = ui.get('browserSandboxKasm')

    if not isinstance(direct, dict):
        return None, None

    username = direct.get('user')
    password = direct.get('password')
    username = username.strip() if isinstance(username, str) else None
    password = password.strip() if isinstance(password, str) else None
    if not username or not password:
        return None, None
    return username, password


def resolve_kasm_user_id(configured_user: str, users: object = None) -> str:
    """Resolve a configured Kasm UUID, username, or email to one user UUID.

    UUIDs, usernames, and email addresses must match exactly (case-insensitively)
    against the Kasm user list and resolve to one distinct account. UUIDs are
    normalized before comparison. Substring matching and fallback to the
    API-key owner are deliberately not supported.

    Raises ``ValueError`` with a safe, actionable explanation if the
    configured identity is missing or ambiguous.
    """
    identifier = str(configured_user or '').strip()
    if not identifier:
        raise ValueError('No Kasm user is configured.')

    target = identifier.casefold()
    try:
        target_uuid = str(UUID(identifier))
    except (ValueError, AttributeError):
        target_uuid = None

    matches: dict[str, str] = {}
    if isinstance(users, (list, tuple)):
        for user in users:
            if not isinstance(user, dict):
                continue

            raw_user_id = user.get('user_id')
            if not isinstance(raw_user_id, str) or not raw_user_id.strip():
                continue
            try:
                user_id = str(UUID(raw_user_id.strip()))
            except ValueError:
                continue

            matches_user_id = target_uuid is not None and user_id == target_uuid
            if matches_user_id or any(
                isinstance(user.get(field), str) and user[field].strip().casefold() == target
                for field in ('username', 'email')
            ):
                matches[user_id] = user_id

    if not matches:
        if users is None:
            return target_uuid or identifier
        raise ValueError('The configured Kasm username or email did not match an account.')
    if len(matches) != 1:
        raise ValueError('The configured Kasm username or email matched multiple accounts.')
    return next(iter(matches))


def is_safe_kasm_connection_url(url: str, configured_url: str) -> bool:
    """Accept only same-origin share, token-bearing, or authenticated Kasm connection URLs."""
    try:
        parsed = urlsplit(url)
        configured = urlsplit(configured_url)
    except (TypeError, ValueError):
        return False

    if (
        parsed.scheme not in {'http', 'https'}
        or parsed.scheme != configured.scheme
        or not parsed.netloc
        or parsed.netloc.lower() != configured.netloc.lower()
    ):
        return False

    parts = parsed.fragment.strip('/').split('/')
    is_share_url = len(parts) == 2 and parts[0] == 'join' and bool(parts[1])
    # Kasm Workspaces returns the connect URL as
    #   #/connect/kasm/<kasm_id>/<user_id>/<operational_token>
    # and older builds omit the user segment:
    #   #/connect/kasm/<kasm_id>/<operational_token>
    # Both forms authenticate the session, so both are safe.  Only the path
    # shape is checked here; the token itself is opaque and unverified.
    is_token_url = (
        len(parts) in {4, 5} and parts[0] == 'connect' and parts[1] == 'kasm' and all(part for part in parts[2:])
    )
    is_cast_url = len(parts) == 2 and parts[0] == 'cast' and bool(parts[1])
    is_query_auth = bool(parsed.query and ('password=' in parsed.query or 'token=' in parsed.query))
    return is_share_url or is_token_url or is_cast_url or is_query_auth
