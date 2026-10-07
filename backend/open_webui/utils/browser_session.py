"""Dependency-free helpers for safely scoping Kasm browser sessions."""

from uuid import UUID
from urllib.parse import urlsplit


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
        raise ValueError('The configured Kasm username or email did not match an account.')
    if len(matches) != 1:
        raise ValueError('The configured Kasm username or email matched multiple accounts.')
    return next(iter(matches))


def is_safe_kasm_connection_url(url: str, configured_url: str) -> bool:
    """Accept only same-origin share or token-bearing Kasm connection URLs.

    Kasm's root and ``#/session/<id>`` pages may redirect to its authenticated
    Workspaces/admin UI inside an iframe. A browser preview must be scoped to a
    share token or an operational session token.
    """
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
    is_token_url = len(parts) == 4 and parts[:2] == ['connect', 'kasm'] and bool(parts[2]) and bool(parts[3])
    return is_share_url or is_token_url
