import pathlib,sys,tempfile,unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from drawing_tool import safe_svg,draw_in_paint
from agent_core import DesktopAgent

EXAMPLE='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 700"><circle cx="300" cy="300" r="120" fill="#c76532"/><path d="M100 500 L300 250 L500 500" fill="none" stroke="black"/></svg>'

class DrawingTests(unittest.TestCase):
    def test_svg_valid(self):
        self.assertEqual(safe_svg(EXAMPLE),EXAMPLE)
    def test_svg_reject_external_and_script(self):
        for malicious in [
            '<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
            '<svg xmlns="http://www.w3.org/2000/svg"><image href="file:///secret"/></svg>',
            '<!DOCTYPE svg [<!ENTITY x SYSTEM "file:///secret">]><svg>&x;</svg>',
            '<svg xmlns="http://www.w3.org/2000/svg"><path fill="url(http://evil.example)"/></svg>'
        ]:
            with self.subTest(payload=malicious[:30]),self.assertRaises(ValueError):
                safe_svg(malicious)
    def test_denied_does_not_write_or_launch(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch("drawing_tool.subprocess.Popen") as launch:
                result=draw_in_paint(EXAMPLE,folder,lambda _:False)
                self.assertEqual(result,{"cancelled":True})
                self.assertEqual(list(pathlib.Path(folder).iterdir()),[])
                launch.assert_not_called()
    def test_draws_png_and_opens_paint(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch("drawing_tool.subprocess.Popen") as launch:
                result=draw_in_paint(EXAMPLE,folder,lambda _:True)
                path=pathlib.Path(result["created_png"])
                self.assertEqual(path.read_bytes()[:8],b"\\x89PNG\\r\\n\\x1a\\n")
                self.assertEqual(result["opened_in"],"paint")
                launch.assert_called_once()
                self.assertEqual(launch.call_args.args[0][0],"mspaint.exe")
    def test_agent_dispatch(self):
        with tempfile.TemporaryDirectory() as folder:
            agent=DesktopAgent("",workspace=folder,approval=lambda _:False)
            self.assertTrue(agent.execute("draw_paint",{"svg":EXAMPLE})["cancelled"])

if __name__=="__main__":unittest.main()
