'use strict';
const $=id=>document.getElementById(id);
let plan=null,index=0,working=false;
const names={ping:'בדיקת חיבור',list_apps:'הצגת תוכנות מאושרות',open_app:'פתיחת תוכנה'};
const apps={notepad:'פנקס רשימות',calculator:'מחשבון',explorer:'סייר הקבצים'};
function log(s){const el=$('log');if(el.textContent==='טרם הופעלו פעולות')el.textContent='';el.textContent+='['+new Date().toLocaleTimeString('he-IL')+'] '+s+'\n';el.scrollTop=el.scrollHeight}
function status(s){$('state').textContent=s}
function draw(){
 $('results').classList.toggle('hidden',!plan);
 if(!plan)return;
 $('summary').textContent=plan.summary;
 $('steps').replaceChildren();
 plan.steps.forEach((s,i)=>{
  const line=document.createElement('div');line.className='step';
  const title=document.createElement('span');title.textContent=(i+1)+'. '+names[s.action]+(s.app?' — '+apps[s.app]:'');
  const state=document.createElement('span');state.className='state';state.textContent=i<index?'בוצע':i===index?'ממתין לאישור':'ממתין';
  line.append(title,state);$('steps').append(line);
 });
 $('execute').disabled=working||index>=plan.steps.length;
 $('execute').textContent=index>=plan.steps.length?'התוכנית הסתיימה':'אשר ובצע צעד '+(index+1);
}
async function native(command,app){
 return new Promise((resolve,reject)=>{
  chrome.runtime.sendNativeMessage('org.gemini_control.bridge',{command,app,id:String(Date.now())},r=>{
   const e=chrome.runtime.lastError;if(e)return reject(Error(e.message));
   if(!r||!r.ok)return reject(Error(r?.error||'הגשר אינו זמין'));
   resolve(r);
  });
 });
}
$('plan').onclick=async()=>{
 if(working)return;
 plan=null;index=0;draw();status('Gemini מתכנן את המשימה...');$('plan').disabled=true;
 try{
  const r=await chrome.runtime.sendMessage({type:'PLAN_DESKTOP',request:$('request').value});
  if(r?.error)throw Error(r.error);
  plan=r.plan;status('התוכנית מוכנה. כל צעד מחייב אישור.');
  log('נוצרה תוכנית עם '+plan.steps.length+' צעדים');draw();
 }catch(e){status('שגיאה: '+String(e.message||e));log('שגיאה בתכנון: '+String(e.message||e))}
 finally{$('plan').disabled=false}
};
$('execute').onclick=async()=>{
 if(working||!plan||index>=plan.steps.length)return;
 const step=plan.steps[index];
 const name=names[step.action]+(step.app?' — '+apps[step.app]:'');
 if(!confirm('לאשר כעת את הפעולה הבאה?\n'+name))return;
 working=true;draw();
 try{
  const response=await native(step.action,step.app);
  log('הצליח: '+name+(response.message?' | '+response.message:''));
  if(Array.isArray(response.apps))log('תוכנות: '+response.apps.join(', '));
  index++;draw();status(index>=plan.steps.length?'כל הפעולות המאושרות הושלמו.':'הצעד בוצע. אשר את הצעד הבא.');
 }catch(e){status('הפעולה נכשלה: '+String(e.message||e));log('נכשל: '+name+' — '+String(e.message||e))}
 finally{working=false;draw()}
};
$('stop').onclick=()=>{if(working)return;plan=null;index=0;draw();status('התוכנית בוטלה');log('המשתמש ביטל את התוכנית')};
$('check').onclick=async()=>{try{const r=await native('ping');status('מחובר לגשר');log('חיבור תקין: '+r.message)}catch(e){status('אין חיבור לגשר: '+e.message)}};
$('files').onclick=()=>chrome.tabs.create({url:chrome.runtime.getURL('workspace.html')});
$('clear').onclick=()=>{$('log').textContent='היומן נוקה'};
chrome.storage.session.get('geminiPendingRequest').then(x=>{if(typeof x.geminiPendingRequest==='string'){$('request').value=x.geminiPendingRequest}}).catch(()=>{});
