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

OPTIONAL_PACKAGES={
    "speech":("faster-whisper>=1.1,<2","pyttsx3>=2.90,<3"),
    "embedding":("sentence-transformers>=3,<6",),
    "image":("diffusers>=0.30,<1","transformers>=4.40,<5",
             "torch>=2.5,<3","accelerate>=0.34,<2"),
}

def prepare_environment(workspace,features,approve,timeout=1200):
    """Explicitly approved package install into a dedicated venv; never downloads models."""
    if (not isinstance(features,list) or not features or
        any(name not in OPTIONAL_PACKAGES for name in features)):
        raise ValueError("Unknown optional AI feature")
    selected=sorted(set(features))
    root=Path(workspace).expanduser().resolve()
    env=root/".ai-venv"
    if env.is_symlink():raise ValueError("AI environment must not be a symlink")
    packages=list(dict.fromkeys(pkg for name in selected for pkg in OPTIONAL_PACKAGES[name]))
    if not callable(approve) or not approve(
        "להתקין ספריות Python חיצוניות לסביבת AI נפרדת? התקנה זו עשויה "
        "להוריד מאות MB או יותר ולהריץ קוד התקנה מקומי. לא יורדו מודלים. רכיבים: "+
        ", ".join(selected)):
        return {"cancelled":True}
    python=shutil.which("python")
    if not python:return {"unavailable":"Install Python and make it available on PATH"}
    root.mkdir(parents=True,exist_ok=True)
    if not env.exists():
        try:
            creation=subprocess.run([python,"-m","venv",str(env)],
                capture_output=True,text=True,encoding="utf-8",errors="replace",
                shell=False,timeout=120)
        except subprocess.TimeoutExpired:
            return {"error":"Creating Python environment timed out"}
        if creation.returncode:
            return {"error":"Cannot create separate Python environment",
                    "details":creation.stderr[-300:]}
    runtime=env/("Scripts/python.exe" if os.name=="nt" else "bin/python")
    if not runtime.is_file():return {"error":"Python environment is incomplete"}
    try:
        installation=subprocess.run([str(runtime),"-m","pip","--isolated","install",
            "--disable-pip-version-check","--no-input","--only-binary=:all:",*packages],
            capture_output=True,text=True,encoding="utf-8",errors="replace",
            timeout=max(60,min(int(timeout),1800)),shell=False)
    except subprocess.TimeoutExpired:
        return {"error":"Optional AI package installation timed out"}
    if installation.returncode:
        return {"error":"Optional AI package installation failed",
                "details":installation.stderr[-350:]}
    return {"installed":selected,"modules":check_modules(workspace).get("modules",{}),
            "models_downloaded":False}
