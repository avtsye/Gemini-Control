"""Optional container runner for reviewed Python plugins.
Requires installed Docker with locally cached python:3.12-alpine image.
No network, read-only root FS and only plugin source/output mounts.
Container security is not a guarantee against host/kernel vulnerabilities.
"""
import json
import shutil
import subprocess
from pathlib import Path

IMAGE="python:3.12-alpine"

def available():
    docker=shutil.which("docker")
    if not docker:return False
    try:
        result=subprocess.run([docker,"image","inspect",IMAGE],capture_output=True,
                              timeout=5,shell=False)
        return result.returncode==0
    except (OSError,subprocess.TimeoutExpired):
        return False

def run_plugin(source,output,payload,timeout=20):
    docker=shutil.which("docker")
    if not docker or not available():
        return {"error":"Docker isolation unavailable: install Docker and cache python:3.12-alpine"}
    source=Path(source).resolve(strict=True)
    output=Path(output).resolve()
    output.mkdir(parents=True,exist_ok=True)
    # Only single plugin file is mounted as read-only source.
    command=[docker,"run","--rm","--pull=never","--network=none",
        "--read-only","--cap-drop=ALL","--security-opt=no-new-privileges",
        "--pids-limit=64","--memory=256m","--cpus=1",
        "--tmpfs","/tmp:rw,noexec,nosuid,size=32m",
        "--mount",f"type=bind,src={source},dst=/plugin/main.py,readonly",
        "--mount",f"type=bind,src={output},dst=/out",
        IMAGE,"python","-I","-c",
        "import json,runpy,sys; m=runpy.run_path('/plugin/main.py');"
        "print(json.dumps({'result':m['run'](json.loads(sys.stdin.read()),'/out')},ensure_ascii=True,default=str))"]
    try:
        result=subprocess.run(command,input=json.dumps(payload,ensure_ascii=True),
            text=True,encoding="utf-8",capture_output=True,shell=False,
            timeout=max(1,min(int(timeout),60)))
    except subprocess.TimeoutExpired:
        return {"error":"Isolated plugin timed out"}
    if result.returncode:return {"error":"Isolated plugin failed","details":result.stderr[-1200:]}
    try:return json.loads(result.stdout.strip().splitlines()[-1])
    except (ValueError,IndexError):return {"error":"Invalid isolated plugin result"}
