import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from agent_core import DesktopAgent

class AgentTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  self.agent=DesktopAgent("testkey", workspace=self.tmp.name, approval=lambda _: True)
 def tearDown(self):
  self.tmp.cleanup()
 def test_write_read_backup(self):
  self.agent.execute("write_file",{"name":"notes.txt","content":"one"})
  self.agent.execute("write_file",{"name":"notes.txt","content":"two"})
  self.assertEqual(self.agent.execute("read_file",{"name":"notes.txt"})["content"],"two")
  self.assertEqual(len(list((Path(self.tmp.name)/".backups").iterdir())),1)
 def test_reject_escape(self):
  for name in ["../outside.txt","../../x.py","foo.exe",".env","dir/file.txt"]:
   with self.subTest(name=name):
    with self.assertRaises(ValueError):
     self.agent.execute("write_file",{"name":name,"content":"no"})
 def test_paused(self):
  self.agent.enabled=False
  with self.assertRaises(PermissionError):
   self.agent.execute("list_files",{})
 def test_reject_unapproved(self):
  self.agent.approval=lambda _:False
  self.assertTrue(self.agent.execute("write_file",{"name":"a.txt","content":"no"})["cancelled"])
  self.assertFalse((Path(self.tmp.name)/"a.txt").exists())
 def test_reject_tool(self):
  with self.assertRaises(ValueError):
   self.agent.execute("run_shell",{"command":"echo hi"})
 def test_no_file_leak_on_cancel(self):
  (Path(self.tmp.name)/"s.txt").write_text("private")
  self.agent.approval=lambda _:False
  self.assertEqual(self.agent.execute("read_file",{"name":"s.txt"}),{"cancelled":True})
if __name__=="__main__":unittest.main()
