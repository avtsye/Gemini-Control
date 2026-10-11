import pathlib,sys,tempfile,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from knowledge_tools import index_workspace,search_knowledge

class KnowledgeTests(unittest.TestCase):
 def test_hebrew_search_and_approval(self):
  with tempfile.TemporaryDirectory() as temp:
   root=pathlib.Path(temp)
   (root/"notes.md").write_text("בדיקת יכולות של מנוע החיפוש המקומי",encoding="utf-8")
   self.assertEqual(index_workspace(root,lambda _:False),{"cancelled":True})
   self.assertEqual(index_workspace(root,lambda _:True)["indexed_files"],1)
   result=search_knowledge(root,"מנוע החיפוש",lambda _:True)
   self.assertEqual(result["results"][0]["path"],"notes.md")
   self.assertEqual(search_knowledge(root,"חיפוש",lambda _:False),{"cancelled":True})
 def test_limit_to_text_files(self):
  with tempfile.TemporaryDirectory() as temp:
   root=pathlib.Path(temp)
   (root/"data.bin").write_bytes(b"no")
   (root/"notes.txt").write_text("hello")
   self.assertEqual(index_workspace(root,lambda _:True)["indexed_files"],1)
   self.assertEqual(search_knowledge(root,"notfound",lambda _:True)["results"],[])
if __name__=="__main__":unittest.main()
