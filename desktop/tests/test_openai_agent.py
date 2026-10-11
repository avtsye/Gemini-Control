import json, pathlib, sys, tempfile, unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from openai_agent import OpenAIComputerAgent

class Stub:
    def __init__(self,responses): self.responses=iter(responses)
    def response(self,prompt,model):return next(self.responses)

class AgentLoopTests(unittest.TestCase):
    def test_no_action(self):
        engine=OpenAIComputerAgent(Stub([json.dumps({"message":"שלום","tool":"none","arguments":{}})]),lambda _:False)
        out=[]
        engine.run("שלום","demo",out.append)
        self.assertEqual(out,["שלום"])
    def test_invalid_tool_not_executed(self):
        engine=OpenAIComputerAgent(Stub([json.dumps({"message":"x","tool":"shell","arguments":{"command":"noop"}})]),lambda _:True)
        out=[]
        engine.run("noop","demo",out.append)
        self.assertTrue(any("אינה נתמכת" in x for x in out))
    def test_disabled(self):
        engine=OpenAIComputerAgent(Stub([]),lambda _:True)
        engine.enabled=False
        out=[]
        engine.run("hello","demo",out.append)
        self.assertIn("הופסקו",out[0])
    def test_file_write_denied(self):
        engine=OpenAIComputerAgent(Stub([json.dumps({"message":"שומר קובץ","tool":"write_file","arguments":{"name":"hi.txt","content":"123"}})]),lambda _:False)
        with tempfile.TemporaryDirectory() as folder:
            engine.local.workspace=pathlib.Path(folder)
            out=[]
            engine.run("write","demo",out.append)
            self.assertFalse((pathlib.Path(folder)/"hi.txt").exists())
            self.assertTrue(any("בוטלה" in x for x in out))
if __name__=="__main__":unittest.main()
