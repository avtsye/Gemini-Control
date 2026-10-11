"""Optional external Python runtime for heavy offline AI libraries.

Compatible with source Python and frozen EXE. No downloads or package installs;
uses an explicitly prepared .ai-venv or an installed system Python.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

def interpreter(workspace):
    root=Path(workspace).expanduser().resolve()
    virtual=root/".ai-venv"/("Scripts/python.exe" if os.name=="nt" else "bin/python")
    if virtual.is_file():return str(virtual)
    if getattr(sys,"frozen",False):return shutil.which("python")
    return sys.executable

def worker_path():
    base=Path(getattr(sys,"_MEIPASS",Path(__file__).resolve().parent))
    return base/"model_worker.py"

def has_external_env(workspace):
    root=Path(workspace).expanduser().resolve()
    return (root/".ai-venv"/("Scripts/python.exe" if os.name=="nt" else "bin/python")).is_file()

def check_modules(workspace):
    python=interpreter(workspace)
    if not python:return {"python_available":False,"modules":{}}
    command=("import json,importlib.util;"
             "print(json.dumps({n:importlib.util.find_spec(n) is not None "
             "for n in ('torch','diffusers','sentence_transformers','faster_whisper')}))")
    try:
        result=subprocess.run([python,"-I","-c",command],
            capture_output=True,text=True,encoding="utf-8",errors="replace",
            timeout=12,shell=False)
        if result.returncode:return {"python_available":True,"modules":{},"error":"Module check failed"}
        return {"python_available":True,"modules":json.loads(result.stdout)}
    except (OSError,ValueError,subprocess.TimeoutExpired):
        return {"python_available":False,"modules":{}}

def execute(workspace,operation,arguments,timeout=300):
    python=interpreter(workspace)
    worker=worker_path()
    if not python:return {"unavailable":"Python model runtime is not installed"}
    if not worker.is_file():return {"error":"The external AI model worker was not bundled"}
    if operation not in {"embed","image","transcribe"}:
        raise ValueError("Unsupported model worker operation")
    if not isinstance(arguments,dict):raise ValueError("Invalid worker arguments")
    payload={"operation":operation,**arguments}
    encoded=json.dumps(payload,ensure_ascii=True)
    if len(encoded)>1_950_000:raise ValueError("Model request too large")
    environment=os.environ.copy()
    environment["HF_HUB_OFFLINE"]="1"
    environment["TRANSFORMERS_OFFLINE"]="1"
    environment["HF_DATASETS_OFFLINE"]="1"
    environment["TOKENIZERS_PARALLELISM"]="false"
    try:
        process=subprocess.run([python,"-I",str(worker)],
            input=encoded,text=True,encoding="utf-8",errors="replace",
            capture_output=True,timeout=max(1,min(int(timeout),600)),
            env=environment,shell=False)
    except subprocess.TimeoutExpired:return {"error":"Local AI model timed out"}
    except OSError:return {"error":"Could not start local AI model runtime"}
    try:response=json.loads(process.stdout.strip())
    except ValueError:return {"error":"Invalid AI model worker response","details":process.stderr[-400:]}
    if process.returncode and "error" not in response:
        return {"error":"AI model worker failed","details":process.stderr[-400:]}
    return response
