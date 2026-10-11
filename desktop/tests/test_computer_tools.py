import pathlib,sys,tempfile,unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from computer_tools import computer_action
class ToolsTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
 def tearDown(self):self.tmp.cleanup()
 def action(self,name,args,allowed=False):
  return computer_action(name,args,self.tmp.name,lambda _:allowed)
 def test_denied_screenshot_never_reads_screen(self):
  with patch.dict(sys.modules,{"pyautogui":None}):
   self.assertEqual(self.action("screenshot",{}),{"cancelled":True})
 def test_denied_mouse_never_acts(self):
  self.assertEqual(self.action("click",{"x":20,"y":50}),{"cancelled":True})
 def test_coordinates_rejected(self):
  for args in ({"x":-1,"y":5},{"x":"20","y":5},{"x":0,"y":20000}):
   with self.assertRaises(ValueError):self.action("click",args,True)
 def test_keyboard_shortcuts_restricted(self):
  with self.assertRaises(ValueError):self.action("hotkey",{"keys":["win","r"]},True)
 def test_email_creates_only_draft(self):
  with patch("computer_tools.webbrowser.open") as open_browser:
   result=self.action("email_draft",{"to":"avtsye@gmail.com","subject":"בדיקה","body":"שלום"},True)
   self.assertEqual(result["sent"],False)
   self.assertEqual(result["attachment_added"],False)
   self.assertTrue(open_browser.call_args.args[0].startswith("mailto:avtsye@gmail.com"))
 def test_email_denial(self):
  with patch("computer_tools.webbrowser.open") as open_browser:
   self.assertEqual(self.action("email_draft",{"to":"avtsye@gmail.com"}),{"cancelled":True})
   open_browser.assert_not_called()
 def test_create_word_denial(self):
  self.assertEqual(self.action("create_word",{"name":"report.docx","content":"Hi"}),{"cancelled":True})
  self.assertEqual(list(pathlib.Path(self.tmp.name).iterdir()),[])
 def test_browser_rejects_http(self):
  with self.assertRaises(ValueError):self.action("open_browser",{"url":"http://example.com"},True)
 def test_project_file_creates_nested_code(self):
  result=self.action("project_file",{"project":"AppOne","path":"src/main.py","content":"print('ok')"},True)
  self.assertTrue(pathlib.Path(result["saved_project_file"]).exists())
 def test_project_rejects_escape(self):
  for name in ("../private.py","src/../../secret.py","src/.hidden.py"):
   with self.assertRaises(ValueError):self.action("project_file",{"project":"AppOne","path":name,"content":"x"},True)
 def test_project_denied(self):
  result=self.action("project_file",{"project":"AppOne","path":"src/main.py","content":"x"})
  self.assertEqual(result,{"cancelled":True})
  self.assertFalse((pathlib.Path(self.tmp.name)/"Projects").exists())
if __name__=="__main__":unittest.main()
