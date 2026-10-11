"""Open-source Windows ChatGPT plan client (preview).
Uses official Sign in with ChatGPT OAuth; no separate API key.
"""
import sys
import threading
from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QComboBox, QMessageBox
)
from openai_signin import ChatGPTSignIn

class Events(QObject):
    signed_in=Signal(object)
    error=Signal(str)
    answer=Signal(str)
    finished=Signal()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Control Desktop — ChatGPT")
        self.resize(960,720)
        self.auth=ChatGPTSignIn()
        self.events=Events()
        self.events.signed_in.connect(self.connected)
        self.events.error.connect(self.error)
        self.events.answer.connect(self.reply)
        self.events.finished.connect(self.finish)
        root=QWidget()
        self.setCentralWidget(root)
        root.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        layout=QVBoxLayout(root)
        top=QHBoxLayout()
        top.addWidget(QLabel("AI Control Desktop"))
        self.connect_button=QPushButton("Continue with ChatGPT")
        self.connect_button.clicked.connect(self.login)
        top.addWidget(self.connect_button)
        self.model=QComboBox()
        self.model.setMinimumWidth(230)
        self.model.setEnabled(False)
        top.addWidget(self.model)
        layout.addLayout(top)
        self.state=QLabel("לא מחובר · נדרש אישור בדפדפן המערכת")
        layout.addWidget(self.state)
        self.chat=QTextEdit()
        self.chat.setReadOnly(True)
        layout.addWidget(self.chat)
        self.input=QTextEdit()
        self.input.setPlaceholderText("כתוב הודעה ל-ChatGPT")
        self.input.setMaximumHeight(110)
        layout.addWidget(self.input)
        self.send=QPushButton("שלח")
        self.send.setEnabled(False)
        self.send.clicked.connect(self.ask)
        layout.addWidget(self.send)
        self.chat.append("התחבר באמצעות ChatGPT. תתבקש לאשר את הרשאות האפליקציה בדפדפן.")
        self.chat.append("התחברות משתמשת במכסת המנוי המורשית, לא במפתח API נפרד.")
        self.chat.append("בגרסת הבסיס אין עדיין הרצת פקודות מחשב מתוך התשובות.")
        root.setStyleSheet("QWidget{font-family:Segoe UI;font-size:14px} QPushButton{padding:10px;border-radius:8px;background:#2060b8;color:white} QTextEdit,QComboBox{padding:7px;border:1px solid #bac8d8;border-radius:7px}")

    def login(self):
        self.connect_button.setEnabled(False)
        self.state.setText("נפתח דפדפן המערכת להשלמת הרשאה...")
        def worker():
            try:
                identity=self.auth.sign_in()
                catalog=self.auth.models()
                self.events.signed_in.emit((identity,catalog))
            except Exception as exc:self.events.error.emit(str(exc))
        threading.Thread(target=worker,daemon=True).start()

    def connected(self,data):
        identity,catalog=data
        self.model.clear()
        for slug,name in catalog:self.model.addItem(name,slug)
        self.model.setEnabled(bool(catalog))
        self.send.setEnabled(bool(catalog))
        self.state.setText("מחובר ל-ChatGPT"+(" — "+identity["email"] if identity.get("email") else ""))
        self.connect_button.setEnabled(True)
        if not catalog:self.chat.append("אין מודלים זמינים במכסת החשבון. בדוק את ההרשאות והמגבלות.")

    def error(self,detail):
        self.state.setText("שגיאת התחברות או בקשה")
        self.chat.append("שגיאה: "+detail)
        self.connect_button.setEnabled(True)
        self.send.setEnabled(bool(self.auth.access_token and self.model.count()))

    def ask(self):
        text=self.input.toPlainText().strip()
        if not text or not self.auth.access_token:return
        model=self.model.currentData()
        if not model:return
        self.send.setEnabled(False)
        self.chat.append("אתה: "+text)
        self.input.clear()
        def worker():
            try:self.events.answer.emit(self.auth.response(text,model))
            except Exception as exc:self.events.error.emit(str(exc))
            finally:self.events.finished.emit()
        threading.Thread(target=worker,daemon=True).start()

    def reply(self,text):
        self.chat.append("ChatGPT: "+text)

    def finish(self):
        self.send.setEnabled(bool(self.auth.access_token and self.model.count()))

def main():
    app=QApplication(sys.argv)
    app.setStyle("Fusion")
    window=MainWindow()
    window.show()
    return app.exec()

if __name__=="__main__":
    sys.exit(main())
