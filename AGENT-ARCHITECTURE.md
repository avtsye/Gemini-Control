# Gemini Control — Agent architecture and roadmap

## What makes an AI agent
The goal is a **closed loop**, not one-off command execution:

1. User describes a goal.
2. Gemini returns a structured proposal or asks for clarification.
3. The extension validates action type, parameters and scope.
4. The user reviews and approves before computer changes.
5. The native bridge executes and returns success/error with observable evidence.
6. The result is returned to the same Gemini conversation.
7. Gemini replans from that result until the user stops or the task is done.

Google Antigravity demonstrates related ideas: an agent with tools, editable artifacts, context, and work across editor/browser/terminal. This project does **not** yet match that capability set.

## Current website flow
- Visit `gemini.google.com` and include "השתמש בתוסף" in your message.
- In the small Gemini Control widget click **הכן הוראת סוכן ב-Gemini**, review the updated prompt and submit it.
- When Gemini returns a structured action click **בדוק את הפעולה האחרונה**, then approve it in the extension.
- Return to the Gemini tab and click **החזר תוצאה לשיחת Gemini**, then review and send the filled message.
- Gemini can now propose another action based on the actual tool result.

This is **not a direct integration with the site's private tool protocol**, and **messages are not sent automatically**. It depends on Gemini's page DOM, which may change. If the editor cannot be updated, use copy/paste. The bridge never executes a webpage's command without validation and user approval.

## Existing bridge capabilities
- Native Messaging connection, persistent global disable switch and local audit log
- Open selected allowlisted applications, list and type text into selected allowlisted windows
- Limited PNG drawing opened in Paint
- List/read/write bounded files in Documents/GeminiControl-Workspace
- Separate Chrome File System Access workspace for user-selected folders

## Next engineering milestones (not implemented)
- More reliable website conversation adapter with regression tests across supported Gemini layouts
- Task state machine and confirmation queue with atomic request IDs / replay protection
- Rich execution feedback: window identity, before/after observation and error recovery
- Per-application permissions, separate read/write grants, time-limited scopes, panic stop
- UI Automation for accessible controls: focused-window discovery, element identification, verify-and-act; avoid secret fields
- File changes with previews, diffs, backups, undo, protected directories and dry-run
- Approved task chaining with step budgets and easy pause/resume
- A dedicated application interface rather than relying entirely on a third-party webpage DOM

## Important
Do not grant blanket shell execution, elevation or unrestricted file access to a model. Every powerful action must be interpreted by a narrow native command handler that enforces permissions **independent of the model's instructions**.
