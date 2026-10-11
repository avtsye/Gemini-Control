"""Local capability workshop. Generated code is never executed during creation or review.

CAUTION: Running a Python plugin is not a security sandbox. Plugins are code with
the user's OS permissions. Activation and every run require explicit user approval.
"""
import ast
import json
import os
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from conversation_store import location

MAX_SOURCE=50000
MAX_INPUT=12000
class CapabilityWorkshop:
    def __init__(self, root=None):
        self.root=Path(root or location().parent/"capabilities")
        self.root.mkdir(parents=True,exist_ok=True)

    def _path(self, identifier):
        identifier=str(uuid.UUID(str(identifier)))
        folder=self.root/identifier
        if not folder.is_dir() or folder.is_symlink():
            raise ValueError("Capability not found")
        return folder

    def _validate(self,source):
        if not isinstance(source,str) or not 1<=len(source)<=MAX_SOURCE:
            raise ValueError("Invalid Python source")
        tree=ast.parse(source)
        if not any(isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name=="run" for n in tree.body):
            raise ValueError("Python capability must define run(payload, output_dir)")
        if not any(isinstance(n,ast.FunctionDef) and n.name=="run" and len(n.args.args)>=2 for n in tree.body):
            raise ValueError("Expected run(payload, output_dir)")
        return source

    def draft(self,name,description,source):
        if not isinstance(name,str) or not 1<=len(name)<=80:raise ValueError("Invalid name")
        source=self._validate(source)
        identifier=str(uuid.uuid4())
        folder=self.root/identifier
        folder.mkdir()
        metadata={"id":identifier,"name":name,"description":str(description)[:1000],
                  "status":"draft","created":datetime.now(timezone.utc).isoformat(),
                  "warnings":["Python capability code is not sandboxed. Review before activation."]}
        (folder/"main.py").write_text(source,encoding="utf-8")
        (folder/"manifest.json").write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding="utf-8")
        return identifier

    def list(self):
        out=[]
        for folder in self.root.iterdir():
            if not folder.is_dir():continue
            try:
                item=json.loads((folder/"manifest.json").read_text(encoding="utf-8"))
                out.append(item)
            except (ValueError,OSError):continue
        return out

    def source(self,identifier):
        folder=self._path(identifier)
        return (folder/"main.py").read_text(encoding="utf-8")

    def inspect(self,identifier):
        folder=self._path(identifier)
        source=self.source(identifier)
        self._validate(source)
        # Syntax and structure check only. No imports, execution, or dependencies.
        findings=[]
        tree=ast.parse(source)
        imports=[]
        for n in ast.walk(tree):
            if isinstance(n,ast.Import):
                imports.extend(a.name for a in n.names)
            elif isinstance(n,ast.ImportFrom):
                imports.append(n.module or "")
        sensitive={"os","subprocess","socket","ctypes","winreg","shutil","requests","urllib",
                   "http","ftplib","pickle","marshal","importlib"}
        findings.extend("REVIEW REQUIRED: "+n for n in imports if n.split(".")[0] in sensitive)
        return {"syntax_ok":True,"imports":sorted(set(imports)),"findings":findings,
                "source":source,"status":json.loads((folder/"manifest.json").read_text(encoding="utf-8"))["status"]}

    def activate(self,identifier,approved):
        if not approved:raise PermissionError("Explicit approval required")
        folder=self._path(identifier)
        self.inspect(identifier)
        meta_path=folder/"manifest.json"
        meta=json.loads(meta_path.read_text(encoding="utf-8"))
        meta["status"]="enabled"
        meta_path.write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8")
        return meta

    def disable(self,identifier):
        folder=self._path(identifier)
        meta_path=folder/"manifest.json"
        meta=json.loads(meta_path.read_text(encoding="utf-8"))
        meta["status"]="disabled"
        meta_path.write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8")

    def run(self,identifier,payload,approve,timeout=20):
        folder=self._path(identifier)
        info=self.inspect(identifier)
        if info["status"]!="enabled":raise PermissionError("Capability is not enabled")
        if not isinstance(payload,dict) or len(json.dumps(payload,ensure_ascii=False))>MAX_INPUT:
            raise ValueError("Invalid input")
        if not approve("להריץ קוד Python של הרחבת צד שלישי? קוד זה פועל בהרשאות המשתמש ואינו מבודד אבטחתית."):
            return {"cancelled":True}
        output_dir=folder/"outputs"
        output_dir.mkdir(exist_ok=True)
        # Separate process provides a timeout and crash isolation, NOT OS security sandboxing.
        runner=Path(__file__).with_name("capability_runner.py")
        result=subprocess.run([sys.executable,str(runner),str(folder/"main.py"),str(output_dir)],
            input=json.dumps(payload,ensure_ascii=False),capture_output=True,text=True,
            timeout=timeout,cwd=str(folder),shell=False)
        if result.returncode:
            return {"error":"Extension failed","details":result.stderr[-1200:]}
        try:return json.loads(result.stdout)
        except ValueError:return {"error":"Extension returned invalid JSON"}
