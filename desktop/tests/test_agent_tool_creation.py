import json,pathlib,sys,tempfile,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from capability_workshop import CapabilityWorkshop
from openai_agent import OpenAIComputerAgent
from task_journal import TaskJournal

class Stub:
 def __init__(self, responses):self.responses=iter(responses)
 def response(self,prompt,model):return next(self.responses)

class AgentToolCreationTests(unittest.TestCase):
 def test_agent_writes_python_module_as_reviewable_draft(self):
  with tempfile.TemporaryDirectory() as root:
   workshop=CapabilityWorkshop(pathlib.Path(root)/"caps")
   code="def run(payload, output_dir):\n return {'hello':payload.get('text')}"
   step=json.dumps({"message":"Creating tool","tool":"create_capability",
     "arguments":{"name":"Hello","description":"Echo","source":code}})
   done=json.dumps({"message":"Created","tool":"none","arguments":{}})
   agent=OpenAIComputerAgent(Stub([step,done]),lambda _:True,
          workshop=workshop,journal=TaskJournal(pathlib.Path(root)/"tasks"))
   output=[]
   agent.run("Build a function","demo",output.append)
   created=workshop.list()
   self.assertEqual(len(created),1)
   self.assertEqual(created[0]["status"],"draft")
   self.assertTrue(created[0]["require_test"])
   self.assertTrue(any("created_draft" in msg for msg in output))
if __name__=="__main__":unittest.main()
