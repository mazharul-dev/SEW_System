from __future__ import annotations

import re
import unicodedata
from typing import Any

from .module_loader import parse_docx_bytes


SET_FIELDS = (
    ("daily_live", "Daily Live"),
    ("daily_practice", "Daily Practice"),
    ("weekly_live", "Weekly Live"),
    ("weekly_practice", "Weekly Practice"),
)


def compare_question_sets(files: dict[str, bytes]) -> dict[str, Any]:
    sets: list[dict[str, Any]] = []
    grouped: dict[str, list[dict[str, Any]]] = {}
    warnings: list[str] = []

    for field, label in SET_FIELDS:
        data = files.get(field, b"")
        if not data:
            sets.append({"field": field, "label": label, "total": 0, "warnings": ["No file uploaded."]})
            continue

        parsed = parse_docx_bytes(data)
        set_warnings = list(parsed.get("warnings", []))
        questions = parsed.get("questions", [])
        sets.append({"field": field, "label": label, "total": len(questions), "warnings": set_warnings})
        warnings.extend(f"{label}: {warning}" for warning in set_warnings)

        for question in questions:
            key = _normalize_question(question.get("question", ""))
            if not key:
                continue

            grouped.setdefault(key, []).append(
                {
                    "set": label,
                    "serial": question.get("serial", ""),
                    "category": question.get("category", ""),
                    "question": question.get("question", ""),
                    "answer": question.get("answerLabel", ""),
                    "sourceTable": question.get("sourceTable", ""),
                }
            )

    repeats = []
    for occurrences in grouped.values():
        set_names = {item["set"] for item in occurrences}
        if len(occurrences) < 2:
            continue

        repeats.append(
            {
                "question": occurrences[0]["question"],
                "sets": sorted(set_names),
                "occurrences": occurrences,
                "crossSet": len(set_names) > 1,
            }
        )

    repeats.sort(key=lambda item: (not item["crossSet"], item["sets"], item["question"]))

    return {
        "sets": sets,
        "repeatCount": len(repeats),
        "crossSetRepeatCount": sum(1 for item in repeats if item["crossSet"]),
        "repeats": repeats,
        "warnings": warnings,
    }


def _normalize_question(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text or "").casefold()
    normalized = normalized.replace("'", "").replace("\u2018", "").replace("\u2019", "")
    normalized = normalized.replace("\u201c", '"').replace("\u201d", '"')
    return re.sub(r"[\W_]+", "", normalized, flags=re.UNICODE)
