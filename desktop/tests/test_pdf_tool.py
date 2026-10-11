import pathlib,sys,tempfile,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from pdf_tool import create_pdf
from agent_core import DesktopAgent
from extensions import ExtensionManager

class PdfCreationTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory()
 def tearDown(self):
  self.temp.cleanup()
 def test_invalid_filenames(self):
  for name in ("../outside.pdf","folder/file.pdf","notes.txt",".hidden.pdf","C:\\evil.pdf"):
   with self.subTest(name=name),self.assertRaises(ValueError):
    create_pdf(name,"שלום",self.temp.name,lambda _:True)
 def test_cancel_does_not_write(self):
  result=create_pdf("test.pdf","שלום",self.temp.name,lambda _:False)
  self.assertEqual(result,{"cancelled":True})
  self.assertFalse((pathlib.Path(self.temp.name)/"test.pdf").exists())
 def test_extension_manifest_accepts_pdf(self):
  with tempfile.TemporaryDirectory() as plugins:
   manager=ExtensionManager(plugins)
   identifier=manager.install({"name":"יצירת PDF","steps":[
    {"tool":"create_pdf","arguments":{"name":"example.pdf","content":"שלום עולם","direction":"rtl"}}]})
   self.assertEqual(manager.list()[0]["status"],"disabled")
   self.assertTrue(identifier)
 def test_pdf_creates_valid_file_with_hebrew(self):
  result=create_pdf("hebrew.pdf","שלום עולם\nשורה שנייה",self.temp.name,lambda _:True)
  path=pathlib.Path(result["created_pdf"])
  self.assertEqual(path.read_bytes()[:5],b"%PDF-")
  self.assertGreater(path.stat().st_size,100)
  self.assertEqual(result["direction"],"rtl")
 def test_overwrite_approval_and_backup(self):
  path=pathlib.Path(self.temp.name)/"existing.pdf"
  path.write_bytes(b"old PDF")
  descriptions=[]
  result=create_pdf("existing.pdf","טקסט חדש",self.temp.name,
                    lambda d:(descriptions.append(d) or False))
  self.assertTrue(result["cancelled"])
  self.assertEqual(path.read_bytes(),b"old PDF")
  result=create_pdf("existing.pdf","טקסט חדש",self.temp.name,lambda _:True)
  self.assertEqual(path.read_bytes()[:5],b"%PDF-")
  self.assertEqual(len(list((pathlib.Path(self.temp.name)/".backups").iterdir())),1)
 def test_agent_routes_tool(self):
  agent=DesktopAgent("",workspace=self.temp.name,approval=lambda _:False)
  result=agent.execute("create_pdf",{"name":"agent.pdf","content":"שלום"})
  self.assertEqual(result,{"cancelled":True})
if __name__=="__main__":unittest.main()
