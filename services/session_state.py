"""In-memory registry of active trip sessions (R3).

Written by graph_routes when a session starts; read by report_routes and
other session endpoints.
"""

from typing import Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from services.trip_session import TripSession

_sessions: Dict[str, "TripSession"] = {}


def register_session(session: "TripSession") -> str:
    """Store a session and return its id."""
    _sessions[session.session_id] = session
    return session.session_id


def get_session(session_id: str) -> Optional["TripSession"]:
    """Return a session by id, or None if it does not exist."""
    return _sessions.get(session_id)
