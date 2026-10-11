"""Offline structural QA checks. Run: python desktop/tests/test_ui_contract.py -v"""
import ast,pathlib,re,unittest,subprocess,shutil
from html.parser import HTMLParser

ROOT=pathlib.Path(__file__).resolve().parents[1]
class IDs(HTMLParser):
 def __init__(self):super().__init__();self.ids=[]
 def handle_starttag(self,tag,attrs):
  attributes=dict(attrs)
  if "id" in attributes:self.ids.append(attributes["id"])

class UIContract(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.html=(ROOT/"chat_ui.html").read_text(encoding="utf-8")
  cls.shell=(ROOT/"web_shell.py").read_text(encoding="utf-8")
  cls.parser=IDs();cls.parser.feed(cls.html)
 def test_unique_html_ids(self):
  self.assertEqual(len(self.parser.ids),len(set(self.parser.ids)))
 def test_html_rtl_and_keyboard_access(self):
  self.assertIn('lang="he" dir="rtl"',self.html)
  self.assertIn('aria-label="הודעה"',self.html)
  self.assertIn('aria-label="שלח"',self.html)
 def test_dom_targets_exist(self):
  for element in set(re.findall(r"\\$\\('([a-zA-Z][\\w-]*)'\\)",self.html)):
   with self.subTest(id=element):
    self.assertTrue(element in self.parser.ids or
                    ".id='"+element+"'" in self.html or
                    '.id="'+element+'"' in self.html,
                    "Missing static or dynamically created ID: "+element)
 def test_webchannel_methods_exist(self):
  methods=set(re.findall(r"call\('([a-z_]+)'",self.html))
  decorators=set(re.findall(r"@Slot\([^\n]*?result=str\)\s+def ([a-z_]+)\(",self.shell))
  self.assertFalse(methods-decorators,"Undeclared Qt bridge methods: "+str(methods-decorators))
 def test_reminder_timer_and_bridge(self):
  self.assertIn("self.reminder_timer.timeout.connect(self._poll_reminders)",self.shell)
  self.assertIn("def _poll_reminders(self):",self.shell)
  for name in ("list_reminders","schedule_reminder","cancel_reminder"):
   self.assertIn("def "+name+"(",self.shell)
 def test_qt_slots_not_shadowed_by_attributes(self):
  self.assertNotIn("self.extensions=ExtensionManager()",self.shell)
  self.assertIn("self.extension_manager=ExtensionManager()",self.shell)
  self.assertIn("def extensions(self):",self.shell)
 def test_native_js_alerts_removed(self):
  self.assertNotIn("alert(",self.html)
  self.assertNotIn("confirm(",self.html)
  self.assertIn("id=\"toastArea\"",self.html)
  self.assertIn("id=\"confirmDialog\"",self.html)
 def test_native_permission_dialog_replaced(self):
  self.assertNotIn("QMessageBox.question",self.shell)
  self.assertIn('self.emit("approval",description=description)',self.shell)
  self.assertIn("def approval_reply(self,allowed):",self.shell)
  self.assertIn("msg.type==='approval'",self.html)
 def test_extension_draft_flow(self):
  self.assertIn("def build_extension(self,identifier,model):",self.shell)
  self.assertIn("self.extension_manager.validate(obj)",self.shell)
  self.assertIn("msg.type==='extension_draft'",self.html)
  self.assertIn("התקן הרחבה מושבתת",self.html)
 def test_chat_attachments_account_activity(self):
  self.assertIn('id="attach"',self.html)
  self.assertIn('id="fileChips"',self.html)
  self.assertIn('id="account"',self.html)
  self.assertIn('id="activityText"',self.html)
  self.assertIn("def pick_attachment(self):",self.shell)
  self.assertIn("def account_details(self):",self.shell)
 def test_direct_capability_request(self):
  self.assertIn('self.generate_capability(text,model)',self.shell)
  self.assertIn('def generate_capability(self,description,model):',self.shell)
 def test_qt_bridge_signal_name(self):
  self.assertIn('registerObject("api",self.bridge)',self.shell)
  self.assertIn("bridge.event.connect(",self.html)
 def test_secure_html_messages(self):
  self.assertIn("renderMarkdown(content,text)",self.html)
  self.assertIn("function renderInlineMarkdown(target,value)",self.html)
  self.assertIn("document.createTextNode(",self.html)
  self.assertIn("noopener noreferrer",self.html)
  self.assertNotIn("innerHTML=",self.html)
 def test_file_picker_preview_binding(self):
  self.assertIn("def preview_attachment(self,index):",self.shell)
  self.assertIn("call('preview_attachment',index)",self.html)
  self.assertIn("content.kind==='image'",self.html)
 def test_narrow_screen_actions_remain_reachable(self):
  import re
  self.assertRegex(self.html,r"\\.side-actions\\{[^}]*overflow-y:auto")
  self.assertRegex(self.html,r"\\.toolbar\\{[^}]*flex-wrap:wrap")
  self.assertRegex(self.html,r"#modalBody\\{[^}]*overflow-y:auto")
  self.assertRegex(self.html,r"\\.compose-actions\\{[^}]*flex-wrap:wrap")
  self.assertRegex(self.html,r"@media\\(max-width:720px\\)")
  self.assertIn('<details class="nav-details">',self.html)
  self.assertIn('<summary>ניהול ותוספים</summary>',self.html)
 def test_inline_javascript_syntax(self):
  executable=shutil.which("node")
  if not executable:self.skipTest("Node.js is not installed")
  blocks=re.findall(r"<script[^>]*>(.*?)</script>",self.html,re.S)
  scripts=[b for b in blocks if b.strip()]
  self.assertTrue(scripts,"Expected inline application script")
  for source in scripts:
   result=subprocess.run([executable,"--check"],input=source,
                         capture_output=True,text=True,encoding="utf-8",
                         errors="replace",timeout=15)
   self.assertEqual(result.returncode,0,result.stderr[-1200:])
 def test_source_python_syntax(self):
  for path in ROOT.glob("*.py"):
   with self.subTest(path=path.name):ast.parse(path.read_text(encoding="utf-8"),filename=str(path))
 def test_only_manual_ci(self):
  pipeline=(ROOT.parent/".github/workflows/build-desktop.yml").read_text(encoding="utf-8")
  self.assertIn("workflow_dispatch:",pipeline)
  self.assertNotIn("  push:",pipeline)

if __name__=="__main__":unittest.main()
