#!/usr/bin/env python3
"""Static UX and integration regression checks. Not a substitute for real browser/Windows QA."""
import json,re,pathlib,sys
p=pathlib.Path(__file__).resolve().parents[1]
manifest=json.loads((p/'manifest.json').read_text(encoding='utf-8'))
checks=[]
def check(name,condition):
 checks.append((name,bool(condition)))
 checkname='PASS' if condition else 'FAIL'
 print(f'{checkname}: {name}')
def source(path):return (p/path).read_text(encoding='utf-8')
for page,script in [('popup.html','popup.js'),('agent.html','agent.js'),('workspace.html','workspace.js'),('bridge-panel.html','bridge-panel.js'),('action-review.html','action-review.js')]:
 html=source(page);js=source(script)
 ids=set(re.findall(r'\bid=["\\\']([^"\\\']+)["\\\']',html))
 called=set(re.findall(r'\$\(["\\\']([^"\\\']+)["\\\']\)',js))|set(re.findall(r'getElementById\(["\\\']([^"\\\']+)["\\\']\)',js))
 # dynamically created control IDs are assigned via .id; include them too
 dynamic=set(re.findall(r'\.id=["\\\']([^"\\\']+)["\\\']',js))
 check(f'{page} - referenced UI IDs exist',called <= ids|dynamic)
 check(f'{page} - JS linked',script in html)
 check(f'{page} - RTL Hebrew', 'dir="rtl"' in html)
check('Gemini bridge registered only for Gemini',len(manifest.get('content_scripts',[]))==1 and manifest['content_scripts'][0]['matches']==['https://gemini.google.com/*'])
check('Native messaging permission exists','nativeMessaging' in manifest['permissions'])
check('Gemini feedback roundtrip handlers exist',all(x in source('background.js') for x in ['GET_GEMINI_EXECUTION_RESULT','ACK_GEMINI_EXECUTION_RESULT']))
check('Website actions require approval','action-review.html' in source('background.js'))
check('Bridge persistent stop switch',all(x in source('windows-bridge/BridgeHost.cs') for x in ['set_enabled','if(!Enabled())','Audit(']))
check('Bridge file backups','gemini-control-backups' in source('windows-bridge/BridgeHost.cs'))
check('Windows controls check process allowlist', 'Allowed.Contains(proc.ProcessName)' in source('windows-bridge/AccessibleWindows.cs'))
check('Gemini action replay guard', 'consumedFingerprint' in source('gemini-protocol.js'))
check('No direct shell execution exposed',not any(x in source('windows-bridge/BridgeHost.cs') for x in ['cmd.exe','powershell.exe','ProcessStartInfo(Str(data']))
check('Gemini composer supports role textbox','[role="textbox"]' in source('gemini-protocol.js'))
check('Feedback retains result until confirmation', 'acknowledged.onclick' in source('gemini-protocol.js') and 'feedback.onclick' in source('gemini-protocol.js'))
check('Website adapter exposes connection diagnostic', 'diagnostic.onclick' in source('gemini-protocol.js'))
check('Website parser checks response marker', 'lastIndexOf(START)' in source('gemini-protocol.js'))
print(f'{sum(ok for _,ok in checks)}/{len(checks)} checks passed')
sys.exit(0 if all(x[1] for x in checks) else 1)
