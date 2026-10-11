import pathlib,sys,tempfile,unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from file_organizer import move_workspace_file,sevenzip_status

class FileOrganizerTests(unittest.TestCase):
 def test_move_and_consent(self):
  with tempfile.TemporaryDirectory() as folder:
   root=pathlib.Path(folder)
   (root/"old.txt").write_text("hello")
   self.assertEqual(move_workspace_file(root,"old.txt","sub/new.txt",lambda _:False),{"cancelled":True})
   result=move_workspace_file(root,"old.txt","sub/new.txt",lambda _:True)
   self.assertEqual(result["moved_to"],"sub/new.txt")
   self.assertEqual((root/"sub/new.txt").read_text(),"hello")
 def test_no_traversal(self):
  with tempfile.TemporaryDirectory() as folder:
   root=pathlib.Path(folder)
   (root/"file.txt").write_text("x")
   with self.assertRaises(ValueError):move_workspace_file(root,"file.txt","../elsewhere.txt",lambda _:True)
 def test_optional_status(self):
  with patch("file_organizer.shutil.which",return_value=None):
   self.assertFalse(sevenzip_status()["available"])
if __name__=="__main__":unittest.main()
