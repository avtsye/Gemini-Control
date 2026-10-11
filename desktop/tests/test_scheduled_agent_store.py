import pathlib,sys,tempfile,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from scheduled_agent_store import ScheduledAgentStore

class ScheduledAgentTests(unittest.TestCase):
 def test_one_time_task_only_runs_once(self):
  with tempfile.TemporaryDirectory() as folder:
   store=ScheduledAgentStore(pathlib.Path(folder)/"tasks.sqlite3")
   item=store.add("Inspect project","test-model",1)
   self.assertEqual(len(store.list()),1)
   tasks=store.due(now=10**12)
   self.assertEqual(tasks[0]["id"],item["id"])
   self.assertEqual(store.due(now=10**12),[])
 def test_repeating_task_advances_and_can_cancel(self):
  with tempfile.TemporaryDirectory() as folder:
   store=ScheduledAgentStore(pathlib.Path(folder)/"tasks.sqlite3")
   item=store.add("Check status","model",1,15)
   self.assertEqual(store.due(now=10**12)[0]["id"],item["id"])
   self.assertEqual(store.due(now=10**12),[])
   self.assertTrue(store.cancel(item["id"]))
   self.assertEqual(store.list(),[])
 def test_limits(self):
  with tempfile.TemporaryDirectory() as folder:
   store=ScheduledAgentStore(pathlib.Path(folder)/"tasks.sqlite3")
   with self.assertRaises(ValueError):store.add("x","model",1)
   with self.assertRaises(ValueError):store.add("Task","model",1,2)
if __name__=="__main__":unittest.main()
