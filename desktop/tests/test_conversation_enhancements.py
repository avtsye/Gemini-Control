import pathlib,sys,tempfile,unittest,json
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from conversation_store import ConversationStore

class ConversationEnhancementsTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  self.db=ConversationStore(pathlib.Path(self.tmp.name)/"test.db")
 def tearDown(self):self.tmp.cleanup()
 def test_search_and_projects(self):
  first=self.db.create("Project conversation")
  self.db.add(first,"user","Searchable unique content 2026")
  self.db.set_flags(first,pinned=True,project="Gemini-Control")
  self.assertEqual(self.db.search("unique")[0][0],first)
  d=self.db.chats_detailed()[0]
  self.assertEqual(d[0],first)
  self.assertEqual(d[2],1)
  self.assertEqual(d[4],"Gemini-Control")
  self.db.set_flags(first,archived=True)
  self.assertEqual(self.db.chats_detailed()[0][3],1)
 def test_edit_truncates_following_messages(self):
  chat=self.db.create()
  self.db.add(chat,"user","original")
  self.db.add(chat,"assistant","original answer")
  self.db.add(chat,"user","later")
  self.db.edit_user_message(chat,0,"changed")
  self.assertEqual(self.db.messages(chat),[("user","changed")])
  with self.assertRaises(ValueError):self.db.edit_user_message(chat,99,"x")
 def test_backup_roundtrip_and_id_remapping(self):
  first=self.db.create("Export")
  self.db.add(first,"user","export text")
  self.db.set_flags(first,pinned=True,project="Project A")
  backup=self.db.export_history()
  with tempfile.TemporaryDirectory() as other:
   target=ConversationStore(pathlib.Path(other)/"import.sqlite3")
   result=target.restore_history(backup)
   self.assertEqual(result["restored_chats"],1)
   restored=target.chats_detailed()[0]
   self.assertNotEqual(restored[0],first)
   self.assertEqual(restored[4],"Project A")
   self.assertEqual(target.messages(restored[0]),[("user","export text")])
 def test_reject_invalid_restore(self):
  with self.assertRaises(ValueError):self.db.restore_history({"version":1,"conversations":[],"messages":[["missing","assistant","x","now"]]})
 def test_backup_and_delete(self):
  chat=self.db.create()
  self.db.add(chat,"user","hello")
  self.db.set_flags(chat,pinned=True,project="My Project")
  data=self.db.export_history()
  self.assertTrue(any(x[0]==chat for x in data["conversations"]))
  self.assertTrue(any(x[0]==chat for x in data["flags"]))
  self.db.delete(chat)
  self.assertFalse(self.db.chats_detailed())
  self.assertTrue(json.dumps(data,ensure_ascii=False))
if __name__=="__main__":unittest.main()
