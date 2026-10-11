"""Simple RTL Qt desktop interface for the Gemini agent."""
import os
import sys
import threading
from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
 QHBoxLayout, QTextEdit, QLineEdit, QPushButton, QLabel, QMessageBox, QInputDialog)
from agent_core import DesktopAgent

class Bus(QObject):
    message = Signal(str)
    approval = Signal(str)
    finished = Signal()

class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gemini Control — סוכן המחשב")
        self.resize(850, 680)
        self.bus = Bus()
        self.bus.message.connect(self.append)
        self.bus.approval.connect(self.decide)
        self.bus.finished.connect(self.finish)
        self.agent = None
        self._decision_event = threading.Event()
        self._decision_value = False
        root=QWidget();self.setCentralWidget(root)
        layout=QVBoxLayout(root);layout.setSpacing(13)
        title=QLabel("Gemini Control");title.setStyleSheet("font-size:25px;font-weight:bold")
        subtitle=QLabel("סוכן AI למחשב · פעולות מאושרות בלבד · תיקיית עבודה ייעודית")
        layout.addWidget(title);layout.addWidget(subtitle)
        row=QHBoxLayout()
        self.key=QLineEdit();self.key.setEchoMode(QLineEdit.EchoMode.Password)
        self.key.setPlaceholderText("Gemini API Key — הזן להפעלה")
        row.addWidget(self.key)
        self.toggle=QPushButton("עצור פעולות")
        self.toggle.clicked.connect(self.toggle_agent)
        row.addWidget(self.toggle);layout.addLayout(row)
        self.messages=QTextEdit();self.messages.setReadOnly(True);layout.addWidget(self.messages)
        self.prompt=QTextEdit();self.prompt.setPlaceholderText("מה תרצה שאעשה במחשב?")
        self.prompt.setMaximumHeight(110);layout.addWidget(self.prompt)
        self.send=QPushButton("תכנן ובצע באישורי")
        self.send.clicked.connect(self.start);layout.addWidget(self.send)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        root.setStyleSheet("QWidget{font-family:Segoe UI;font-size:14px} QPushButton{padding:12px;border-radius:8px;background:#275bb8;color:white} QTextEdit,QLineEdit{padding:10px;border:1px solid #bbc8d9;border-radius:8px}")
        self.append("ברוך הבא! הכנס מפתח API וכתוב משימה. פעולות משמעותיות ידרשו אישור.")

    def append(self, message):
        self.messages.append(message)

    def approve(self, description):
        self._decision_event.clear()
        self.bus.approval.emit(description)
        if not self._decision_event.wait(timeout=180):
            return False
        return self._decision_value

    def decide(self, description):
        self._decision_value = QMessageBox.question(self,"אישור פעולת מחשב",description,
            QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes
        self._decision_event.set()

    def toggle_agent(self):
        if self.agent:
            self.agent.enabled = not self.agent.enabled
            self.toggle.setText("עצור פעולות" if self.agent.enabled else "אפשר פעולות")
            self.append("מצב: פעיל" if self.agent.enabled else "מצב: עצור")

    def finish(self):
        self.send.setEnabled(True)

    def start(self):
        task=self.prompt.toPlainText().strip()
        if not task:
            return
        if not self.key.text().strip():
            QMessageBox.warning(self,"מפתח חסר","הזן מפתח Gemini API")
            return
        if self.agent is None or self.agent.api_key!=self.key.text().strip():
            self.agent=DesktopAgent(self.key.text(),approval=self.approve)
        if not self.agent.enabled:
            QMessageBox.warning(self,"סוכן עצור","הפעל את הסוכן לפני שליחת משימה")
            return
        self.send.setEnabled(False)
        self.append("אתה: " + task)
        self.prompt.clear()
        def worker():
            try:self.agent.run(task,self.bus.message.emit)
            except Exception as e:self.bus.message.emit("שגיאה: "+str(e))
            finally:self.bus.finished.emit()
        threading.Thread(target=worker,daemon=True).start()

def main():
    app=QApplication(sys.argv)
    app.setStyle("Fusion")
    w=Window();w.show()
    sys.exit(app.exec())
if __name__=="__main__":main()
