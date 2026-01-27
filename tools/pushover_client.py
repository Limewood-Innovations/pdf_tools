# -*- coding: utf-8 -*-
"""Pushover notification client.

This module provides a simple interface for sending push notifications
via the Pushover service.
"""

import logging
import os
import sys
from typing import Optional

import requests

logger = logging.getLogger(__name__)


def send_pushover_message(
    message: str,
    user_key: Optional[str] = None,
    token: Optional[str] = None,
    title: Optional[str] = None,
    priority: int = 0,
    timeout: int = 30,
) -> bool:
    """Send a push notification via Pushover.

    Sends a message to the configured Pushover user. Configuration can be
    provided via parameters or environment variables.

    Args:
        message: Message text to send.
        user_key: Pushover user key. If ``None``, uses ``PUSHOVER_USER_KEY``
            environment variable.
        token: Pushover application token. If ``None``, uses ``PUSHOVER_TOKEN``
            environment variable.
        title: Optional message title.
        priority: Message priority from -2 (lowest) to 2 (highest). Default: 0.
        timeout: Request timeout in seconds (default: 30).

    Returns:
        bool: ``True`` if the message was sent successfully, ``False`` otherwise.

    Note:
        If credentials are not configured, a warning is printed to stderr
        and the function returns ``False`` without raising an exception.

    Example:
        >>> send_pushover_message("Processing complete", title="PDF Tools")
        True
    """
    if user_key is None:
        user_key = os.getenv("PUSHOVER_USER_KEY")

    if token is None:
        token = os.getenv("PUSHOVER_TOKEN")

    if not user_key or not token:
        logger.warning(
            "Pushover not configured (missing user_key or token); "
            "skipping notification"
        )
        return False

    payload = {
        "token": token,
        "user": user_key,
        "message": message,
    }

    if title:
        payload["title"] = title

    if priority != 0:
        payload["priority"] = priority

    try:
        resp = requests.post(
            "https://api.pushover.net/1/messages.json",
            data=payload,
            timeout=timeout,
        )
        resp.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Failed to send Pushover message: {e}")
        return False
