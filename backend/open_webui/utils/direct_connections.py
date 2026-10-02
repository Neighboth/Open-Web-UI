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
                urls[idx]
                if idx < len(urls) and urls[idx] and str(urls[idx]).strip()
                else 'https://api.openai.com/v1'
            )
            cfg = configs.get(str(idx)) or configs.get(idx) or {}
            return str(key).strip(), str(raw_url).strip().rstrip('/'), cfg

    return None, None, {}

