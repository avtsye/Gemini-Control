"""Create a standalone, safely escaped HTML report."""
from html import escape
from pathlib import Path

def run(payload,output_dir):
    title=str(payload.get("title","Report"))[:120]
    paragraphs=payload.get("paragraphs",[])
    if not isinstance(paragraphs,list) or len(paragraphs)>50:
        raise ValueError("Expected up to 50 paragraphs")
    content="".join("<p>"+escape(str(x)[:3000])+"</p>" for x in paragraphs)
    document='<!doctype html><html lang="he" dir="rtl"><meta charset="utf-8"><title>'+escape(title)+'</title><style>body{font:16px Arial;max-width:850px;margin:60px auto;line-height:1.8;padding:15px}</style><h1>'+escape(title)+'</h1>'+content+'</html>'
    output=Path(output_dir)/"report.html"
    output.write_text(document,encoding="utf-8")
    return {"file":str(output),"paragraphs":len(paragraphs)}
