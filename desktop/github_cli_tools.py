"""Optional GitHub CLI integration. Read-only commands using existing local gh login."""
import json
import os
import re
import shutil
import subprocess

def github_engine():
    return {"available":bool(shutil.which("gh"))}

def _repo(value):
    if not isinstance(value,str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,70}/[A-Za-z0-9_.-]{1,100}",value):
        raise ValueError("Expected owner/repository")
    if ".." in value:raise ValueError("Invalid owner/repository")
    return value

def _call(args):
    executable=shutil.which("gh")
    if not executable:return {"unavailable":"GitHub CLI (gh) is not installed"}
    env=os.environ.copy()
    env["GH_PROMPT_DISABLED"]="1"
    try:
        process=subprocess.run([executable,*args],capture_output=True,text=True,
            encoding="utf-8",errors="replace",shell=False,timeout=30,env=env)
    except subprocess.TimeoutExpired:return {"error":"GitHub request timed out"}
    if process.returncode:return {"error":"GitHub CLI request failed","details":process.stderr[-280:]}
    try:return {"results":json.loads(process.stdout)}
    except ValueError:return {"error":"Invalid GitHub response"}

def github_issues(repository,approve):
    repo=_repo(repository)
    if not approve("לקרוא רשימת Issues ציבוריים/מורשים ממאגר GitHub "+repo+"?"):
        return {"cancelled":True}
    return _call(["issue","list","-R",repo,"--limit","30",
                  "--json","number,title,state,url"])

def github_pull_requests(repository,approve):
    repo=_repo(repository)
    if not approve("לקרוא את רשימת בקשות המשיכה ממאגר "+repo+"?"):
        return {"cancelled":True}
    return _call(["pr","list","-R",repo,"--limit","30",
                  "--json","number,title,state,url,isDraft"])
