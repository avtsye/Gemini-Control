'use strict';
const $=id=>document.getElementById(id);
let action=null;
function done(t){$('status').textContent=t;$('approve').disabled=true}
function sanitizeSVG(text){
 const doc=new DOMParser().parseFromString(text,'image/svg+xml');
 if(doc.querySelector('parsererror'))throw Error('SVG לא תקין');
 const root=doc.documentElement;if(root.localName!=='svg')throw Error('לא נמצא ציור SVG');
 const allow=new Set(['svg','g','path','rect','circle','ellipse','line','polyline','polygon','text','tspan','defs','linearGradient','radialGradient','stop']);
 const attrs=new Set(['xmlns','width','height','viewBox','d','x','y','x1','y1','x2','y2','cx','cy','r','rx','ry','points','fill','stroke','stroke-width','opacity','transform','font-size','font-family','text-anchor','offset','stop-color','stop-opacity','id']);
 function scrub(node){for(const child of [...node.children]){if(!allow.has(child.localName))child.remove();else scrub(child)}
 for(const a of [...node.attributes])if(!attrs.has(a.name)||/url\s*\(|javascript:|data:|https?:/i.test(a.value))node.removeAttribute(a.name)}
 scrub(root);return new XMLSerializer().serializeToString(root);
}
chrome.storage.session.get('pendingWebsiteAction').then(({pendingWebsiteAction})=>{
 if(!pendingWebsiteAction)throw Error('לא נמצאה פעולה');
 action=pendingWebsiteAction;$('summary').textContent=action.description||'פעולת Gemini';
 if(action.type==='question'){$('summary').textContent=action.question;$('approve').hidden=true}
 if(action.type==='open_app'){$('summary').textContent='Gemini מבקש לפתוח את התוכנה: '+action.app+'\n'+(action.description||'')}
 if(action.type==='drawing_svg'){
  $('summary').textContent='Gemini הכין ציור לתצוגה בדפדפן. הוא לא ייפתח אוטומטית בתוכנת Windows.';
  const safe=sanitizeSVG(action.svg);
  const doc=new DOMParser().parseFromString(safe,'image/svg+xml');
  $('preview').append(document.importNode(doc.documentElement,true));
  $('approve').textContent='שמור ציור כקובץ SVG';
 }
}).catch(e=>done('שגיאה: '+e.message));
$('cancel').onclick=async()=>{await chrome.storage.session.remove('pendingWebsiteAction');window.close()};
$('approve').onclick=async()=>{
 if(!action)return;
 $('approve').disabled=true;
 try{
  if(action.type==='open_app'){
   if(!confirm('לפתוח את '+action.app+' במחשב?')){$('approve').disabled=false;return}
   const r=await new Promise((resolve,reject)=>chrome.runtime.sendNativeMessage('org.gemini_control.bridge',{command:'open_app',app:action.app,id:String(Date.now())},x=>{
    const e=chrome.runtime.lastError;if(e)reject(Error(e.message));else if(!x?.ok)reject(Error(x?.error||'הפעולה נכשלה'));else resolve(x)}));
   done(r.message||'התוכנה נפתחה');
  }else if(action.type==='drawing_svg'){
   const safe=sanitizeSVG(action.svg),blob=new Blob([safe],{type:'image/svg+xml'});
   const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='gemini-drawing.svg';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),2000);
   done('הציור נשמר בהורדות. אפשר לפתוח אותו בתוכנה התומכת ב-SVG.');
  }
  await chrome.storage.session.remove('pendingWebsiteAction');
 }catch(e){$('approve').disabled=false;$('status').textContent='שגיאה: '+String(e.message||e)}
};