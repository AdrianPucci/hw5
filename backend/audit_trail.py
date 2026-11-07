"""Append-only audit trail of every agent-loop step: output/audit_trail.json.

The file is one JSON list. Each write reads the list, adds the new entries and swaps the file in
atomically, so earlier runs are never wiped (Adrian, Prompt 74). A file that can't be parsed is
moved aside (audit_trail.corrupt-<time>.json), never deleted.
"""

from __future__ import annotations

import json
import threading
import time
from datetime import datetime
from typing import Any

from pydantic_core import to_jsonable_python

from models import ROOT

AUDIT_PATH = ROOT / "output" / "audit_trail.json"
PREVIEW_CHARS = 600
_lock = threading.Lock()


def preview(value: Any) -> Any:
    """Keep tool results readable: long text is cut to PREVIEW_CHARS (the full result is in team_runs)."""
    text = json.dumps(to_jsonable_python(value, fallback=str), ensure_ascii=False)
    return value if len(text) <= PREVIEW_CHARS else text[: PREVIEW_CHARS - 1] + "…"


def append(entries: list[dict[str, Any]]) -> None:
    if not entries:
        return
    with _lock:
        AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        rows: list[Any] = []
        if AUDIT_PATH.exists() and AUDIT_PATH.stat().st_size > 0:
            try:
                loaded = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
                rows = loaded if isinstance(loaded, list) else [loaded]
            except json.JSONDecodeError:
                AUDIT_PATH.replace(AUDIT_PATH.with_name(f"audit_trail.corrupt-{datetime.now():%Y%m%d-%H%M%S}.json"))
        rows.extend(to_jsonable_python(entries, fallback=str))
        tmp = AUDIT_PATH.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        # OneDrive or an open viewer can lock the file for a moment (it crashed ticket #902 once): retry.
        for attempt in range(10):
            try:
                tmp.replace(AUDIT_PATH)
                return
            except PermissionError:
                time.sleep(0.5 * (attempt + 1))
        tmp.replace(AUDIT_PATH)  # last try: let the error surface
