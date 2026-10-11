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
