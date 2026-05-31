"""Flask routes for trip session interactions."""

import routes.graph_routes as graph_routes

from flask import Blueprint, jsonify, request

trip_session_bp = Blueprint("trip_session", __name__)


@trip_session_bp.route("/api/session/<session_id>/close", methods=["POST"])
def close_session(session_id: str):
    """Close an active session.

    Args:
        session_id: Session identifier to close.

    Returns:
        Response: JSON response indicating whether the session was closed.
    """
    session = graph_routes._SESSIONS.pop(session_id, None)
    if session is None:
        return jsonify({"error": "session not found"}), 404

    return jsonify({
        "message": "Session closed",
        "session_id": session_id,
        "lock_state": graph_routes._config_lock_state(),
    })


@trip_session_bp.route("/api/session/start", methods=["POST"])
def start_session():
    """Start a planning session.

    Returns:
        Response: JSON response with the session identifier, proposals, and metadata.
    """
    payload = request.get_json(silent=True) or {}
    origin = (payload.get("origin") or payload.get("start") or "").strip().upper()
    try:
        budget = float(payload.get("budget", 0))
    except (TypeError, ValueError):
        budget = 0.0
    try:
        time_h = float(payload.get("time_h", payload.get("hours", 72)))
    except (TypeError, ValueError):
        time_h = 72.0

    if graph_routes._ADVANCED_PLANNER is None or graph_routes._LAST_GRAPH is None:
        return jsonify({"error": "No graph loaded. Upload a graph first."}), 400

    try:
        session = graph_routes._ADVANCED_PLANNER.start_session(origin=origin, budget=budget, time_h=time_h)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400

    graph_routes._SESSIONS[session.session_id] = session
    proposals = session.step_proposals()
    return jsonify({
        "message": "Session started",
        "session_id": session.session_id,
        "proposals": graph_routes._serialize(proposals),
        "meta": graph_routes._serialize(proposals.meta),
    })


@trip_session_bp.route("/api/session/<session_id>/proposals", methods=["GET"])
def session_proposals(session_id: str):
    """Return the current proposals for a session.

    Args:
        session_id: Session identifier to inspect.

    Returns:
        Response: JSON response with proposals and metadata, or an error payload.
    """
    session = graph_routes._SESSIONS.get(session_id)
    if session is None:
        return jsonify({"error": "session not found"}), 404
    proposals = session.step_proposals()
    return jsonify({"proposals": graph_routes._serialize(proposals), "meta": graph_routes._serialize(proposals.meta)})


@trip_session_bp.route("/api/session/<session_id>/suggest-route", methods=["POST"])
def session_suggest_route(session_id: str):
    """Suggest the next route for a session.

    Args:
        session_id: Session identifier to inspect.

    Returns:
        Response: JSON response with the suggested route data, or an error payload.
    """
    session = graph_routes._SESSIONS.get(session_id)
    if session is None:
        return jsonify({"error": "session not found"}), 404

    result = session.suggest_route()
    return jsonify({
        "suggested_route": graph_routes._serialize(result.get("suggested_route")),
        "route_plan": graph_routes._serialize(result.get("route_plan") or []),
        "proposals": graph_routes._serialize(result.get("proposals")),
        "meta": graph_routes._serialize(result.get("proposals").meta if result.get("proposals") is not None else {}),
    })


@trip_session_bp.route("/api/session/<session_id>/update-budget", methods=["POST"])
def session_update_budget(session_id: str):
    """Update the budget for a session.

    Args:
        session_id: Session identifier to update.

    Returns:
        Response: JSON response with the updated proposals or an error payload.
    """
    session = graph_routes._SESSIONS.get(session_id)
    if session is None:
        return jsonify({"error": "session not found"}), 404

    payload = request.get_json(silent=True) or {}
    try:
        budget = float(payload.get("budget"))
    except (TypeError, ValueError):
        return jsonify({"error": "invalid budget value"}), 400

    if budget < 0:
        return jsonify({"error": "budget must be >= 0"}), 400

    # Update session state: set remaining budget, optionally raise initial budget
    session.state.budget_remaining = round(float(budget), 2)
    try:
        if float(budget) > float(getattr(session.state, "budget_initial", 0)):
            session.state.budget_initial = round(float(budget), 2)
    except Exception:
        session.state.budget_initial = round(float(budget), 2)

    proposals = session.step_proposals()
    return jsonify({
        "message": "Budget updated",
        "meta": graph_routes._serialize(proposals.meta),
        "proposals": graph_routes._serialize(proposals),
    })


@trip_session_bp.route("/api/session/<session_id>/choice", methods=["POST"])
def session_choice(session_id: str):
    """Apply a user choice to a session.

    Args:
        session_id: Session identifier to update.

    Returns:
        Response: JSON response with the updated state and next proposals, or an error payload.
    """
    session = graph_routes._SESSIONS.get(session_id)
    if session is None:
        return jsonify({"error": "session not found"}), 404
    payload = request.get_json(silent=True) or {}
    result = session.apply_choice(payload)
    return jsonify({
        "updated_state": graph_routes._serialize(result.updated_state),
        "next_proposals": graph_routes._serialize(result.next_proposals) if result.next_proposals is not None else None,
        "events": list(result.events or []),
        "errors": list(result.errors or []),
    })


@trip_session_bp.route("/api/session/<session_id>/report", methods=["GET"])
def session_report(session_id: str):
    """Finalize a session and return its report.

    Args:
        session_id: Session identifier to finalize.

    Returns:
        Response: JSON response with the final report and lock state, or an error payload.
    """
    session = graph_routes._SESSIONS.get(session_id)
    if session is None:
        return jsonify({"error": "session not found"}), 404

    report = session.finalize_and_report()
    graph_routes._SESSIONS.pop(session_id, None)
    return jsonify({
        "session_id": session_id,
        "report": graph_routes._serialize(report),
        "lock_state": graph_routes._config_lock_state(),
    })