"""Offline ranked search over explicitly selected workspace text files.

No embeddings or remote APIs. Search uses token frequency ranking with Unicode-aware
normalization; it is lexical search, not true semantic understanding.
"""
import math
import re
from collections import Counter
from pathlib import Path
from workspace_data import safe_path

EXTENSIONS={".txt",".md",".json",".csv",".py",".html"}
MAX_FILES=500
MAX_SIZE=400_000
TOKEN=re.compile(r"[^\W_]+",re.UNICODE)

def _tokens(value):
    return [x.casefold() for x in TOKEN.findall(value) if len(x)>1]

def search_knowledge(workspace,query,folder,approve,limit=8):
    if not isinstance(query,str) or not 2<=len(query)<=300:
        raise ValueError("Invalid query")
    if not isinstance(limit,int) or not 1<=limit<=20:
        raise ValueError("Invalid result count")
    root=safe_path(workspace,folder)
    if not root.is_dir() or root.is_symlink():
        raise ValueError("Knowledge folder does not exist")
    if not approve("לחפש בתוך קובצי בסיס הידע המקומי בתיקייה "+str(folder)+"?"):
        return {"cancelled":True}
    documents=[]
    for path in sorted(root.rglob("*")):
        if len(documents)>=MAX_FILES:break
        if not path.is_file() or path.is_symlink() or path.suffix.lower() not in EXTENSIONS:
            continue
        if not path.resolve().is_relative_to(root.resolve()) or path.stat().st_size>MAX_SIZE:
            continue
        try: body=path.read_text(encoding="utf-8")
        except (OSError,UnicodeError):continue
        counts=Counter(_tokens(body))
        if counts:
            documents.append((path,body,counts))
    terms=set(_tokens(query))
    if not terms:return {"results":[],"searched_files":len(documents)}
    df={term:sum(term in doc[2] for doc in documents) for term in terms}
    scored=[]
    for path,body,counts in documents:
        total=sum(counts.values())
        score=sum((counts.get(t,0)/max(1,total))*(1+math.log((len(documents)+1)/(df[t]+1)))
                  for t in terms)
        if score>0:
            lower=body.casefold()
            positions=[lower.find(t) for t in terms if lower.find(t)>=0]
            pivot=max(0,min(positions)-90) if positions else 0
            scored.append({"file":path.relative_to(Path(workspace).resolve()).as_posix(),
                           "score":round(score,6),
                           "excerpt":body[pivot:pivot+420]})
    scored.sort(key=lambda x:(-x["score"],x["file"]))
    return {"results":scored[:limit],"searched_files":len(documents),
            "method":"offline keyword-frequency ranking (not semantic embeddings)"}
