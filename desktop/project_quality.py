"""Reviewed project testing tools; never run code without explicit consent."""
import subprocess
import sys
from pathlib import Path
from workspace_data import safe_path

def inspect_python_project(workspace,project,approve):
    root=safe_path(workspace,project)
    if not root.is_dir():raise FileNotFoundError("Project folder not found")
    if not approve("לקרוא את קובצי Python ולבדוק את התחביר בפרויקט "+str(project)+"?"):
        return {"cancelled":True}
    import ast
    errors=[]
    checked=0
    for path in root.rglob("*.py"):
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):continue
        checked+=1
        if checked>500:break
        if path.stat().st_size>1_000_000:
            errors.append({"file":str(path.relative_to(root)),"error":"File too large"})
            continue
        try:ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError,UnicodeError) as exc:
            errors.append({"file":str(path.relative_to(root)),"error":str(exc)[:400]})
    return {"files_checked":checked,"syntax_ok":not errors,"errors":errors[:50]}

def run_python_tests(workspace,project,approve,timeout=90):
    root=safe_path(workspace,project)
    if not root.is_dir():raise FileNotFoundError("Project folder not found")
    if not isinstance(timeout,int) or not 1<=timeout<=180:raise ValueError("Invalid timeout")
    if not approve("להריץ בדיקות Python של הפרויקט? קוד הבדיקות יכול להריץ פקודות בהרשאות המשתמש ואינו מבודד."):
        return {"cancelled":True}
    try:
        process=subprocess.run([sys.executable,"-m","unittest","discover","-v"],
            cwd=str(root),capture_output=True,text=True,encoding="utf-8",errors="replace",
            timeout=timeout,shell=False)
        return {"passed":process.returncode==0,"exit_code":process.returncode,
                "stdout":process.stdout[-2500:],"stderr":process.stderr[-2500:]}
    except subprocess.TimeoutExpired:
        return {"error":"Tests timed out"}
