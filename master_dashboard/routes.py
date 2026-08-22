from __future__ import annotations

from datetime import datetime
from io import BytesIO
import re
import tempfile
from pathlib import Path

from flask import (
    Blueprint,
    Response,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    send_from_directory,
    session,
    url_for,
)

from .access_control import (
    approve_join_request,
    current_access_state,
    is_current_user_approved,
    list_join_requests,
    revoke_join_request,
    submit_join_request,
)
from .in_branch_converter import convert_docx_to_sutonny
from .module_loader import clean_model_test_docx, convert_table_docx, parse_docx_bytes
from .paths import MAZHARUL_CONVERTER_DIR, MODEL_TEST_DIR, PROOFREADER_DIR, STATIC_DIR
from .proofreader_service import spellcheck_payload


dashboard_bp = Blueprint("dashboard", __name__)
bangla_convert_bp = Blueprint("bangla_convert", __name__)
model_test_bp = Blueprint("model_test", __name__)
proofreader_bp = Blueprint("proofreader", __name__)
table_converter_bp = Blueprint("table_converter", __name__)
in_branch_bp = Blueprint("in_branch", __name__)


TOOL_CARDS = [
    {
        "title": "Bangla Convert",
        "description": "Unicode and Bijoy Bangla text conversion.",
        "icon": "languages",
        "accent": "teal",
        "endpoint": "bangla_convert.page",
    },
    {
        "title": "Model Test Book Generate",
        "description": "Clean exam DOCX files and generate print-ready output.",
        "icon": "book-open-check",
        "accent": "blue",
        "endpoint": "model_test.page",
    },
    {
        "title": "Question Repeat Checker",
        "description": "Parse MCQ tables, detect repeated questions, and review spelling.",
        "icon": "scan-search",
        "accent": "amber",
        "endpoint": "proofreader.page",
    },
    {
        "title": "Table Based Convert",
        "description": "Convert unstructured DOCX MCQ content into structured table format.",
        "icon": "table-properties",
        "accent": "green",
        "endpoint": "table_converter.page",
    },
    {
        "title": "In-Branch Question Convert",
        "description": "Convert Unicode/Avro DOCX questions into Bijoy SutonnyMJ DOCX.",
        "icon": "git-branch",
        "accent": "rose",
        "endpoint": "in_branch.page",
    },
    {
        "title": "Coming Soon",
        "description": "Reserved for the next employee productivity tool.",
        "icon": "hourglass",
        "accent": "muted",
        "disabled": True,
        "badge": "Coming Soon",
    },
]


@bangla_convert_bp.before_request
def _bangla_convert_guard():
    return _require_join_approval()


@model_test_bp.before_request
def _model_test_guard():
    return _require_join_approval()


@proofreader_bp.before_request
def _proofreader_guard():
    return _require_join_approval()


@table_converter_bp.before_request
def _table_converter_guard():
    return _require_join_approval()


@in_branch_bp.before_request
def _in_branch_guard():
    return _require_join_approval()


@dashboard_bp.route("/")
def dashboard():
    return render_template("dashboard.html", tool_cards=TOOL_CARDS, access_state=current_access_state())


@dashboard_bp.route("/assets/<path:filename>")
def assets(filename: str):
    return send_from_directory(STATIC_DIR, filename)


@dashboard_bp.route("/join/request", methods=["POST"])
def join_request():
    payload = request.get_json(silent=True) or request.form
    email = (payload.get("email") or "").strip()
    if not email:
        return jsonify({"detail": "Please enter a mail address."}), 400

    try:
        request_data = submit_join_request(email)
    except ValueError as exc:
        return jsonify({"detail": str(exc)}), 400
    access = current_access_state()
    detail = (
        "এই মেইল আগে থেকেই approved আছে।"
        if access["approved"]
        else "01706452007 এই নাম্বারে যোগাযোগ করে approval নিন।"
    )

    return jsonify(
        {
            "detail": detail,
            "request": request_data,
            "access": access,
        }
    )


@dashboard_bp.route("/join/status")
def join_status():
    return jsonify(current_access_state())


@dashboard_bp.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    error = ""
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        if username == current_app.config["ADMIN_USERNAME"] and password == current_app.config["ADMIN_PASSWORD"]:
            session["is_admin"] = True
            return redirect(url_for("dashboard.admin_approvals"))
        error = "Invalid admin username or password."

    return render_template("admin_login.html", error=error)


@dashboard_bp.route("/admin/logout", methods=["POST"])
def admin_logout():
    session.pop("is_admin", None)
    return redirect(url_for("dashboard.dashboard"))


@dashboard_bp.route("/admin/approvals", methods=["GET"])
def admin_approvals():
    guard = _require_admin()
    if guard is not None:
        return guard
    return render_template("admin_approvals.html", approval_requests=list_join_requests())


@dashboard_bp.route("/admin/approvals/approve", methods=["POST"])
def admin_approve():
    guard = _require_admin()
    if guard is not None:
        return guard
    email = (request.form.get("email") or "").strip()
    if email:
        approve_join_request(email)
    return redirect(url_for("dashboard.admin_approvals"))


@dashboard_bp.route("/admin/approvals/revoke", methods=["POST"])
def admin_revoke():
    guard = _require_admin()
    if guard is not None:
        return guard
    email = (request.form.get("email") or "").strip()
    if email:
        revoke_join_request(email)
    return redirect(url_for("dashboard.admin_approvals"))


def _require_admin():
    if session.get("is_admin"):
        return None
    if request.method == "GET":
        return redirect(url_for("dashboard.admin_login"))
    return jsonify({"detail": "Admin login is required."}), 403


def _require_join_approval():
    if is_current_user_approved():
        return None

    if request.method != "GET" or "/api/" in request.path or request.path.endswith("/convert"):
        return jsonify({"detail": "Join approval is required."}), 403

    return redirect(url_for("dashboard.dashboard", locked="1"))


@bangla_convert_bp.route("/tools/bangla-convert")
def page():
    return render_template(
        "tool_frame.html",
        title="Bangla Convert",
        icon="languages",
        subtitle="Unicode and Bijoy Bangla converter",
        iframe_src=url_for("bangla_convert.module_index"),
    )


@bangla_convert_bp.route("/tools/bangla-convert/_module/")
def module_index():
    html = (MAZHARUL_CONVERTER_DIR / "index.html").read_text(encoding="utf-8")
    html = html.replace(
        "</head>",
        '<base href="/tools/bangla-convert/_module/">'
        "<style>"
        "body{min-height:auto!important;}"
        ".topbar,.footer,#back-to-top{display:none!important;}"
        "main.shell{padding-top:18px!important;padding-bottom:24px!important;}"
        "</style></head>",
    )
    return Response(html, mimetype="text/html")


@bangla_convert_bp.route("/tools/bangla-convert/_module/<path:filename>")
def module_file(filename: str):
    return send_from_directory(MAZHARUL_CONVERTER_DIR, filename)


@model_test_bp.route("/tools/model-test-generate", methods=["GET"])
def page():
    return render_template(
        "tool_frame.html",
        title="Model Test Book Generate",
        icon="book-open-check",
        subtitle="Clean exam DOCX files and generate print-ready output",
        iframe_src=url_for("model_test.model_module_index"),
    )


@model_test_bp.route("/tools/model-test-generate/convert", methods=["POST"])
def convert_model_test():
    upload = request.files.get("upload")
    if upload is None or not upload.filename:
        return render_template("model_test.html", error="Please upload a DOCX file."), 400
    if not upload.filename.lower().endswith(".docx"):
        return render_template("model_test.html", error="Only .docx files are supported."), 400

    options = {
        "delete_solve": request.form.get("delete_solve") == "on",
        "keep_answer_marks": request.form.get("keep_answer_marks") == "on",
        "convert_omr": request.form.get("convert_omr") == "on",
        "two_column": request.form.get("two_column") == "on",
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        input_path = tmp_path / "input.docx"
        output_path = tmp_path / "model_test_output.docx"
        upload.save(input_path)
        clean_model_test_docx(str(input_path), str(output_path), **options)
        output = output_path.read_bytes()

    filename = _download_name(upload.filename, "model_test")
    return send_file(
        BytesIO(output),
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        as_attachment=True,
        download_name=filename,
    )


@model_test_bp.route("/tools/model-test-generate/_module/")
def model_module_index():
    html = (MODEL_TEST_DIR / "index.html").read_text(encoding="utf-8")
    html = html.replace(
        "</head>",
        '<base href="/tools/model-test-generate/_module/">'
        "<style>"
        "body{min-height:auto!important;}"
        ".topbar{display:none!important;}"
        ".app{padding-top:18px!important;}"
        "</style></head>",
    )
    return Response(html, mimetype="text/html")


@model_test_bp.route("/tools/model-test-generate/_module/<path:filename>")
def model_module_file(filename: str):
    return send_from_directory(MODEL_TEST_DIR, filename)


@proofreader_bp.route("/tools/question-proofreader")
def page():
    return render_template(
        "tool_frame.html",
        title="Question Repeat Checker",
        icon="scan-search",
        subtitle="DOCX MCQ parser, duplicate detector, and spelling review",
        iframe_src=url_for("proofreader.module_index"),
    )


@proofreader_bp.route("/tools/question-proofreader/_module/")
def module_index():
    html = (PROOFREADER_DIR / "templates" / "index.html").read_text(encoding="utf-8")
    html = html.replace('/static/styles.css', url_for("proofreader.static_file", filename="styles.css"))
    html = html.replace('/static/app.js', url_for("proofreader.static_file", filename="app.js"))
    html = html.replace(
        "</head>",
        "<style>.app-shell{padding-top:16px!important;}</style></head>",
    )
    return Response(html, mimetype="text/html")


@proofreader_bp.route("/tools/question-proofreader/_static/<path:filename>")
def static_file(filename: str):
    path = PROOFREADER_DIR / "static" / filename
    if filename == "app.js" and path.exists():
        js = path.read_text(encoding="utf-8")
        js = js.replace('fetch("/api/parse"', 'fetch("/tools/question-proofreader/api/parse"')
        js = js.replace('fetch("/api/spellcheck"', 'fetch("/tools/question-proofreader/api/spellcheck"')
        return Response(js, mimetype="application/javascript")
    return send_from_directory(PROOFREADER_DIR / "static", filename)


@proofreader_bp.route("/tools/question-proofreader/api/parse", methods=["POST"])
def api_parse():
    upload = request.files.get("upload")
    if upload is None or not upload.filename:
        return jsonify({"detail": "Please upload a .docx file."}), 400
    if not upload.filename.lower().endswith(".docx"):
        return jsonify({"detail": "Please upload a .docx file."}), 400

    data = upload.read()
    if len(data) > current_app.config["MAX_CONTENT_LENGTH"]:
        return jsonify({"detail": "The uploaded file is larger than the configured limit."}), 413

    try:
        return jsonify(parse_docx_bytes(data))
    except Exception as exc:
        return jsonify({"detail": f"Could not parse DOCX: {exc}"}), 400


@proofreader_bp.route("/tools/question-proofreader/api/spellcheck", methods=["POST"])
def api_spellcheck():
    payload = request.get_json(silent=True) or {}
    return jsonify(spellcheck_payload(payload))


@table_converter_bp.route("/tools/table-converter", methods=["GET"])
def page():
    return render_template("table_converter.html")


@table_converter_bp.route("/tools/table-converter/convert", methods=["POST"])
def convert_table():
    upload = request.files.get("upload")
    subject = (request.form.get("subject") or "").strip()

    if upload is None or not upload.filename:
        return render_template("table_converter.html", error="Please upload a DOCX file.", subject=subject), 400
    if not upload.filename.lower().endswith(".docx"):
        return render_template("table_converter.html", error="Only .docx files are supported.", subject=subject), 400
    if not subject:
        return render_template("table_converter.html", error="Please enter a subject/category name.", subject=subject), 400

    try:
        output = convert_table_docx(BytesIO(upload.read()), subject)
    except Exception as exc:
        return render_template("table_converter.html", error=f"Processing failed: {exc}", subject=subject), 400

    safe_subject = re.sub(r"[^A-Za-z0-9_-]+", "_", subject).strip("_") or "structured"
    filename = f"{safe_subject}_table_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        as_attachment=True,
        download_name=filename,
    )


@in_branch_bp.route("/tools/in-branch-question-convert", methods=["GET"])
def page():
    return render_template("in_branch_converter.html")


@in_branch_bp.route("/tools/in-branch-question-convert/convert", methods=["POST"])
def convert():
    upload = request.files.get("upload")
    if upload is None or not upload.filename:
        return render_template("in_branch_converter.html", error="Please upload a DOCX file."), 400
    if not upload.filename.lower().endswith(".docx"):
        return render_template("in_branch_converter.html", error="Only .docx files are supported."), 400

    try:
        output, _stats = convert_docx_to_sutonny(upload.read())
    except Exception as exc:
        return render_template("in_branch_converter.html", error=f"Conversion failed: {exc}"), 400

    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        as_attachment=True,
        download_name=_download_name(upload.filename, "in_branch_sutonny"),
    )


def _download_name(original_name: str, suffix: str) -> str:
    stem = Path(original_name).stem
    safe_stem = re.sub(r"[^A-Za-z0-9_-]+", "_", stem).strip("_") or "output"
    return f"{safe_stem}_{suffix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
