"""End-to-end integration: create actual Python tool, smoke test, activate, agent call."""
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from capability_workshop import CapabilityWorkshop
from openai_agent import OpenAIComputerAgent
from task_journal import TaskJournal

class FakeModel:
    def __init__(self, identifier):
        self.identifier=identifier
        self.prompts=[]
    def response(self,prompt,model):
        self.prompts.append(prompt)
        if len(self.prompts)==1:
            return json.dumps({"message":"יצירת קובץ לדוגמה","tool":"run_capability",
              "arguments":{"id":self.identifier,"payload":{"title":"בדיקה"}}})
        return json.dumps({"message":"הפעולה הושלמה","tool":"none","arguments":{}})

class CapabilityIntegrationTests(unittest.TestCase):
    def test_real_python_tool_from_draft_to_chat(self):
        source='''from pathlib import Path
def run(payload, output_dir):
    file=Path(output_dir)/"sample.txt"
    file.write_text(payload.get("title","hello"),encoding="utf-8")
    return {"created":file.name}
'''
        with tempfile.TemporaryDirectory() as temp:
            root=pathlib.Path(temp)
            workshop=CapabilityWorkshop(root/"capabilities")
            identifier=workshop.draft("Text creator","Creates a real TXT file",source)
            folder=workshop._path(identifier)
            meta=workshop._manifest(folder)
            meta["require_test"]=True
            workshop._write_manifest(folder,meta)
            with self.assertRaises(PermissionError):
                workshop.activate(identifier,True)
            self.assertTrue(workshop.test_capability(identifier,{"title":"ניסיון"},lambda _:True)["passed"])
            workshop.activate(identifier,True)
            model=FakeModel(identifier)
            agent=OpenAIComputerAgent(model,lambda _:True,journal=TaskJournal(root/"tasks"),workshop=workshop)
            messages=[]
            agent.run("Create text file","demo",messages.append)
            output=folder/"outputs"/"sample.txt"
            self.assertTrue(output.is_file())
            self.assertEqual(output.read_text(encoding="utf-8"),"בדיקה")
            self.assertIn(identifier,model.prompts[0])
            self.assertEqual(agent.journal.recent()[0]["status"],"completed")

    def test_missing_import_analysis(self):
        with tempfile.TemporaryDirectory() as temp:
            workshop=CapabilityWorkshop(pathlib.Path(temp)/"caps")
            identifier=workshop.draft("Missing","",
                "import nonexistent_gemini_package_12345\ndef run(payload, output_dir): return {}")
            self.assertIn("nonexistent_gemini_package_12345",
                workshop.analyze_dependencies(identifier)["missing"])

if __name__=="__main__":
    unittest.main()
