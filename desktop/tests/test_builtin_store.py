import pathlib,sys,tempfile,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from capability_workshop import CapabilityWorkshop
from capability_store import list_builtins,install_builtin

class BuiltinStoreTests(unittest.TestCase):
 def test_catalog_integrity(self):
  catalog=list_builtins()
  self.assertEqual(len(catalog),6)
  self.assertEqual(len({x["id"] for x in catalog}),6)
 def test_install_each_as_disabled_reviewable_draft(self):
  with tempfile.TemporaryDirectory() as temp:
   workshop=CapabilityWorkshop(pathlib.Path(temp)/"capabilities")
   for builtin in list_builtins():
    identifier=install_builtin(workshop,builtin["id"])
    meta=workshop._manifest(workshop._path(identifier))
    self.assertEqual(meta["status"],"draft")
    self.assertTrue(meta["require_test"])
    self.assertTrue(workshop.inspect(identifier)["syntax_ok"])
 def test_html_plugin_creates_real_file(self):
  with tempfile.TemporaryDirectory() as temp:
   workshop=CapabilityWorkshop(pathlib.Path(temp)/"cap")
   ident=install_builtin(workshop,"html")
   result=workshop.test_capability(ident,{"title":"בדיקה","paragraphs":["שלום"]},lambda _:True)
   self.assertTrue(result["passed"],result)
   output=workshop._path(ident)/"test_outputs"/"report.html"
   self.assertTrue(output.is_file())
   self.assertIn("שלום",output.read_text(encoding="utf-8"))
if __name__=="__main__":unittest.main()
