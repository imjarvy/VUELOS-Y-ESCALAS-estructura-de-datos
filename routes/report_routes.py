"""
REST endpoints — trip report (R5).

Single responsibility: HTTP parsing/validation and JSON responses.
Report assembly lives in services/report_service.py.

Registered in app.py as:
    from routes.report_routes import report_bp
    app.register_blueprint(report_bp)
"""

from flask import Blueprint, jsonify

from services.report_service import build_session_report

report_bp = Blueprint("report", __name__)


@report_bp.route("/api/report/<session_id>", methods=["GET"])
def get_report(session_id: str):
    """
    Return the full trip summary for a session (R5).

    Response:
    {
        "session_id": "...",
        "visited":   [...],
        "legs":      [...],
        "activities":[...],
        "jobs":      [...],
        "decisions": [...],
        "totals":    {...}
    }
    """
    try:
        payload = build_session_report(session_id)
    except LookupError as exc:
        return jsonify({"error": str(exc)}), 404
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(payload)
