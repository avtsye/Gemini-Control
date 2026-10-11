"""Official Sign in with ChatGPT OAuth for an open-source local Windows client.
No API key, browser scraping, or disabled TLS verification.
Access tokens remain in memory for this first version (sign in again after restart).
"""
import base64, hashlib, json, secrets, threading, uuid, webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlencode, urlparse, parse_qs
import requests
import jwt
from jwt import PyJWKClient

AUTH="https://auth.openai.com/api/accounts/authorize"
TOKEN="https://auth.openai.com/api/accounts/oauth/token"
RESOURCE="https://api.openai.com/v1"
ISSUER="https://auth.openai.com"
SCOPES="openid profile email offline_access resource.invoke chatgpt.tokens.use.direct"
JWKS=ISSUER+"/.well-known/jwks.json"

class SignInError(Exception): pass

class ChatGPTSignIn:
    def __init__(self):
        self.access_token=None
        self.identity=None
        self.client_id=None
        self.scopes=set()
        self.host_id="urn:uuid:"+str(uuid.uuid4())

    def sign_in(self, timeout=180):
        """Blocking method: run in a worker, never on Qt UI thread."""
        state=secrets.token_urlsafe(32)
        nonce=secrets.token_urlsafe(32)
        verifier=secrets.token_urlsafe(72)
        challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
        received={}
        finished=threading.Event()
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if urlparse(self.path).path!="/auth/callback":
                    self.send_error(404);return
                received.update({k:v[0] for k,v in parse_qs(urlparse(self.path).query).items() if v})
                body="You may return to Gemini Control Desktop."
                self.send_response(200);self.send_header("Content-Type","text/plain; charset=utf-8")
                self.send_header("Content-Length",str(len(body)));self.end_headers()
                self.wfile.write(body.encode())
                finished.set()
            def log_message(self,*args): pass
        server=HTTPServer(("127.0.0.1",0),Handler)
        server.timeout=1
        uri=f"http://127.0.0.1:{server.server_port}/auth/callback"
        params={
            "client_id":"dynamic_agent_client","agent_name_hint":"Gemini Control Desktop",
            "ext_agent_host_id":self.host_id,"response_type":"code",
            "redirect_uri":uri,"scope":SCOPES,"resource":RESOURCE,
            "state":state,"nonce":nonce,
            "code_challenge_method":"S256","code_challenge":challenge
        }
        url=AUTH+"?"+urlencode(params)
        webbrowser.open(url)
        try:
            import time
            end=time.monotonic()+timeout
            while not finished.is_set() and time.monotonic()<end:
                server.handle_request()
            if not finished.is_set():raise SignInError("ההתחברות לא הושלמה בזמן")
        finally:
            server.server_close()
        if not secrets.compare_digest(received.get("state",""),state):
            raise SignInError("OAuth state mismatch")
        if "error" in received:raise SignInError("ההתחברות לא אושרה: "+received["error"])
        code=received.get("code")
        issued=received.get("client_id")
        if not code or not issued or issued=="dynamic_agent_client":
            raise SignInError("לא התקבלו קוד הרשאה ומזהה לקוח רשמי")
        response=requests.post(TOKEN,data={
            "grant_type":"authorization_code","client_id":issued,
            "code":code,"code_verifier":verifier,
            "redirect_uri":uri,"resource":RESOURCE
        },timeout=30)
        response.raise_for_status()
        data=response.json()
        id_token=data.get("id_token")
        if not id_token:raise SignInError("Missing ID token")
        try:
            key=PyJWKClient(JWKS).get_signing_key_from_jwt(id_token)
            claims=jwt.decode(id_token,key.key,algorithms=["RS256"],audience=issued,issuer=ISSUER)
        except Exception as e:
            raise SignInError("ID token validation failed") from e
        if not secrets.compare_digest(str(claims.get("nonce","")),nonce):
            raise SignInError("OIDC nonce mismatch")
        scopes=set(data.get("scope","").split())
        if "chatgpt.tokens.use.direct" not in scopes:
            raise SignInError("לא ניתנה הרשאה להשתמש במכסת ChatGPT. ההתחברות אינה מספיקה.")
        if not data.get("access_token"):
            raise SignInError("Missing access token")
        self.client_id=issued
        self.access_token=data["access_token"]
        self.identity={"sub":claims["sub"],"email":claims.get("email","")}
        self.scopes=scopes
        return self.identity

    def response(self, prompt,model="gpt-5.6"):
        if not self.access_token:raise SignInError("תחילה יש להתחבר עם ChatGPT")
        r=requests.post(RESOURCE+"/responses",
            headers={"Authorization":"Bearer "+self.access_token,"Content-Type":"application/json"},
            json={"model":model,"input":prompt,"store":False,"stream":False},
            timeout=90)
        if not r.ok:raise SignInError("Responses error HTTP "+str(r.status_code)+": "+r.text[:350])
        data=r.json()
        return "\n".join(c.get("text","") for item in data.get("output",[])
            for c in item.get("content",[]) if c.get("type")=="output_text")
