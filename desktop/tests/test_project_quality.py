import pathlib,sys,tempfile,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from project_quality import inspect_python_project,run_python_tests

class ProjectQualityTests(unittest.TestCase):
 def test_syntax_check(self):
  with tempfile.TemporaryDirectory() as folder:
   root=pathlib.Path(folder)
   project=root/"Projects"/"TestApp"
   project.mkdir(parents=True)
   (project/"main.py").write_text("def hello():\n return 42",encoding="utf-8")
   self.assertTrue(inspect_python_project(root,"Projects/TestApp",lambda _:True)["syntax_ok"])
   (project/"bad.py").write_text("def broken(",encoding="utf-8")
   self.assertFalse(inspect_python_project(root,"Projects/TestApp",lambda _:True)["syntax_ok"])
 def test_approved_unittest(self):
  with tempfile.TemporaryDirectory() as folder:
   root=pathlib.Path(folder)
   project=root/"Projects"/"TestApp"
   project.mkdir(parents=True)
   (project/"test_basic.py").write_text("import unittest\nclass T(unittest.TestCase):\n def test_ok(self):self.assertTrue(True)\n")
   self.assertEqual(run_python_tests(root,"Projects/TestApp",lambda _:False),{"cancelled":True})
   self.assertTrue(run_python_tests(root,"Projects/TestApp",lambda _:True)["passed"])
 def test_escape(self):
  with tempfile.TemporaryDirectory() as root:
   with self.assertRaises(ValueError):
    inspect_python_project(root,"../outside",lambda _:True)
if __name__=="__main__":unittest.main()
