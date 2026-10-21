import logging
from typing import Optional, Tuple, Dict, Any
from urllib.parse import urlsplit

log = logging.getLogger(__name__)

DEFAULT_OPENAI_BASE_URL = 'https://api.openai.com/v1'


def _same_endpoint(left: str, right: str) -> bool:
    """True when both URLs point at the same host (scheme + host + port)."""
    try:
        a = urlsplit(left)
        b = urlsplit(right)
    except (TypeError, ValueError):
        return False
    return a.scheme == b.scheme and a.netloc.lower() == b.netloc.lower()


def resolve_provider_base_url(
    admin_base_url: Optional[str],
    user_base_url: Optional[str],
    default: str = DEFAULT_OPENAI_BASE_URL,
) -> str:
    """Pick the base URL that a user's own API key has to be sent to.

    The Admin can configure a gateway for the whole instance.  A user who
    brings their own key must have that key sent to their own endpoint and
    never to a host they did not choose, so the Admin URL is only kept when it
    points at the same host as the user's own connection.

    This replaces a hard coded provider name check: the rule is about hosts,
    not about any particular vendor.
    """
    admin_base_url = (admin_base_url or '').strip()
    user_base_url = (user_base_url or '').strip()

    if not admin_base_url or admin_base_url == 'test':
        return user_base_url or default
    if not user_base_url:
        return admin_base_url
    if _same_endpoint(admin_base_url, user_base_url):
        return admin_base_url
    return user_base_url


def get_user_direct_connection(user: Any) -> Tuple[Optional[str], Optional[str], Dict[str, Any]]:
    """
    Extracts the user's personal direct connection (BYOK) API key, base URL, and config.
    Returns (api_key, base_url, config_dict) or (None, None, {}).
    """
    if not user:
        return None, None, {}

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

    direct = settings.get('directConnections')
    if not direct or not isinstance(direct, dict):
        ui = settings.get('ui') or {}
        if hasattr(ui, 'model_dump'):
            try:
                ui = ui.model_dump()
            except Exception:
                ui = {}
        if isinstance(ui, dict):
            direct = ui.get('directConnections')

    if not direct or not isinstance(direct, dict):
        return None, None, {}

    keys = direct.get('OPENAI_API_KEYS') or []
    urls = direct.get('OPENAI_API_BASE_URLS') or []
    configs = direct.get('OPENAI_API_CONFIGS') or {}

    if isinstance(keys, str):
        keys = [keys]
    if isinstance(urls, str):
        urls = [urls]

    for idx, key in enumerate(keys):
        if key and str(key).strip():
            raw_url = (
                urls[idx] if idx < len(urls) and urls[idx] and str(urls[idx]).strip() else 'https://api.openai.com/v1'
            )
            cfg = configs.get(str(idx)) or configs.get(idx) or {}
            return str(key).strip(), str(raw_url).strip().rstrip('/'), cfg

    return None, None, {}
