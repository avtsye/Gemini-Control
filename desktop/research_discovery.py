"""Public research discovery using documented Wikipedia and Crossref JSON APIs.

Results are source discovery metadata, not full article verification.
No API keys, fabricated citations, redirects, or uncontrolled target hosts.
"""
import re
from urllib.parse import quote

def discover_research_sources(query,approve,language="he",limit=6):
    if not isinstance(query,str) or not 3<=len(query)<=300:
        raise ValueError("Invalid topic")
    if language not in {"he","en"}:raise ValueError("Unsupported Wikipedia language")
    if not isinstance(limit,int) or not 2<=limit<=10:raise ValueError("Invalid limit")
    if not approve("לחפש מקורות ציבוריים בוויקיפדיה וב־Crossref ולהציג למודל כותרות וקישורים?"):
        return {"cancelled":True}
    import requests
    items=[];warnings=[]
    session=requests.Session()
    session.headers.update({"User-Agent":"GeminiControlResearch/1.0 (desktop open-source research client)"})
    try:
        response=session.get("https://"+language+".wikipedia.org/w/api.php",
            params={"action":"query","list":"search","srsearch":query,
                    "srlimit":max(1,limit//2),"format":"json","utf8":1},
            timeout=15,allow_redirects=False)
        response.raise_for_status()
        for item in response.json().get("query",{}).get("search",[])[:limit]:
            title=item.get("title","")
            if not isinstance(title,str) or not title:continue
            items.append({"source":"Wikipedia","title":title[:220],
                "url":"https://"+language+".wikipedia.org/wiki/"+quote(title.replace(" ","_")),
                "description":"Encyclopedia search result; verify article contents separately"})
    except (requests.RequestException,ValueError,TypeError,KeyError):
        warnings.append("Wikipedia search unavailable")
    try:
        response=session.get("https://api.crossref.org/works",
             params={"query.bibliographic":query,"rows":max(1,limit//2),
                     "select":"DOI,title,published,URL"},
             timeout=15,allow_redirects=False)
        response.raise_for_status()
        for item in response.json().get("message",{}).get("items",[])[:limit]:
            doi=item.get("DOI","")
            title=item.get("title",[])
            title=title[0] if isinstance(title,list) and title else ""
            if not isinstance(doi,str) or not re.fullmatch(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+",doi):
                continue
            items.append({"source":"Crossref","title":str(title)[:220],
                          "url":"https://doi.org/"+doi,
                          "description":"Publication metadata; full paper content not fetched"})
    except (requests.RequestException,ValueError,TypeError,KeyError):
        warnings.append("Crossref search unavailable")
    return {"topic":query,"sources":items[:limit],"warnings":warnings,
            "note":"Search metadata is not evidence that linked pages were read."}
