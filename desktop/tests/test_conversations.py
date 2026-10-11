import pathlib,sys,tempfile,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from conversation_store import ConversationStore
class HistoryTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  self.store=ConversationStore(pathlib.Path(self.tmp.name)/"test.db")
 def tearDown(self):self.tmp.cleanup()
 def test_persists_messages_across_reopen(self):
  chat=self.store.create()
  self.store.add(chat,"user","שלום")
  self.store.add(chat,"assistant","שלום וברכה")
  again=ConversationStore(pathlib.Path(self.tmp.name)/"test.db")
  self.assertEqual(again.messages(chat),[("user","שלום"),("assistant","שלום וברכה")])
  self.assertEqual(again.chats()[0][0],chat)
 def test_delete_removes_messages_and_proposals(self):
  chat=self.store.create()
  self.store.add(chat,"user","first")
  proposal=self.store.propose(chat,"capability","build a local adapter after review")
  self.store.delete(chat)
  self.assertEqual(self.store.messages(chat),[])
  self.assertEqual(self.store.proposals(),[])
 def test_proposal_does_not_execute_code(self):
  chat=self.store.create()
  identifier=self.store.propose(chat,"missing tool","import os; print('NEVER EXECUTE')")
  self.assertEqual(self.store.proposals()[0][3],"pending")
  self.store.review(identifier,"approved")
  self.assertEqual(self.store.proposals()[0][3],"approved")
 def test_invalid_roles(self):
  chat=self.store.create()
  with self.assertRaises(ValueError):self.store.add(chat,"root","not allowed")
if __name__=="__main__":unittest.main()
