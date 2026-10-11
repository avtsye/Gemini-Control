"""Workspace search and CSV/JSON conversion without unrestricted filesystem access."""
import csv
import json
from pathlib import Path

MAX_MATCHES=150
MAX_BYTES=2_000_000

def safe_path(workspace, name):
    if not isinstance(name,str) or not name or "\x00" in name:
        raise ValueError("Invalid path")
    raw=Path(name)
    if raw.is_absolute() or ".." in raw.parts or ":" in name:
        raise ValueError("Path outside workspace")
    root=Path(workspace).resolve()
    path=(root/raw).resolve()
    if not path.is_relative_to(root) or (root/raw).is_symlink():
        raise ValueError("Path outside workspace")
    return path

def search_workspace(workspace,query,approve):
    if not isinstance(query,str) or not 2<=len(query)<=100:
        raise ValueError("Invalid search term")
    if not approve("לחפש שמות קבצים ותוכן טקסט בתיקיית העבודה ולשלוח תוצאות למודל?"):
        return {"cancelled":True}
    root=Path(workspace).resolve()
    root.mkdir(parents=True,exist_ok=True)
    matches=[]
    count=0
    for p in root.rglob("*"):
        if p.is_symlink() or not p.is_file() or not p.resolve().is_relative_to(root):
            continue
        count+=1
        if count>2500:break
        relative=p.relative_to(root).as_posix()
        name_match=query.casefold() in relative.casefold()
        snippet=""
        if p.suffix.lower() in {".txt",".md",".csv",".json",".py",".html",".css",".js"} and p.stat().st_size<=MAX_BYTES:
            try:
                data=p.read_text(encoding="utf-8")
                at=data.casefold().find(query.casefold())
                if at>=0:snippet=data[max(0,at-70):at+130]
            except (OSError,UnicodeError):
                pass
        if name_match or snippet:
            matches.append({"path":relative,"snippet":snippet})
        if len(matches)>=MAX_MATCHES:break
    return {"matches":matches,"scanned":count,"truncated":count>2500 or len(matches)>=MAX_MATCHES}

def convert_data(workspace,source,target,approve):
    inp=safe_path(workspace,source)
    out=safe_path(workspace,target)
    if not inp.is_file() or inp.stat().st_size>MAX_BYTES:
        raise ValueError("Source missing or too large")
    if out.exists() or out.is_symlink():
        raise FileExistsError("Output exists")
    mode=(inp.suffix.lower(),out.suffix.lower())
    if mode not in {(".csv",".json"),(".json",".csv")}:
        raise ValueError("Supported conversions: CSV to JSON or JSON to CSV")
    if not approve("להמיר "+str(source)+" אל "+str(target)+" בתוך תיקיית העבודה?"):
        return {"cancelled":True}
    if mode==(".csv",".json"):
        with inp.open(encoding="utf-8-sig",newline="") as f:
            rows=list(csv.DictReader(f))
        if len(rows)>5000:raise ValueError("Too many records")
        contents=json.dumps(rows,ensure_ascii=False,indent=2)
    else:
        data=json.loads(inp.read_text(encoding="utf-8-sig"))
        if not isinstance(data,list) or len(data)>5000 or not all(isinstance(item,dict) for item in data):
            raise ValueError("JSON must be an array of objects")
        columns=list(dict.fromkeys(key for item in data for key in item))
        if len(columns)>100:raise ValueError("Too many columns")
        import io
        f=io.StringIO()
        writer=csv.DictWriter(f,fieldnames=columns,extrasaction="ignore")
        writer.writeheader()
        for item in data:
            if any(isinstance(x,(list,dict)) for x in item.values()):
                raise ValueError("Nested values are unsupported")
            writer.writerow(item)
        contents=f.getvalue()
    if len(contents.encode("utf-8"))>MAX_BYTES*2:raise ValueError("Output too large")
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open("x",encoding="utf-8-sig" if out.suffix==".csv" else "utf-8",newline="") as f:
        f.write(contents)
    return {"converted":str(out.relative_to(Path(workspace).resolve()))}
