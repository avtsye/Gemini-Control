import pathlib,sys,tempfile,unittest,subprocess,shutil
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from git_tools import git_engine,git_status,git_diff,git_commit

@unittest.skipUnless(shutil.which("git"),"Git not installed")
class GitToolsTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  self.root=pathlib.Path(self.tmp.name)
  self.repo=self.root/"Demo"
  self.repo.mkdir()
  subprocess.run(["git","init","-q",str(self.repo)],check=True)
  for key,value in [("user.name","Test Developer"),("user.email","test@example.org")]:
   subprocess.run(["git","-C",str(self.repo),"config",key,value],check=True)
  (self.repo/"example.txt").write_text("hello")
 def tearDown(self):self.tmp.cleanup()
 def test_status_approval_and_commit(self):
  self.assertEqual(git_status(self.root,"Demo",lambda _:False),{"cancelled":True})
  self.assertIn("example.txt",git_status(self.root,"Demo",lambda _:True)["stdout"])
  self.assertEqual(git_commit(self.root,"Demo",["example.txt"],"First test",lambda _:False),{"cancelled":True})
  result=git_commit(self.root,"Demo",["example.txt"],"First test",lambda _:True)
  self.assertTrue(result["ok"],result)
  (self.repo/"example.txt").write_text("new contents")
  self.assertIn("example.txt",git_diff(self.root,"Demo",lambda _:True)["stdout"])
 def test_path_restriction(self):
  with self.assertRaises(ValueError):git_status(self.root,"../outside",lambda _:True)
  with self.assertRaises(ValueError):git_commit(self.root,"Demo",["../x"],"Test",lambda _:True)
if __name__=="__main__":unittest.main()
