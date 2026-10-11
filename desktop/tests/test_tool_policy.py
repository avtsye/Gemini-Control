import json,pathlib,sys,tempfile,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from tool_policy import ToolPolicy

class PolicyTests(unittest.TestCase):
 def test_persistent_deny_only(self):
  with tempfile.TemporaryDirectory() as temp:
   path=pathlib.Path(temp)/"policy.json"
   p=ToolPolicy(path)
   self.assertTrue(p.allowed("create_pdf"))
   p.set_allowed("create_pdf",False,{"create_pdf","run_capability"})
   self.assertFalse(ToolPolicy(path).allowed("create_pdf"))
   self.assertTrue(p.allowed("run_capability"))
   p.set_allowed("create_pdf",True,{"create_pdf"})
   self.assertTrue(ToolPolicy(path).allowed("create_pdf"))
 def test_cannot_register_unknown_tools(self):
  with tempfile.TemporaryDirectory() as temp:
   p=ToolPolicy(pathlib.Path(temp)/"settings.json")
   with self.assertRaises(ValueError):
    p.set_allowed("malicious_tool",True,{"create_pdf"})
if __name__=="__main__":unittest.main()
