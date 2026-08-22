from __future__ import annotations

from functools import lru_cache
import os
from pathlib import Path
import re
from typing import Any

import httpx

from .paths import PROOFREADER_DIR


LANGUAGETOOL_URL = os.getenv("LANGUAGETOOL_URL", "https://api.languagetool.org/v2/check")
DEFAULT_BN_WORDLIST = PROOFREADER_DIR / "data" / "bn_words.txt"
BANGLA_WORD_RE = re.compile(r"[\u0980-\u09ff]+")
BANGLA_LETTER_RE = re.compile(r"[\u0985-\u09b9\u09ce\u09dc-\u09df\u09f0-\u09f1]")
LATIN_WORD_RE = re.compile(r"[A-Za-z]{2,}")


def spellcheck_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if os.getenv("SPELLCHECK_ENABLED", "true").lower() in {"0", "false", "no"}:
        return {
            "source": "disabled",
            "segments": [{"id": str(segment.get("id", ""))[:120], "matches": []} for segment in _segments(payload)],
            "errors": ["Spell checking is disabled by SPELLCHECK_ENABLED."],
        }

    language = str(payload.get("language") or "auto")[:20]
    results: list[dict[str, Any]] = []
    errors: list[str] = []

    with httpx.Client(timeout=httpx.Timeout(15.0)) as client:
        for segment in _segments(payload):
            segment_id = str(segment.get("id", ""))[:120]
            text = str(segment.get("text", ""))[:12000].strip()
            if not text:
                results.append({"id": segment_id, "matches": []})
                continue

            matches: list[dict[str, Any]] = []

            if _should_check_bangla(language, text):
                bangla_matches, bangla_error = _bangla_matches(text)
                matches.extend(bangla_matches)
                if bangla_error:
                    errors.append(f"{segment_id}: {bangla_error}")

            if _should_check_languagetool(language, text):
                try:
                    response = client.post(
                        LANGUAGETOOL_URL,
                        data={"text": text, "language": _languagetool_language(language), "enabledOnly": "false"},
                        headers={"Accept": "application/json"},
                    )
                    response.raise_for_status()
                    data = response.json()
                    matches.extend(_compact_matches(data.get("matches", [])))
                except httpx.HTTPStatusError as exc:
                    detail = exc.response.text[:300]
                    errors.append(f"{segment_id}: LanguageTool returned {exc.response.status_code}. {detail}")
                except (httpx.HTTPError, ValueError) as exc:
                    errors.append(f"{segment_id}: {exc}")

            results.append({"id": segment_id, "matches": _dedupe_matches(matches)})

    return {"source": "LanguageTool + Bangla wordlist", "segments": results, "errors": errors}


def _segments(payload: dict[str, Any]) -> list[dict[str, Any]]:
    raw_segments = payload.get("segments")
    if not isinstance(raw_segments, list):
        return []
    return [segment for segment in raw_segments[:250] if isinstance(segment, dict)]


def _compact_matches(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    compact: list[dict[str, Any]] = []
    for match in matches:
        compact.append(
            {
                "offset": match.get("offset", 0),
                "length": match.get("length", 0),
                "message": match.get("message", ""),
                "shortMessage": match.get("shortMessage", ""),
                "ruleId": (match.get("rule") or {}).get("id", ""),
                "replacements": [
                    replacement.get("value", "")
                    for replacement in match.get("replacements", [])[:5]
                    if replacement.get("value")
                ],
            }
        )
    return compact


def _should_check_bangla(language: str, text: str) -> bool:
    return language in {"auto", "bn"} and bool(BANGLA_LETTER_RE.search(text))


def _should_check_languagetool(language: str, text: str) -> bool:
    if language == "bn":
        return False
    if language == "auto":
        return bool(LATIN_WORD_RE.search(text))
    return True


def _languagetool_language(language: str) -> str:
    return "auto" if language == "auto" else language


def _bangla_matches(text: str) -> tuple[list[dict[str, Any]], str | None]:
    words = _bangla_words()
    if not words:
        return [], "Bangla wordlist not configured. Set BN_WORDLIST_PATH or edit data/bn_words.txt."

    matches: list[dict[str, Any]] = []
    for match in BANGLA_WORD_RE.finditer(text):
        word = match.group(0)
        if len(word) < 2 or not BANGLA_LETTER_RE.search(word) or word in words:
            continue

        suggestions = _bangla_suggestions(word, words)
        if not suggestions:
            continue

        matches.append(
            {
                "offset": match.start(),
                "length": len(word),
                "message": "Possible Bangla spelling issue.",
                "shortMessage": "Bangla spelling",
                "ruleId": "BN_WORDLIST",
                "replacements": suggestions,
            }
        )
        if len(matches) >= 80:
            break

    return matches, None


@lru_cache(maxsize=1)
def _bangla_words() -> frozenset[str]:
    configured = os.getenv("BN_WORDLIST_PATH")
    paths = [Path(path) for path in configured.split(os.pathsep)] if configured else [DEFAULT_BN_WORDLIST]
    words: set[str] = set()

    for path in paths:
        if not path.exists():
            continue

        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.split("#", 1)[0].strip()
            if line:
                words.update(word for word in re.split(r"[\s,]+", line) if word)

    return frozenset(words)


def _bangla_suggestions(word: str, words: frozenset[str]) -> list[str]:
    candidates: list[tuple[int, str]] = []
    limit = 1 if len(word) <= 4 else 2

    for candidate in words:
        if abs(len(candidate) - len(word)) > limit:
            continue
        if candidate[0] != word[0] and _levenshtein_limited(word, candidate, 1) > 1:
            continue

        distance = _levenshtein_limited(word, candidate, limit)
        if distance <= limit:
            candidates.append((distance, candidate))

    candidates.sort(key=lambda item: (item[0], len(item[1]), item[1]))
    return [candidate for _, candidate in candidates[:5]]


def _levenshtein_limited(left: str, right: str, limit: int) -> int:
    if abs(len(left) - len(right)) > limit:
        return limit + 1

    previous = list(range(len(right) + 1))
    for row_index, left_char in enumerate(left, start=1):
        current = [row_index]
        row_min = current[0]

        for column_index, right_char in enumerate(right, start=1):
            insertion = current[column_index - 1] + 1
            deletion = previous[column_index] + 1
            substitution = previous[column_index - 1] + (left_char != right_char)
            value = min(insertion, deletion, substitution)
            current.append(value)
            row_min = min(row_min, value)

        if row_min > limit:
            return limit + 1
        previous = current

    return previous[-1]


def _dedupe_matches(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[tuple[int, int, str], dict[str, Any]] = {}
    for match in matches:
        key = (int(match.get("offset", 0)), int(match.get("length", 0)), str(match.get("ruleId", "")))
        deduped[key] = match
    return sorted(deduped.values(), key=lambda match: (match.get("offset", 0), match.get("length", 0)))
