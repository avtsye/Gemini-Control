import sys,pathlib,unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import windows_state
from agent_core import DesktopAgent

class NativeStateTests(unittest.TestCase):
 def test_handle_rejects_strings_zero(self):
  for value in ("123",0,-4,None,True):
   with self.assertRaises(ValueError):windows_state._handle(value)
 def test_snapshot_denied_before_inspection(self):
  agent=DesktopAgent("",approval=lambda _:False)
  with patch("windows_state.windows_snapshot") as inspect:
   self.assertEqual(agent.execute("windows_snapshot",{}),{"cancelled":True})
   inspect.assert_not_called()
 def test_window_denied_before_inspection(self):
  agent=DesktopAgent("",approval=lambda _:False)
  with patch("windows_state.inspect_window") as inspect:
   self.assertEqual(agent.execute("inspect_window",{"handle":55}),{"cancelled":True})
   inspect.assert_not_called()
 def test_native_discovery_authorized(self):
  agent=DesktopAgent("",approval=lambda _:True)
  with patch("windows_state.windows_snapshot",return_value=[{"handle":2,"title":"Test"}]):
   self.assertEqual(agent.execute("windows_snapshot",{})["windows"][0]["handle"],2)
 def test_native_action_denied(self):
  agent=DesktopAgent("",approval=lambda _:False)
  with patch("windows_state.activate_control",return_value={"cancelled":True}) as invoke:
   result=agent.execute("activate_control",{"handle":2,"automation_id":"ok","expected_name":"OK"})
   self.assertTrue(result["cancelled"])
   invoke.assert_called_once()
if __name__=="__main__":unittest.main()
