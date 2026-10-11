"""Opt-in machine health diagnostics without exposing tokens or secrets."""
import importlib.util
import platform
import shutil
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

MODULES=("PySide6","requests","psutil","PIL","pypdf","pypdfium2",
         "faster_whisper","pyttsx3","openpyxl","pptx","docx")
EXECUTABLES=("ffmpeg","ffprobe","tesseract","git","gh","docker")

def inspect_environment(workshop=None,db_path=None):
    modules={}
    for module in MODULES:
        try:modules[module]=importlib.util.find_spec(module) is not None
        except (ImportError,ValueError):modules[module]=False
    executables={name:bool(shutil.which(name)) for name in EXECUTABLES}
    warnings=[]
    if not modules["psutil"]:
        warnings.append("psutil חסר — יש להתקין את קובץ התלויות של התוכנה")
    if not executables["tesseract"]:
        warnings.append("מנוע OCR אינו מותקן — יכולות OCR לא יהיו זמינות")
    if not executables["ffmpeg"]:
        warnings.append("FFmpeg חסר — המרות שמע ווידאו לא יהיו זמינות")
    extensions={"enabled":0,"draft":0,"disabled":0,"invalid":0}
    if workshop is not None:
        for item in workshop.list():
            state=item.get("status","invalid")
            extensions[state if state in extensions else "invalid"]+=1
            try:
                inspection=workshop.inspect(item["id"])
                if inspection["findings"]:
                    extensions["invalid"]+=1
            except (ValueError,OSError,SyntaxError,KeyError):
                extensions["invalid"]+=1
    database="not_checked"
    if db_path is not None and Path(db_path).is_file():
        try:
            url=Path(db_path).resolve().as_uri()+"?mode=ro"
            with closing(sqlite3.connect(url,uri=True,timeout=4)) as db:
                database=db.execute("PRAGMA quick_check(1)").fetchone()[0]
        except (sqlite3.Error,OSError) as exc:
            database="error: "+type(exc).__name__
    return {
        "python":platform.python_version(),
        "os":platform.system()+" "+platform.release(),
        "modules":modules,"executables":executables,
        "extensions":extensions,"conversation_database":database,
        "warnings":warnings,
        "note":"דוח טכני בלבד: אינו כולל שמות משתמשים, טוקנים או תוכן שיחות"
    }
