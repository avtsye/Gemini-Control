import pathlib,sys,unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from internet_tools import fetch_page,_validate_url

class InternetTests(unittest.TestCase):
 def test_private_literal_rejected(self):
  for url in ("https://127.0.0.1/", "http://example.com/", "https://localhost/", "https://user:secret@example.com/"):
   with self.subTest(url=url),self.assertRaises(ValueError):
    _validate_url(url)
 def test_public_requests_require_permission(self):
  fake=[(None,None,None,None,("8.8.8.8",443))]
  with patch("internet_tools.socket.getaddrinfo",return_value=fake):
   self.assertEqual(fetch_page("https://example.com",lambda _:False),{"cancelled":True})

if __name__=="__main__":unittest.main()
