from __future__ import annotations

from datetime import datetime, timezone
import json
import re
import tempfile
from pathlib import Path
from threading import RLock
from typing import Any

from flask import current_app, session


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PENDING = "pending"
APPROVED = "approved"

_LOCK = RLock()


def current_access_state() -> dict[str, Any]:
    email = normalize_email(session.get("join_email", ""))
    request_data = get_join_request(email) if email else None
    status = request_data["status"] if request_data else "none"
    return {
        "email": email,
        "status": status,
        "approved": status == APPROVED,
    }


def is_current_user_approved() -> bool:
    return current_access_state()["approved"]


def submit_join_request(email: str) -> dict[str, Any]:
    email = normalize_email(email)
    if not EMAIL_RE.match(email):
        raise ValueError("Please enter a valid email address.")

    with _LOCK:
        store = _load_store()
        request_data = store.get(email)
        now = _timestamp()
        if request_data is None:
            request_data = {
                "email": email,
                "status": PENDING,
                "created_at": now,
                "approved_at": "",
            }
        elif request_data.get("status") != APPROVED:
            request_data["status"] = PENDING
            request_data.setdefault("created_at", now)
            request_data["approved_at"] = ""

        store[email] = request_data
        _save_store(store)

    session.permanent = True
    session["join_email"] = email
    return request_data


def approve_join_request(email: str) -> dict[str, Any] | None:
    email = normalize_email(email)
    if not email:
        return None

    with _LOCK:
        store = _load_store()
        request_data = store.get(email)
        if request_data is None:
            return None

        request_data["status"] = APPROVED
        request_data["approved_at"] = _timestamp()
        store[email] = request_data
        _save_store(store)
        return request_data


def revoke_join_request(email: str) -> dict[str, Any] | None:
    email = normalize_email(email)
    if not email:
        return None

    with _LOCK:
        store = _load_store()
        request_data = store.get(email)
        if request_data is None:
            return None

        request_data["status"] = PENDING
        request_data["approved_at"] = ""
        store[email] = request_data
        _save_store(store)
        return request_data


def list_join_requests() -> list[dict[str, Any]]:
    with _LOCK:
        items = list(_load_store().values())
    return sorted(items, key=lambda item: (item.get("status") != PENDING, item.get("created_at", "")))


def get_join_request(email: str) -> dict[str, Any] | None:
    email = normalize_email(email)
    if not email:
        return None

    with _LOCK:
        return _load_store().get(email)


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def _load_store() -> dict[str, dict[str, Any]]:
    path = _store_path()
    if not path.exists():
        return {}

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    requests = raw.get("requests", raw if isinstance(raw, dict) else {})
    if not isinstance(requests, dict):
        return {}
    return {normalize_email(key): value for key, value in requests.items() if isinstance(value, dict)}


def _save_store(requests: dict[str, dict[str, Any]]) -> None:
    path = _store_path()
    payload = json.dumps({"requests": requests}, ensure_ascii=False, indent=2, sort_keys=True)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload, encoding="utf-8")
        return
    except OSError:
        fallback = Path(current_app.instance_path) / "join_requests.json"
        try:
            fallback.parent.mkdir(parents=True, exist_ok=True)
            fallback.write_text(payload, encoding="utf-8")
            current_app.config["JOIN_REQUESTS_FILE"] = str(fallback)
            return
        except OSError:
            temp_dir = Path(tempfile.gettempdir())
            temp_dir.mkdir(parents=True, exist_ok=True)
            temp_path = temp_dir / "smart_employee_join_requests.json"
            temp_path.write_text(payload, encoding="utf-8")
            current_app.config["JOIN_REQUESTS_FILE"] = str(temp_path)


def _store_path() -> Path:
    configured = Path(current_app.config["JOIN_REQUESTS_FILE"])
    if configured.exists() or configured.parent.exists():
        return configured

    fallback = Path(current_app.instance_path) / "join_requests.json"
    try:
        fallback.parent.mkdir(parents=True, exist_ok=True)
        return fallback
    except OSError:
        temp_dir = Path(tempfile.gettempdir())
        temp_dir.mkdir(parents=True, exist_ok=True)
        return temp_dir / "smart_employee_join_requests.json"


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
