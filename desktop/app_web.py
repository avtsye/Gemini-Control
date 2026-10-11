"""Embedded Gemini website with a narrow, approval-gated Windows bridge.
No Gemini API calls. Google login may restrict embedded browsers.
"""
import json
import sys
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import QObject, Slot, Signal, QUrl, Qt
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QMessageBox)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineScript, QWebEngineProfile
from PySide6.QtWebChannel import QWebChannel
from agent_core import DesktopAgent

class Operations(QObject):
    result = Signal(str)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.agent=DesktopAgent("",approval=self.confirm)
        self.enabled=True
    def confirm(self, description):
        return QMessageBox.question(None,"אישור פעולה של Gemini",description,
            QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)==QMessageBox.StandardButton.Yes
    @Slot(str)
    def propose(self, raw):
        try:
            obj=json.loads(raw)
            if not isinstance(obj,dict) or obj.get("version")!=1:
                raise ValueError("פורמט לא תקין")
            operation=obj.get("type")
            if operation not in {"open_app","write_file","question","screenshot"}:
                raise ValueError("פעולה אינה נתמכת בגרסת האתר")
            if not self.enabled:
                raise PermissionError("הגשר כבוי")
            if operation=="question":
                result={"question":str(obj.get("question",""))[:500]}
            elif operation=="screenshot":
                if not self.confirm("לצלם מסך ולשמור צילום מקומי? הצילום לא יישלח ל-Gemini."):
                    result={"cancelled":True}
                else:
                    screen=QApplication.primaryScreen()
                    if screen is None: raise RuntimeError("לא נמצא מסך לצילום")
                    folder=Path.home()/"Pictures"/"GeminiControl"
                    folder.mkdir(parents=True,exist_ok=True)
                    destination=folder/("Screenshot-"+datetime.now().strftime("%Y%m%d-%H%M%S-%f")+".png")
                    if not screen.grabWindow(0).save(str(destination),"PNG"):
                        raise RuntimeError("שמירת צילום המסך נכשלה")
                    result={"saved_screenshot":str(destination),"uploaded":False}
            elif operation=="open_app":
                result=self.agent.execute("open_app",{"app":obj.get("app")})
            else:
                result=self.agent.execute("write_file",{"name":obj.get("name"),"content":obj.get("content")})
            self.result.emit(json.dumps({"ok":True,"result":result},ensure_ascii=False))
        except Exception as exc:
            self.result.emit(json.dumps({"ok":False,"error":str(exc)[:400]},ensure_ascii=False))

class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gemini Control — אתר Gemini עם גשר מקומי")
        self.resize(1200,800)
        root=QWidget(); self.setCentralWidget(root)
        layout=QVBoxLayout(root)
        layout.setContentsMargins(0,0,0,0)
        self.statusBar().showMessage("Gemini Control פעיל · אישור נדרש לפעולות מחשב")
        self.web=QWebEngineView()
        # Use a persistent profile for website sign-in and local cookies.
        profile=QWebEngineProfile("GeminiControl",self)
        profile.setPersistentStoragePath(str(Path.home()/".gemini-control-browser"))
        self.web.setPage(__import__("PySide6.QtWebEngineCore",fromlist=["QWebEnginePage"]).QWebEnginePage(profile,self.web))
        self.operations=Operations(self)
        channel=QWebChannel(self.web.page())
        channel.registerObject("computerBridge",self.operations)
        self.web.page().setWebChannel(channel)
        script=QWebEngineScript()
        script.setName("Gemini Control website adapter")
        script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentReady)
        script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
        script.setRunsOnSubFrames(False)
        script.setSourceCode((Path(__file__).with_name("website_bridge.js")).read_text(encoding="utf-8"))
        profile.scripts().insert(script)
        # The page may navigate to Google sign-in; the adapter checks hostname before activation.
        layout.addWidget(self.web)
        self.web.setUrl(QUrl("https://gemini.google.com/app"))
        self.web.loadFinished.connect(self.loaded)
        root.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        menu=self.menuBar().addMenu("גשר מקומי")
        menu.addAction("השבת / הפעל פעולות").triggered.connect(self.toggle_agent)
    def toggle_agent(self):
        self.operations.enabled=not self.operations.enabled
        self.operations.agent.enabled=self.operations.enabled
        self.statusBar().showMessage("הגשר פעיל" if self.operations.enabled else "הגשר מושבת")
    def loaded(self,ok):
        if not ok:self.statusBar().showMessage("האתר לא נטען. בדוק רשת, תעודות או חסימה של דפדפן מוטמע.")

def main():
    app=QApplication(sys.argv)
    win=Window();win.show()
    sys.exit(app.exec())
if __name__=="__main__":main()
