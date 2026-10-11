"""Permission-gated simple HTTPS content retrieval.

Intended for reading public pages, not authenticated browsing or full website interaction.
"""
import ipaddress
import socket
from urllib.parse import urlparse
from pathlib import Path
from workspace_data import safe_path

MAX_RESPONSE=1_500_000

def _validate_url(url):
    if not isinstance(url,str) or len(url)>2000:raise ValueError("Invalid URL")
    parsed=urlparse(url)
    if parsed.scheme!="https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Only anonymous HTTPS URLs are accepted")
    if parsed.port not in {None,443}:raise ValueError("Nonstandard ports are not allowed")
    if parsed.hostname.lower() in {"localhost"} or parsed.hostname.lower().endswith((".local",".internal")):
        raise ValueError("Local destinations are not allowed")
    # Prevent common access to local machines and metadata endpoints.
    try:
        addresses=socket.getaddrinfo(parsed.hostname,443,type=socket.SOCK_STREAM)
    except socket.gaierror as error:
        raise ValueError("Cannot resolve HTTPS host") from error
    if not addresses:raise ValueError("No addresses found")
    for item in addresses:
        address=ipaddress.ip_address(item[4][0])
        if not address.is_global:raise ValueError("Private/reserved networks are forbidden")
    return url

def fetch_page(url,approve):
    checked=_validate_url(url)
    if not approve("לאחזר תוכן דף ציבורי מ-"+urlparse(checked).hostname+" ולשלוח אותו למודל?"):
        return {"cancelled":True}
    import requests
    try:
        with requests.get(checked,timeout=(6,18),stream=True,allow_redirects=False,
                          headers={"User-Agent":"GeminiControlDesktop/1.0"}) as response:
            if 300<=response.status_code<400:return {"error":"Redirects are not automatically followed"}
            response.raise_for_status()
            ctype=response.headers.get("Content-Type","").lower()
            if not any(x in ctype for x in ("text/html","text/plain","application/json")):
                return {"error":"Unsupported page content type"}
            data=bytearray()
            for chunk in response.iter_content(chunk_size=16384):
                data.extend(chunk)
                if len(data)>MAX_RESPONSE:return {"error":"Page too large"}
            text=data.decode(response.encoding or "utf-8",errors="replace")
            return {"url":checked,"text":text[:18000],"truncated":len(text)>18000}
    except requests.RequestException as error:
        return {"error":"HTTPS request failed","details":str(error)[:250]}

DOWNLOAD_EXT={".pdf",".txt",".csv",".json",".png",".jpg",".jpeg",".zip",".md",".webp"}
MAX_DOWNLOAD=30_000_000

def download_file(workspace,url,destination,approve):
    checked=_validate_url(url)
    path=safe_path(workspace,destination)
    if path.suffix.lower() not in DOWNLOAD_EXT:
        raise ValueError("This file type is not approved for downloads")
    if path.exists() or path.is_symlink():raise FileExistsError("Destination exists")
    if not approve("להוריד קובץ ציבורי מאתר "+urlparse(checked).hostname+
                   " לתיקיית העבודה בשם "+str(destination)+"?"):
        return {"cancelled":True}
    import requests
    temp=path.with_name(path.name+".partial")
    if temp.exists():raise FileExistsError("Partial file already exists")
    try:
        with requests.get(checked,timeout=(6,30),stream=True,allow_redirects=False,
                          headers={"User-Agent":"GeminiControlDesktop/1.0"}) as response:
            if 300<=response.status_code<400:return {"error":"Redirects require a new explicit request"}
            response.raise_for_status()
            path.parent.mkdir(parents=True,exist_ok=True)
            count=0
            with temp.open("xb") as out:
                for chunk in response.iter_content(chunk_size=32768):
                    count+=len(chunk)
                    if count>MAX_DOWNLOAD:raise ValueError("Download exceeds 30 MB")
                    out.write(chunk)
        temp.replace(path)
        return {"downloaded":str(destination),"bytes":count}
    except requests.RequestException as error:
        return {"error":"Download failed","details":str(error)[:250]}
    finally:
        temp.unlink(missing_ok=True)

def research_pages(urls,approve):
    """Read 2-5 explicit public sources; no search-index discovery or fabrication."""
    if not isinstance(urls,list) or not 2<=len(urls)<=5 or not all(isinstance(u,str) for u in urls):
        raise ValueError("Provide between two and five HTTPS source URLs")
    if len(set(urls))!=len(urls):raise ValueError("Duplicate source URL")
    # Validate all hosts before asking the user to authorize any requests.
    for url in urls:_validate_url(url)
    if not approve("לקרוא עד חמישה מקורות אינטרנט ציבוריים ולהעביר את תוכנם למודל לצורך מחקר?"):
        return {"cancelled":True}
    sources=[]
    for url in urls:
        result=fetch_page(url,lambda _:True)
        if "text" in result:
            sources.append({"url":url,"text":result["text"][:6500],
                            "truncated":result.get("truncated",False)})
        else:
            sources.append({"url":url,"error":result.get("error","Unavailable")})
    return {"sources":sources,"successful":sum("text" in row for row in sources),
            "note":"These are retrieved source texts; the model must cite each URL and cannot invent sources."}
