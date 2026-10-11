import pathlib,sys,unittest
from unittest.mock import patch,MagicMock
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from research_discovery import discover_research_sources

class DiscoveryTests(unittest.TestCase):
 def test_approval_needed(self):
  result=discover_research_sources("local development",lambda _:False)
  self.assertEqual(result,{"cancelled":True})
 def test_two_named_sources(self):
  wiki=MagicMock()
  wiki.json.return_value={"query":{"search":[{"title":"Project A"}]}}
  crossref=MagicMock()
  crossref.json.return_value={"message":{"items":[{"DOI":"10.1234/article.1","title":["Paper B"]}]}}
  with patch("requests.Session") as factory:
   factory.return_value.get.side_effect=[wiki,crossref]
   result=discover_research_sources("local development",lambda _:True)
  self.assertEqual(len(result["sources"]),2)
  self.assertEqual(result["sources"][0]["source"],"Wikipedia")
  self.assertEqual(result["sources"][1]["url"],"https://doi.org/10.1234/article.1")
 def test_limit(self):
  with self.assertRaises(ValueError):
   discover_research_sources("testing",lambda _:True,limit=100)
if __name__=="__main__":unittest.main()
