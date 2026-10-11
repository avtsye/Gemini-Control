"""Bounded, local task journal for the desktop agent.

Contains model messages and tool output; protect the Windows user profile.
No credentials are intentionally added. Journals are JSON files in the app data dir.
"""
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from conversation_store import location

MAX_EVENTS = 100
MAX_EVENT_CHARS = 1600

def _now():
    return datetime.now(timezone.utc).isoformat()

class TaskJournal:
    def __init__(self, root=None):
        self.root = Path(root) if root is not None else location().parent / "tasks"
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, identifier):
        return self.root / (str(uuid.UUID(str(identifier))) + ".json")

    def start(self, request):
        identifier = str(uuid.uuid4())
        task = {"id": identifier, "created": _now(), "updated": _now(),
                "status": "running", "request": str(request)[:1000], "events": []}
        self._save(task)
        return identifier

    def _save(self, obj):
        target = self._path(obj["id"])
        part = target.with_suffix(".tmp")
        try:
            part.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(part, target)
        finally:
            part.unlink(missing_ok=True)

    def read(self, identifier):
        return json.loads(self._path(identifier).read_text(encoding="utf-8"))

    def event(self, identifier, kind, message):
        if kind not in {"step", "result", "error", "state"}:
            raise ValueError("Invalid event type")
        task = self.read(identifier)
        if task["status"] != "running":
            raise ValueError("Task has ended")
        task["events"].append({"at": _now(), "kind": kind,
                               "message": str(message)[:MAX_EVENT_CHARS]})
        task["events"] = task["events"][-MAX_EVENTS:]
        task["updated"] = _now()
        self._save(task)

    def finish(self, identifier, status):
        if status not in {"completed", "failed", "cancelled", "limit_reached"}:
            raise ValueError("Invalid task status")
        task = self.read(identifier)
        task["status"] = status
        task["updated"] = _now()
        self._save(task)

    def recent(self, limit=20):
        result = []
        for p in sorted(self.root.glob("*.json"), key=lambda x:x.stat().st_mtime, reverse=True)[:min(limit, 50)]:
            try:
                task = json.loads(p.read_text(encoding="utf-8"))
                result.append({key: task.get(key) for key in ("id", "status", "request", "updated")})
            except (ValueError, OSError):
                continue
        return result
