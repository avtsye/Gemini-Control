import pathlib,sys,unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from openai_signin import ChatGPTSignIn
class FakeResponse:
 def raise_for_status(self):pass
 def json(self):return {"access_token":"new-access","refresh_token":"new-refresh","expires_in":3600}

class CredentialTests(unittest.TestCase):
 @patch("openai_signin.keyring.get_password",return_value="saved-refresh")
 @patch("openai_signin.keyring.set_password")
 @patch("openai_signin.requests.post",return_value=FakeResponse())
 def test_refresh_saved_token(self,post,save,load):
  instance=ChatGPTSignIn()
  instance.registration={"client_id":"oaiapp_test","sub":"test-user"}
  self.assertTrue(instance.restore_session())
  self.assertEqual(instance.access_token,"new-access")
  self.assertEqual(instance.refresh_token,"new-refresh")
  save.assert_called_with("AIControlDesktop","refresh:test-user","new-refresh")
  self.assertEqual(post.call_args.kwargs["data"]["grant_type"],"refresh_token")
 @patch("openai_signin.keyring.get_password",return_value=None)
 def test_missing_token_requires_login(self,load):
  instance=ChatGPTSignIn()
  instance.registration={"client_id":"oaiapp_test","sub":"test-user"}
  self.assertFalse(instance.restore_session())

if __name__=="__main__":unittest.main()
