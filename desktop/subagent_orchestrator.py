"""Concurrent read-only AI analysis with synthesis and per-worker attribution.

Workers only ask the model for text. They do not execute desktop tools,
write files, or share filesystem credentials.
"""
from concurrent.futures import ThreadPoolExecutor,as_completed

ROLES=(
  ("researcher","Collect factual context and identify open questions. Cite only sources supplied."),
  ("critic","Challenge assumptions, identify reliability gaps and possible errors."),
  ("designer","Propose a concrete user-centered implementation or explanation."),
)

def parallel_analysis(model_client,model,request,emit=None,max_workers=3):
    if not isinstance(request,str) or not 3<=len(request)<=12000:
        raise ValueError("Invalid research request")
    if not 1<=max_workers<=3:raise ValueError("Invalid worker count")
    results={}
    def one(role,instruction):
        prompt=("You are a bounded analysis worker. Do not claim you used tools or browsed "
                "the internet. Return concise, grounded analysis and explicit uncertainties. "
                +instruction+"\nUSER REQUEST:\n"+request)
        return model_client.response(prompt,model)
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures={pool.submit(one,name,guide):name for name,guide in ROLES[:max_workers]}
        for future in as_completed(futures):
            name=futures[future]
            try:output=str(future.result())[:10000]
            except Exception as error:output="Worker failed: "+type(error).__name__
            results[name]=output
            if emit:emit("Worker "+name+" completed")
    context="\n\n".join(role.upper()+":\n"+results[role] for role,_ in ROLES[:max_workers])
    synthesis=model_client.response(
        "Combine the following independent analyses into one clear answer in the user's language. "
        "Never invent citations, facts, executed work, or verification. Disclose unresolved limitations.\n"+
        context+"\nOriginal request:\n"+request,model)
    return {"answer":str(synthesis),"workers":results,"worker_count":len(results),
            "mode":"parallel_text_analysis_no_computer_actions"}
