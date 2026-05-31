"""Build session reports via ReportGenerator."""

from services import graph_state, session_state
from services.report_generator import ReportGenerator

_generator = ReportGenerator()


def build_session_report(session_id: str) -> dict:
    """Return the full report dict for a session id."""
    session = session_state.get_session(session_id)
    if session is None:
        raise LookupError(f"Sesión '{session_id}' no encontrada.")

    graph = graph_state.get_graph()
    if graph is None:
        raise RuntimeError("No hay grafo cargado. Usa POST /api/load-graph primero.")

    trip_report = session.finalize_and_report()
    decisions = list(getattr(session.state, "decisions", []) or [])

    report = _generator.generate(
        graph=graph,
        trip_report=trip_report,
        decisions=decisions,
    )

    return {
        "session_id": session_id,
        **report,
    }
