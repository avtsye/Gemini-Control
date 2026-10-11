import pathlib,sys,tempfile,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from data_analysis import analyze_csv,chart_csv

class CSVAnalysisTests(unittest.TestCase):
 def test_profile_and_chart(self):
  with tempfile.TemporaryDirectory() as folder:
   root=pathlib.Path(folder)
   (root/"data.csv").write_text("Month,Revenue\nJan,100\nFeb,200\n",encoding="utf-8")
   profile=analyze_csv(root,"data.csv",lambda _:True)
   self.assertEqual(profile["rows"],2)
   self.assertEqual(profile["columns"][1]["sum"],300)
   result=chart_csv(root,"data.csv","chart.svg","Month","Revenue",lambda _:True)
   self.assertEqual(result["bars"],2)
   self.assertIn("<svg", (root/"chart.svg").read_text(encoding="utf-8"))
 def test_cannot_write_without_approval(self):
  with tempfile.TemporaryDirectory() as folder:
   root=pathlib.Path(folder)
   (root/"data.csv").write_text("X,Y\na,5\n",encoding="utf-8")
   self.assertEqual(chart_csv(root,"data.csv","chart.svg","X","Y",lambda _:False),{"cancelled":True})
   self.assertFalse((root/"chart.svg").exists())
 def test_xml_is_escaped(self):
  with tempfile.TemporaryDirectory() as folder:
   root=pathlib.Path(folder)
   (root/"data.csv").write_text("Label,Value\n<b>hello</b>,2\n",encoding="utf-8")
   chart_csv(root,"data.csv","chart.svg","Label","Value",lambda _:True)
   self.assertIn("&lt;b&gt;hello&lt;/b&gt;",(root/"chart.svg").read_text(encoding="utf-8"))
if __name__=="__main__":unittest.main()
