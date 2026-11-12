"""Explicit, process-local activation for external messaging.

Importing modules or approving routine service maintenance never enables these
channels. This module reads no configuration files and changes no environment.
"""

import os


RECDEBUT_OUTBOUND_FLAG = "AI_BS_RECDEBUT_OUTBOUND_ENABLED"
RECDEBUT_SENDING_FLAG = "RECDEBUT_SENDING_ENABLED"
RECDEBUT_POLLING_FLAG = "AI_BS_RECDEBUT_INBOUND_POLLING_ENABLED"
DISCORD_NOTIFICATIONS_FLAG = "AI_BS_DISCORD_NOTIFICATIONS_ENABLED"
DASHBOARD_NOTIFICATIONS_FLAG = "AI_BS_DASHBOARD_NOTIFICATIONS_ENABLED"
RECDEBUT_DISABLED_MESSAGE = "RecDebut outbound messaging is disabled. No message was sent."
RECDEBUT_REVIEW_HOLD = True  # Audit hold overrides activation flags until outbound acceptance is verified.

_CHANNEL_FLAGS = {
    "recdebut": RECDEBUT_OUTBOUND_FLAG,
    "discord": DISCORD_NOTIFICATIONS_FLAG,
    "dashboard": DASHBOARD_NOTIFICATIONS_FLAG,
}


def _explicitly_enabled(flag: str) -> bool:
    return os.environ.get(flag, "").strip().lower() == "true"


def outbound_messaging_enabled(channel: str) -> bool:
    """Unknown channels and unset/non-true values always fail closed."""
    if channel == 'recdebut' and RECDEBUT_REVIEW_HOLD:
        return False
    if channel == 'recdebut':
        return _explicitly_enabled(RECDEBUT_OUTBOUND_FLAG) or _explicitly_enabled(RECDEBUT_SENDING_FLAG)
    flag = _CHANNEL_FLAGS.get(channel)
    return bool(flag and _explicitly_enabled(flag))


def recdebut_polling_enabled() -> bool:
    """Polling also forwards eligible replies, so both activations are needed."""
    return outbound_messaging_enabled("recdebut") and _explicitly_enabled(RECDEBUT_POLLING_FLAG)
