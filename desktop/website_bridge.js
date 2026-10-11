// Gemini website adapter. No sidebar; actions always pass through Windows approval.
(() => {
  if (location.origin !== 'https://gemini.google.com' || window.__gcDesktop) return;
  window.__gcDesktop = true;
  const MARKER='GEMINI_CONTROL_ACTION';
  const contract='You have a local Gemini Control Windows tool adapter. If the user asks to perform a computer action (e.g. open Paint, save a text file, take a screenshot), respond naturally in Hebrew and include one GEMINI_CONTROL_ACTION code block containing one valid JSON object. Allowed: {"version":1,"type":"open_app","app":"paint|notepad|calculator|explorer"}; {"version":1,"type":"write_file","name":"notes.txt","content":"text"}; {"version":1,"type":"screenshot"}; {"version":1,"type":"question","question":"..."}. Ask if details are missing. The native user approval dialog is mandatory. A screenshot is saved locally and NOT uploaded. Never claim completion until the result returns. Never propose shell commands, login details, unrestricted file paths, or instructions to bypass approvals.';
  const intent=/(?:פתח|תפתח|הפעל|תריץ|תצלם|צלם|צילום מסך|שמור (?:קובץ|מסמך)|כתוב (?:קובץ|מסמך)|צור (?:קובץ|מסמך)|open (?:paint|notepad|calculator|explorer)|screenshot|save (?:a )?file)/i;
  let bridge=null, pending=null, seen=new Set(), lastResult='';
  function field(){
    return [...document.querySelectorAll('textarea,[contenteditable="true"],[role="textbox"]')]
      .filter(n=>n.getBoundingClientRect().width>180&&n.getBoundingClientRect().height>10)
      .at(-1);
  }
  function read(el){return el?(el.tagName==='TEXTAREA'?el.value:el.innerText||el.textContent||''):''}
  function write(el,value){
    if(!el)return false;
    el.focus();
    if(el.tagName==='TEXTAREA'){
      const setter=Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set;
      setter.call(el,value);
    }else el.textContent=value;
    el.dispatchEvent(new InputEvent('input',{bubbles:true,inputType:'insertText',data:value}));
    return read(el).includes(value.slice(0,Math.min(20,value.length)));
  }
  // Only modify messages that clearly request a desktop action. Never silently
  // submit an altered message: the first Enter previews it, the second sends it.
  document.addEventListener('keydown',event=>{
    if(event.key!=='Enter'||event.shiftKey||event.ctrlKey||event.altKey||event.metaKey||event.isComposing)return;
    const el=field();
    if(!el||!(el===event.target||el.contains(event.target)))return;
    const text=read(el);
    if(!intent.test(text)||text.includes('You have a local Gemini Control Windows tool adapter'))return;
    event.preventDefault();event.stopImmediatePropagation();
    if(!write(el,text+'\n\n'+contract)){
      // Do not submit a truncated or changed prompt accidentally.
      console.warn('Gemini Control: editor did not accept protocol');
    }
  },true);
  function extract(text){
    const offset=text.lastIndexOf(MARKER);
    if(offset<0)return null;
    const tail=text.slice(offset+MARKER.length);
    const start=tail.indexOf('{');
    if(start<0||start>160)return null;
    let depth=0,quoted=false,escape=false;
    for(let i=start;i<tail.length&&i<50000;i++){
      const c=tail[i];
      if(quoted){if(escape)escape=false;else if(c==='\\')escape=true;else if(c==='"')quoted=false}
      else if(c==='"')quoted=true;
      else if(c==='{')depth++;
      else if(c==='}'&&--depth===0){
        const raw=tail.slice(start,i+1);
        try{
          const data=JSON.parse(raw);
          if(data.version!==1||!['open_app','write_file','screenshot','question'].includes(data.type))return null;
          return {data,id:raw};
        }catch{return null}
      }
    }
    return null;
  }
  function scan(){
    if(!bridge||pending)return;
    const nodes=[...document.querySelectorAll('model-response,[data-message-author-role="model"],.model-response-text,[data-test-id="model-response"]')];
    const message=nodes.slice(-4).map(n=>n.innerText||'').join('\n');
    const parsed=extract(message);
    if(!parsed||seen.has(parsed.id))return;
    seen.add(parsed.id);
    pending=parsed.id;
    // This requests a native action; native dialog handles approval.
    bridge.propose(JSON.stringify(parsed.data));
  }
  function connect(){
    if(!window.qt?.webChannelTransport||typeof QWebChannel!=='function')return;
    new QWebChannel(qt.webChannelTransport,channel=>{
      bridge=channel.objects.computerBridge;
      bridge.result.connect(payload=>{
        lastResult=payload;
        pending=null;
        // Prepare, but do not auto-submit: Gemini chat changes its composer,
        // and this is a user-visible data transfer from the local computer.
        const el=field();
        if(el&&!read(el).trim()){
          write(el,'תוצאת הפעולה של Gemini Control: '+payload+'\nהמשך לפי התוצאה; אם צריך הצע את הפעולה הבאה בפורמט GEMINI_CONTROL_ACTION.');
        }
      });
      scan();
    });
  }
  const q=document.createElement('script');
  q.src='qrc:///qtwebchannel/qwebchannel.js';
  q.onload=connect;
  (document.head||document.documentElement).append(q);
  new MutationObserver(scan).observe(document.documentElement,{subtree:true,childList:true,characterData:true});
  setInterval(scan,2000);
})();