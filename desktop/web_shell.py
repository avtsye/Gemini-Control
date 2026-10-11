"""HTML-backed ChatGPT desktop shell with Qt WebChannel. Native execution remains approval gated."""
import json,sys,threading
from pathlib import Path
from PySide6.QtCore import QObject,Signal,Slot,QUrl,Qt
from PySide6.QtWidgets import QApplication,QMainWindow,QFileDialog
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel
from openai_signin import ChatGPTSignIn
from openai_agent import OpenAIComputerAgent
from conversation_store import ConversationStore
from extensions import ExtensionManager
from capability_workshop import CapabilityWorkshop

class Events(QObject):
 message=Signal(str,str)
 status=Signal(str)
 models=Signal(object)
 finished=Signal()
 approval=Signal(str)
 extension_draft=Signal(object)
 
class Bridge(QObject):
 event=Signal(str)
 def __init__(self,parent=None):
  super().__init__(parent)
  self.store=ConversationStore()
  self.extension_manager=ExtensionManager()
  self.workshop=CapabilityWorkshop()
  self.chat_id=self.store.chats()[0][0] if self.store.chats() else self.store.create()
  self.auth=ChatGPTSignIn()
  self.events=Events()
  self.events.message.connect(self.on_message)
  self.events.status.connect(lambda msg:self.emit("status",text=msg))
  self.events.models.connect(self.on_models)
  self.events.finished.connect(self.done)
  self.events.approval.connect(self.ask_permission)
  self.events.extension_draft.connect(lambda info:self.emit("extension_draft",**info))
  self._wait=threading.Event()
  self._allowed=False
  self.busy=False
  self.active_task_chat=None
  self.available_models=[]
  self.logins_in_progress=False
  self.attachments=[]
  self.agent=OpenAIComputerAgent(self.auth,self.approve,self.propose,workshop=self.workshop,
    on_capability_draft=lambda info:self.events.extension_draft.emit(info))
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
  self.available_models=models
  self.emit("models",models=models,status=label)
 def on_message(self,role,message):
  target=self.active_task_chat or self.chat_id
  self.store.add(target,role,message)
  self.emit("message",role=role,text=message)
 def done(self):
  self.busy=False
  self.active_task_chat=None
  self.emit("finished")
 def approve(self,description):
  self._wait.clear()
  self._allowed=False
  self.events.approval.emit(description)
  return self._wait.wait(timeout=180) and self._allowed
 def ask_permission(self,description):
  self.emit("approval",description=description)
 @Slot(bool,result=str)
 def approval_reply(self,allowed):
  self._allowed=bool(allowed)
  self._wait.set()
  return self.encode({"ok":True})
 def propose(self,description,steps):
  return self.store.propose(self.chat_id,description,steps)
 @Slot(result=str)
 def session(self):
  return self.encode({"models":self.available_models,
   "status":"מחובר ל־ChatGPT" if self.auth.access_token else "לחץ התחבר ל־ChatGPT"})

 @Slot(result=str)
 def account_details(self):
  identity=self.auth.identity or {}
  return self.encode({"connected":bool(self.auth.access_token),
   "email":identity.get("email") or "לא זמין",
   "model_count":len(self.available_models),
   "models":[name for _,name in self.available_models],
   "expires_at":self.auth.expires_at if self.auth.access_token else 0,
   "usage":"השרת לא מספק לממשק הזה נתוני מכסה מדויקים",
   "history_path":self.store.path,
   "capability_count":len(self.workshop.list())})

 @Slot(result=str)
 def pick_attachment(self):
  if self.busy:return self.encode({"error":"המתן לסיום הבקשה"})
  paths,_=QFileDialog.getOpenFileNames(None,"בחר קבצים לשיחה","","מסמכים (*.txt *.md *.csv *.json *.py *.pdf *.docx);;כל הקבצים (*)")
  if not paths:return self.encode({"cancelled":True})
  added=[]
  for path in paths[:12]:
   item=json.loads(self.add_attachment_path(path))
   if item.get("error"):return self.encode({"error":item["error"],"added":added})
   added.append(item)
  return self.encode({"items":added,"pending":len(self.attachments)})
 @Slot(str,result=str)
 def add_attachment_path(self,path):
  file=Path(path)
  if not file.is_file() or file.stat().st_size>5_000_000:
   return self.encode({"error":"אפשר לצרף קובץ עד 5MB בלבד"})
  allowed={".txt",".md",".csv",".json",".py",".pdf",".docx"}
  if file.suffix.lower() not in allowed:
   return self.encode({"error":"פורמט זה אינו נתמך עדיין לקריאת תוכן"})
  try:
   if file.suffix.lower()==".pdf":
    from pypdf import PdfReader
    reader=PdfReader(str(file))
    body="\n".join((page.extract_text() or "") for page in reader.pages[:12])
   elif file.suffix.lower()==".docx":
    from docx import Document
    body="\n".join(p.text for p in Document(str(file)).paragraphs)
   else:
    body=file.read_text(encoding="utf-8",errors="replace")
   body=body[:18000]
   if len(self.attachments)>=12:return self.encode({"error":"ניתן לצרף עד 12 קבצים"})
   self.attachments.append({"name":file.name,"text":body})
   return self.encode({"name":file.name,"characters":len(body),"pending":len(self.attachments)})
  except Exception as exc:return self.encode({"error":"לא ניתן לקרוא את הקובץ: "+str(exc)[:150]})

 @Slot(result=str)
 def clear_attachments(self):
  self.attachments.clear()
  return self.encode({"ok":True})

 @Slot(result=str)
 def chats(self):
  return self.encode({"items":[{"id":i,"title":t,"pinned":bool(pin),"archived":bool(arc),"project":project} for i,t,pin,arc,project in self.store.chats_detailed()],"active":self.chat_id})
 @Slot(str,result=str)
 def search_chats(self,query):
  return self.encode({"items":[{"id":i,"title":title,"role":role,"snippet":snippet}
                               for i,title,role,snippet in self.store.search(query)]})
 @Slot(str,str,str,result=str)
 def set_chat_property(self,identifier,property_name,value):
  try:
   if property_name=="project":self.store.set_flags(identifier,project=value)
   elif property_name=="pinned":self.store.set_flags(identifier,pinned=value=="true")
   elif property_name=="archived":self.store.set_flags(identifier,archived=value=="true")
   else:raise ValueError("Unknown property")
   return self.encode({"ok":True})
  except (ValueError,OSError) as exc:return self.encode({"error":str(exc)})
 @Slot(int,str,result=str)
 def edit_message(self,index,text):
  if self.busy:return self.encode({"error":"Cannot edit during active task"})
  try:
   self.store.edit_user_message(self.chat_id,index,text)
   return self.select_chat(self.chat_id)
  except (ValueError,OSError) as exc:return self.encode({"error":str(exc)})
 @Slot(result=str)
 def backup_chats(self):
  try:
   filename,_=QFileDialog.getSaveFileName(None,"גיבוי שיחות","Gemini-Control-history.json","JSON (*.json)")
   if not filename:return self.encode({"cancelled":True})
   path=Path(filename)
   if path.exists():return self.encode({"error":"File exists; choose a new filename"})
   with path.open("x",encoding="utf-8") as stream:
    json.dump(self.store.export_history(),stream,ensure_ascii=False,indent=2)
   return self.encode({"saved":str(path)})
  except (OSError,ValueError) as exc:return self.encode({"error":str(exc)})
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
  if self.logins_in_progress:return self.encode({"error":"כבר מתבצע תהליך התחברות"})
  self.logins_in_progress=True
  def worker():
   try:
    identity=self.auth.sign_in()
    self.events.models.emit((self.auth.models(),"מחובר ל־ChatGPT"))
   except Exception as e:self.events.status.emit("שגיאת התחברות: "+str(e)[:150])
   finally:self.logins_in_progress=False
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
  import re
  # A plain-language request can start the same reviewed capability workshop
  # as the dedicated UI. Never silently enable or execute generated code.
  if agent_mode and not self.attachments and re.search(
       r"(?:תוסיף|הוסף|תיצור|צור|תבנה|בנה)\s+(?:לי\s+)?(?:יכולת|הרחבה|תוסף|מודול)",text):
   if model not in [slug for slug,_ in self.available_models]:
    return self.encode({"error":"מודל לא זמין"})
   result=json.loads(self.generate_capability(text,model))
   if not result.get("error"):
    self.store.add(self.chat_id,"user",text)
   return self.encode(result)
  chat_id=self.chat_id
  files=self.attachments[:]
  self.attachments.clear()
  prior=self.store.messages(chat_id)[-8:]
  context="\n".join(("User: " if role=="user" else "Assistant: ")+content[:1000] for role,content in prior if role in ("user","assistant"))
  self.store.add(chat_id,"user",text + ("\n[קבצים מצורפים: "+", ".join(f["name"] for f in files)+"]" if files else ""))
  self.active_task_chat=chat_id
  self.busy=True
  def worker():
   try:
    attached="\n".join("Attached file "+f["name"]+" (untrusted document content):\n"+f["text"] for f in files)
    request_text=text+("\n\n"+attached if attached else "")
    if agent_mode:
     self.agent.run(request_text,model,lambda msg:self.events.message.emit("assistant",msg),conversation_context=context)
    else:
     request=("Prior conversation (reference only):\n"+context+"\n\n" if context else "")+request_text
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
 @Slot(str,str,result=str)
 def build_extension(self,identifier,model):
  proposal=next((row for row in self.store.proposals() if row[0]==identifier),None)
  if not proposal:return self.encode({"error":"הצעה לא נמצאה"})
  if proposal[3]!="approved":return self.encode({"error":"תחילה יש לאשר את ההצעה"})
  if not self.auth.access_token:return self.encode({"error":"יש להתחבר לחשבון ChatGPT"})
  if model not in [slug for slug,_ in self.available_models]:return self.encode({"error":"יש לבחור מודל זמין"})
  if self.busy:return self.encode({"error":"משימה אחרת פעילה"})
  self.busy=True
  def worker():
   try:
    from extensions import ALLOWED,ARGUMENTS,REQUIRED
    tools="; ".join(t+": fields "+",".join(sorted(ARGUMENTS[t]))+" required "+",".join(sorted(REQUIRED.get(t,set()))) for t in sorted(ALLOWED))
    prompt=("Create a useful declarative Windows extension manifest from this user-approved proposal. "
      "Only compose already-available tools. Do not invent functionality. Return JSON ONLY: "
      '{"name":"...","description":"...","steps":[{"tool":"...","arguments":{}}]}. '
      "At most 6 steps. No shell/code execution, placeholders, credential requests, secrets, or URLs to unknown sites. "
      "If this cannot be implemented with the allowed tools return JSON "
      '{"unavailable":"Clear Hebrew explanation of what native capability must be developed first"}. '
      "Allowed tools and argument keys: "+tools+"\nProposal: "+proposal[1]+"\nSuggested plan: "+proposal[2][:6000])
    raw=self.auth.response(prompt,model).strip()
    if raw.startswith("```"):
     raw=raw.split("\n",1)[-1].rsplit("```",1)[0].strip()
    obj=json.loads(raw)
    if "unavailable" in obj:
     self.events.extension_draft.emit({"error":str(obj["unavailable"])[:700]})
    else:
     validated=self.extension_manager.validate(obj)
     self.events.extension_draft.emit({"manifest":validated,"proposal":identifier})
   except Exception as e:
    self.events.extension_draft.emit({"error":"לא ניתן ליצור הרחבה תקינה: "+str(e)[:300]})
   finally:self.events.finished.emit()
  threading.Thread(target=worker,daemon=True).start()
  return self.encode({"started":True})

 @Slot(str,result=str)
 def install_proposal(self,identifier):
  proposal=next((row for row in self.store.proposals() if row[0]==identifier),None)
  if not proposal:return self.encode({"error":"הצעה לא נמצאה"})
  if proposal[3]!="approved":return self.encode({"error":"יש לאשר את ההצעה לפני התקנת הרחבה"})
  try:
   manifest=json.loads(proposal[2])
   result=self.extension_manager.install(manifest)
   return self.encode({"id":result,"enabled":False})
  except (ValueError,TypeError) as e:
   return self.encode({"error":"כדי להתקין יש לצרף תוכנית JSON תקינה: "+str(e)})

 @Slot(str,result=str)
 def example_capability(self,kind):
  templates={"audio":"audio_tone.py","video":"video_gif.py"}
  if kind not in templates:return self.encode({"error":"דוגמה לא קיימת"})
  try:
   source=(Path(__file__).resolve().parent/"examples"/templates[kind]).read_text(encoding="utf-8")
   name="מחולל WAV" if kind=="audio" else "מחולל אנימציית GIF"
   identifier=self.workshop.draft(name,"דוגמה מקומית בקוד Python — נדרשת בדיקה לפני הפעלה",source)
   return self.encode({"id":identifier})
  except (OSError,ValueError) as e:return self.encode({"error":str(e)})

 @Slot(result=str)
 def tools_catalog(self):
  from openai_agent import TOOLS
  from capabilities_catalog import catalog
  return self.encode({"coverage":catalog(TOOLS),"native_tools":sorted(TOOLS),
    "capabilities":[{"id":item.get("id"),"name":item.get("name"),
                     "status":item.get("status"),"description":item.get("description","")}
                     for item in self.workshop.list()]})

 @Slot(result=str)
 def capabilities(self):
  return self.encode({"items":self.workshop.list()})

 @Slot(str,str,str,result=str)
 def draft_capability(self,name,description,source):
  try:
   identifier=self.workshop.draft(name,description,source)
   return self.encode({"id":identifier})
  except (ValueError,SyntaxError,OSError) as e:
   return self.encode({"error":str(e)})

 @Slot(str,result=str)
 def inspect_capability(self,identifier):
  try:return self.encode(self.workshop.inspect(identifier))
  except (ValueError,SyntaxError,OSError) as e:return self.encode({"error":str(e)})

 @Slot(str,bool,result=str)
 def enable_capability(self,identifier,approved):
  try:return self.encode(self.workshop.activate(identifier,approved))
  except (ValueError,PermissionError,OSError,SyntaxError) as e:
   return self.encode({"error":str(e)})

 @Slot(str,result=str)
 def capability_versions(self,identifier):
  try:return self.encode({"versions":self.workshop.versions(identifier)})
  except (ValueError,OSError) as e:return self.encode({"error":str(e)})

 @Slot(str,str,bool,result=str)
 def revise_capability(self,identifier,source,approved):
  try:return self.encode(self.workshop.revise(identifier,source,approved))
  except (ValueError,OSError,PermissionError,SyntaxError) as e:return self.encode({"error":str(e)})

 @Slot(str,int,bool,result=str)
 def rollback_capability(self,identifier,version,approved):
  try:return self.encode(self.workshop.rollback(identifier,version,approved))
  except (ValueError,OSError,PermissionError,SyntaxError) as e:return self.encode({"error":str(e)})

 @Slot(str,result=str)
 def capability_analyze_dependencies(self,identifier):
  try:return self.encode(self.workshop.analyze_dependencies(identifier))
  except (ValueError,OSError,ImportError) as e:return self.encode({"error":str(e)})

 @Slot(str,result=str)
 def capability_dependency_status(self,identifier):
  try:return self.encode(self.workshop.dependency_status(identifier))
  except (ValueError,OSError) as e:return self.encode({"error":str(e)})

 @Slot(str,str,bool,result=str)
 def capability_set_dependencies(self,identifier,raw_packages,approved):
  try:return self.encode(self.workshop.set_dependencies(identifier,json.loads(raw_packages),approved))
  except (ValueError,OSError,PermissionError) as e:return self.encode({"error":str(e)})

 @Slot(str,bool,result=str)
 def capability_create_environment(self,identifier,approved):
  try:return self.encode(self.workshop.create_environment(identifier,approved))
  except (ValueError,OSError,PermissionError) as e:return self.encode({"error":str(e)})

 @Slot(str,bool,result=str)
 def capability_install_dependencies(self,identifier,approved):
  if self.busy:return self.encode({"error":"משימה אחרת פעילה"})
  if not approved:return self.encode({"cancelled":True})
  # Explicit user consent is checked again by workshop.install_dependencies.
  self.busy=True
  self.active_task_chat=self.chat_id
  def worker():
   try:
    result=self.workshop.install_dependencies(identifier,self.approve)
    self.events.message.emit("assistant","התקנת תלויות: "+json.dumps(result,ensure_ascii=False)[:2000])
   except Exception as exc:self.events.message.emit("system_note","התקנת תלויות נכשלה: "+str(exc)[:300])
   finally:self.events.finished.emit()
  threading.Thread(target=worker,daemon=True).start()
  return self.encode({"started":True})

 @Slot(str,str,result=str)
 def test_capability(self,identifier,raw_payload):
  if self.busy:return self.encode({"error":"משימה אחרת פעילה"})
  try:payload=json.loads(raw_payload)
  except ValueError:return self.encode({"error":"קלט JSON אינו תקין"})
  self.busy=True
  self.active_task_chat=self.chat_id
  def worker():
   try:
    result=self.workshop.test_capability(identifier,payload,self.approve)
    self.events.message.emit("assistant","בדיקת הרחבה: "+json.dumps(result,ensure_ascii=False)[:2200])
   except Exception as exc:
    self.events.message.emit("system_note","בדיקת ההרחבה נכשלה: "+str(exc)[:400])
   finally:self.events.finished.emit()
  threading.Thread(target=worker,daemon=True).start()
  return self.encode({"started":True})

 @Slot(str,result=str)
 def disable_capability(self,identifier):
  try:self.workshop.disable(identifier);return self.encode({"ok":True})
  except (ValueError,OSError) as e:return self.encode({"error":str(e)})

 @Slot(str,str,result=str)
 def run_capability(self,identifier,raw_payload):
  if self.busy:return self.encode({"error":"משימה אחרת עדיין פעילה"})
  try:payload=json.loads(raw_payload)
  except ValueError:return self.encode({"error":"קלט JSON אינו תקין"})
  self.busy=True
  self.active_task_chat=self.chat_id
  def worker():
   try:
    result=self.workshop.run(identifier,payload,self.approve)
    self.events.message.emit("assistant","תוצאת הרחבה: "+json.dumps(result,ensure_ascii=False)[:3000])
   except Exception as e:self.events.message.emit("system_note","הרצת הרחבה נכשלה: "+str(e)[:500])
   finally:self.events.finished.emit()
  threading.Thread(target=worker,daemon=True).start()
  return self.encode({"started":True})

 @Slot(str,str,result=str)
 def generate_capability(self,description,model):
  if self.busy:return self.encode({"error":"משימה אחרת עדיין פעילה"})
  if not self.auth.access_token:return self.encode({"error":"יש להתחבר ל־ChatGPT"})
  if model not in [slug for slug,_ in self.available_models]:
   return self.encode({"error":"מודל לא זמין"})
  if not isinstance(description,str) or not 5<=len(description)<=1500:
   return self.encode({"error":"תיאור הרחבה חייב להכיל 5–1500 תווים"})
  self.busy=True
  def worker():
   try:
    prompt=("Design a Python 3 capability extension for this Windows desktop tool. "
      "Return ONLY JSON with keys name, description, source. The source must define "
      "run(payload, output_dir), returning a JSON-serializable result. "
      "The output_dir is where files must be saved. Use Python standard library where possible. "
      "For WAV use wave and math; for simple animations create SVG frame files or GIF if a supported "
      "local image library is explicitly available; do not pretend to generate MP4 without a codec. "
      "Do not read credentials, use network, execute shell commands, or access files outside output_dir. "
      "Clearly explain limits in description. User request: "+description)
    obj=json.loads(self.auth.response(prompt,model))
    identifier=self.workshop.draft(obj["name"],obj.get("description",""),obj["source"])
    folder=self.workshop._path(identifier)
    metadata=self.workshop._manifest(folder)
    metadata["require_test"]=True
    self.workshop._write_manifest(folder,metadata)
    # Generated code stays disabled. Automated review may propose repairs,
    # but every actual execution needs an explicit user approval.
    findings=[]
    test_result=None
    for attempt in range(3):
     info=self.workshop.inspect(identifier)
     findings=info["findings"]
     if findings:
      issue="Sensitive imports detected: "+", ".join(findings)
     else:
      test_result=self.workshop.test_capability(identifier,{},self.approve,timeout=12)
      if test_result.get("passed") or test_result.get("cancelled"):
       break
      issue=str(test_result.get("details","Test failed"))[-1200:]
     if attempt==2:break
     repair_prompt=("Repair this Python capability. Return ONLY a JSON object with key source. "
       "Keep run(payload, output_dir). Use standard library; do not use network, shell, "
       "credentials, or paths outside output_dir. Current source: "+
       self.workshop.source(identifier)+"\\nFailure: "+issue)
     repaired=json.loads(self.auth.response(repair_prompt,model))
     self.workshop.revise(identifier,repaired["source"],approved=True)
    info=self.workshop.inspect(identifier)
    self.events.extension_draft.emit({"capability_id":identifier,"name":obj["name"],
      "description":obj.get("description",""),"source":info["source"],
      "findings":info["findings"],"test_result":test_result,
      "version":self.workshop._manifest(self.workshop._path(identifier)).get("version",1),
      "requires_review":True})
   except Exception as e:
    self.events.extension_draft.emit({"error":"יצירת קוד הרחבה נכשלה: "+str(e)[:350]})
   finally:self.events.finished.emit()
  threading.Thread(target=worker,daemon=True).start()
  return self.encode({"started":True})

 @Slot(result=str)
 def extensions(self):
  return self.encode({"items":self.extension_manager.list()})
 @Slot(str,result=str)
 def install_extension(self,raw):
  try:return self.encode({"id":self.extension_manager.install(json.loads(raw))})
  except (ValueError,TypeError) as e:return self.encode({"error":str(e)})
 @Slot(str,bool,result=str)
 def toggle_extension(self,identifier,enabled):
  try:self.extension_manager.toggle(identifier,enabled);return self.encode({"ok":True})
  except (ValueError,OSError,PermissionError) as e:return self.encode({"error":str(e)})
 @Slot(str,result=str)
 def run_extension(self,identifier):
  if self.busy:return self.encode({"error":"משימה פעילה"})
  self.busy=True
  self.active_task_chat=self.chat_id
  def worker():
   try:self.extension_manager.execute(identifier,self.agent.local,lambda m:self.events.message.emit("assistant",m))
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
