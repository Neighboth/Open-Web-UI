"""Helpers for resolving video generation options.

The video tool is exposed to language models as a function with optional
``duration`` and ``size`` arguments.  Models frequently fill optional
arguments with a value they consider reasonable, even when the user did not
ask for one.  These helpers keep the configured Admin defaults authoritative
unless the latest user message explicitly mentions an option.

The module intentionally has no Open WebUI imports so that the behaviour can
be tested without bootstrapping the application.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any


def _message_text(message: Any) -> str:
    """Return text from an OpenAI-style message or content part."""

    if isinstance(message, str):
        return message
    if not isinstance(message, Mapping):
        return ''

    content = message.get('content', '')
    if isinstance(content, str):
        return content
    if not isinstance(content, Iterable):
        return ''

    parts: list[str] = []
    for part in content:
        if isinstance(part, str):
            parts.append(part)
        elif isinstance(part, Mapping):
            text = part.get('text')
            if isinstance(text, str):
                parts.append(text)
    return ' '.join(parts)


def latest_user_message(messages: Iterable[Mapping[str, Any]] | None) -> str:
    """Get the latest user message as plain text.

    The helper returns an empty string for absent/malformed messages.  Callers
    that do not have chat context should therefore skip filtering and retain
    explicitly supplied API values.
    """

    if messages is None:
        return ''
    for message in reversed(list(messages)):
        if isinstance(message, Mapping) and message.get('role') == 'user':
            return _message_text(message)
    return ''


def _normalise_size(value: Any) -> str:
    return re.sub(r'\s+', '', str(value or '').strip().lower())


def _size_was_requested(text: str, value: Any) -> bool:
    normalised = _normalise_size(value)
    if not normalised:
        return False

    # Accept both ``1080P`` and common spacing around dimensions (``1920 x
    # 1080``). Match against the original text so word boundaries remain
    # meaningful; stripping all spaces from the prompt made ``1080P`` fail to
    # match when it appeared next to ordinary words.
    escaped = r'\s*'.join(re.escape(character) for character in normalised)
    return re.search(rf'(?<![\w]){escaped}(?![\w])', text, re.IGNORECASE) is not None


def _duration_was_requested(text: str, value: Any) -> bool:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return False
    if number <= 0:
        return False

    # A duration is explicit when the number is paired with a duration unit,
    # or with a duration label.  This deliberately ignores unrelated numbers
    # in prompts (for example, "8 scenes").
    number_pattern = re.escape(str(number))
    units = r'(?:s|sec|secs|second|seconds|sn|saniye|saniyelik)'
    return bool(
        re.search(rf'(?<![\w]){number_pattern}\s*[-–]?\s*{units}\b', text, re.IGNORECASE)
        or re.search(
            rf'\b(?:duration|length|süre|sure|uzunluk)\s*(?:(?:is|of|:|=)\s*)?{number_pattern}\b',
            text,
            re.IGNORECASE,
        )
    )


def option_was_requested(messages: Iterable[Mapping[str, Any]] | None, option: str, value: Any) -> bool:
    """Return whether the user explicitly requested a video option."""

    text = latest_user_message(messages)
    if not text:
        return False
    if option == 'size':
        return _size_was_requested(text, value)
    if option == 'duration':
        return _duration_was_requested(text, value)
    return False


def filter_unrequested_video_options(form_data: Mapping[str, Any], messages: Iterable[Mapping[str, Any]] | None) -> dict:
    """Remove model-inferred size/duration values from a tool invocation.

    ``None`` for ``messages`` means the request came from an API caller with
    no chat context; in that case values are preserved.  Native tool calls
    always pass the chat messages and therefore fall back to Admin defaults
    when the model invents optional values.
    """

    result = dict(form_data)
    if messages is None:
        return result

    for option in ('size', 'duration'):
        if option in result and result[option] is not None and not option_was_requested(messages, option, result[option]):
            result.pop(option)
    return result


def resolve_duration(value: Any, default: Any) -> int | str | None:
    """Resolve a positive duration, falling back to the configured default."""

    candidate = value if value not in (None, '') else default
    if candidate in (None, ''):
        return None
    try:
        parsed = int(candidate)
    except (TypeError, ValueError):
        return candidate if isinstance(candidate, str) else default
    return parsed if parsed > 0 else default


def resolve_size(value: Any, default: Any, configured_size: Any = None) -> Any:
    """Resolve a non-empty size, falling back to the configured default."""

    candidate = value if value not in (None, '') else default or configured_size
    if candidate in (None, ''):
        return None
    return str(candidate).strip() or (default or configured_size)
