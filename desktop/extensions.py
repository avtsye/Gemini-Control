"""Declarative extensions: reviewed, scoped workflows; never execute arbitrary code."""
import json,re,uuid
from pathlib import Path
from datetime import datetime,timezone
from conversation_store import location
ALLOWED={"windows_snapshot","inspect_window","installed_apps","system_status","workspace_files","inspect_workspace_file","open_workspace_file","open_browser","create_word","project_file","screenshot","draw_paint"}
MAX_STEPS=6

class ExtensionManager:
 def __init__(self,root=None):
  self.root=Path(root or location().parent/"extensions")
  self.root.mkdir(parents=True,exist_ok=True)
 def validate(self,manifest):
  if not isinstance(manifest,dict):raise ValueError("Invalid extension")
  name=manifest.get("name");steps=manifest.get("steps")
  if not isinstance(name,str) or not 1<=len(name)<=80:raise ValueError("Invalid name")
  if not isinstance(steps,list) or not 1<=len(steps)<=MAX_STEPS:raise ValueError("Expected 1-6 steps")
  for step in steps:
   if not isinstance(step,dict) or step.get("tool") not in ALLOWED or not isinstance(step.get("arguments",{}),dict):
    raise ValueError("Unsupported extension tool")
   if len(json.dumps(step,ensure_ascii=False))>40000:raise ValueError("Step too large")
  return {"name":name,"description":str(manifest.get("description",""))[:500],
          "steps":[{"tool":s["tool"],"arguments":s.get("arguments",{})} for s in steps]}
 def install(self,manifest):
  approved=self.validate(manifest)
  identifier=str(uuid.uuid4())
  obj={"id":identifier,"status":"disabled","created":datetime.now(timezone.utc).isoformat(),**approved}
  (self.root/(identifier+".json")).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding="utf-8")
  return identifier
 def list(self):
  result=[]
  for file in self.root.glob("*.json"):
   try:result.append(json.loads(file.read_text(encoding="utf-8")))
   except (OSError,ValueError):continue
  return result
 def toggle(self,identifier,enabled):
  path=self._path(identifier)
  obj=json.loads(path.read_text(encoding="utf-8"))
  self.validate(obj)
  obj["status"]="enabled" if enabled else "disabled"
  path.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding="utf-8")
 def _path(self,identifier):
  try:identifier=str(uuid.UUID(identifier))
  except (ValueError,TypeError):raise ValueError("Invalid extension id")
  path=self.root/(identifier+".json")
  if not path.is_file():raise FileNotFoundError("Extension unavailable")
  return path
 def execute(self,identifier,local,report):
  obj=json.loads(self._path(identifier).read_text(encoding="utf-8"))
  self.validate(obj)
  if obj.get("status")!="enabled":raise PermissionError("Extension disabled")
  outcomes=[]
  for step in obj["steps"]:
   if not local.enabled:break
   # Every sensitive operation retains its native approval gate.
   tool=step["tool"];result=local.execute(tool,step["arguments"])
   outcomes.append({"tool":tool,"result":result})
   report(json.dumps(outcomes[-1],ensure_ascii=False)[:1000])
   if result.get("cancelled") or result.get("error"):break
  return outcomes
