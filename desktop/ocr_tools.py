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

def ocr_pdf(workspace,source,target,approve,language="heb+eng",max_pages=12):
    """Extract text from locally rendered scanned PDF with optional PDFium + Tesseract."""
    src=safe_path(workspace,source)
    dst=safe_path(workspace,target)
    if not src.is_file() or src.suffix.lower()!=".pdf" or src.stat().st_size>60_000_000:
        raise ValueError("Expected a local PDF below 60 MB")
    if dst.suffix.lower()!=".txt" or dst.exists():
        raise ValueError("Destination must be a new TXT file")
    if language not in {"heb","eng","heb+eng"} or not isinstance(max_pages,int) or not 1<=max_pages<=40:
        raise ValueError("Invalid OCR settings")
    engine=ocr_engines()
    if not engine["available"] or (language.startswith("heb") and not engine.get("hebrew")):
        return {"unavailable":"Tesseract with requested language is required"}
    try:
        import pypdfium2 as pdfium
    except ImportError:
        return {"unavailable":"PDF rendering dependency pypdfium2 is missing"}
    if not approve("לבצע OCR לספר PDF מקומי ולהפיק ממנו קובץ טקסט?"):
        return {"cancelled":True}
    import tempfile
    pdf=pdfium.PdfDocument(str(src))
    pages=min(len(pdf),max_pages)
    results=[]
    with tempfile.TemporaryDirectory() as tmp:
        for index in range(pages):
            page=pdf[index]
            bitmap=page.render(scale=1.6)
            path=Path(tmp)/("page-"+str(index)+".png")
            bitmap.to_pil().save(path)
            process=subprocess.run([shutil.which("tesseract"),str(path),"stdout","-l",language],
                capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=90,shell=False)
            if process.returncode:return {"error":"OCR failed on page "+str(index+1),"details":process.stderr[-500:]}
            results.append(process.stdout.strip())
    dst.parent.mkdir(parents=True,exist_ok=True)
    with dst.open("x",encoding="utf-8") as stream:stream.write("\n\n".join(results))
    return {"created_text":str(dst),"pages":pages,"truncated":len(pdf)>pages}
