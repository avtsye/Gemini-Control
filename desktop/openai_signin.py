"""Official Sign in with ChatGPT OAuth for an open-source local Windows client.
No API key, browser scraping, or disabled TLS verification.
Access tokens remain in memory for this first version (sign in again after restart).
"""
import base64, hashlib, json, secrets, threading, uuid, webbrowser, os, time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlencode, urlparse, parse_qs
from pathlib import Path
import truststore
truststore.inject_into_ssl()  # Honor the Windows trust store, including trusted filter root CAs.
import requests
import jwt
import keyring
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
        self.refresh_token=None
        self.expires_at=0
        directory=Path(os.environ.get("LOCALAPPDATA",Path.home()/".config"))/"GeminiControl"
        directory.mkdir(parents=True,exist_ok=True)
        host_path=directory/"host-id"
        try:
            value=str(uuid.UUID(host_path.read_text(encoding="utf-8").strip()))
        except (ValueError,OSError):
            value=str(uuid.uuid4())
            host_path.write_text(value,encoding="utf-8")
        self.host_id="urn:uuid:"+value
        self.registration_file=directory/"registration.json"
        self.registration=None
        try:
            registration=json.loads(self.registration_file.read_text(encoding="utf-8"))
            if registration.get("client_id","").startswith("oaiapp_") and registration.get("sub"):
                self.registration=registration
        except (OSError,ValueError,KeyError):
            pass

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
        client_id=self.registration["client_id"] if self.registration else "dynamic_agent_client"
        params={
            "client_id":client_id,
            "ext_agent_host_id":self.host_id,"response_type":"code",
            "redirect_uri":uri,"scope":SCOPES,"resource":RESOURCE,
            "state":state,"nonce":nonce,
            "code_challenge_method":"S256","code_challenge":challenge
        }
        if not self.registration:
            params["agent_name_hint"]="Gemini Control Desktop"
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
        issued=received.get("client_id",client_id)
        if self.registration and issued!=self.registration["client_id"]:
            raise SignInError("Client ID changed unexpectedly")
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
        if self.registration and str(claims.get("sub",""))!=self.registration["sub"]:
            raise SignInError("Signed-in account does not match the saved registration")
        if not secrets.compare_digest(str(claims.get("nonce","")),nonce):
            raise SignInError("OIDC nonce mismatch")
        scopes=set(data.get("scope","").split())
        if "chatgpt.tokens.use.direct" not in scopes:
            raise SignInError("לא ניתנה הרשאה להשתמש במכסת ChatGPT. ההתחברות אינה מספיקה.")
        if not data.get("access_token"):
            raise SignInError("Missing access token")
        if not self.registration:
            self.registration={"client_id":issued,"sub":claims["sub"]}
            # Only non-secret registration metadata is persisted, never OAuth tokens.
            temp=self.registration_file.with_suffix(".tmp")
            temp.write_text(json.dumps(self.registration),encoding="utf-8")
            temp.replace(self.registration_file)
        self.client_id=issued
        self.refresh_token=data.get("refresh_token")
        self.expires_at=time.time()+int(data.get("expires_in",3600))
        if self.refresh_token:
            keyring.set_password("AIControlDesktop","refresh:"+claims["sub"],self.refresh_token)
        self.access_token=data["access_token"]
        self.identity={"sub":claims["sub"],"email":claims.get("email","")}
        self.scopes=scopes
        return self.identity

    def restore_session(self):
        """Refresh from Windows Credential Manager; never save tokens as plaintext."""
        if not self.registration:return False
        client_id=self.registration["client_id"]
        stored=keyring.get_password("AIControlDesktop","refresh:"+self.registration["sub"])
        if not stored:return False
        try:
            r=requests.post(TOKEN,data={"grant_type":"refresh_token","client_id":client_id,
                "refresh_token":stored,"resource":RESOURCE},timeout=30)
            r.raise_for_status()
            data=r.json()
            if not data.get("access_token"):return False
            self.access_token=data["access_token"]
            self.refresh_token=data.get("refresh_token",stored)
            self.expires_at=time.time()+int(data.get("expires_in",3600))
            self.client_id=client_id
            self.identity={"sub":self.registration["sub"]}
            if self.refresh_token!=stored:
                keyring.set_password("AIControlDesktop","refresh:"+self.registration["sub"],self.refresh_token)
            return True
        except (requests.RequestException,ValueError):
            return False

    def ensure_fresh(self):
        if self.expires_at and time.time()+60>=self.expires_at:
            if not self.restore_session():raise SignInError("פג תוקף החיבור. התחבר שוב ל-ChatGPT.")

    def models(self):
        if not self.access_token: raise SignInError("Not authenticated")
        self.ensure_fresh()
        response=requests.get(RESOURCE+"/models",
            headers={"Authorization":"Bearer "+self.access_token},timeout=25)
        response.raise_for_status()
        data=response.json()
        return [(m["slug"],m.get("display_name",m["slug"]))
                for m in data.get("models",[]) if m.get("visibility")=="list" and m.get("slug")]

    def response(self, prompt,model):
        if not self.access_token:raise SignInError("תחילה יש להתחבר עם ChatGPT")
        self.ensure_fresh()
        chunks=[]
        completed=False
        with requests.post(RESOURCE+"/responses",
            headers={"Authorization":"Bearer "+self.access_token,"Content-Type":"application/json"},
            json={"model":model,"input":[{"role":"user","content":prompt}],"store":False,"stream":True},
            stream=True,timeout=90) as r:
            if not r.ok:
                raise SignInError("Responses error HTTP "+str(r.status_code)+": "+r.text[:350])
            for line in r.iter_lines(decode_unicode=True):
                if isinstance(line,bytes):line=line.decode('utf-8','replace')
                if not line or not line.startswith("data: "):continue
                try: event=json.loads(line[6:])
                except ValueError:continue
                kind=event.get("type")
                if kind=="response.output_text.delta":
                    chunks.append(event.get("delta",""))
                elif kind in ("response.failed","response.incomplete"):
                    raise SignInError("Response did not complete: "+kind)
                elif kind=="response.completed":
                    completed=True
        if not completed: raise SignInError("Connection ended before response.completed")
        return "".join(chunks)
