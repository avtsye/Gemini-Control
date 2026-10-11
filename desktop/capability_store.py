"""Offline curated capability catalog. Installs as disabled draft after review.

All built-ins are shipped with the app and never downloaded or auto-executed.
"""
from pathlib import Path

BUILTINS={
 "audio":{"name":"מחולל WAV","file":"audio_tone.py","description":"יצירת WAV בסיסי מקוד Python מקומי"},
 "video":{"name":"מחולל אנימציית GIF","file":"video_gif.py","description":"אנימציית GIF מקומית (תלוי בספריית תמונות)"},
 "html":{"name":"מחולל HTML","file":"html_report.py","description":"יצירת דוח HTML מעוצב ומוגן מפני הזרקת HTML"},
 "csv":{"name":"מחולל CSV","file":"csv_report.py","description":"יצירת טבלאות CSV עם עברית"},
 "json":{"name":"מסדר JSON","file":"json_formatter.py","description":"ייצוא נתונים לקובץ JSON קריא"},
 "chart":{"name":"מחולל תרשימי SVG","file":"svg_chart.py","description":"יצירת תרשים עמודות SVG ללא תלות חיצונית"}
}

def list_builtins():
    return [{"id":key,"name":value["name"],"description":value["description"]}
            for key,value in BUILTINS.items()]

def install_builtin(workshop,key):
    if key not in BUILTINS:raise ValueError("Unknown builtin capability")
    item=BUILTINS[key]
    source=(Path(__file__).resolve().parent/"examples"/item["file"]).read_text(encoding="utf-8")
    identifier=workshop.draft(item["name"],item["description"],source)
    folder=workshop._path(identifier)
    meta=workshop._manifest(folder)
    meta["require_test"]=True
    meta["origin"]="builtin:"+key
    workshop._write_manifest(folder,meta)
    return identifier
