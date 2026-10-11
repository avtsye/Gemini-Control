'use strict';
const $=id=>document.getElementById(id);
function send(command,extras={}){
 return new Promise((resolve,reject)=>chrome.runtime.sendNativeMessage('org.gemini_control.bridge',{command,...extras,id:String(Date.now())},reply=>{
  const error=chrome.runtime.lastError;if(error)return reject(Error(error.message));
  if(!reply?.ok)return reject(Error(reply?.error||'לא התקבלה תשובה'));
  resolve(reply);
 }));
}
async function check(){
 try{const x=await send('status');$('status').textContent=x.enabled?'● הגשר מחובר ופעיל':'● הגשר מחובר אך חסום לפעולות';$('status').style.color=x.enabled?'#12704b':'#b25314'}
 catch(e){$('status').textContent='הגשר אינו מחובר: '+e.message;$('status').style.color='#b32525'}
}
$('refresh').onclick=check;
$('enable').onclick=async()=>{if(!confirm('להפעיל מחדש אפשרות לבצע פעולות במחשב?'))return;try{await send('set_enabled',{enabled:'on'});await check()}catch(e){alert(e.message)}};
$('disable').onclick=async()=>{try{await send('set_enabled',{enabled:'off'});await check()}catch(e){alert(e.message)}};
$('load').onclick=async()=>{try{const r=await send('recent_log');$('log').textContent=(r.lines||[]).join('\n')||'אין פעולות מתועדות'}catch(e){$('log').textContent='שגיאה: '+e.message}};
check();

async function pending(){
 const {pendingWebsiteAction}=await chrome.storage.session.get('pendingWebsiteAction');
 const summary=pendingWebsiteAction?(pendingWebsiteAction.description||pendingWebsiteAction.type):'אין כרגע פעולות שממתינות לאישור';
 $('pending').textContent=summary;
 $('review').disabled=!pendingWebsiteAction;
}
$('review').onclick=()=>chrome.tabs.create({url:chrome.runtime.getURL('action-review.html')});
pending();
setInterval(pending,3000);

let controls=[];
$('inspect').onclick=async()=>{
 try{const result=await send('inspect_controls');controls=result.controls||[];const select=$('control');select.replaceChildren();
 controls.forEach((c,i)=>{const o=document.createElement('option');o.value=String(i);o.textContent=c.role+' · '+c.label;select.append(o)});
 $('uiResult').textContent=controls.length+' רכיבים זמינים בחלון הפעיל';
 }catch(e){$('uiResult').textContent='שגיאה: '+e.message}
};
$('clickControl').onclick=async()=>{
 const c=controls[Number($('control').value)];if(!c)return;
 if(!confirm('ללחוץ על "'+c.label+'" בתוכנה הפעילה?'))return;
 try{const r=await send('click_control',{index:c.index,label:c.label});$('uiResult').textContent=r.message;controls=[];$('control').replaceChildren()}
 catch(e){$('uiResult').textContent=e.message}
};
