from __future__ import annotations

from .session_manager import session_manager
from .session_store import SessionStore


# Single binding used by TELEPAT runtime layers.
# Swap this binding when shared session storage is introduced.
session_store: SessionStore = session_manager
