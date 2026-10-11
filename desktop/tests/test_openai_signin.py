"""Offline unit tests for official SIWC helpers; no credentials/network needed."""
import sys, pathlib, unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from openai_signin import ChatGPTSignIn, SignInError

class FakeModels:
    def raise_for_status(self):pass
    def json(self):return {"models":[
      {"slug":"model-a","display_name":"A","visibility":"list"},
      {"slug":"hidden","visibility":"hidden"},
      {"slug":"model-b","display_name":"B","visibility":"list"}]}
class FakeStream:
    ok=True
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def iter_lines(self,decode_unicode=False):
        for s in [
          'data: {"type":"response.output_text.delta","delta":"שלום"}',
          'data: {"type":"response.output_text.delta","delta":" עולם"}',
          'data: {"type":"response.completed"}'
        ]:yield s
class BadStream(FakeStream):
    def iter_lines(self,decode_unicode=False):
        yield 'data: {"type":"response.output_text.delta","delta":"partial"}'

class SignInTests(unittest.TestCase):
    def test_model_filter(self):
        c=ChatGPTSignIn();c.access_token="mock"
        with patch("openai_signin.requests.get",return_value=FakeModels()):
            self.assertEqual(c.models(),[("model-a","A"),("model-b","B")])
    def test_response_stream_success(self):
        c=ChatGPTSignIn();c.access_token="mock"
        with patch("openai_signin.requests.post",return_value=FakeStream()) as post:
            self.assertEqual(c.response("hi","model-a"),"שלום עולם")
            payload=post.call_args.kwargs["json"]
            self.assertTrue(payload["stream"])
            self.assertFalse(payload["store"])
    def test_question_specific_image_analysis(self):
        c=ChatGPTSignIn();c.access_token="mock"
        with patch("openai_signin.requests.post",return_value=FakeStream()) as post:
            answer=c.describe_image(b"valid enough for fake backend","model-a","מה מופיע בתמונה?")
            self.assertEqual(answer,"שלום עולם")
            payload=post.call_args.kwargs["json"]
            content=payload["input"][0]["content"]
            self.assertIn("מה מופיע בתמונה?",content[0]["text"])
            self.assertEqual(content[1]["type"],"input_image")
            self.assertFalse(payload["store"])
    def test_no_completion_is_error(self):
        c=ChatGPTSignIn();c.access_token="mock"
        with patch("openai_signin.requests.post",return_value=BadStream()):
            with self.assertRaises(SignInError):c.response("hi","model-a")
    def test_requires_sign_in(self):
        with self.assertRaises(SignInError):ChatGPTSignIn().response("hi","model-a")

if __name__=="__main__":unittest.main()
