# Gemini Control — Gemini website Desktop

The default EXE now uses **the actual website** `https://gemini.google.com/app` inside a QtWebEngine window. **No Gemini API key** is required for this mode. The old API implementation remains in `desktop/app.py` as an optional source-only legacy prototype.

The local bridge is connected to the embedded page through Qt WebChannel. Use **הוסף הוראות סוכן להודעה** to insert a structured protocol in the current Gemini message, then submit it in the website. If Gemini returns `GEMINI_CONTROL_ACTION`, click **בדוק פעולה**, approve the selected action in Windows, and use **העתק תוצאה לשיחה** to continue. Supported actions initially: open allowlisted applications and write approved files in the dedicated Documents workspace. The EXE includes an enable/disable switch. It is not an unrestricted desktop agent.

**Security and compatibility:** HTTPS certificate validation remains enabled. Do not pass `--ignore-certificate-errors` or disable SSL verification. If your content filter uses a private CA, have the filter's trusted root certificate installed in Windows via the filter's official instructions; never install an unverified certificate. Embedded login may be blocked by Google; this mode cannot guarantee sign-in or function as an official Gemini tool integration. An external-browser extension may be required as a fallback.

---
# Gemini Control Desktop — preview

Standalone Windows application in Hebrew with Gemini API and a constrained, confirmed desktop agent.

## Current capabilities
- Chat-style RTL interface with explicit approval prompts
- Sequential Gemini planning and tool results (up to five steps/request)
- Open Notepad, Calculator, Explorer and Paint
- Create/read/edit allowlisted files in Documents/GeminiControl-Workspace, backup on overwrite
- Stop new actions from the UI

## Run on Windows
```powershell
cd desktop
py -m pip install -r requirements.txt
py app.py
```
Enter your own Gemini API key in the app. The key is kept in memory, not saved to disk.

## Boundaries
This is the **first desktop foundation**, not a fully autonomous Antigravity replacement. No arbitrary shell, broad filesystem writes, web browsing, screenshots or general keyboard/mouse control yet. The desktop UI uses the official Gemini API, **not** Google's website or hidden/internal Gemini instructions. Human approval is required for computer changes.
