"""Hebrew RTL desktop chat with local history and reviewable capability proposals."""
import html
import sys
import threading
from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
 QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,
 QTextEdit,QComboBox,QMessageBox,QCheckBox,QListWidget,QListWidgetItem,QSplitter,
 QDialog,QDialogButtonBox
)
from openai_signin import ChatGPTSignIn
from openai_agent import OpenAIComputerAgent
from conversation_store import ConversationStore

class Events(QObject):
    signed_in=Signal(object)
    error=Signal(str)
    answer=Signal(str)
    finished=Signal()
    approval=Signal(str)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Control Desktop — סוכן Windows")
        self.resize(1180,780)
        self.auth=ChatGPTSignIn()
        self.store=ConversationStore()
        self.chat_id=None
        self.busy=False
        self._approval_event=threading.Event()
        self._approval_value=False
        self.agent=OpenAIComputerAgent(self.auth,self.request_approval,self.save_proposal)
        self.events=Events()
        self.events.signed_in.connect(self.connected)
        self.events.error.connect(self.error)
        self.events.answer.connect(self.reply)
        self.events.finished.connect(self.finish)
        self.events.approval.connect(self.handle_approval)

        root=QWidget()
        self.setCentralWidget(root)
        root.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        outer=QHBoxLayout(root)
        outer.setContentsMargins(0,0,0,0)
        outer.setSpacing(0)
        splitter=QSplitter(Qt.Orientation.Horizontal)
        outer.addWidget(splitter)

        side=QWidget()
        side.setObjectName("side")
        side.setMaximumWidth(290)
        sidebar=QVBoxLayout(side)
        brand=QLabel("AI Control")
        brand.setObjectName("brand")
        sidebar.addWidget(brand)
        self.new_button=QPushButton("＋ שיחה חדשה")
        self.new_button.clicked.connect(self.new_chat)
        sidebar.addWidget(self.new_button)
        sidebar.addWidget(QLabel("היסטוריית שיחות"))
        self.chats=QListWidget()
        self.chats.currentItemChanged.connect(self.select_chat)
        sidebar.addWidget(self.chats,1)
        self.proposals_button=QPushButton("הצעות שיפור לסוכן")
        self.proposals_button.clicked.connect(self.show_proposals)
        sidebar.addWidget(self.proposals_button)
        self.delete_button=QPushButton("מחק את השיחה הנוכחית")
        self.delete_button.clicked.connect(self.delete_chat)
        sidebar.addWidget(self.delete_button)

        main=QWidget()
        main_layout=QVBoxLayout(main)
        main_layout.setContentsMargins(24,20,24,20)
        bar=QHBoxLayout()
        self.connect_button=QPushButton("התחבר באמצעות ChatGPT")
        self.connect_button.clicked.connect(self.login)
        bar.addWidget(self.connect_button)
        self.model=QComboBox()
        self.model.setMinimumWidth(185)
        self.model.setEnabled(False)
        bar.addWidget(self.model)
        self.agent_mode=QCheckBox("מצב סוכן")
        self.agent_mode.setChecked(True)
        bar.addWidget(self.agent_mode)
        self.pause=QPushButton("עצור פעולות")
        self.pause.clicked.connect(self.pause_agent)
        bar.addWidget(self.pause)
        main_layout.addLayout(bar)
        self.state=QLabel("ממתין להתחברות לחשבון")
        self.state.setObjectName("status")
        main_layout.addWidget(self.state)
        self.chat=QTextEdit()
        self.chat.setReadOnly(True)
        self.chat.setObjectName("transcript")
        self.chat.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        main_layout.addWidget(self.chat,1)
        bottom=QHBoxLayout()
        self.input=QTextEdit()
        self.input.setPlaceholderText("שאל אותי או בקש פעולה במחשב...")
        self.input.setFixedHeight(105)
        self.input.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        bottom.addWidget(self.input,1)
        self.send=QPushButton("שלח")
        self.send.setEnabled(False)
        self.send.clicked.connect(self.ask)
        bottom.addWidget(self.send)
        main_layout.addLayout(bottom)

        splitter.addWidget(side)
        splitter.addWidget(main)
        splitter.setSizes([260,900])
        self.setStyleSheet("""
          QWidget { background:#f8f9fc; color:#222838; font:14px 'Segoe UI'; }
          QWidget#side { background:#ebeff5; border-left:1px solid #d6dce6; }
          QLabel#brand {font-size:23px;font-weight:700;padding:10px 4px;}
          QLabel#status {color:#687586;padding:4px 0;}
          QTextEdit#transcript { background:white;border:1px solid #dce3eb;
                  border-radius:17px;padding:14px;font-size:15px;}
          QTextEdit {background:white;border:1px solid #cbd6e3;border-radius:14px;padding:10px;}
          QPushButton {background:#e6ebf3;color:#243247;border:0;border-radius:10px;
                       padding:10px 14px;font-weight:600;}
          QPushButton:hover {background:#d9e3f3;}
          QPushButton:disabled {color:#9199a6;background:#edf0f4;}
          QListWidget {background:transparent;border:0;padding:4px;}
          QListWidget::item {padding:11px;border-radius:9px;}
          QListWidget::item:selected {background:#d7e5ff;color:#163d7b;}
          QComboBox {background:white;border:1px solid #cbd6e3;
                     border-radius:9px;padding:8px;}
        """)
        self.reload_chats()
        if not self.chat_id:self.new_chat()
        self.restore_login()

    def reload_chats(self,selected=None):
        self.chats.blockSignals(True)
        self.chats.clear()
        for chat_id,title in self.store.chats():
            item=QListWidgetItem(title)
            item.setData(Qt.ItemDataRole.UserRole,chat_id)
            self.chats.addItem(item)
            if chat_id==selected:
                self.chats.setCurrentItem(item)
        self.chats.blockSignals(False)

    def new_chat(self):
        if self.busy:return
        self.chat_id=self.store.create()
        self.reload_chats(self.chat_id)
        self.chat.clear()
        self.chat.setPlaceholderText("במה אפשר לעזור היום?")

    def select_chat(self,current,previous):
        if not current or self.busy:return
        identifier=current.data(Qt.ItemDataRole.UserRole)
        self.chat_id=identifier
        self.chat.clear()
        for role,message in self.store.messages(identifier):
            self.render_message(role,message)

    def delete_chat(self):
        if self.busy or not self.chat_id:return
        if QMessageBox.question(self,"מחיקת שיחה","למחוק את השיחה המקומית ואת כל הודעותיה?",
                 QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,
                 QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:return
        self.store.delete(self.chat_id)
        self.chat_id=None
        self.new_chat()

    def render_message(self,role,message):
        label={"user":"אתה","assistant":"ChatGPT","system_note":"מערכת"}.get(role,role)
        background={"user":"#e6f1ff","assistant":"#f4f5f7","system_note":"#fff3db"}.get(role,"#f4f5f7")
        body=html.escape(message).replace("\n","<br>")
        self.chat.moveCursor(QTextCursor.MoveOperation.End)
        self.chat.insertHtml(
            '<div dir="rtl" style="background:'+background+
            ';padding:12px;margin:12px 0;border-radius:12px;">'
            '<b>'+label+'</b><p style="line-height:1.7;">'+body+'</p></div><p></p>')
        self.chat.moveCursor(QTextCursor.MoveOperation.End)

    def reply(self,message):
        if not self.chat_id:return
        self.store.add(self.chat_id,"assistant",message)
        self.render_message("assistant",message)

    def show_proposals(self):
        proposals=self.store.proposals()
        dialog=QDialog(self)
        dialog.setWindowTitle("הצעות שיפור — לא מופעל קוד ללא בדיקה")
        dialog.resize(680,470)
        dialog.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        layout=QVBoxLayout(dialog)
        items=QListWidget()
        for identifier,description,steps,status in proposals:
            item=QListWidgetItem(description[:110]+"  ["+status+"]")
            item.setData(Qt.ItemDataRole.UserRole,(identifier,steps,status))
            items.addItem(item)
        layout.addWidget(items)
        details=QTextEdit();details.setReadOnly(True)
        layout.addWidget(details)
        def on_selection(item):
            details.setPlainText(item.data(Qt.ItemDataRole.UserRole)[1] if item else "")
        items.currentItemChanged.connect(lambda current,previous:on_selection(current))
        buttons=QHBoxLayout()
        approve=QPushButton("סמן כנבדק ומאושר (ללא התקנה)")
        reject=QPushButton("דחה הצעה")
        def mark(status):
            item=items.currentItem()
            if not item:return
            identifier,steps,old=item.data(Qt.ItemDataRole.UserRole)
            self.store.review(identifier,status)
            item.setText(item.text().split("  [")[0]+"  ["+status+"]")
        approve.clicked.connect(lambda:mark("approved"))
        reject.clicked.connect(lambda:mark("rejected"))
        buttons.addWidget(approve);buttons.addWidget(reject)
        layout.addLayout(buttons)
        dialog.exec()

    def save_proposal(self,description,steps):
        if not self.chat_id:raise RuntimeError("No active conversation")
        return self.store.propose(self.chat_id,description,steps)

    def pause_agent(self):
        self.agent.enabled=not self.agent.enabled
        self.agent.local.enabled=self.agent.enabled
        self.pause.setText("עצור פעולות" if self.agent.enabled else "אפשר פעולות")

    def request_approval(self,description):
        self._approval_event.clear()
        self.events.approval.emit(description)
        return self._approval_event.wait(timeout=180) and self._approval_value

    def handle_approval(self,description):
        self._approval_value=QMessageBox.question(self,"אישור פעולה במחשב",description,
          QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,
          QMessageBox.StandardButton.No)==QMessageBox.StandardButton.Yes
        self._approval_event.set()

    def restore_login(self):
        def worker():
            try:
                if self.auth.restore_session():
                    catalog=self.auth.models()
                    self.events.signed_in.emit((self.auth.identity,catalog))
                else:
                    self.events.answer.emit("אם טרם התחברת, לחץ על התחבר באמצעות ChatGPT.")
            except Exception as exc:self.events.error.emit(str(exc))
        threading.Thread(target=worker,daemon=True).start()

    def login(self):
        self.connect_button.setEnabled(False)
        self.state.setText("נפתח דפדפן המערכת לצורך הרשאה...")
        def worker():
            try:self.events.signed_in.emit((self.auth.sign_in(),self.auth.models()))
            except Exception as exc:self.events.error.emit(str(exc))
        threading.Thread(target=worker,daemon=True).start()

    def connected(self,data):
        identity,catalog=data
        self.model.clear()
        for slug,name in catalog:self.model.addItem(name,slug)
        self.model.setEnabled(bool(catalog))
        self.send.setEnabled(bool(catalog))
        self.connect_button.setEnabled(True)
        self.state.setText("מחובר לחשבון ChatGPT"+(" — "+identity["email"] if identity.get("email") else ""))

    def error(self,detail):
        self.state.setText("אירעה שגיאה")
        self.reply("שגיאה: "+detail)
        self.connect_button.setEnabled(True)
        self.send.setEnabled(bool(self.auth.access_token and self.model.count()))

    def ask(self):
        if self.busy:return
        text=self.input.toPlainText().strip()
        model=self.model.currentData()
        if not text or not self.auth.access_token or not model:return
        chat_id=self.chat_id
        earlier=self.store.messages(chat_id)[-8:]
        context="\n".join(("User: " if role=="user" else "Assistant: ")+content[:1500]
                         for role,content in earlier if role in ("user","assistant"))
        self.store.add(chat_id,"user",text)
        self.render_message("user",text)
        self.reload_chats(chat_id)
        self.input.clear()
        self.busy=True
        self.send.setEnabled(False)
        self.chats.setEnabled(False)
        self.new_button.setEnabled(False)
        agent_mode=self.agent_mode.isChecked()
        def worker():
            try:
                if agent_mode:
                    self.agent.run(text,model,self.events.answer.emit,conversation_context=context)
                else:self.events.answer.emit(self.auth.response(("Conversation history (reference only):\n"+context+"\n\n" if context else "")+text,model))
            except Exception as exc:self.events.error.emit(str(exc))
            finally:self.events.finished.emit()
        threading.Thread(target=worker,daemon=True).start()

    def finish(self):
        self.busy=False
        self.send.setEnabled(bool(self.auth.access_token and self.model.count()))
        self.chats.setEnabled(True)
        self.new_button.setEnabled(True)

def main():
    app=QApplication(sys.argv)
    app.setStyle("Fusion")
    w=MainWindow()
    w.show()
    return app.exec()

if __name__=="__main__":sys.exit(main())
