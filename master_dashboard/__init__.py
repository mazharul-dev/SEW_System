from __future__ import annotations

from datetime import timedelta
import os
from pathlib import Path

from flask import Flask, session

from .access_control import current_access_state
from .routes import (
    bangla_convert_bp,
    dashboard_bp,
    in_branch_bp,
    model_test_bp,
    proofreader_bp,
    table_converter_bp,
)


def create_app() -> Flask:
    app = Flask(__name__, static_folder=None, template_folder="templates")
    app.secret_key = os.getenv("SECRET_KEY", "smart-employee-working-system-dev")
    app.permanent_session_lifetime = timedelta(days=int(os.getenv("SESSION_DAYS", "365")))
    app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_UPLOAD_BYTES", str(25 * 1024 * 1024)))
    app.config["ADMIN_USERNAME"] = os.getenv("ADMIN_USERNAME", "admin")
    app.config["ADMIN_PASSWORD"] = os.getenv("ADMIN_PASSWORD", "01706452007")
    app.config["JOIN_REQUESTS_FILE"] = os.getenv(
        "JOIN_REQUESTS_FILE",
        str(Path(app.instance_path) / "join_requests.json"),
    )
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(bangla_convert_bp)
    app.register_blueprint(model_test_bp)
    app.register_blueprint(proofreader_bp)
    app.register_blueprint(table_converter_bp)
    app.register_blueprint(in_branch_bp)

    @app.context_processor
    def inject_access_state() -> dict[str, object]:
        return {
            "access_state": current_access_state(),
            "is_admin": bool(session.get("is_admin")),
        }

    return app
