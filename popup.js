document.getElementById('bridgeControl').onclick=()=>chrome.tabs.create({url:chrome.runtime.getURL('bridge-panel.html')});
document.getElementById('agent').onclick=()=>chrome.tabs.create({url:chrome.runtime.getURL('agent.html')});
const $=id=>document.getElementById(id);let pending=null;
$('workspace').onclick=()=>chrome.tabs.create({url:chrome.runtime.getURL('workspace.html')});
function report(text,error=false){$('response').textContent=text;$('response').classList.toggle('error',error)}
function busy(v){$('plan').disabled=v;$('approve').disabled=v;$('status').textContent=v?'מעבד בקשה...':''}
function reset(){pending=null;$('approve').style.display='none';$('cancel').style.display='none'}
chrome.storage.local.get('apiKey').then(data=>{if(data.apiKey)$('apiKey').value=data.apiKey});
$('save').onclick=async()=>{let k=$('apiKey').value.trim();if(!k)return report('צריך להזין מפתח API.',true);await chrome.storage.local.set({apiKey:k});report('המפתח נשמר מקומית. אפשר להמשיך.')};
$('cancel').onclick=()=>{reset();report('הפעולה בוטלה.')};
async function tab(){let [t]=await chrome.tabs.query({active:true,currentWindow:true});if(!t?.id)throw Error('לא נמצא דף פעיל.');if(!/^https?:/.test(t.url||''))throw Error('Chrome אינו מאפשר לתוסף לפעול בדף זה. פתח אתר רגיל.');return t}
async function pageSnapshot(tabId){let [{result}]=await chrome.scripting.executeScript({target:{tabId},func:()=>{
  let selectors=['a','button','input','textarea','select','[role="button"]','[contenteditable="true"]'];
  document.querySelectorAll('[data-gc-id]').forEach(el=>el.removeAttribute('data-gc-id'));
  let elements=[];for(let el of document.querySelectorAll(selectors.join(','))){if(elements.length>=120)break;let r=el.getBoundingClientRect();if(r.width<1||r.height<1)continue;if(getComputedStyle(el).visibility==='hidden')continue;let id=String(elements.length);el.setAttribute('data-gc-id',id);elements.push({selector:`[data-gc-id="${id}"]`,tag:el.tagName.toLowerCase(),text:(el.innerText||el.getAttribute('aria-label')||el.getAttribute('placeholder')||(el.type==='password'?'':el.value)||'').slice(0,120),type:el.getAttribute('type')||'',href:el.getAttribute('href')?.slice(0,180)||''})}
  return {title:document.title,url:location.href,content:(document.body?.innerText||'').slice(0,12500),elements}
}});return result}
$('plan').onclick=async()=>{reset();busy(true);try{
  let request=$('request').value.trim();if(!request)throw Error('כתוב מה תרצה לבצע.');let t=await tab();let snapshot=await pageSnapshot(t.id);
  let result=await chrome.runtime.sendMessage({type:'PLAN',request,page:snapshot});if(result?.error)throw Error(result.error);
  let p=result.plan;if(p.action==='answer'){report(p.answer||p.reason||'אין תשובה.');return}
  if(['click','fill'].includes(p.action)&&!snapshot.elements.some(x=>x.selector===p.selector))throw Error('Gemini החזיר רכיב שאינו מופיע בדף. נסה שוב.');
  if(p.action==='navigate') {let u=new URL(p.url,snapshot.url);if(!['http:','https:'].includes(u.protocol))throw Error('כתובת לא בטוחה');p.url=u.href}
  let descriptions={click:'לחיצה',fill:'הזנת טקסט',scroll_down:'גלילה למטה',scroll_up:'גלילה למעלה',navigate:'מעבר לאתר'};
  let target=snapshot.elements.find(x=>x.selector===p.selector);
  pending={tabId:t.id,pageUrl:snapshot.url,plan:p};
  report(`Gemini מציע: ${descriptions[p.action]}\n${target?`רכיב: ${target.text||target.tag}`:''}${p.action==='fill'?`\nטקסט: ${p.text||''}`:''}${p.action==='navigate'?`\nיעד: ${p.url}`:''}\n${p.reason||''}\n\nלא תבוצע פעולה בלי אישורך.`);
  $('approve').style.display='block';$('cancel').style.display='block';
}catch(e){report(e.message||String(e),true)}finally{busy(false)}};
$('approve').onclick=async()=>{if(!pending)return;busy(true);try{
  let {tabId,pageUrl,plan}=pending;let t=await chrome.tabs.get(tabId);if(!t||t.url!==pageUrl)throw Error('הדף השתנה מאז ההצעה. בקש פעולה חדשה.');
  if(plan.action==='navigate')await chrome.tabs.update(tabId,{url:plan.url});else{
    let [{result}]=await chrome.scripting.executeScript({target:{tabId},func:(p)=>{
      if(p.action==='scroll_down'||p.action==='scroll_up'){window.scrollBy({top:p.action==='scroll_down'?550:-550,behavior:'smooth'});return 'הגלילה בוצעה'}
      let el=document.querySelector(p.selector);if(!el||!el.hasAttribute('data-gc-id'))throw Error('הרכיב כבר לא קיים');
      if(p.action==='click'){el.click();return 'בוצעה לחיצה'}
      if(p.action==='fill'){if(el.type==='password'||el.type==='hidden'||el.type==='file')throw Error('לא ניתן להזין בשדה זה');if(el.isContentEditable){el.focus();el.textContent=p.text||'';el.dispatchEvent(new InputEvent('input',{bubbles:true,inputType:'insertText',data:p.text||''}))}else if('value' in el){el.focus();let proto=el instanceof HTMLTextAreaElement?HTMLTextAreaElement.prototype:el instanceof HTMLInputElement?HTMLInputElement.prototype:null;let setter=proto&&Object.getOwnPropertyDescriptor(proto,'value')?.set;if(setter)setter.call(el,p.text||'');else el.value=p.text||'';el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}))}else throw Error('זה אינו שדה טקסט');return 'הטקסט הוזן'}
    },args:[plan]});report(result||'הפעולה בוצעה')}
  if(plan.action==='navigate')report('הניווט בוצע.');reset();
}catch(e){report(e.message||String(e),true);reset()}finally{busy(false)}};
