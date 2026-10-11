"""Permission-gated, workspace-confined ZIP and file comparison utilities."""
import difflib
import os
import shutil
import zipfile
from pathlib import Path

MAX_ARCHIVE_FILES = 500
MAX_UNCOMPRESSED = 100 * 1024 * 1024
MAX_FILE = 25 * 1024 * 1024

def _safe(root, name):
    if not isinstance(name, str) or not name or "\\x00" in name:
        raise ValueError("Invalid relative path")
    p = Path(name)
    if p.is_absolute() or any(part in ("..", "") for part in p.parts) or ":" in name:
        raise ValueError("Path must be relative to workspace")
    root = Path(root).resolve()
    out = root.joinpath(p)
    if not out.resolve().is_relative_to(root):
        raise ValueError("Path escapes workspace")
    if any(item.is_symlink() for item in (out, *out.parents) if item != root and item.is_relative_to(root)):
        raise ValueError("Symlinks are not allowed")
    return out

def _approval(approval, description):
    if not approval(description):
        return {"cancelled": True}
    return None

def compare_files(workspace, left, right, approval):
    root = Path(workspace).resolve()
    a, b = _safe(root, left), _safe(root, right)
    if not a.is_file() or not b.is_file():
        raise FileNotFoundError("Both files must exist")
    if max(a.stat().st_size, b.stat().st_size) > MAX_FILE:
        raise ValueError("File too large")
    cancelled = _approval(approval, "לקרוא ולהשוות שני קבצים בתיקיית העבודה ולשלוח את ההבדלים למודל?")
    if cancelled:
        return cancelled
    x, y = a.read_bytes(), b.read_bytes()
    if x == y:
        return {"identical": True, "diff": ""}
    try:
        xs, ys = x.decode("utf-8").splitlines(), y.decode("utf-8").splitlines()
    except UnicodeDecodeError:
        return {"identical": False, "binary": True, "left_size": len(x), "right_size": len(y)}
    diff = "\n".join(difflib.unified_diff(xs, ys, fromfile=str(left), tofile=str(right), lineterm=""))
    return {"identical": False, "binary": False, "diff": diff[:12000], "truncated": len(diff)>12000}

def create_zip(workspace, sources, target, approval):
    root = Path(workspace).resolve()
    if not isinstance(sources, list) or not sources or len(sources)>MAX_ARCHIVE_FILES:
        raise ValueError("Invalid source list")
    dest = _safe(root, target)
    if dest.suffix.lower() != ".zip":
        raise ValueError("Expected .zip output")
    files = []
    for source in sources:
        path = _safe(root, source)
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(p for p in path.rglob("*") if p.is_file())
        else:
            raise FileNotFoundError(str(source))
    files = sorted(set(files))
    if not files or len(files)>MAX_ARCHIVE_FILES:
        raise ValueError("Archive file count limit exceeded")
    if dest in files:
        raise ValueError("Output cannot be an input")
    for file in files:
        _safe(root, str(file.relative_to(root)))
        if file.stat().st_size>MAX_FILE:
            raise ValueError("Input file too large")
    if sum(p.stat().st_size for p in files)>MAX_UNCOMPRESSED:
        raise ValueError("Archive size limit exceeded")
    cancelled = _approval(approval, "ליצור ארכיון ZIP עם "+str(len(files))+" קבצים?"+(" הארכיון הקיים יוחלף." if dest.exists() else ""))
    if cancelled:return cancelled
    dest.parent.mkdir(parents=True, exist_ok=True)
    temp = dest.with_name(dest.name+".partial")
    try:
        with zipfile.ZipFile(temp, "w", compression=zipfile.ZIP_DEFLATED) as z:
            for p in files:
                z.write(p, p.relative_to(root).as_posix())
        os.replace(temp, dest)
    finally:
        temp.unlink(missing_ok=True)
    return {"created_zip": str(dest.relative_to(root)), "files": len(files)}

def extract_zip(workspace, archive, destination, approval):
    root = Path(workspace).resolve()
    source, dest = _safe(root, archive), _safe(root, destination)
    if source.suffix.lower() != ".zip" or not source.is_file():
        raise ValueError("Expected an existing ZIP file")
    with zipfile.ZipFile(source) as z:
        entries = z.infolist()
        if len(entries)>MAX_ARCHIVE_FILES or sum(i.file_size for i in entries)>MAX_UNCOMPRESSED:
            raise ValueError("Archive limits exceeded")
        targets=[]
        for i in entries:
            path = _safe(dest, i.filename.replace("/", os.sep))
            if i.is_dir():continue
            if i.file_size>MAX_FILE:raise ValueError("Entry too large")
            if ((i.external_attr >> 16) & 0o170000)==0o120000:
                raise ValueError("Symbolic links rejected")
            if path.exists():raise FileExistsError("Extraction would overwrite: "+i.filename)
            targets.append((i,path))
        cancelled=_approval(approval,"לחלץ "+str(len(targets))+" קבצים לתיקיית העבודה?")
        if cancelled:return cancelled
        dest.mkdir(parents=True,exist_ok=True)
        for i,path in targets:
            path.parent.mkdir(parents=True,exist_ok=True)
            with z.open(i) as src, path.open("xb") as dst:
                shutil.copyfileobj(src,dst)
    return {"extracted":len(targets),"destination":str(dest.relative_to(root))}
