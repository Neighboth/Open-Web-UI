"""A small Chrome DevTools Protocol client for the browser sandbox.

The sandbox hands out a remote browser.  To let the model actually *use* it
(click, scroll, type, drag, select, delete, read, look) the browser has to be
driven with the Chrome DevTools Protocol.  Only a handful of domains are
needed, so this is a focused client instead of a full browser automation
stack.

No extra dependency: the WebSocket is handled by aiohttp, which the backend
already uses.
"""

import asyncio
import base64
import json
import logging
from typing import Any
from urllib.parse import urljoin, urlparse

import aiohttp

from open_webui.utils.json_codec import JSONCodec

log = logging.getLogger(__name__)

# Container port that Chrome exposes for the DevTools protocol.
CDP_CONTAINER_PORT = 9222


class CdpError(Exception):
    """A DevTools command could not be executed."""


class CdpUnavailable(CdpError):
    """No DevTools endpoint could be reached for the session."""


class CdpClient:
    """Drives one browser tab over the DevTools protocol."""

    def __init__(self, ws_url: str, session: aiohttp.ClientSession | None = None):
        self.ws_url = ws_url
        self._session = session
        self._owns_session = session is None
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._next_id = 0

    async def __aenter__(self) -> 'CdpClient':
        if self._session is None:
            self._session = aiohttp.ClientSession()
        try:
            self._ws = await self._session.ws_connect(self.ws_url, heartbeat=20, max_msg_size=32 * 1024 * 1024)
        except Exception as error:
            await self.close()
            raise CdpUnavailable(f'Could not open the DevTools connection: {error}') from error
        return self

    async def __aexit__(self, *args):
        await self.close()

    async def close(self):
        if self._ws is not None:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None
        if self._owns_session and self._session is not None:
            try:
                await self._session.close()
            except Exception:
                pass
            self._session = None

    async def send(self, method: str, params: dict | None = None, timeout: float = 30.0) -> dict:
        """Run one DevTools command and return its result."""
        if self._ws is None:
            raise CdpError('The DevTools connection is closed')
        self._next_id += 1
        message_id = self._next_id
        await self._ws.send_json({'id': message_id, 'method': method, 'params': params or {}})

        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        while True:
            remaining = deadline - loop.time()
            if remaining <= 0:
                raise CdpError(f'The DevTools command "{method}" timed out')
            message = await self._ws.receive(timeout=remaining)
            if message.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.CLOSING, aiohttp.WSMsgType.ERROR):
                raise CdpError(f'The DevTools connection closed while running "{method}"')
            if message.type != aiohttp.WSMsgType.TEXT:
                continue
            try:
                data = JSONCodec.loads(message.data)
            except Exception:
                continue
            if data.get('id') != message_id:
                continue
            if 'error' in data:
                error = data['error'] or {}
                raise CdpError(f'{method} failed: {error.get("message", error)}')
            return data.get('result') or {}

    async def evaluate(self, expression: str, timeout: float = 30.0) -> Any:
        """Evaluate JavaScript in the page and return the value."""
        result = await self.send(
            'Runtime.evaluate',
            {
                'expression': expression,
                'returnByValue': True,
                'awaitPromise': True,
                'userGesture': True,
            },
            timeout=timeout,
        )
        details = result.get('exceptionDetails')
        if details:
            text = details.get('exception', {}).get('description') or details.get('text') or 'script error'
            raise CdpError(str(text)[:300])
        return (result.get('result') or {}).get('value')

    async def screenshot(self, full_page: bool = False) -> str:
        """Capture the page and return it as base64 encoded PNG."""
        params: dict[str, Any] = {'format': 'png'}
        if full_page:
            metrics = await self.send('Page.getLayoutMetrics')
            size = metrics.get('cssContentSize') or metrics.get('contentSize') or {}
            width = int(size.get('width') or 0)
            height = int(size.get('height') or 0)
            if width and height:
                params['captureBeyondViewport'] = True
                params['clip'] = {'x': 0, 'y': 0, 'width': width, 'height': height, 'scale': 1}
        result = await self.send('Page.captureScreenshot', params, timeout=45)
        return result.get('data') or ''

    async def navigate(self, url: str, timeout: float = 30.0) -> None:
        await self.send('Page.navigate', {'url': url}, timeout=timeout)

    async def click(self, x: int, y: int, button: str = 'left', click_count: int = 1) -> None:
        """Click at a viewport position with a real (trusted) mouse event."""
        base = {'x': int(x), 'y': int(y), 'button': button, 'clickCount': click_count}
        await self.send('Input.dispatchMouseEvent', {**base, 'type': 'mouseMoved'})
        await self.send('Input.dispatchMouseEvent', {**base, 'type': 'mousePressed'})
        await self.send('Input.dispatchMouseEvent', {**base, 'type': 'mouseReleased'})

    async def drag(self, x1: int, y1: int, x2: int, y2: int, steps: int = 12) -> None:
        """Press at the first position, move to the second and release."""
        await self.send(
            'Input.dispatchMouseEvent',
            {'type': 'mousePressed', 'x': int(x1), 'y': int(y1), 'button': 'left', 'clickCount': 1},
        )
        for step in range(1, max(steps, 1) + 1):
            ratio = step / max(steps, 1)
            await self.send(
                'Input.dispatchMouseEvent',
                {
                    'type': 'mouseMoved',
                    'x': int(x1 + (x2 - x1) * ratio),
                    'y': int(y1 + (y2 - y1) * ratio),
                    'button': 'left',
                    'buttons': 1,
                },
            )
        await self.send(
            'Input.dispatchMouseEvent',
            {'type': 'mouseReleased', 'x': int(x2), 'y': int(y2), 'button': 'left', 'clickCount': 1},
        )

    async def scroll(self, x: int, y: int, delta_x: int = 0, delta_y: int = 0) -> None:
        """Scroll with the mouse wheel at a viewport position."""
        await self.send(
            'Input.dispatchMouseEvent',
            {
                'type': 'mouseWheel',
                'x': int(x),
                'y': int(y),
                'deltaX': int(delta_x),
                'deltaY': int(delta_y),
            },
        )

    async def insert_text(self, text: str) -> None:
        """Type text into the focused element."""
        await self.send('Input.insertText', {'text': text})

    async def press_key(self, key: str, modifiers: int = 0) -> None:
        """Press a key such as Enter, Tab, Backspace, Delete or ArrowDown."""
        spec = KEY_SPECS.get(key.lower(), KEY_SPECS.get(key, None))
        if spec is None:
            spec = _key_spec_from_name(key)
        payload = {'key': spec['key'], 'code': spec['code'], 'windowsVirtualKeyCode': spec['vk']}
        if spec.get('text'):
            payload['text'] = spec['text']
        if modifiers:
            payload['modifiers'] = modifiers
        await self.send('Input.dispatchKeyEvent', {**payload, 'type': 'keyDown'})
        await self.send('Input.dispatchKeyEvent', {**payload, 'type': 'keyUp'})


# Key definitions for Input.dispatchKeyEvent.
KEY_SPECS: dict[str, dict] = {
    'enter': {'key': 'Enter', 'code': 'Enter', 'vk': 13, 'text': '\r'},
    'return': {'key': 'Enter', 'code': 'Enter', 'vk': 13, 'text': '\r'},
    'tab': {'key': 'Tab', 'code': 'Tab', 'vk': 9, 'text': '\t'},
    'escape': {'key': 'Escape', 'code': 'Escape', 'vk': 27},
    'esc': {'key': 'Escape', 'code': 'Escape', 'vk': 27},
    'backspace': {'key': 'Backspace', 'code': 'Backspace', 'vk': 8},
    'delete': {'key': 'Delete', 'code': 'Delete', 'vk': 46},
    'space': {'key': ' ', 'code': 'Space', 'vk': 32, 'text': ' '},
    'arrowup': {'key': 'ArrowUp', 'code': 'ArrowUp', 'vk': 38},
    'arrowdown': {'key': 'ArrowDown', 'code': 'ArrowDown', 'vk': 40},
    'arrowleft': {'key': 'ArrowLeft', 'code': 'ArrowLeft', 'vk': 37},
    'arrowright': {'key': 'ArrowRight', 'code': 'ArrowRight', 'vk': 39},
    'pageup': {'key': 'PageUp', 'code': 'PageUp', 'vk': 33},
    'pagedown': {'key': 'PageDown', 'code': 'PageDown', 'vk': 34},
    'home': {'key': 'Home', 'code': 'Home', 'vk': 36},
    'end': {'key': 'End', 'code': 'End', 'vk': 35},
    'ctrl+a': {'key': 'a', 'code': 'KeyA', 'vk': 65, 'text': 'a'},
    'ctrl+c': {'key': 'c', 'code': 'KeyC', 'vk': 67, 'text': 'c'},
    'ctrl+v': {'key': 'v', 'code': 'KeyV', 'vk': 86, 'text': 'v'},
    'ctrl+x': {'key': 'x', 'code': 'KeyX', 'vk': 88, 'text': 'x'},
}


def _key_spec_from_name(name: str) -> dict:
    """Build a key definition for a single printable character."""
    if len(name) == 1:
        return {
            'key': name,
            'code': f'Key{name.upper()}' if name.isalpha() else 'Unidentified',
            'vk': ord(name.upper()),
            'text': name,
        }
    return {'key': name, 'code': name, 'vk': 0}


async def discover_cdp_url(
    configured: str | None,
    *,
    kasm_url: str = '',
    kasm_id: str = '',
    api_key: str = '',
    api_secret: str = '',
    session: aiohttp.ClientSession | None = None,
) -> str | None:
    """Find the DevTools WebSocket URL of the sandbox browser.

    An explicitly configured address always wins.  Otherwise the Kasm
    container is asked for its port mapping, because the DevTools port of the
    browser is published there.
    """
    if configured:
        candidate = configured.strip()
        if candidate.startswith('ws://') or candidate.startswith('wss://'):
            return candidate
        resolved = await _resolve_http_to_ws(candidate, session=session)
        if resolved:
            return resolved

    if not (kasm_url and kasm_id and api_key and api_secret):
        return None

    try:
        from open_webui.routers.browser import kasm_post

        data = await kasm_post(
            kasm_url,
            '/api/public/get_kasms',
            {'api_key': api_key, 'api_key_secret': api_secret},
            attempts=2,
        )
    except Exception as error:
        log.info('Could not read the Kasm port mapping: %s', error)
        return None

    host = ''
    port = None
    for kasm in data.get('kasms', []) if isinstance(data, dict) else []:
        if (kasm.get('kasm_id') or '').replace('-', '') != str(kasm_id).replace('-', ''):
            continue
        host = kasm.get('hostname') or ''
        port_map = kasm.get('port_map') or {}
        for entry in port_map.values() if isinstance(port_map, dict) else []:
            if not isinstance(entry, dict):
                continue
            container_port = entry.get('container_port') or entry.get('internal_port')
            if int(container_port or 0) == CDP_CONTAINER_PORT:
                port = entry.get('host_port') or entry.get('external_port')
                break
        break

    if not host or not port:
        return None
    base = f'http://{host}:{port}'
    return await _resolve_http_to_ws(base, session=session)


async def _resolve_http_to_ws(base_url: str, session: aiohttp.ClientSession | None = None) -> str | None:
    """Turn a DevTools HTTP endpoint into the WebSocket URL of the page."""
    owns = session is None
    session = session or aiohttp.ClientSession()
    try:
        base_url = base_url.rstrip('/')
        async with session.get(f'{base_url}/json/list', timeout=aiohttp.ClientTimeout(total=8)) as response:
            if response.status != 200:
                return None
            targets = await response.json(content_type=None)
        for target in targets or []:
            if target.get('type') == 'page' and target.get('webSocketDebuggerUrl'):
                return target['webSocketDebuggerUrl']
        for target in targets or []:
            if target.get('webSocketDebuggerUrl'):
                return target['webSocketDebuggerUrl']
        return None
    except Exception as error:
        log.info('No DevTools endpoint at %s: %s', base_url, error)
        return None
    finally:
        if owns:
            await session.close()


# The script that reads the page for the model: the visible text plus the
# interactive elements with their viewport position, so the model can aim.
PAGE_SNAPSHOT_SCRIPT = r"""
(() => {
  const isVisible = (el) => {
    const r = el.getBoundingClientRect();
    if (r.width <= 0 || r.height <= 0) return false;
    const style = getComputedStyle(el);
    return style.visibility !== 'hidden' && style.display !== 'none' && style.opacity !== '0';
  };
  const describe = (el) => {
    const r = el.getBoundingClientRect();
    const parts = [];
    const text = (el.innerText || el.value || el.placeholder || '').trim().replace(/\s+/g, ' ');
    if (text) parts.push(text.slice(0, 80));
    const label = el.getAttribute('aria-label') || el.getAttribute('title') || el.getAttribute('name') || '';
    if (label) parts.push(label);
    const role = el.getAttribute('role') || el.tagName.toLowerCase();
    return {
      role,
      text: parts.join(' | ').slice(0, 120),
      x: Math.round(r.left + r.width / 2),
      y: Math.round(r.top + r.height / 2),
      w: Math.round(r.width),
      h: Math.round(r.height)
    };
  };
  const interactive = [];
  const seen = new Set();
  const selector = 'a, button, input, textarea, select, [role="button"], [role="link"], [onclick], [contenteditable="true"]';
  for (const el of document.querySelectorAll(selector)) {
    if (!isVisible(el)) continue;
    const key = el.tagName + ':' + (el.innerText || el.value || '').slice(0, 24) + ':' + el.getBoundingClientRect().top;
    if (seen.has(key)) continue;
    seen.add(key);
    interactive.push(describe(el));
    if (interactive.length >= 120) break;
  }
  const bodyText = (document.body ? document.body.innerText : '').replace(/\n{3,}/g, '\n\n').trim();
  return {
    url: location.href,
    title: document.title,
    scroll: { x: Math.round(window.scrollX), y: Math.round(window.scrollY), max: Math.round(document.body ? document.body.scrollHeight : 0) },
    viewport: { w: window.innerWidth, h: window.innerHeight },
    text: bodyText.slice(0, 6000),
    interactive
  };
})()
"""


def build_click_script(text: str) -> str:
    """Script that finds an element by its visible text and returns its position."""
    needle = json.dumps(text)
    return f"""
(() => {{
  const needle = {needle}.toLowerCase();
  const nodes = Array.from(document.querySelectorAll('a, button, [role="button"], [role="link"], input[type="submit"], input[type="button"], li, td, span, div, label'));
  for (const el of nodes) {{
    const r = el.getBoundingClientRect();
    if (r.width <= 0 || r.height <= 0) continue;
    const label = (el.innerText || el.value || el.getAttribute('aria-label') || '').trim().toLowerCase();
    if (!label || !label.includes(needle)) continue;
    if (nodes.some((other) => other !== el && other.contains(el) && (other.innerText || '').trim().toLowerCase().includes(needle))) {{
      continue;
    }}
    return {{ found: true, x: Math.round(r.left + r.width / 2), y: Math.round(r.top + r.height / 2), text: label.slice(0, 120) }};
  }}
  return {{ found: false }};
}})()
"""


def build_select_script(option_text: str) -> str:
    """Script that selects an option in a <select> element."""
    needle = json.dumps(option_text)
    return f"""
(() => {{
  const needle = {needle}.toLowerCase();
  const selects = Array.from(document.querySelectorAll('select'));
  for (const sel of selects) {{
    for (const opt of Array.from(sel.options)) {{
      const label = (opt.textContent || '').trim().toLowerCase();
      if (label === needle || label.includes(needle)) {{
        sel.value = opt.value;
        sel.dispatchEvent(new Event('input', {{ bubbles: true }}));
        sel.dispatchEvent(new Event('change', {{ bubbles: true }}));
        return {{ found: true, value: opt.value, label: opt.textContent.trim() }};
      }}
    }}
  }}
  return {{ found: false, selects: selects.length }};
}})()
"""


def build_find_script(text: str) -> str:
    """Script that scrolls a piece of text into view."""
    needle = json.dumps(text)
    return f"""
(() => {{
  const needle = {needle}.toLowerCase();
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let node;
  while ((node = walker.nextNode())) {{
    const value = (node.nodeValue || '').toLowerCase();
    const index = value.indexOf(needle);
    if (index === -1) continue;
    const range = document.createRange();
    range.setStart(node, index);
    range.setEnd(node, index + needle.length);
    const rect = range.getBoundingClientRect();
    range.startContainer.scrollIntoView({{ block: 'center', inline: 'nearest' }});
    return {{ found: true, x: Math.round(rect.left + rect.width / 2), y: Math.round(rect.top + rect.height / 2) }};
  }}
  return {{ found: false }};
}})()
"""


def normalize_url(base: str, url: str) -> str:
    """Resolve a possibly relative URL against the current page."""
    if not url:
        return base
    if url.startswith(('http://', 'https://', 'about:', 'data:', 'file://', 'javascript:')):
        return url
    if base.startswith('http'):
        return urljoin(base, url)
    return url


def is_http_url(url: str) -> bool:
    try:
        return urlparse(url).scheme in {'http', 'https'}
    except ValueError:
        return False


def decode_image(data: str) -> bytes:
    """Decode a base64 encoded PNG."""
    return base64.b64decode(data)
