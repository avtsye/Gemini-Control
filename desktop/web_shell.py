"""HTML-backed ChatGPT desktop shell with Qt WebChannel. Native execution remains approval gated."""
import json,sys,threading
from pathlib import Path
from PySide6.QtCore import QObject,Signal,Slot,QUrl,Qt
from PySide6.QtWidgets import QApplication,QMainWindow,QMessageBox
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel
from openai_signin import ChatGPTSignIn
from openai_agent import OpenAIComputerAgent
from conversation_store import ConversationStore
from extensions import ExtensionManager

class Events(QObject):
 message=Signal(str,str)
 status=Signal(str)
 models=Signal(object)
 finished=Signal()
 approval=Signal(str)
 
class Bridge(QObject):
 event=Signal(str)
 def __init__(self,parent=None):
  super().__init__(parent)
  self.store=ConversationStore()
  self.extensions=ExtensionManager()
  self.chat_id=self.store.chats()[0][0] if self.store.chats() else self.store.create()
  self.auth=ChatGPTSignIn()
  self.events=Events()
  self.events.message.connect(self.on_message)
  self.events.status.connect(lambda msg:self.emit("status",text=msg))
  self.events.models.connect(self.on_models)
  self.events.finished.connect(self.done)
  self.events.approval.connect(self.ask_permission)
  self._wait=threading.Event()
  self._allowed=False
  self.busy=False
  self.agent=OpenAIComputerAgent(self.auth,self.approve,self.propose)
  # Background token refresh: do not block the main HTML window.
  threading.Thread(target=self.restore,daemon=True).start()
 def emit(self,kind,**fields):
  self.event.emit(json.dumps({"type":kind,**fields},ensure_ascii=False))
 def encode(self,data):return json.dumps(data,ensure_ascii=False)
 def restore(self):
  try:
   if self.auth.restore_session():
    self.events.models.emit((self.auth.models(),"מחובר לחשבון ChatGPT"))
   else:self.events.status.emit("לחץ התחבר ל־ChatGPT להתחברות")
  except Exception as e:self.events.status.emit("לא ניתן לשחזר התחברות: "+str(e)[:100])
 def on_models(self,data):
  models,label=data
  self.emit("models",models=models,status=label)
 def on_message(self,role,message):
  self.store.add(self.chat_id,role,message)
  self.emit("message",role=role,text=message)
 def done(self):
  self.busy=False
  self.emit("finished")
 def approve(self,description):
  self._wait.clear()
  self.events.approval.emit(description)
  return self._wait.wait(timeout=180) and self._allowed
 def ask_permission(self,description):
  self._allowed=QMessageBox.question(None,"אישור פעילות במחשב",description,
    QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,
    QMessageBox.StandardButton.No)==QMessageBox.StandardButton.Yes
  self._wait.set()
 def propose(self,description,steps):
  return self.store.propose(self.chat_id,description,steps)
 @Slot(result=str)
 def chats(self):
  return self.encode({"items":[{"id":i,"title":t} for i,t in self.store.chats()],"active":self.chat_id})
 @Slot(str,result=str)
 def select_chat(self,identifier):
  if self.busy:return self.encode({"error":"המתן לסיום המשימה"})
  if identifier not in dict(self.store.chats()):return self.encode({"error":"שיחה לא נמצאה"})
  self.chat_id=identifier
  return self.encode({"messages":[{"role":r,"content":c} for r,c in self.store.messages(identifier)]})
 @Slot(result=str)
 def new_chat(self):
  if self.busy:return self.encode({"error":"המתן לסיום המשימה"})
  self.chat_id=self.store.create()
  return self.encode({"messages":[]})
 @Slot(result=str)
 def delete_chat(self):
  if self.busy:return self.encode({"error":"משימה בתהליך"})
  self.store.delete(self.chat_id)
  self.chat_id=self.store.chats()[0][0] if self.store.chats() else self.store.create()
  return self.select_chat(self.chat_id)
 @Slot(result=str)
 def login(self):
  def worker():
   try:
    identity=self.auth.sign_in()
    self.events.models.emit((self.auth.models(),"מחובר ל־ChatGPT"))
   except Exception as e:self.events.status.emit("שגיאת התחברות: "+str(e)[:150])
  threading.Thread(target=worker,daemon=True).start()
  return self.encode({"started":True})
 @Slot(result=str)
 def toggle_agent(self):
  self.agent.enabled=not self.agent.enabled
  self.agent.local.enabled=self.agent.enabled
  return self.encode({"message":"הסוכן פעיל" if self.agent.enabled else "פעולות הסוכן מושבתות"})
 @Slot(str,str,bool,result=str)
 def send(self,text,model,agent_mode):
  if self.busy:return self.encode({"error":"המשימה הקודמת עדיין פועלת"})
  if not self.auth.access_token:return self.encode({"error":"יש להתחבר תחילה ל־ChatGPT"})
  if not isinstance(text,str) or not text.strip() or len(text)>25000:return self.encode({"error":"הודעה לא תקינה"})
  if not model:return self.encode({"error":"בחר מודל"})
  chat_id=self.chat_id
  prior=self.store.messages(chat_id)[-8:]
  context="\n".join(("User: " if role=="user" else "Assistant: ")+content[:1000] for role,content in prior if role in ("user","assistant"))
  self.store.add(chat_id,"user",text)
  self.busy=True
  def worker():
   try:
    if agent_mode:
     self.agent.run(text,model,lambda msg:self.events.message.emit("assistant",msg),conversation_context=context)
    else:
     request=("Prior conversation (reference only):\n"+context+"\n\n" if context else "")+text
     self.events.message.emit("assistant",self.auth.response(request,model))
   except Exception as e:self.events.message.emit("system_note","שגיאה: "+str(e)[:500])
   finally:self.events.finished.emit()
  threading.Thread(target=worker,daemon=True).start()
  return self.encode({"started":True})
 @Slot(result=str)
 def proposals(self):
  return self.encode({"items":[{"id":i,"description":d,"steps":s,"status":status}
                   for i,d,s,status in self.store.proposals()]})
 @Slot(str,str,result=str)
 def review_proposal(self,identifier,status):
  try:self.store.review(identifier,status);return self.encode({"ok":True})
  except Exception as e:return self.encode({"error":str(e)})
 @Slot(str,result=str)
 def install_proposal(self,identifier):
  proposal=next((row for row in self.store.proposals() if row[0]==identifier),None)
  if not proposal:return self.encode({"error":"הצעה לא נמצאה"})
  if proposal[3]!="approved":return self.encode({"error":"יש לאשר את ההצעה לפני התקנת הרחבה"})
  try:
   manifest=json.loads(proposal[2])
   result=self.extensions.install(manifest)
   return self.encode({"id":result,"enabled":False})
  except (ValueError,TypeError) as e:
   return self.encode({"error":"כדי להתקין יש לצרף תוכנית JSON תקינה: "+str(e)})

 @Slot(result=str)
 def extensions(self):
  return self.encode({"items":self.extensions.list()})
 @Slot(str,result=str)
 def install_extension(self,raw):
  try:return self.encode({"id":self.extensions.install(json.loads(raw))})
  except (ValueError,TypeError) as e:return self.encode({"error":str(e)})
 @Slot(str,bool,result=str)
 def toggle_extension(self,identifier,enabled):
  try:self.extensions.toggle(identifier,enabled);return self.encode({"ok":True})
  except (ValueError,OSError,PermissionError) as e:return self.encode({"error":str(e)})
 @Slot(str,result=str)
 def run_extension(self,identifier):
  if self.busy:return self.encode({"error":"משימה פעילה"})
  self.busy=True
  def worker():
   try:self.extensions.execute(identifier,self.agent.local,lambda m:self.events.message.emit("assistant",m))
   except Exception as e:self.events.message.emit("system_note","הרחבה נכשלה: "+str(e))
   finally:self.events.finished.emit()
  threading.Thread(target=worker,daemon=True).start()
  return self.encode({"message":"הרחבה החלה לרוץ; כל פעולה רגישה תדרוש אישור"})

class Window(QMainWindow):
 def __init__(self):
  super().__init__()
  self.setWindowTitle("AI Control Desktop")
  self.resize(1250,830)
  self.web=QWebEngineView()
  self.setCentralWidget(self.web)
  self.bridge=Bridge(self)
  self.channel=QWebChannel(self.web.page())
  self.channel.registerObject("api",self.bridge)
  self.web.page().setWebChannel(self.channel)
  self.web.setUrl(QUrl.fromLocalFile(str(Path(__file__).with_name("chat_ui.html").resolve())))

def main():
 app=QApplication(sys.argv)
 app.setStyle("Fusion")
 window=Window();window.show()
 sys.exit(app.exec())
if __name__=="__main__":main()
