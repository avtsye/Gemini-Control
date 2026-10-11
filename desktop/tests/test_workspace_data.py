import json,pathlib,sys,tempfile,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from workspace_data import search_workspace,convert_data

class WorkspaceDataTests(unittest.TestCase):
 def test_search_and_convert(self):
  with tempfile.TemporaryDirectory() as folder:
   root=pathlib.Path(folder)
   (root/"data.csv").write_text("name,score\nשלום,4\n",encoding="utf-8")
   result=search_workspace(root,"שלום",lambda _:True)
   self.assertEqual(len(result["matches"]),1)
   convert_data(root,"data.csv","data.json",lambda _:True)
   self.assertEqual(json.loads((root/"data.json").read_text())[0]["score"],"4")
   convert_data(root,"data.json","copy.csv",lambda _:True)
   self.assertIn("שלום",(root/"copy.csv").read_text(encoding="utf-8-sig"))
 def test_refuse_overwrite_and_escape(self):
  with tempfile.TemporaryDirectory() as folder:
   root=pathlib.Path(folder)
   (root/"data.json").write_text("[]")
   with self.assertRaises(FileExistsError):
    convert_data(root,"data.json","data.json",lambda _:True)
   with self.assertRaises(ValueError):
    convert_data(root,"../outside.csv","file.json",lambda _:True)
 def test_consent(self):
  with tempfile.TemporaryDirectory() as folder:
   self.assertEqual(search_workspace(folder,"abc",lambda _:False),{"cancelled":True})
if __name__=="__main__":unittest.main()
