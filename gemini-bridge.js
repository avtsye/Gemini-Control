// This content script runs only on gemini.google.com.
// It requires an explicit user click and never treats AI-generated replies as commands.
(() => {
  if (window.__gcGeminiBridge) return;
  window.__gcGeminiBridge = true;
  const TRIGGER = /(?:השתמש(?:י)?\\s+בתוסף|באמצעות\\s+התוסף|use\\s+(?:the\\s+)?(?:gemini\\s+control\\s+)?extension)/i;
  const host = document.createElement('div');
  host.id = 'gc-gemini-bridge';
  const shadow = host.attachShadow({ mode: 'closed' });
  const style = document.createElement('style');
  style.textContent = `:host{all:initial}button{font:600 13px Arial,sans-serif;background:#2557bd;color:white;border:0;border-radius:20px;padding:9px 14px;cursor:pointer;box-shadow:0 2px 9px #0003}button:disabled{background:#757c87;cursor:default}small{font:12px Arial;color:#334155;display:block;background:#fff;padding:5px;border-radius:6px;max-width:250px;direction:rtl}`;
  const button = document.createElement('button');
  button.type = 'button';
  button.textContent = 'Gemini Control: פתח בקשה בתוסף';
  button.disabled = true;
  button.title = 'כתוב בתיבת ההודעה "השתמש בתוסף" ואז לחץ כאן להעברת הבקשה';
  const help = document.createElement('small');
  help.textContent = 'הוסף להודעה "השתמש בתוסף" כדי להפעיל';
  shadow.append(style, button, help);
  Object.assign(host.style, {position:'fixed',right:'20px',bottom:'20px',zIndex:'2147483647',direction:'rtl'});
  (document.body || document.documentElement).append(host);
  function composer() {
    // Only read the user's active composer; do not parse Gemini's responses.
    const a = [...document.querySelectorAll('[contenteditable="true"],textarea')].filter(el => {
      const rect = el.getBoundingClientRect();
      return rect.width > 90 && rect.height > 12 && !el.closest('#gc-gemini-bridge');
    });
    return a.find(el => el.matches(':focus, :focus-within')) || a.at(-1);
  }
  function content(el) {
    if (!el) return '';
    return (el instanceof HTMLTextAreaElement ? el.value : el.innerText || el.textContent || '').trim().slice(0,4000);
  }
  function refresh() {
    const text = content(composer());
    const allowed = TRIGGER.test(text);
    button.disabled = !allowed;
    help.textContent = allowed ? 'הבקשה תיפתח לניהול קבצים. בחר תיקייה וקובץ ואשר כל שינוי.' : 'הוסף להודעה "השתמש בתוסף" כדי להפעיל';
  }
  document.addEventListener('input',refresh,true);
  document.addEventListener('focusin',refresh,true);
  button.addEventListener('click',async () => {
    const instruction = content(composer());
    if (!TRIGGER.test(instruction)) return;
    button.disabled = true;
    try {
      const r = await chrome.runtime.sendMessage({type:'OPEN_WORKSPACE_FROM_GEMINI',instruction});
      if (r?.error) throw Error(r.error);
      help.textContent = 'מנהל הקבצים נפתח בלשונית חדשה';
    } catch(e) {
      help.textContent = 'שגיאה: '+(e.message||String(e));
    } finally {refresh()}
  });
  refresh();
})();