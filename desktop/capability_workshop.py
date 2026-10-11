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
import hashlib
import zipfile
import importlib.util
import shutil
import venv
import re
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

    @staticmethod
    def _runner_path():
        # PyInstaller's extracted source script is bundled as explicit data.
        base=Path(getattr(sys,"_MEIPASS",Path(__file__).resolve().parent))
        path=base/"capability_runner.py"
        if not path.is_file():
            raise FileNotFoundError("Python capability runner missing from the application bundle")
        return path

    @staticmethod
    def _system_python():
        if not getattr(sys,"frozen",False):
            return sys.executable
        candidate=shutil.which("python")
        if not candidate:
            raise RuntimeError("Running Python plugins from the EXE requires a separate Python installation on PATH")
        return candidate

    def _interpreter(self,folder):
        local=folder/"venv"/("Scripts/python.exe" if os.name=="nt" else "bin/python")
        return str(local) if local.is_file() else self._system_python()

    def _ensure_environment(self,folder):
        env=folder/"venv"
        if env.exists():return
        if getattr(sys,"frozen",False):
            python=self._system_python()
            outcome=subprocess.run([python,"-m","venv",str(env)],
                capture_output=True,text=True,encoding="utf-8",errors="replace",
                timeout=120,shell=False)
            if outcome.returncode:
                raise RuntimeError("Could not create Python environment: "+outcome.stderr[-350:])
        else:
            venv.EnvBuilder(with_pip=True,clear=False).create(str(env))

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

    def _manifest(self,folder):
        return json.loads((folder/"manifest.json").read_text(encoding="utf-8"))

    def _write_manifest(self,folder,metadata):
        (folder/"manifest.json").write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding="utf-8")

    def versions(self,identifier):
        folder=self._path(identifier)
        backup=folder/"versions"
        if not backup.exists():return []
        return sorted(int(p.stem) for p in backup.glob("*.py") if p.stem.isdigit())

    def revise(self,identifier,source,approved=False):
        if not approved:raise PermissionError("Review and approval required")
        folder=self._path(identifier)
        self._validate(source)
        meta=self._manifest(folder)
        if meta["status"]=="enabled":
            meta["status"]="disabled"
        rev=int(meta.get("version",1))
        archive=folder/"versions"
        archive.mkdir(exist_ok=True)
        shutil.copy2(folder/"main.py",archive/(str(rev)+".py"))
        (folder/"main.py").write_text(source,encoding="utf-8")
        meta["version"]=rev+1
        meta["source_sha256"]=hashlib.sha256(source.encode("utf-8")).hexdigest()
        self._write_manifest(folder,meta)
        return {"id":identifier,"version":meta["version"],"status":meta["status"]}

    def rollback(self,identifier,version,approved=False):
        if not approved:raise PermissionError("Review and approval required")
        folder=self._path(identifier)
        if not isinstance(version,int) or version<1:raise ValueError("Invalid version")
        archive=folder/"versions"/(str(version)+".py")
        if not archive.is_file():raise FileNotFoundError("Version unavailable")
        return self.revise(identifier,archive.read_text(encoding="utf-8"),approved=True)

    def set_dependencies(self,identifier,packages,approved=False):
        if not approved:raise PermissionError("Approval required")
        if not isinstance(packages,list) or len(packages)>12:raise ValueError("Invalid packages")
        # Version-pinned requirement names only; never install shell flags or URLs.
        pattern=r"[A-Za-z][A-Za-z0-9_.-]{0,60}==[0-9][A-Za-z0-9_.+!-]{0,55}"
        if not all(isinstance(x,str) and re.fullmatch(pattern,x) for x in packages):
            raise ValueError("Only exact pinned package versions are accepted")
        folder=self._path(identifier)
        meta=self._manifest(folder)
        meta["dependencies"]=packages
        meta["status"]="disabled"
        self._write_manifest(folder,meta)
        return {"dependencies":packages,"installed":False}

    def analyze_dependencies(self,identifier):
        info=self.inspect(identifier)
        import sys as _sys
        available=[]
        missing=[]
        for module in info["imports"]:
            root=module.split(".")[0]
            if not root:continue
            if root in _sys.stdlib_module_names or importlib.util.find_spec(root) is not None:
                available.append(module)
            else:
                missing.append(module)
        return {"available":sorted(set(available)),
                "missing":sorted(set(missing)),
                "declared":self._manifest(self._path(identifier)).get("dependencies",[]),
                "note":"Import names are not necessarily PyPI distribution names."}

    def dependency_status(self,identifier):
        folder=self._path(identifier)
        meta=self._manifest(folder)
        env=folder/"venv"
        executable=env/("Scripts/python.exe" if os.name=="nt" else "bin/python")
        return {"dependencies":meta.get("dependencies",[]),"environment_ready":executable.is_file()}

    def create_environment(self,identifier,approved=False):
        if not approved:raise PermissionError("Explicit approval required")
        folder=self._path(identifier)
        meta=self._manifest(folder)
        # Creation of an empty environment never executes untrusted capability source.
        env=folder/"venv"
        if not env.exists():self._ensure_environment(folder)
        return self.dependency_status(identifier)

    def install_dependencies(self,identifier,approve,timeout=120):
        folder=self._path(identifier)
        meta=self._manifest(folder)
        packages=meta.get("dependencies",[])
        if not packages:
            return {"installed":True,"packages":[]}
        if not callable(approve) or not approve(
            "להוריד ולהתקין חבילות Python חיצוניות לתוך סביבה נפרדת? "
            "תהליך התקנת חבילות אינו מבודד אבטחתית ועלול להריץ קוד. "
            "חבילות: "+", ".join(packages)):
            return {"cancelled":True}
        env=folder/"venv"
        if not env.exists():
            self._ensure_environment(folder)
        python=env/("Scripts/python.exe" if os.name=="nt" else "bin/python")
        cmd=[str(python),"-m","pip","--isolated","install","--disable-pip-version-check",
             "--no-input","--only-binary=:all:","--"]+packages
        try:
            outcome=subprocess.run(cmd,capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=timeout,
                                   cwd=str(folder),shell=False)
        except subprocess.TimeoutExpired:
            return {"error":"Package installation timed out"}
        if outcome.returncode:
            return {"error":"Package installation failed","details":outcome.stderr[-1200:]}
        return {"installed":True,"packages":packages}

    def draft(self,name,description,source):
        if not isinstance(name,str) or not 1<=len(name)<=80:raise ValueError("Invalid name")
        source=self._validate(source)
        identifier=str(uuid.uuid4())
        folder=self.root/identifier
        folder.mkdir()
        metadata={"id":identifier,"name":name,"description":str(description)[:1000],
                  "status":"draft","version":1,"source_sha256":hashlib.sha256(source.encode("utf-8")).hexdigest(),"created":datetime.now(timezone.utc).isoformat(),
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

    def export_package(self,identifier,target):
        folder=self._path(identifier)
        path=Path(target)
        if path.suffix.lower()!=".zip" or path.exists() or path.is_symlink():
            raise ValueError("Select a new .zip export path")
        meta=self._manifest(folder)
        manifest={"name":meta.get("name"),"description":meta.get("description",""),
                  "package_version":1}
        with zipfile.ZipFile(path,"x",compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("manifest.json",json.dumps(manifest,ensure_ascii=False))
            archive.writestr("main.py",self.source(identifier))
        return {"exported":str(path)}
    def import_package(self,source):
        path=Path(source)
        if not path.is_file() or path.stat().st_size>2_000_000:
            raise ValueError("Invalid plugin archive")
        with zipfile.ZipFile(path) as archive:
            entries={item.filename:item for item in archive.infolist()}
            if set(entries)!={"manifest.json","main.py"}:
                raise ValueError("Package may contain only manifest.json and main.py")
            if entries["main.py"].file_size>MAX_SOURCE or entries["manifest.json"].file_size>10000:
                raise ValueError("Package exceeds size limits")
            meta=json.loads(archive.read("manifest.json").decode("utf-8"))
            code=archive.read("main.py").decode("utf-8")
        if not isinstance(meta,dict) or meta.get("package_version")!=1:
            raise ValueError("Unsupported package manifest")
        identifier=self.draft(meta.get("name"),meta.get("description",""),code)
        folder=self._path(identifier)
        manifest=self._manifest(folder)
        manifest["require_test"]=True
        manifest["origin"]="imported"
        self._write_manifest(folder,manifest)
        return {"id":identifier,"status":"draft"}
    def remove(self,identifier,approved=False):
        if not approved:raise PermissionError("Explicit removal approval required")
        folder=self._path(identifier)
        if self._manifest(folder).get("status")=="enabled":
            raise PermissionError("Disable the plugin before removing it")
        shutil.rmtree(folder)
        return {"removed":identifier}
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

    def test_capability(self,identifier,payload,approve,timeout=15):
        """Opt-in live smoke test. Executes code as user, NOT a security sandbox."""
        folder=self._path(identifier)
        info=self.inspect(identifier)
        if info["findings"]:
            raise PermissionError("Sensitive imports must be resolved before testing")
        if not isinstance(payload,dict) or len(json.dumps(payload,ensure_ascii=False))>MAX_INPUT:
            raise ValueError("Invalid test input")
        if not approve("להריץ בדיקת ניסיון לקוד Python שנוצר? הבדיקה מפעילה קוד בהרשאות המשתמש."):
            return {"cancelled":True}
        # Testing doesn't require enabling the capability; records evidence for review.
        output=folder/"test_outputs"
        output.mkdir(exist_ok=True)
        runner=self._runner_path()
        executable=folder/"venv"/("Scripts/python.exe" if os.name=="nt" else "bin/python")
        interpreter=self._interpreter(folder)
        if os.environ.get("GEMINI_CONTROL_PLUGIN_RUNTIME")=="docker":
            from container_capabilities import run_plugin
            isolated=run_plugin(folder/"main.py",output,payload,timeout)
            passed="error" not in isolated
            details=json.dumps(isolated,ensure_ascii=True)[-1500:]
            meta=self._manifest(folder)
            meta["last_test"]={"passed":passed,"at":datetime.now(timezone.utc).isoformat(),
                "source_sha256":hashlib.sha256(self.source(identifier).encode("utf-8")).hexdigest(),
                "details":details}
            self._write_manifest(folder,meta)
            return {"passed":passed,"details":details,"isolated":True}
        try:
            process=subprocess.run([interpreter,str(runner),str(folder/"main.py"),str(output)],
                input=json.dumps(payload,ensure_ascii=True),text=True,encoding="utf-8",errors="replace",capture_output=True,
                cwd=str(folder),timeout=min(max(timeout,1),30),shell=False)
            passed=process.returncode==0
            details=(process.stdout if passed else process.stderr)[-1500:]
        except subprocess.TimeoutExpired:
            passed=False
            details="Timed out"
        meta=self._manifest(folder)
        meta["last_test"]={"passed":passed,"at":datetime.now(timezone.utc).isoformat(),
                           "source_sha256":hashlib.sha256(self.source(identifier).encode("utf-8")).hexdigest(),
                           "details":details}
        self._write_manifest(folder,meta)
        return {"passed":passed,"details":details}

    def activate(self,identifier,approved):
        if not approved:raise PermissionError("Explicit approval required")
        folder=self._path(identifier)
        info=self.inspect(identifier)
        if info["findings"]:
            raise PermissionError("Sensitive imports require manual review; activation blocked")
        meta_path=folder/"manifest.json"
        meta=json.loads(meta_path.read_text(encoding="utf-8"))
        test=meta.get("last_test",{})
        current_hash=hashlib.sha256(self.source(identifier).encode("utf-8")).hexdigest()
        if meta.get("require_test",False) and (not test.get("passed") or test.get("source_sha256")!=current_hash):
            raise PermissionError("Run a successful approved smoke test before activation")
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
        if info["findings"]:raise PermissionError("Sensitive imports blocked")
        if not isinstance(payload,dict) or len(json.dumps(payload,ensure_ascii=False))>MAX_INPUT:
            raise ValueError("Invalid input")
        if not approve("להריץ קוד Python של הרחבת צד שלישי? קוד זה פועל בהרשאות המשתמש ואינו מבודד אבטחתית."):
            return {"cancelled":True}
        output_dir=folder/"outputs"
        output_dir.mkdir(exist_ok=True)
        # Separate process provides a timeout and crash isolation, NOT OS security sandboxing.
        runner=Path(__file__).with_name("capability_runner.py")
        executable=folder/"venv"/("Scripts/python.exe" if os.name=="nt" else "bin/python")
        interpreter=str(executable) if executable.is_file() else sys.executable
        if os.environ.get("GEMINI_CONTROL_PLUGIN_RUNTIME")=="docker":
            from container_capabilities import run_plugin
            return run_plugin(folder/"main.py",output_dir,payload,timeout)
        result=subprocess.run([interpreter,str(runner),str(folder/"main.py"),str(output_dir)],
            input=json.dumps(payload,ensure_ascii=True),capture_output=True,text=True,encoding="utf-8",errors="replace",
            timeout=timeout,cwd=str(folder),shell=False)
        if result.returncode:
            return {"error":"Extension failed","details":result.stderr[-1200:]}
        try:return json.loads(result.stdout)
        except ValueError:return {"error":"Extension returned invalid JSON"}
