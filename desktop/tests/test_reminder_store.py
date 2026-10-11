import pathlib,sys,tempfile,unittest,time
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from reminder_store import ReminderStore

class ReminderTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  self.store=ReminderStore(pathlib.Path(self.tmp.name)/"reminders.sqlite3")
 def tearDown(self):self.tmp.cleanup()
 def test_one_time_due(self):
  created=self.store.add("Finish homework",1)
  self.assertEqual(len(self.store.list()),1)
  self.assertEqual(self.store.due(now=created["due"]+1)[0]["title"],"Finish homework")
  self.assertEqual(self.store.list(),[])
 def test_recurring_due(self):
  created=self.store.add("Break",1,repeat_minutes=5)
  self.assertEqual(len(self.store.due(now=created["due"]+10)),1)
  self.assertEqual(len(self.store.list()),1)
  self.assertGreater(self.store.list()[0]["due"],created["due"]+10)
 def test_cancel(self):
  created=self.store.add("Review",1)
  self.assertTrue(self.store.cancel(created["id"]))
  self.assertEqual(self.store.list(),[])
 def test_invalid_inputs(self):
  with self.assertRaises(ValueError):self.store.add("Title",0)
  with self.assertRaises(ValueError):self.store.add("Title",5,repeat_minutes=1)
  with self.assertRaises(ValueError):self.store.cancel("../incorrect")
if __name__=="__main__":unittest.main()
