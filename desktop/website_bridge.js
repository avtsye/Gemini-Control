// Runs in embedded QtWebEngine. Only active on the expected Gemini origin.
(() => {
 if (location.origin !== "https://gemini.google.com" || window.__gcDesktop) return;
 window.__gcDesktop = true;
 const contract = 'You can propose a computer operation using a code block starting with GEMINI_CONTROL_ACTION followed by a JSON object. Supported: {"version":1,"type":"open_app","app":"notepad|calculator|explorer|paint"} or {"version":1,"type":"write_file","name":"notes.txt","content":"..."} or {"version":1,"type":"question","question":"..."}. These operations require separate user approval. Do not claim execution until confirmation. Ask for a clarification if necessary.';
 const host = document.createElement('div');
 host.style.cssText='position:fixed;right:15px;bottom:15px;z-index:2147483647;background:white;color:#1a2c49;padding:12px;border-radius:12px;box-shadow:0 2px 15px #0004;font:14px Arial;direction:rtl;max-width:300px';
 const info=document.createElement('p');info.textContent='Gemini Control · גשר מקומי';
 const prepare=document.createElement('button');prepare.textContent='הוסף הוראות סוכן להודעה';
 const execute=document.createElement('button');execute.textContent='בדוק פעולה';execute.disabled=true;
 const feedback=document.createElement('button');feedback.textContent='העתק תוצאה לשיחה';
 const status=document.createElement('div');status.textContent='אין פעולה ממתינה';
 for(const b of [prepare,execute,feedback])b.style.cssText='display:block;width:100%;margin:5px 0;padding:7px;cursor:pointer';
 host.append(info,prepare,execute,feedback,status);
 (document.body||document.documentElement).append(host);
 function editor(){return [...document.querySelectorAll('[contenteditable="true"],textarea,[role="textbox"]')].filter(n=>n.getBoundingClientRect().width>180).at(-1)}
 function get(n){return n?(n.tagName==='TEXTAREA'?n.value:n.innerText||''):''}
 function put(n,s){if(!n)return false;n.focus();if(n.tagName==='TEXTAREA'){n.value=s}else{n.textContent=s}n.dispatchEvent(new InputEvent('input',{bubbles:true,data:s,inputType:'insertText'}));return true}
 prepare.onclick=()=>{const e=editor();const message=get(e);if(!message.trim()){status.textContent='כתוב בקשה באתר Gemini';return}put(e,message+'\n\n'+contract);status.textContent='בדוק ושלח את ההודעה באתר'};
 let bridge=null,lastResult='',candidate=null,fingerprint='',consumed='';
 function connect(){
  if(!window.qt||!window.qt.webChannelTransport){status.textContent='הגשר אינו זמין';return}
  new QWebChannel(qt.webChannelTransport,channel=>{
   bridge=channel.objects.computerBridge;
   bridge.result.connect(payload=>{lastResult=payload;status.textContent='הפעולה הסתיימה. ניתן לצרף את התוצאה לשיחה.'});
  });
 }
 const qscript=document.createElement('script');qscript.src='qrc:///qtwebchannel/qwebchannel.js';qscript.onload=connect;document.head.append(qscript);
 const types=new Set(['question','open_app','write_file']);
 function scan(){
  const nodes=[...document.querySelectorAll('model-response,[data-message-author-role="model"],.model-response-text,[data-test-id="model-response"]')];
  const text=nodes.slice(-5).map(n=>n.innerText||'').join('\n');
  const marker=text.lastIndexOf('GEMINI_CONTROL_ACTION');
  if(marker<0)return;
  const slice=text.slice(marker+21);const first=slice.indexOf('{');if(first<0)return;
  let depth=0,quoted=false,escaped=false,end=-1;
  for(let i=first;i<slice.length&&i<30000;i++){
   const c=slice[i];
   if(quoted){if(escaped)escaped=false;else if(c==='\\')escaped=true;else if(c==='"')quoted=false}
   else if(c==='"')quoted=true;else if(c==='{')depth++;else if(c==='}'&&--depth===0){end=i+1;break}
  }
  if(end<0)return;
  const raw=slice.slice(first,end);if(raw===consumed)return;
  try{const value=JSON.parse(raw);if(value.version!==1||!types.has(value.type))return;candidate=value;fingerprint=raw;execute.disabled=false;status.textContent='נמצאה פעולת מחשב. נדרש אישור.'}catch{}
 }
 execute.onclick=()=>{
  if(!candidate||!bridge)return;
  if(!confirm('להעביר את הפעולה לבדיקה ולאישור במחשב?'))return;
  execute.disabled=true;
  bridge.propose(JSON.stringify(candidate));
  consumed=fingerprint;candidate=null;
 };
 feedback.onclick=()=>{if(!lastResult){status.textContent='אין תוצאה חדשה';return}if(put(editor(),'תוצאת כלי Gemini Control: '+lastResult+'\nהמשך בהתאם לתוצאה והצע פעולה נוספת לפי הצורך.')){status.textContent='בדוק ושלח את המשוב בשיחה';lastResult=''}};
 const observer=new MutationObserver(scan);observer.observe(document.documentElement,{subtree:true,childList:true,characterData:true});
 setInterval(scan,2000);
})();