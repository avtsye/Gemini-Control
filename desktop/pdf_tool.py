"""Native Qt PDF authoring with Unicode Hebrew and RTL layout.

Creates a PDF only inside the approved local workspace; never executes HTML.
"""
import html
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path


def create_pdf(name, content, workspace, approve, direction="rtl"):
    if not isinstance(name, str) or not 1 <= len(name) <= 100 or Path(name).name != name:
        raise ValueError("יש לבחור שם קובץ פשוט, בלי תיקיות")
    if name in (".", "..") or name.startswith(".") or not name.lower().endswith(".pdf"):
        raise ValueError("שם הקובץ חייב להסתיים ב־.pdf")
    if any(c in name for c in ('/', '\\', ':', '\0')):
        raise ValueError("שם הקובץ מכיל תווים אסורים")
    if not isinstance(content, str) or not 1 <= len(content) <= 100000:
        raise ValueError("תוכן ה־PDF חייב להכיל בין 1 ל־100000 תווים")
    if direction not in ("rtl", "ltr"):
        raise ValueError("כיווניות לא תקינה")

    folder = Path(workspace).resolve()
    # Refuse a symlinked workspace or destination.
    original_folder = Path(workspace).expanduser()
    if original_folder.is_symlink():
        raise ValueError("תיקיית עבודה מקושרת אינה נתמכת")
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / name
    if target.is_symlink() or (target.exists() and not target.is_file()):
        raise ValueError("נתיב היעד אינו קובץ רגיל")
    existing = target.exists()
    description = ("לדרוס PDF קיים" if existing else "ליצור PDF חדש") + ": " + name + " בתיקיית העבודה?"
    if not approve(description):
        return {"cancelled": True}

    from PySide6.QtCore import QMarginsF
    from PySide6.QtGui import QFont, QPageSize, QTextDocument
    from PySide6.QtPrintSupport import QPrinter

    paragraphs = content.splitlines()
    blocks = "".join(
        '<p style="margin:0 0 9pt 0;white-space:pre-wrap;">'
        + (html.escape(line) if line else "&nbsp;") + "</p>"
        for line in paragraphs
    )
    document = QTextDocument()
    document.setDefaultFont(QFont("Segoe UI", 11))
    document.setHtml(
        '<html><head><meta charset="utf-8"></head><body>'
        '<div dir="' + direction + '" style="font-family:Segoe UI,Arial,sans-serif;'
        'font-size:11pt;line-height:1.5;text-align:' + ("right" if direction == "rtl" else "left")
        + ';">' + blocks + "</div></body></html>"
    )

    fd, temp_path = tempfile.mkstemp(prefix=".pending-pdf-", suffix=".pdf", dir=str(folder))
    os.close(fd)
    try:
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(temp_path)
        printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        printer.setPageMargins(QMarginsF(18, 18, 18, 18), QPageSize.Unit.Millimeter)
        document.print_(printer)
        with open(temp_path, "rb") as stream:
            if stream.read(5) != b"%PDF-":
                raise IOError("הפקת ה־PDF נכשלה")
        if os.path.getsize(temp_path) < 100:
            raise IOError("קובץ PDF ריק או לא תקין")
        if existing:
            backup = folder / ".backups"
            backup.mkdir(exist_ok=True)
            shutil.copy2(target, backup / (datetime.now().strftime("%Y%m%d-%H%M%S-%f") + "-" + name))
        os.replace(temp_path, target)
        return {"created_pdf": str(target), "size_bytes": target.stat().st_size, "direction": direction}
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
