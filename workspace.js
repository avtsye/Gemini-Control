'use strict';
const $=id=>document.getElementById(id);
let root=null,dir=null,parts=[],chosen=null,currentText='',proposal=null;
const isText=name=>/\.(txt|md|js|jsx|ts|tsx|json|html|css|xml|csv|py|ps1|cmd|bat|yml|yaml|toml|ini|cfg|log|sql|sh|c|cpp|h|java|go|rs|php|rb|vue|svelte)$/i.test(name);
const safeName=s=>/^[\w\-.\u0590-\u05ff ]{1,150}$/.test(s)&&!['.','..'].includes(s)&&!s.startsWith('.gemini-control-backups');
function msg(t){$('status').textContent=t}
function clearPlan(){proposal=null;$('proposal').hidden=true}
function buttons(){let exists=!!chosen;for(let k of ['save','rename','delete','ask'])$(k).disabled=!exists;$('new').disabled=!dir;$('refresh').disabled=!root;$('up').disabled=!root||parts.length===0}
async function ensurePermission(handle,mode='readwrite') {const opts={mode}; if(await handle.queryPermission(opts)==='granted')return true;return (await handle.requestPermission(opts))==='granted'}
async function list(){if(!dir)return;chosen=null;currentText='';$('editor').value='';$('selected').textContent='3. עריכת קובץ';clearPlan();$('folder').textContent=`תיקייה מורשית: ${root.name}`;$('path').textContent='/'+[root.name,...parts].join('/');const el=$('files');el.replaceChildren();let entries=[];for await (const [name,h] of dir.entries()){if(name==='.gemini-control-backups')continue;entries.push([name,h])} entries.sort((a,b)=>(b[1].kind==='directory')-(a[1].kind==='directory')||a[0].localeCompare(b[0]));for(const [name,h] of entries){const b=document.createElement('button');b.textContent=(h.kind==='directory'?'📁 ':'📄 ')+name;b.disabled=h.kind==='file'&&!isText(name);b.onclick=async()=>{try{if(h.kind==='directory'){dir=h;parts.push(name);await list()}else await openFile(name,h)}catch(e){msg(e.message)}};el.append(b)} buttons()}
async function openFile(name,h){const f=await h.getFile();if(f.size>500000)throw Error('הקובץ גדול מדי לעריכה (מעל 500KB)');const text=await f.text();if(text.includes('\0'))throw Error('קובץ בינארי אינו נתמך');chosen={name,handle:h};currentText=text;$('editor').value=text;$('selected').textContent='3. '+name;clearPlan();buttons();msg('הקובץ נטען. השינויים לא יישמרו עד לאישור שמירה.')}
$('choose').onclick=async()=>{try{if(!window.showDirectoryPicker)throw Error('הדפדפן אינו תומך בבחירת תיקיות. עדכן ל-Chrome בגרסת מחשב.');root=await showDirectoryPicker({mode:'readwrite',id:'gemini-control-workspace'});dir=root;parts=[];await list();msg('התיקייה נבחרה בהצלחה.')}catch(e){if(e.name!=='AbortError')msg(e.message)}};
$('refresh').onclick=async()=>{try{await list()}catch(e){msg(e.message)}};
$('up').onclick=async()=>{if(!parts.length)return;parts.pop();dir=root;for(const p of parts)dir=await dir.getDirectoryHandle(p);await list()};
async function backup(name,data){const b=await root.getDirectoryHandle('.gemini-control-backups',{create:true});const stamp=new Date().toISOString().replace(/[:.]/g,'-');const label=([...parts,name].join('__')).replace(/[^\w.\-\u0590-\u05ff]/g,'_').slice(0,130);const h=await b.getFileHandle(`${stamp}__${label}.bak`,{create:true});const w=await h.createWritable();await w.write(data);await w.close()}
async function saveText(value){if(!chosen)throw Error('לא נבחר קובץ');if(!await ensurePermission(root))throw Error('לא אושרה גישת כתיבה');const before=await (await chosen.handle.getFile()).text();await backup(chosen.name,before);const w=await chosen.handle.createWritable();await w.write(value);await w.close();currentText=value;$('editor').value=value;clearPlan();msg('נשמר בהצלחה. גיבוי נוצר בתיקיית .gemini-control-backups.')}
$('save').onclick=async()=>{try{if(!confirm('לשמור את הקובץ לאחר יצירת גיבוי?'))return;await saveText($('editor').value)}catch(e){msg(e.message)}};
$('new').onclick=async()=>{const name=prompt('שם קובץ חדש (כולל סיומת, למשל example.txt):');if(name===null)return;if(!safeName(name)||!isText(name))return msg('שם או סיומת לא תקינים');try{if(!await ensurePermission(root))throw Error('לא אושרה הרשאה');let h=await dir.getFileHandle(name,{create:false}).catch(()=>null);if(h)return msg('קובץ בשם זה כבר קיים');h=await dir.getFileHandle(name,{create:true});await openFile(name,h);await list();await openFile(name,h);msg('קובץ ריק נוצר.')}catch(e){msg(e.message)}};
$('rename').onclick=async()=>{if(!chosen)return;const old=chosen;const name=prompt('שם חדש לקובץ:',old.name);if(name===null)return;if(!safeName(name)||!isText(name))return msg('שם או סיומת לא תקינים');if(name===old.name)return;try{if(!await ensurePermission(root))throw Error('אין הרשאת כתיבה');const existing=await dir.getFileHandle(name).catch(()=>null);if(existing)throw Error('השם כבר קיים');const content=await (await old.handle.getFile()).text();await backup(old.name,content);const replacement=await dir.getFileHandle(name,{create:true});const w=await replacement.createWritable();await w.write(content);await w.close();await dir.removeEntry(old.name);await list();await openFile(name,replacement);msg('שם הקובץ שונה, ונשמר גיבוי קודם.')}catch(e){msg(e.message)}};
$('delete').onclick=async()=>{if(!chosen)return;const name=chosen.name;if(prompt(`למחיקת ${name}, כתוב את שם הקובץ בדיוק:`)!==name)return;try{if(!await ensurePermission(root))throw Error('אין הרשאת כתיבה');await backup(name,await (await chosen.handle.getFile()).text());await dir.removeEntry(name);await list();msg('הקובץ נמחק. נוצר גיבוי בתיקיית .gemini-control-backups.')}catch(e){msg(e.message)}};
chrome.storage.local.get('apiKey').then(x=>{if(x.apiKey)$('api').value=x.apiKey});
$('keySave').onclick=async()=>{const apiKey=$('api').value.trim();if(!apiKey)return msg('הזן מפתח API');await chrome.storage.local.set({apiKey});msg('מפתח API נשמר מקומית בתוסף')};
$('ask').onclick=async()=>{if(!chosen)return;const instruction=$('instruction').value.trim();if(!instruction)return msg('כתוב מה לשנות בקובץ');const content=$('editor').value;if(content.length>35000)return msg('לצורך הצעות Gemini יש לבחור קובץ קצר מ-35,000 תווים');clearPlan();$('ask').disabled=true;msg('מבקש הצעה מ-Gemini...');try{const r=await chrome.runtime.sendMessage({type:'EDIT_FILE',name:chosen.name,instruction,content});if(r.error)throw Error(r.error);if(typeof r.content!=='string'||r.content.length>100000)throw Error('Gemini לא החזיר קובץ תקין');proposal={name:chosen.name,original:content,content:r.content};$('reason').textContent=r.reason||'הצעה לעדכון הקובץ';$('preview').textContent=r.content;$('proposal').hidden=false;msg('נוצרה הצעה. היא לא נשמרה. בדוק את הקוד המוצג לפני אישור.')}catch(e){msg(e.message)}finally{buttons()}};
$('reject').onclick=()=>{clearPlan();msg('ההצעה בוטלה')};
$('apply').onclick=async()=>{if(!proposal||!chosen)return;try{if(chosen.name!==proposal.name||$('editor').value!==proposal.original)throw Error('הקובץ השתנה מאז יצירת ההצעה. בקש הצעה מחדש');if(!confirm('לשמור את השינוי המוצע? העותק הקודם יישמר בגיבוי.'))return;await saveText(proposal.content)}catch(e){msg(e.message)}};
buttons();
/* One-time instruction handoff from the Gemini page.  No file access occurs
   until the user chooses a directory and file in this extension page. */
chrome.storage.session.get('geminiPendingRequest').then(async ({geminiPendingRequest})=>{
  if(typeof geminiPendingRequest!=='string'||!geminiPendingRequest)return;
  $('instruction').value=geminiPendingRequest;
  msg('התקבלה בקשה מדף Gemini. בחר תיקייה וקובץ, בדוק את ההוראה ולחץ על "צור הצעת שינוי".');
  await chrome.storage.session.remove('geminiPendingRequest');
}).catch(e=>msg('שגיאה בקריאת הבקשה: '+String(e.message||e)));

/* Read-only project review; user must click to send selected source files to Gemini. */
(() => {
  const panel=document.createElement('section');
  panel.className='panel';
  const heading=document.createElement('strong');
  heading.textContent='5. סקירת פרויקט (ללא שינוי קבצים)';
  const description=document.createElement('p');
  description.className='muted';
  description.textContent='סורק עד 12 קובצי קוד/טקסט מהתיקייה שנבחרה ותיקיות המשנה. עד 10,000 תווים לקובץ ו-50,000 תווים בסך הכול. שמות ותוכן הקבצים שנבחרו יישלחו ל-Gemini, רק לאחר אישורך. אין לבחור תיקיות המכילות סודות.';
  const input=document.createElement('textarea');
  input.placeholder='למשל: סרוק את הפרויקט ומצא שגיאות JavaScript וסיכוני אבטחה';
  const button=document.createElement('button');
  button.textContent='סקור את קובצי הפרויקט עם Gemini';
  const output=document.createElement('pre');
  output.style.cssText='white-space:pre-wrap;overflow-wrap:anywhere;max-height:480px;overflow:auto;direction:rtl';
  panel.append(heading,description,input,button,output);
  document.querySelector('main').append(panel);
  button.addEventListener('click',async()=>{
    button.disabled=true;
    try{
      if(!root)throw Error('ראשית בחר תיקיית עבודה');
      const request=input.value.trim();
      if(!request)throw Error('יש לכתוב הוראה לסקירה');
      const files=[],queue=[{handle:root,path:''}];
      let chars=0;
      while(queue.length && files.length<12){
        const {handle,path}=queue.shift();
        for await(const [name,entry] of handle.entries()){
          if(name==='.gemini-control-backups'||name.startsWith('.')||/secret|private|credential|token|password|key/i.test(name))continue;
          const rel=path+name;
          if(entry.kind==='directory'){
            if(queue.length<60)queue.push({handle:entry,path:rel+'/'});
          }else if(isText(name)){
            const file=await entry.getFile();
            if(file.size>15000)continue;
            const content=await file.text();
            if(content.includes('\\0')||content.length>10000||chars+content.length>50000)continue;
            files.push({name:rel,content});chars+=content.length;
            if(files.length>=12)break;
          }
        }
      }
      if(!files.length)throw Error('לא נמצאו קובצי טקסט מתאימים לסקירה');
      const names=files.map(x=>'• '+x.name).join('\\n');
      if(!confirm('לשלוח ל-Gemini את תוכן '+files.length+' הקבצים הבאים?\\n'+names+'\\n\\nבדוק שאין בהם מידע רגיש.'))return;
      output.textContent='שולח קבצים לניתוח...';
      const response=await chrome.runtime.sendMessage({type:'REVIEW_PROJECT',request,files});
      if(response?.error)throw Error(response.error);
      output.textContent='נסקרו '+response.filesReviewed+' קבצים. לא בוצעו שינויים.\\n\\n'+response.answer;
    }catch(e){output.textContent='שגיאה: '+String(e.message||e)}
    finally{button.disabled=false}
  });
})();
