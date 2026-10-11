"""Offline structural QA checks. Run: python desktop/tests/test_ui_contract.py -v"""
import ast,pathlib,re,unittest
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
  for element in set(re.findall(r"\$\('([a-zA-Z][\w-]*)'\)",self.html)):
   with self.subTest(id=element):self.assertIn(element,self.parser.ids)
 def test_webchannel_methods_exist(self):
  methods=set(re.findall(r"call\('([a-z_]+)'",self.html))
  decorators=set(re.findall(r"@Slot\([^\n]*?result=str\)\s+def ([a-z_]+)\(",self.shell))
  self.assertFalse(methods-decorators,"Undeclared Qt bridge methods: "+str(methods-decorators))
 def test_qt_bridge_signal_name(self):
  self.assertIn('registerObject("api",self.bridge)',self.shell)
  self.assertIn("bridge.event.connect(",self.html)
 def test_secure_html_messages(self):
  self.assertIn("document.createTextNode(text)",self.html)
  self.assertNotIn("innerHTML=",self.html)
 def test_source_python_syntax(self):
  for path in ROOT.glob("*.py"):
   with self.subTest(path=path.name):ast.parse(path.read_text(encoding="utf-8"),filename=str(path))
 def test_only_manual_ci(self):
  pipeline=(ROOT.parent/".github/workflows/build-desktop.yml").read_text(encoding="utf-8")
  self.assertIn("workflow_dispatch:",pipeline)
  self.assertNotIn("  push:",pipeline)

if __name__=="__main__":unittest.main()
