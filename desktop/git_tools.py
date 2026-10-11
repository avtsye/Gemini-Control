"""Bounded local Git operations within a designated workspace only.

Never pushes commits, changes Git remotes, or reads credentials.
Every operation requires approval; commit disables repository hooks.
"""
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from workspace_data import safe_path

def git_engine():
    return {"available":bool(shutil.which("git"))}

def _repo(workspace,project):
    root=safe_path(workspace,project)
    if not root.is_dir() or root.is_symlink() or not (root/".git").is_dir():
        raise ValueError("Expected a Git repository directory inside the workspace")
    return root

def _invoke(root,*args,timeout=25):
    executable=shutil.which("git")
    if not executable:return {"unavailable":"Git executable is not installed"}
    env=os.environ.copy()
    env["GIT_TERMINAL_PROMPT"]="0"
    env["GIT_PAGER"]="cat"
    try:
        result=subprocess.run([executable,"-C",str(root),*args],
            capture_output=True,text=True,encoding="utf-8",errors="replace",
            timeout=timeout,shell=False,env=env)
        return {"ok":result.returncode==0,"code":result.returncode,
                "stdout":result.stdout[-10000:],"stderr":result.stderr[-1500:]}
    except subprocess.TimeoutExpired:
        return {"error":"Git command timed out"}

def git_status(workspace,project,approve):
    root=_repo(workspace,project)
    if not approve("לבדוק את מצב מאגר Git מקומי ולשתף את תוצאות הבדיקה עם המודל?"):
        return {"cancelled":True}
    return _invoke(root,"status","--short","--branch")

def git_diff(workspace,project,approve):
    root=_repo(workspace,project)
    if not approve("לקרוא רשימת שינויים במאגר Git ולשתף אותה עם המודל?"):
        return {"cancelled":True}
    return _invoke(root,"diff","--no-ext-diff","--stat")

def git_commit(workspace,project,paths,message,approve):
    root=_repo(workspace,project)
    if not isinstance(message,str) or not 1<=len(message)<=200:
        raise ValueError("Invalid commit message")
    if not isinstance(paths,list) or not 1<=len(paths)<=30:
        raise ValueError("Specify 1-30 paths")
    safe=[]
    for name in paths:
        if not isinstance(name,str) or not name or name.startswith("-") or name.startswith(".git"):
            raise ValueError("Invalid staged path")
        if not (root/name).resolve().is_relative_to(root.resolve()):
            raise ValueError("Path escapes repository")
        safe.append(name)
    if not approve("להוסיף "+str(len(safe))+" קבצים ל־Git וליצור commit מקומי? לא יבוצע push."):
        return {"cancelled":True}
    # Hooks may run untrusted code. Force an empty hooks directory.
    with tempfile.TemporaryDirectory(prefix="gemini-no-hooks-") as hookdir:
        add=_invoke(root,"-c","core.hooksPath="+hookdir,"add","--",*safe)
        if not add.get("ok"):return add
        commit=_invoke(root,"-c","core.hooksPath="+hookdir,"commit","-m",message,"--",*safe)
    return commit
