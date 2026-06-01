from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from models.planner_models import TripConfig, TripState

from services.trip_session_clock import TripSessionClockMixin
from services.trip_session_decisions import TripSessionDecisionMixin
from services.trip_session_persistence import TripSessionPersistenceMixin
from services.trip_session_reporting import TripSessionReportingMixin
from services.trip_session_transport import TripSessionTransportMixin

if TYPE_CHECKING:
    from services.advanced_planner import AdvancedPlanner


class TripSession(
    TripSessionClockMixin,
    TripSessionTransportMixin,
    TripSessionDecisionMixin,
    TripSessionPersistenceMixin,
    TripSessionReportingMixin,
):
    """Represents a step-by-step interactive session managed by the advanced planner.

    The UI should call ``step_proposals()`` and then ``apply_choice()``
    according to the traveler decision. Every decision is stored in
    ``state.decisions``.
    """

    def __init__(self, config: TripConfig, initial_state: TripState, planner: "AdvancedPlanner") -> None:
        """Store the session configuration, initial state, and parent planner."""
        self.config = config
        self.state = initial_state
        self.planner = planner
        self.session_id = str(uuid.uuid4())


__all__ = ["TripSession"]