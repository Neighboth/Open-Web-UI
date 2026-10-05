import asyncio
import logging
import os
import shutil
import tarfile
import time
from pathlib import Path
from typing import Optional
from urllib.parse import quote

import aiohttp
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from open_webui.env import DATA_DIR
from open_webui.models.config import Config
from open_webui.utils.auth import get_admin_user, get_verified_user

log = logging.getLogger(__name__)

router = APIRouter()

# Active Kasm sessions cache: key = f"{user_id}_{chat_id}"
ACTIVE_KASM_SESSIONS: dict[str, dict] = {}

DEFAULT_BROWSERS = [
    {
        'id': 'chrome',
        'name': 'Google Chrome',
        'image': 'kasmweb/chrome:1.16.0',
        'logo': '/assets/browsers/chrome.png',
        'description': 'Google Chrome with isolated profile & DevTools CDP',
        'default': True,
    },
    {
        'id': 'chromium',
        'name': 'Chromium',
        'image': 'kasmweb/chromium:1.16.0',
        'logo': '/assets/browsers/chromium.png',
        'description': 'Fast open-source Chromium Browser',
        'default': False,
    },
    {
        'id': 'firefox',
        'name': 'Mozilla Firefox',
        'image': 'kasmweb/firefox:1.16.0',
        'logo': '/assets/browsers/firefox.png',
        'description': 'Mozilla Firefox with privacy protections',
        'default': False,
    },
    {
        'id': 'brave',
        'name': 'Brave',
        'image': 'kasmweb/brave:1.16.0',
        'logo': '/assets/browsers/brave.png',
        'description': 'Brave Privacy Browser with ad-blocking',
        'default': False,
    },
    {
        'id': 'tor',
        'name': 'Tor Browser',
        'image': 'kasmweb/tor-browser:1.16.0',
        'logo': '/assets/browsers/tor.png',
        'description': 'Tor Anonymous & Onion Routing Browser',
        'default': False,
    },
    {
        'id': 'vivaldi',
        'name': 'Vivaldi Browser',
        'image': 'kasmweb/vivaldi:1.16.0',
        'logo': '/assets/browsers/vivaldi.png',
        'description': 'Vivaldi customizable feature-rich browser',
        'default': False,
    },
    {
        'id': 'edge',
        'name': 'Microsoft Edge',
        'image': 'kasmweb/edge:1.16.0',
        'logo': '/assets/browsers/edge.png',
        'description': 'Microsoft Edge Browser',
        'default': False,
    },
]


class StartSessionForm(BaseModel):
    chat_id: str
    browser_id: Optional[str] = 'chrome'


class StopSessionForm(BaseModel):
    chat_id: str


def get_session_dir(user_id: str, chat_id: str) -> Path:
    safe_user = ''.join(c for c in user_id if c.isalnum() or c in '-_') or 'user'
    safe_chat = ''.join(c for c in chat_id if c.isalnum() or c in '-_') or 'session'
    base = Path(DATA_DIR) / 'browser_sessions' / f"{safe_user}_{safe_chat}"
    base.mkdir(parents=True, exist_ok=True)
    return base


def save_profile_archive(session_dir: Path):
    """Compresses the browser profile folder into profile.tar.gz for permanent persistence."""
    profile_dir = session_dir / 'profile'
    if profile_dir.exists() and profile_dir.is_dir():
        archive_path = session_dir / 'profile.tar.gz'
        try:
            with tarfile.open(archive_path, 'w:gz') as tar:
                tar.add(profile_dir, arcname='.')
            log.info(f"Saved compressed profile archive to {archive_path}")
        except Exception as e:
            log.warning(f"Failed to compress profile directory: {e}")


def restore_profile_archive(session_dir: Path):
    """Unpacks profile.tar.gz if present into profile directory before container start."""
    archive_path = session_dir / 'profile.tar.gz'
    profile_dir = session_dir / 'profile'
    if archive_path.exists() and archive_path.is_file():
        try:
            profile_dir.mkdir(parents=True, exist_ok=True)
            with tarfile.open(archive_path, 'r:gz') as tar:
                if hasattr(tarfile, 'data_filter'):
                    tar.extractall(path=profile_dir, filter='data')
                else:
                    tar.extractall(path=profile_dir)
            log.info(f"Restored profile archive from {archive_path}")
        except Exception as e:
            log.warning(f"Failed to unpack profile archive: {e}")


async def destroy_kasm_container(kasm_id: str, user_id: str, kasm_url: str, api_key: str, api_secret: str) -> bool:
    """Invokes Kasm API /api/public/destroy_kasm to completely destroy container and free 100% RAM."""
    if not (kasm_url and api_key and api_secret and kasm_id):
        return False

    url = f"{kasm_url.rstrip('/')}/api/public/destroy_kasm"
    payload = {
        'api_key': api_key,
        'api_key_secret': api_secret,
        'kasm_id': kasm_id,
        'user_id': user_id,
    }

    try:
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                data = await resp.json()
                log.info(f"Kasm container {kasm_id} destroyed successfully: {data}")
                return True
    except Exception as e:
        log.warning(f"Error destroying Kasm container {kasm_id}: {e}")
        return False


async def cleanup_chat_browser_session(user_id: str, chat_id: str):
    """Called on chat deletion: destroys any active Kasm container and wipes disk profile data."""
    session_key = f"{user_id}_{chat_id}"
    active = ACTIVE_KASM_SESSIONS.pop(session_key, None)

    if active and active.get('kasm_id'):
        kasm_url = await Config.get('browser_sandbox.kasm.url', '')
        api_key = await Config.get('browser_sandbox.kasm.api_key', '')
        api_secret = await Config.get('browser_sandbox.kasm.api_secret', '')
        await destroy_kasm_container(active['kasm_id'], active.get('kasm_user_id', user_id), kasm_url, api_key, api_secret)

    # Wipe session files on disk
    try:
        session_dir = get_session_dir(user_id, chat_id)
        if session_dir.exists() and session_dir.is_dir():
            shutil.rmtree(session_dir, ignore_errors=True)
            log.info(f"Wiped browser session directory on chat deletion: {session_dir}")
    except Exception as e:
        log.warning(f"Error removing browser session directory: {e}")


@router.get('/browsers')
async def get_available_browsers(user=Depends(get_verified_user)):
    """Returns the list of available browsers configured by admin or system defaults."""
    custom_browsers = await Config.get('browser_sandbox.kasm.browsers', None)
    if custom_browsers is None:
        custom_browsers = ['chrome', 'vivaldi', 'firefox']
    elif isinstance(custom_browsers, str):
        try:
            custom_browsers = json.loads(custom_browsers)
        except Exception:
            custom_browsers = [b.strip() for b in custom_browsers.split(',') if b.strip()]

    if isinstance(custom_browsers, list) and len(custom_browsers) > 0:
        if isinstance(custom_browsers[0], str):
            # List of enabled browser IDs
            enabled_ids = set(custom_browsers)
            filtered = [b for b in DEFAULT_BROWSERS if b['id'] in enabled_ids]
            if filtered:
                return filtered
        elif isinstance(custom_browsers[0], dict):
            return custom_browsers
    return [b for b in DEFAULT_BROWSERS if b['id'] in ['chrome', 'vivaldi', 'firefox']]


@router.post('/session/start')
async def start_browser_session(request: Request, form_data: StartSessionForm, user=Depends(get_verified_user)):
    """Starts a live browser session with zero-waste Kasm container lifecycle and profile persistence."""
    chat_id = form_data.chat_id
    browser_id = form_data.browser_id or 'chrome'
    session_key = f"{user.id}_{chat_id}"

    provider = await Config.get('browser_sandbox.provider', 'browserless')
    kasm_url = await Config.get('browser_sandbox.kasm.url', '')
    kasm_api_key = await Config.get('browser_sandbox.kasm.api_key', '')
    kasm_api_secret = await Config.get('browser_sandbox.kasm.api_secret', '')
    kasm_user = await Config.get('browser_sandbox.kasm.user', 'kasm_user')
    kasm_password = await Config.get('browser_sandbox.kasm.password', '')
    kasm_cdp_url = await Config.get('browser_sandbox.kasm.cdp_url', '')

    # Return already active session if running the same browser
    if session_key in ACTIVE_KASM_SESSIONS:
        active = ACTIVE_KASM_SESSIONS[session_key]
        if active.get('browser_id') == browser_id:
            return {
                'status': True,
                'live_url': active.get('live_url'),
                'kasm_id': active.get('kasm_id'),
                'provider': active.get('provider', 'kasm'),
                'browser_id': active.get('browser_id', browser_id),
            }
        else:
            # Different browser selected: destroy old container and spin up new one
            old_kasm_id = active.get('kasm_id')
            old_kasm_user = active.get('kasm_user_id', user.id)
            del ACTIVE_KASM_SESSIONS[session_key]
            if old_kasm_id and kasm_url and kasm_api_key and kasm_api_secret:
                try:
                    await destroy_kasm_container(old_kasm_id, old_kasm_user, kasm_url, kasm_api_key, kasm_api_secret)
                    log.info(f"Destroyed previous Kasm container {old_kasm_id} when switching browser to {browser_id}")
                except Exception as e:
                    log.warning(f"Failed to destroy old container on browser switch: {e}")

    session_dir = get_session_dir(user.id, chat_id)
    # Restore any existing profile archive (cookies, sessions, login state)
    restore_profile_archive(session_dir)

    # Map browser_id to docker image or image ID
    browsers = await get_available_browsers(user)
    selected_browser = next((b for b in browsers if b['id'] == browser_id), browsers[0])
    image_identifier = selected_browser.get('image', 'kasmweb/chrome:1.16.0')

    # Case 1: Kasm Workspaces API Mode (On-demand container creation)
    if provider == 'kasm' and kasm_url and kasm_api_key and kasm_api_secret:
        api_endpoint = f"{kasm_url.rstrip('/')}/api/public/request_kasm"

        # Auto-resolve Kasm user_id: if username or email provided, lookup real Kasm UUID
        kasm_user_id = (kasm_user or '').strip()
        clean_uid = kasm_user_id.replace('-', '')
        is_already_uuid = (len(clean_uid) == 32 and all(c in '0123456789abcdefABCDEF' for c in clean_uid))
        if not is_already_uuid:
            try:
                users_url = f"{kasm_url.rstrip('/')}/api/public/get_users"
                async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
                    async with session.post(
                        users_url,
                        json={'api_key': kasm_api_key, 'api_key_secret': kasm_api_secret},
                        timeout=aiohttp.ClientTimeout(total=8),
                    ) as uresp:
                        if uresp.status == 200:
                            udata = await uresp.json()
                            users_list = udata.get('users', [])
                            target_uname = (kasm_user or '').strip().lower()
                            # 1. Match configured username / email
                            matched_user = next(
                                (
                                    u for u in users_list
                                    if target_uname and (
                                        (u.get('username') or '').lower() == target_uname
                                        or target_uname in (u.get('username') or '').lower()
                                    )
                                ),
                                None,
                            )
                            # 2. Match administrator account
                            if not matched_user:
                                matched_user = next(
                                    (
                                        u for u in users_list
                                        if any(
                                            isinstance(g, dict) and g.get('name') == 'Administrators'
                                            for g in u.get('groups', [])
                                        )
                                    ),
                                    None,
                                )
                            # 3. Match any active non-anonymous user
                            if not matched_user:
                                matched_user = next(
                                    (
                                        u for u in users_list
                                        if not u.get('anonymous') and not u.get('disabled')
                                    ),
                                    None,
                                )
                            if matched_user and matched_user.get('user_id'):
                                kasm_user_id = matched_user['user_id']
                                log.info(f"Resolved Kasm username '{kasm_user}' to user_id '{kasm_user_id}' ({matched_user.get('username')})")
            except Exception as e:
                log.warning(f"Failed to auto-resolve Kasm user: {e}")

        # Auto-resolve Kasm workspace image_id via get_images
        actual_image_id = image_identifier
        try:
            images_url = f"{kasm_url.rstrip('/')}/api/public/get_images"
            async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
                async with session.post(
                    images_url,
                    json={'api_key': kasm_api_key, 'api_key_secret': kasm_api_secret},
                    timeout=aiohttp.ClientTimeout(total=8),
                ) as iresp:
                    if iresp.status == 200:
                        idata = await iresp.json()
                        img_list = idata.get('images', [])
                        target_name = browser_id.lower()
                        matched_img = next(
                            (
                                img for img in img_list
                                if target_name in (img.get('friendly_name') or '').lower()
                                or target_name in (img.get('docker_image') or '').lower()
                            ),
                            None,
                        )
                        if matched_img and matched_img.get('image_id'):
                            actual_image_id = matched_img['image_id']
                            log.info(f"Resolved browser '{browser_id}' to Kasm image_id '{actual_image_id}' ({matched_img.get('friendly_name')})")
        except Exception as e:
            log.warning(f"Failed to auto-resolve Kasm image: {e}")

        payload = {
            'api_key': kasm_api_key,
            'api_key_secret': kasm_api_secret,
            'image_id': actual_image_id,
            'enable_sharing': True,
        }
        if kasm_user_id:
            payload['user_id'] = kasm_user_id

        try:
            async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
                async with session.post(api_endpoint, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    data = await resp.json()

                    if resp.status != 200 or data.get('error_message'):
                        err = data.get('error_message') or f"Kasm API error (HTTP {resp.status})"
                        log.error(f"Failed to start Kasm container: {err}")
                        return {
                            'status': False,
                            'error': err,
                            'provider': 'kasm'
                        }

                    kasm_id = data.get('kasm_id') or (data.get('kasm') or {}).get('kasm_id')
                    share_id = data.get('share_id') or (data.get('kasm') or {}).get('share_id')
                    kasm_live_url = data.get('kasm_url') or (data.get('kasm') or {}).get('kasm_url')
                    session_token = (
                        data.get('session_token')
                        or data.get('operational_token')
                        or (data.get('kasm') or {}).get('session_token')
                        or (data.get('kasm') or {}).get('operational_token')
                    )

                    base_url = kasm_url.rstrip('/')

                    if kasm_live_url:
                        if not (kasm_live_url.startswith('http://') or kasm_live_url.startswith('https://')):
                            kasm_live_url = f"{base_url}{kasm_live_url if kasm_live_url.startswith('/') else '/' + kasm_live_url}"
                    elif share_id:
                        kasm_live_url = f"{base_url}/#/join/{share_id}"
                    elif kasm_id and session_token:
                        kasm_live_url = f"{base_url}/#/connect/kasm/{kasm_id}/{quote(session_token)}"
                    elif kasm_id:
                        kasm_live_url = f"{base_url}/#/session/{kasm_id}"
                    else:
                        kasm_live_url = base_url

                    # Ensure container has reached 'running' state before returning live_url
                    # (Prevents Kasm 'Connection Failed' due to premature WebRTC negotiation)
                    if kasm_id:
                        try:
                            status_url = f"{base_url}/api/public/get_kasm_status"
                            for _ in range(15):
                                await asyncio.sleep(2)
                                async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as st_session:
                                    async with st_session.post(
                                        status_url,
                                        json={'api_key': kasm_api_key, 'api_key_secret': kasm_api_secret, 'kasm_id': kasm_id},
                                        timeout=aiohttp.ClientTimeout(total=3),
                                    ) as st_resp:
                                        if st_resp.status == 200:
                                            st_data = await st_resp.json()
                                            k_st = st_data.get('kasm', {})
                                            if k_st.get('operational_status') == 'running' or k_st.get('status') == 'running':
                                                log.info(f"Kasm container {kasm_id} is running and ready for connection.")
                                                break
                        except Exception as e:
                            log.debug(f"Kasm readiness poll notice: {e}")

                    ACTIVE_KASM_SESSIONS[session_key] = {
                        'kasm_id': kasm_id,
                        'live_url': kasm_live_url,
                        'share_id': share_id,
                        'user_id': user.id,
                        'kasm_user_id': kasm_user_id,
                        'chat_id': chat_id,
                        'browser_id': browser_id,
                        'provider': 'kasm_api',
                        'started_at': time.time(),
                    }

                    log.info(f"Started Kasm Workspaces API container {kasm_id} for user {user.id} chat {chat_id}")
                    return {
                        'status': True,
                        'live_url': kasm_live_url,
                        'kasm_id': kasm_id,
                        'provider': 'kasm',
                        'browser_id': browser_id,
                    }
        except Exception as e:
            log.exception(f"Failed to request Kasm Workspaces container: {e}")
            # Fallback to standalone Kasm URL if API fails

    # Case 2: Standalone Kasm Container Mode
    if provider == 'kasm' and kasm_url:
        clean_url = kasm_url.rstrip('/')
        auth_query = ''
        if kasm_password:
            auth_query = f"?password={quote(kasm_password)}&username={quote(kasm_user)}"
        live_url = f"{clean_url}/{auth_query}"

        ACTIVE_KASM_SESSIONS[session_key] = {
            'live_url': live_url,
            'user_id': user.id,
            'chat_id': chat_id,
            'browser_id': browser_id,
            'provider': 'kasm_standalone',
            'started_at': time.time(),
        }

        return {
            'status': True,
            'live_url': live_url,
            'cdp_url': kasm_cdp_url or None,
            'provider': 'kasm',
            'browser_id': browser_id,
        }

    # Case 3: Browserless / Generic VNC Mode
    live_url = await Config.get('browser_sandbox.live_url', 'http://localhost:6080/vnc.html')
    cdp_url = await Config.get('browser_sandbox.url', 'http://localhost:3000')

    ACTIVE_KASM_SESSIONS[session_key] = {
        'live_url': live_url,
        'user_id': user.id,
        'chat_id': chat_id,
        'browser_id': browser_id,
        'provider': provider,
        'started_at': time.time(),
    }

    return {
        'status': True,
        'live_url': live_url,
        'cdp_url': cdp_url,
        'provider': provider,
        'browser_id': browser_id,
    }


@router.post('/session/stop')
async def stop_browser_session(request: Request, form_data: StopSessionForm, user=Depends(get_verified_user)):
    """Stops the browser session: compresses profile and destroys Kasm container to free 100% memory."""
    chat_id = form_data.chat_id
    session_key = f"{user.id}_{chat_id}"

    # Compress and persist browser cookies & sessions
    session_dir = get_session_dir(user.id, chat_id)
    save_profile_archive(session_dir)

    active = ACTIVE_KASM_SESSIONS.pop(session_key, None)
    if active and active.get('kasm_id'):
        kasm_url = await Config.get('browser_sandbox.kasm.url', '')
        api_key = await Config.get('browser_sandbox.kasm.api_key', '')
        api_secret = await Config.get('browser_sandbox.kasm.api_secret', '')
        await destroy_kasm_container(active['kasm_id'], active.get('kasm_user_id', user.id), kasm_url, api_key, api_secret)

    return {'status': True, 'message': 'Browser session stopped and resources freed.'}
