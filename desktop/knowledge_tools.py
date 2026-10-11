"""Local Hebrew-friendly full-text knowledge search (SQLite FTS5).

Keyword/phrase retrieval; not an embedding-based semantic search engine.
All indexed content remains on disk until a user-approved search sends snippets to the model.
"""
import re
import sqlite3
from contextlib import closing
from pathlib import Path

EXTENSIONS={".txt",".md",".csv",".json",".py",".html",".css",".js"}
MAX_FILES=1000
MAX_BYTES=250_000

def _db_path(workspace):
    root=Path(workspace).expanduser().resolve()
    root.mkdir(parents=True,exist_ok=True)
    return root/".gemini-knowledge.sqlite3"

def index_workspace(workspace,approve):
    if not approve("ליצור אינדקס חיפוש מקומי של קובצי טקסט בתיקיית העבודה?"):
        return {"cancelled":True}
    root=Path(workspace).expanduser().resolve()
    root.mkdir(parents=True,exist_ok=True)
    items=[]
    for path in root.rglob("*"):
        if len(items)>=MAX_FILES:break
        if path.is_symlink() or not path.is_file() or path.suffix.lower() not in EXTENSIONS:
            continue
        resolved=path.resolve()
        if not resolved.is_relative_to(root) or path.stat().st_size>MAX_BYTES:continue
        text=path.read_text(encoding="utf-8",errors="replace")
        items.append((str(path.relative_to(root)),text[:MAX_BYTES]))
    with closing(sqlite3.connect(_db_path(workspace))) as db:
        db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS documents USING fts5(path UNINDEXED, body, tokenize='unicode61')")
        db.execute("DELETE FROM documents")
        db.executemany("INSERT INTO documents(path,body) VALUES(?,?)",items)
        db.commit()
    return {"indexed_files":len(items),"index":"local"}

def search_knowledge(workspace,query,approve,limit=10):
    if not isinstance(query,str) or not query.strip() or len(query)>200:
        raise ValueError("Invalid search query")
    words=re.findall(r"[^\W_]+",query,flags=re.UNICODE)[:10]
    if not words:return {"results":[]}
    if not approve("לחפש באינדקס הידע המקומי ולשתף קטעי מסמכים עם המודל?"):
        return {"cancelled":True}
    target=_db_path(workspace)
    if not target.is_file():return {"error":"Index missing; run index_workspace first"}
    expression=" OR ".join('"'+word.replace('"','')+'"' for word in words)
    with closing(sqlite3.connect(target)) as db:
        rows=db.execute("""SELECT path,snippet(documents,1,'[',']',' … ',24)
            FROM documents WHERE documents MATCH ? ORDER BY bm25(documents) LIMIT ?""",
            (expression,max(1,min(int(limit),30)))).fetchall()
    return {"results":[{"path":name,"snippet":snippet} for name,snippet in rows]}
