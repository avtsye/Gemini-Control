import tempfile, pathlib, unittest
from unittest.mock import Mock
import sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from extensions import ExtensionManager

class ExtensionTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory()
  self.manager=ExtensionManager(pathlib.Path(self.temp.name)/"extensions")
 def tearDown(self):self.temp.cleanup()
 def test_installed_disabled_by_default(self):
  identifier=self.manager.install({"name":"הצג חלונות","steps":[{"tool":"windows_snapshot","arguments":{}}]})
  self.assertEqual(self.manager.list()[0]["status"],"disabled")
  with self.assertRaises(PermissionError):self.manager.execute(identifier,Mock(),lambda _:None)
 def test_enable_then_run(self):
  identifier=self.manager.install({"name":"סטטוס","steps":[{"tool":"system_status","arguments":{}}]})
  self.manager.toggle(identifier,True)
  local=Mock();local.enabled=True;local.execute.return_value={"ok":True}
  result=self.manager.execute(identifier,local,lambda _:None)
  self.assertEqual(result[0]["tool"],"system_status")
  local.execute.assert_called_once_with("system_status",{})
 def test_rejects_arbitrary_commands(self):
  for tool in ("exec","shell","subprocess","python","email_draft","click","type_text"):
   with self.assertRaises(ValueError):
    self.manager.install({"name":"bad","steps":[{"tool":tool,"arguments":{}}]})
 def test_rejects_oversized_workflow(self):
  with self.assertRaises(ValueError):
   self.manager.install({"name":"long","steps":[{"tool":"system_status"}]*7})
 def test_per_tool_parameters_checked(self):
  for manifest in (
   {"name":"bad","steps":[{"tool":"windows_snapshot","arguments":{"url":"https://example.com"}}]},
   {"name":"bad","steps":[{"tool":"open_browser","arguments":{}}]},
   {"name":"bad","steps":[{"tool":"project_file","arguments":{"project":"Demo"}}]},
  ):
   with self.subTest(manifest=manifest),self.assertRaises(ValueError):
    self.manager.install(manifest)
 def test_cancel_breaks_chain(self):
  identifier=self.manager.install({"name":"check","steps":[{"tool":"system_status"},{"tool":"windows_snapshot"}]})
  self.manager.toggle(identifier,True)
  local=Mock();local.enabled=True;local.execute.return_value={"cancelled":True}
  result=self.manager.execute(identifier,local,lambda _:None)
  self.assertEqual(len(result),1)

if __name__=="__main__":unittest.main()
