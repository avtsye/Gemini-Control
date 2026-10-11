import pathlib,sys,tempfile,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from knowledge_search import search_knowledge
class KnowledgeTests(unittest.TestCase):
 def test_rank_and_hebrew(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d)
   folder=root/"Notes"
   folder.mkdir()
   (folder/"a.md").write_text("תוכנת מחשב פרויקט ממשק קוד",encoding="utf-8")
   (folder/"b.txt").write_text("מסמך טכני בנושא בסיס נתונים",encoding="utf-8")
   result=search_knowledge(root,"מחשב ממשק","Notes",lambda _:True)
   self.assertEqual(result["searched_files"],2)
   self.assertEqual(result["results"][0]["file"],"Notes/a.md")
 def test_consent_and_traversal(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d); (root/"Notes").mkdir()
   self.assertEqual(search_knowledge(root,"search","Notes",lambda _:False),{"cancelled":True})
   with self.assertRaises(ValueError):search_knowledge(root,"search","../",lambda _:True)
if __name__=="__main__":unittest.main()
