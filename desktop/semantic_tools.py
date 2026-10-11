"""Offline embedding search over local workspace documents.

Requires sentence-transformers and an already cached LOCAL model directory.
Never downloads model weights. Index is built only with explicit approval.
"""
import json
import math
import sys
from pathlib import Path
from workspace_data import safe_path

EXTENSIONS={".txt",".md",".csv",".json",".py"}
MAX_FILES=250
MAX_BYTES=80000

def embedding_status(workspace,model_folder):
    path=safe_path(workspace,model_folder)
    from model_runtime import has_external_env,check_modules
    if getattr(sys,"frozen",False) or has_external_env(workspace):
        engine=check_modules(workspace).get("modules",{}).get("sentence_transformers",False)
    else:
        try:
            import sentence_transformers
            engine=True
        except ImportError:
            engine=False
    return {"engine_installed":engine,"local_model_ready":path.is_dir(),
            "downloads_allowed":False}

def _model(workspace,folder):
    path=safe_path(workspace,folder)
    if not path.is_dir():return None
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:return None
    # Explicit local_files_only prevents accidental model downloads.
    return SentenceTransformer(str(path),local_files_only=True)

def _encode(workspace,model_folder,texts):
    from model_runtime import has_external_env,execute
    if getattr(sys,"frozen",False) or has_external_env(workspace):
        path=safe_path(workspace,model_folder)
        result=execute(workspace,"embed",{"model":str(path),"texts":texts},timeout=300)
        return result.get("vectors"),result.get("error") or result.get("unavailable")
    model=_model(workspace,model_folder)
    if model is None:return None,"Local sentence-transformers model/dependency missing"
    return model.encode(texts,normalize_embeddings=True),None

def build_semantic_index(workspace,model_folder,folder,approve):
    root=safe_path(workspace,folder)
    if not root.is_dir():raise ValueError("Missing knowledge folder")
    if not approve("לבנות אינדקס סמנטי מקומי מתוך מסמכים באמצעות מודל Embeddings מותקן?"):
        return {"cancelled":True}
    documents=[]
    for p in sorted(root.rglob("*")):
        if len(documents)>=MAX_FILES:break
        if not p.is_file() or p.is_symlink() or not p.resolve().is_relative_to(root.resolve()):
            continue
        if p.suffix.lower() not in EXTENSIONS or p.stat().st_size>MAX_BYTES:continue
        body=p.read_text(encoding="utf-8",errors="replace").strip()
        if body:
            documents.append({"path":p.relative_to(Path(workspace).resolve()).as_posix(),
                              "text":body[:2000]})
    if not documents:return {"error":"No supported documents in folder"}
    embeddings,error=_encode(workspace,model_folder,[d["text"] for d in documents])
    if error:return {"unavailable":error}
    payload={"version":1,"model_folder":model_folder,"folder":folder,
             "items":[{"path":d["path"],"text":d["text"],
                       "vector":[float(v) for v in vector]}
                      for d,vector in zip(documents,embeddings)]}
    target=Path(workspace).resolve()/".gemini-semantic-index.json"
    scratch=target.with_suffix(".json.tmp")
    scratch.write_text(json.dumps(payload,ensure_ascii=False),encoding="utf-8")
    scratch.replace(target)
    return {"indexed":len(documents),"index":"local_embeddings"}

def semantic_search(workspace,query,model_folder,approve,limit=6):
    if not isinstance(query,str) or not query.strip() or len(query)>400:raise ValueError("Invalid query")
    if not isinstance(limit,int) or not 1<=limit<=20:raise ValueError("Invalid limit")
    if not approve("לחפש סמנטית במסמכים המקומיים ולשתף קטעים מתאימים עם המודל?"):
        return {"cancelled":True}
    index=Path(workspace).resolve()/".gemini-semantic-index.json"
    if not index.is_file() or index.stat().st_size>15_000_000:
        return {"error":"Semantic index missing or too large"}
    data=json.loads(index.read_text(encoding="utf-8"))
    if data.get("version")!=1 or data.get("model_folder")!=model_folder:
        return {"error":"Index does not match requested local model"}
    vectors,error=_encode(workspace,model_folder,[query])
    if error:return {"unavailable":error}
    vector=[float(x) for x in vectors[0]]
    ranking=[]
    for item in data.get("items",[])[:MAX_FILES]:
        other=item.get("vector",[])
        if len(other)!=len(vector):continue
        score=math.fsum(a*float(b) for a,b in zip(vector,other))
        if math.isfinite(score):
            ranking.append({"path":item["path"],"score":round(score,5),
                            "excerpt":item["text"][:600]})
    ranking.sort(key=lambda x:-x["score"])
    return {"results":ranking[:limit],"method":"local_sentence_transformer_embeddings"}
