"""Bounded local workspace file organization and extraction with 7-Zip if installed."""
import os
import shutil
import subprocess
from pathlib import Path
from workspace_data import safe_path

def move_workspace_file(workspace, source, destination, approve):
    src=safe_path(workspace,source)
    dst=safe_path(workspace,destination)
    if not src.is_file() or src.is_symlink():raise FileNotFoundError("Source file is missing")
    if dst.exists() or dst.is_symlink():raise FileExistsError("Destination already exists")
    if not approve("להעביר קובץ בתיקיית העבודה מ-"+str(source)+" אל "+str(destination)+"?"):
        return {"cancelled":True}
    dst.parent.mkdir(parents=True,exist_ok=True)
    shutil.move(str(src),str(dst))
    return {"moved_from":str(source),"moved_to":str(destination)}

def sevenzip_status():
    executable=shutil.which("7z") or shutil.which("7za") or shutil.which("7zz")
    return {"available":bool(executable),"executable":Path(executable).name if executable else None}

def extract_7z(workspace,source,destination,approve):
    src=safe_path(workspace,source)
    dst=safe_path(workspace,destination)
    if not src.is_file() or src.suffix.lower()!=".7z":raise ValueError("Expected .7z archive")
    if src.stat().st_size>100_000_000:raise ValueError("Archive too large")
    exe=shutil.which("7z") or shutil.which("7za") or shutil.which("7zz")
    if not exe:return {"unavailable":"7-Zip command line engine is not installed"}
    if dst.exists() and any(dst.iterdir()):raise FileExistsError("Use an empty new destination")
    # Archive metadata can contain traversing paths. Extract inside a temporary directory
    # then verify every created file is a regular file before moving into destination.
    if not approve("לחלץ ארכיון 7z לתיקיית עבודה חדשה?"):
        return {"cancelled":True}
    import tempfile
    root=Path(workspace).resolve()
    with tempfile.TemporaryDirectory(prefix=".7z-",dir=root) as scratch:
        scratch=Path(scratch)
        try:
            proc=subprocess.run([exe,"x","-y","-bd",f"-o{scratch}",str(src)],
                capture_output=True,text=True,encoding="utf-8",errors="replace",
                timeout=90,shell=False)
        except subprocess.TimeoutExpired:
            return {"error":"Archive extraction timed out"}
        if proc.returncode:return {"error":"7z extraction failed","details":proc.stderr[-700:]}
        entries=list(scratch.rglob("*"))
        if len(entries)>500:raise ValueError("Archive contains too many items")
        files=[p for p in entries if p.is_file()]
        if any(p.is_symlink() or not p.resolve().is_relative_to(scratch.resolve()) for p in entries):
            raise ValueError("Unsafe archive entries")
        if sum(p.stat().st_size for p in files)>100_000_000:
            raise ValueError("Archive extracted size exceeded")
        if dst.exists():raise FileExistsError("Destination already exists")
        shutil.move(str(scratch),str(dst))
        return {"extracted":len(files),"destination":str(dst.relative_to(root))}
