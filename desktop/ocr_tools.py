"""Opt-in Hebrew OCR of local images and scanned PDF via installed Tesseract.

No network use; tools never install a language model behind the user's back.
"""
import shutil
import subprocess
from pathlib import Path
from workspace_data import safe_path

def ocr_engines():
    exe=shutil.which("tesseract")
    if not exe:return {"available":False,"languages":[],"hint":"Install Tesseract and Hebrew language data"}
    try:
        proc=subprocess.run([exe,"--list-langs"],capture_output=True,
            text=True,encoding="utf-8",errors="replace",timeout=8)
        langs=[x.strip() for x in proc.stdout.splitlines() if x.strip() and not x.lower().startswith("list of")]
        return {"available":True,"languages":langs,"hebrew": "heb" in langs}
    except (OSError,subprocess.TimeoutExpired):
        return {"available":False,"languages":[]}

def ocr_image(workspace,source,target,approve,language="heb+eng"):
    src=safe_path(workspace,source)
    dst=safe_path(workspace,target)
    if not src.is_file() or src.suffix.lower() not in {".png",".jpg",".jpeg",".tif",".tiff",".bmp"}:
        raise ValueError("Expected an existing image")
    if src.stat().st_size>25_000_000:raise ValueError("Image exceeds limit")
    if dst.suffix.lower()!=".txt" or dst.exists():raise ValueError("Destination must be a new .txt file")
    if language not in {"heb","eng","heb+eng"}:raise ValueError("Unsupported language")
    engine=ocr_engines()
    if not engine["available"]:return {"unavailable":"Tesseract OCR is not installed"}
    if language.startswith("heb") and not engine.get("hebrew"):
        return {"unavailable":"Tesseract Hebrew language data (heb) is missing"}
    if not approve("לקרוא טקסט מתמונה מקומית באמצעות OCR וליצור קובץ טקסט?"):
        return {"cancelled":True}
    proc=subprocess.run([shutil.which("tesseract"),str(src),"stdout","-l",language],
        capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=90)
    if proc.returncode:return {"error":"OCR failed","details":proc.stderr[-600:]}
    dst.parent.mkdir(parents=True,exist_ok=True)
    with dst.open("x",encoding="utf-8") as output:output.write(proc.stdout)
    return {"created_text":str(dst),"characters":len(proc.stdout)}
