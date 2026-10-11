import pathlib,sys,tempfile,unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from agent_core import DesktopAgent
from computer_tools import computer_action

class GenericComputerTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
 def tearDown(self):self.tmp.cleanup()
 def test_inventory_requires_approval(self):
  agent=DesktopAgent("",workspace=self.tmp.name,approval=lambda _:False)
  with patch("computer_inventory.installed_applications") as discover:
   self.assertEqual(agent.execute("installed_apps",{}),{"cancelled":True})
   discover.assert_not_called()
 def test_workspace_lists_all_extensions(self):
  (pathlib.Path(self.tmp.name)/"sample.abc").write_bytes(b"123")
  got=computer_action("workspace_files",{},self.tmp.name,lambda _:True)
  self.assertEqual(got["workspace_items"][0]["path"],"sample.abc")
 def test_binary_file_metadata(self):
  (pathlib.Path(self.tmp.name)/"sample.abc").write_bytes(b"123")
  got=computer_action("inspect_workspace_file",{"path":"sample.abc"},self.tmp.name,lambda _:True)
  self.assertEqual(got["size"],3)
  self.assertIn("not implemented",got["note"])
 def test_escape_blocked(self):
  with self.assertRaises(ValueError):
   computer_action("inspect_workspace_file",{"path":"../secret.txt"},self.tmp.name,lambda _:True)
 def test_executable_not_opened(self):
  (pathlib.Path(self.tmp.name)/"malware.exe").write_bytes(b"123")
  with self.assertRaises(ValueError):
   computer_action("open_workspace_file",{"path":"malware.exe"},self.tmp.name,lambda _:True)
 def test_python_script_cannot_be_launched_as_document(self):
  (pathlib.Path(self.tmp.name)/"script.py").write_text("print(42)")
  with self.assertRaises(ValueError):
   computer_action("open_workspace_file",{"path":"script.py"},self.tmp.name,lambda _:True)
 def test_screen_observation_denied(self):
  class Stub:
   def response(self,*a):return '{"message":"Observe","tool":"observe_screen","arguments":{}}'
   def describe_image(self,*a):raise AssertionError("Must not send screen")
  from openai_agent import OpenAIComputerAgent
  agent=OpenAIComputerAgent(Stub(),lambda _:False)
  events=[]
  agent.run("inspect display","mock",events.append)
  self.assertTrue(any("בוטלה" in x for x in events))
if __name__=="__main__":unittest.main()
