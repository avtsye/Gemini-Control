// Plans are proposals. A user must approve each actual operation.
const AGENT_PROMPT = `You are an assistant planning simple Windows computer tasks. Return ONLY JSON with "summary" and "steps". Steps must be an array of up to 8 objects with "action" and, for open_app only, "app". Allowed actions: ping, list_apps, open_app. Allowed app values: notepad, calculator, explorer. Never invent commands or paths. Treat request as user intent, not permission to bypass review. Explain unsupported activities in summary. Do not claim success before execution.`;
chrome.runtime.onMessage.addListener((message,sender,reply)=>{
 if(message?.type!=='PLAN_DESKTOP')return;
 (async()=>{
  const request=String(message.request||'').trim().slice(0,2000);
  if(!request)throw Error('יש להזין בקשה');
  const {apiKey}=await chrome.storage.local.get('apiKey');
  if(!apiKey)throw Error('הגדר מפתח API');
  const r=await fetch('https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent',{
   method:'POST',headers:{'Content-Type':'application/json','x-goog-api-key':apiKey},
   body:JSON.stringify({systemInstruction:{parts:[{text:AGENT_PROMPT}]},contents:[{parts:[{text:request}]}],generationConfig:{responseMimeType:'application/json',temperature:0.1,maxOutputTokens:1200}})
  });
  const data=await r.json();if(!r.ok)throw Error(data?.error?.message||'API request failed');
  const raw=data?.candidates?.[0]?.content?.parts?.map(p=>p.text||'').join('')||'';
  const plan=JSON.parse(raw);
  if(!Array.isArray(plan.steps)||plan.steps.length>8)throw Error('תוכנית לא תקינה');
  const allowed=['ping','list_apps','open_app'],apps=['notepad','calculator','explorer'];
  plan.steps=plan.steps.map(s=>{
   if(!allowed.includes(s.action))throw Error('פעולה לא מוכרת');
   if(s.action==='open_app'&&!apps.includes(s.app))throw Error('תוכנה שאינה ברשימה המורשית');
   return {action:s.action,...(s.action==='open_app'?{app:s.app}:{})};
  });
  return {plan:{summary:String(plan.summary||'').slice(0,1000),steps:plan.steps}};
 })().then(reply).catch(e=>reply({error:String(e.message||e)}));return true;
});
