"""Local deny-only tool policy. Never grants permanent approvals.

Tools with write/execute/screen capabilities still require their own interactive permission.
"""
import json
from pathlib import Path
from conversation_store import location

class ToolPolicy:
    def __init__(self,path=None):
        self.path=Path(path or location().parent/"tool-policy.json")
    def disabled(self):
        try:
            payload=json.loads(self.path.read_text(encoding="utf-8"))
            return set(x for x in payload.get("blocked",[]) if isinstance(x,str))
        except (FileNotFoundError,ValueError,OSError,TypeError):
            return set()
    def allowed(self,name):
        return isinstance(name,str) and name not in self.disabled()
    def set_allowed(self,name,enabled,valid_names):
        if name not in valid_names:raise ValueError("Unknown tool")
        if not isinstance(enabled,bool):raise ValueError("Expected boolean")
        blocked=self.disabled()
        if enabled:blocked.discard(name)
        else:blocked.add(name)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        temporary=self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps({"version":1,"blocked":sorted(blocked)},indent=2),encoding="utf-8")
        temporary.replace(self.path)
        return {"name":name,"enabled":enabled}
