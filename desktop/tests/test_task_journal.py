import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from task_journal import TaskJournal
from openai_agent import OpenAIComputerAgent

class Stub:
    def __init__(self, responses):
        self.responses = iter(responses)
    def response(self, prompt, model):
        return next(self.responses)

class TaskJournalTests(unittest.TestCase):
    def test_journal_lifecycle(self):
        with tempfile.TemporaryDirectory() as root:
            journal = TaskJournal(root)
            identifier = journal.start("Test")
            journal.event(identifier, "step", "Working")
            journal.finish(identifier, "completed")
            task = journal.read(identifier)
            self.assertEqual(task["status"], "completed")
            self.assertEqual(task["events"][0]["kind"], "step")
            self.assertEqual(journal.recent()[0]["id"], identifier)

    def test_agent_success(self):
        with tempfile.TemporaryDirectory() as root:
            journal = TaskJournal(root)
            response = json.dumps({"message":"ok","tool":"none","arguments":{}})
            agent = OpenAIComputerAgent(Stub([response]), lambda _:False, journal=journal)
            output = []
            agent.run("hello", "demo", output.append)
            self.assertEqual(journal.recent()[0]["status"], "completed")

    def test_agent_consecutive_errors(self):
        with tempfile.TemporaryDirectory() as root:
            journal = TaskJournal(root)
            plan = json.dumps({"message":"attempt","tool":"read_file","arguments":{"name":"missing.txt"}})
            agent = OpenAIComputerAgent(Stub([plan,plan]), lambda _:True, journal=journal)
            agent.local.workspace = pathlib.Path(root)
            output = []
            agent.run("read", "demo", output.append)
            self.assertEqual(journal.recent()[0]["status"], "failed")
            self.assertTrue(any("שתי שגיאות" in x for x in output))

    def test_task_cancelled(self):
        with tempfile.TemporaryDirectory() as root:
            journal = TaskJournal(root)
            plan = json.dumps({"message":"write","tool":"write_file","arguments":{"name":"x.txt","content":"abc"}})
            agent = OpenAIComputerAgent(Stub([plan]), lambda _:False, journal=journal)
            agent.local.workspace = pathlib.Path(root)
            agent.run("write", "demo", lambda _:None)
            self.assertEqual(journal.recent()[0]["status"], "cancelled")

if __name__ == "__main__":
    unittest.main()
