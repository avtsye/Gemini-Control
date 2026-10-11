import json,pathlib,sys,tempfile,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from openai_agent import OpenAIComputerAgent

class Stub:
 def __init__(self,responses):self.responses=iter(responses)
 def response(self,prompt,model):return next(self.responses)

class Workshop:
 def __init__(self):self.calls=[]
 def list(self):return [{"id":"11111111-1111-4111-8111-111111111111","name":"Echo","description":"Echo payload","status":"enabled"}]
 def run(self,identifier,payload,approve):
  self.calls.append((identifier,payload))
  if not approve("Run?"):return {"cancelled":True}
  return {"result":payload}

class DynamicToolsTests(unittest.TestCase):
 def test_enabled_capability_callable(self):
  ident="11111111-1111-4111-8111-111111111111"
  workshop=Workshop()
  responses=[{"message":"Run echo","tool":"run_capability","arguments":{"id":ident,"payload":{"text":"hi"}}},{"message":"Done","tool":"none","arguments":{}}]
  engine=OpenAIComputerAgent(Stub([json.dumps(x) for x in responses]),lambda _:True,workshop=workshop)
  with tempfile.TemporaryDirectory() as root:
   from task_journal import TaskJournal
   engine.journal=TaskJournal(root)
   out=[]
   engine.run("Echo","demo",out.append)
   self.assertEqual(workshop.calls[0][1],{"text":"hi"})
 def test_unknown_capability_never_runs(self):
  workshop=Workshop()
  response={"message":"No","tool":"run_capability","arguments":{"id":"unknown","payload":{}}}
  engine=OpenAIComputerAgent(Stub([json.dumps(response),json.dumps({"message":"Done","tool":"none","arguments":{}})]),lambda _:True,workshop=workshop)
  with tempfile.TemporaryDirectory() as root:
   from task_journal import TaskJournal
   engine.journal=TaskJournal(root)
   engine.run("Unknown","demo",lambda _:None)
   self.assertEqual(workshop.calls,[])
 def test_without_workshop_not_available(self):
  engine=OpenAIComputerAgent(Stub([json.dumps({"message":"No","tool":"run_capability","arguments":{}})]),lambda _:True)
  with tempfile.TemporaryDirectory() as root:
   from task_journal import TaskJournal
   engine.journal=TaskJournal(root)
   out=[]
   engine.run("Run","demo",out.append)
   self.assertTrue(any("אינה נתמכת" in x for x in out))

if __name__=="__main__":unittest.main()
