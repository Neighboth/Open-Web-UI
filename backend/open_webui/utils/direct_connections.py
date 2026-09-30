import logging
from typing import Optional, Tuple, Dict, Any

log = logging.getLogger(__name__)

def get_user_direct_connection(user: Any) -> Tuple[Optional[str], Optional[str], Dict[str, Any]]:
    """
    Extracts the user's personal direct connection (BYOK) API key, base URL, and config.
    Returns (api_key, base_url, config_dict) or (None, None, {}).
    """
    if not user:
        return None, None, {}
    settings = getattr(user, 'settings', None) or {}
    if not isinstance(settings, dict):
        return None, None, {}
    ui = settings.get('ui') or {}
    if not isinstance(ui, dict):
        return None, None, {}
    direct = ui.get('directConnections')
    if not direct or not isinstance(direct, dict):
        return None, None, {}

    keys = direct.get('OPENAI_API_KEYS') or []
    urls = direct.get('OPENAI_API_BASE_URLS') or []
    configs = direct.get('OPENAI_API_CONFIGS') or {}

    for idx, key in enumerate(keys):
        if key and idx < len(urls) and urls[idx]:
            cfg = configs.get(str(idx)) or configs.get(idx) or {}
            return str(key).strip(), str(urls[idx]).rstrip('/'), cfg
    return None, None, {}
