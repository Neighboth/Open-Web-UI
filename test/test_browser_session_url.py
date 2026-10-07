from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / 'backend' / 'open_webui' / 'utils' / 'browser_session.py'
SPEC = spec_from_file_location('browser_session', MODULE_PATH)
BROWSER_SESSION = module_from_spec(SPEC)
SPEC.loader.exec_module(BROWSER_SESSION)
is_safe_kasm_connection_url = BROWSER_SESSION.is_safe_kasm_connection_url
resolve_kasm_user_id = BROWSER_SESSION.resolve_kasm_user_id


def test_share_and_token_connection_urls_are_allowed():
    origin = 'https://kasm.example.test'

    assert is_safe_kasm_connection_url(f'{origin}/#/join/share-token', origin)
    assert is_safe_kasm_connection_url(f'{origin}/#/connect/kasm/session-id/operational-token', origin)


def test_admin_and_unscoped_urls_are_rejected():
    origin = 'https://kasm.example.test'

    assert not is_safe_kasm_connection_url(origin, origin)
    assert not is_safe_kasm_connection_url(f'{origin}/#/', origin)
    assert not is_safe_kasm_connection_url(f'{origin}/#/session/session-id', origin)
    assert not is_safe_kasm_connection_url(f'{origin}/#/connect/kasm/session-id', origin)


def test_cross_origin_connection_url_is_rejected():
    assert not is_safe_kasm_connection_url(
        'https://other.example.test/#/join/share-token',
        'https://kasm.example.test',
    )


def test_kasm_user_resolver_accepts_uuid_and_exact_username_or_email():
    configured_id = '8efbc18c-5fd9-47ad-ae69-a39a54aafc5d'
    users = [
        {
            'user_id': configured_id,
            'username': 'workspace-service',
            'email': 'workspace@example.test',
        },
        {
            'user_id': '1df3f880-8df6-480a-9360-1eec11a9f6b7',
            'username': 'workspace-service-admin',
            'email': 'admin@example.test',
        },
    ]

    assert resolve_kasm_user_id(configured_id.upper(), users) == configured_id
    assert resolve_kasm_user_id('WORKSPACE-SERVICE', users) == configured_id
    assert resolve_kasm_user_id('WORKSPACE@example.test', users) == configured_id


def test_kasm_user_resolver_rejects_partial_missing_and_ambiguous_matches():
    users = [
        {'user_id': '8efbc18c-5fd9-47ad-ae69-a39a54aafc5d', 'username': 'workspace-service'},
        {'user_id': '1df3f880-8df6-480a-9360-1eec11a9f6b7', 'username': 'workspace-service'},
    ]

    for configured, accounts in (
        ('workspace', users),  # substring matching could pick the wrong account
        ('missing@example.test', users),
        ('workspace-service', users),  # two exact matches are ambiguous
        ('', users),
        (users[0]['user_id'], []),  # UUIDs must exist in the Kasm user list too
    ):
        try:
            resolve_kasm_user_id(configured, accounts)
            assert False, f'Expected {configured!r} to be rejected'
        except ValueError:
            pass
