"""Prevent the model from advertising native tool names without a handler."""
import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from openai_agent import TOOLS
from agent_core import DesktopAgent

ROOT=pathlib.Path(__file__).resolve().parents[1]
class ToolRegistryTests(unittest.TestCase):
 def test_every_advertised_native_tool_has_a_handler(self):
  code=(ROOT/"agent_core.py").read_text(encoding="utf-8")
  agent=(ROOT/"openai_agent.py").read_text(encoding="utf-8")
  # Most tools route through DesktopAgent; the remainder have explicit agent handlers.
  dedicated={"none","list_available_tools","create_capability","run_capability",
             "observe_screen","propose_capability"}
  missing=[name for name in TOOLS if name not in dedicated and ('"'+name+'"') not in code]
  self.assertEqual(missing,[],"Agent advertised tool without desktop dispatch")
  for name in dedicated-{"run_capability"}:
   self.assertIn('"'+name+'"',agent)
 def test_no_duplicate_tool_names_in_static_definition(self):
  source=(ROOT/"openai_agent.py").read_text(encoding="utf-8")
  import re
  section=source.split("TOOLS={",1)[1].split("}",1)[0]
  names=re.findall(r'"([^"]+)"',section)
  self.assertEqual(len(names),len(set(names)),"Duplicate tool names in static catalog")
if __name__=="__main__":unittest.main()
