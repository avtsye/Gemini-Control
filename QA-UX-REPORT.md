# QA + UX audit — 2026-10-11

## Scope
Chrome popup, Gemini website adapter, agent dashboard, file workspace, action review, bridge panel, native Windows host, build and installation scripts.

## Automated result
[Chrome extension validation workflow](https://github.com/avtsye/Gemini-Control/actions/runs/38145170486) passed. The new UX integration-contract suite reported **24/24 PASS**. Checks cover cross-file UI ID references, page scripts, RTL, source registration, approval enforcement, feedback handlers, native stop switch, backups, allowlist and Gemini proposal replay prevention.

## Issues fixed in this pass
1. **Duplicate proposal submission**: A Gemini reply remained actionable even after it was already handed off for approval. The website adapter now marks that exact response as consumed.
2. **Regression gaps**: previous workflows checked syntax and entrypoints but did not test screen-element wiring or bridge invariants. Added `tests/ux_contract_check.py` to CI.
3. **User-facing distinction**: pass/fail results are now explicitly separated from unverified interactive behavior.

## Important remaining gaps (not validated or complete)
- Cannot perform a full mouse-and-keyboard interactive Chrome + Windows QA on GitHub-hosted code alone, and no real interactive GUI session was run in this audit.
- Gemini website adapter uses DOM selectors and may break when the third-party site changes. It is **not** a first-party Gemini tool integration or a privileged server connection.
- Gemini→approval→native→feedback remains a **human-reviewed**, partially manual workflow; sending the feedback message into the conversation is not automated.
- Native UI Automation handles inspected accessible buttons of allowlisted foreground apps only, with user approval; it is not general desktop autonomy.
- No end-to-end tests verify reliable app focus, Hebrew keyboard input, file rollback after failures, Gemini streaming responses or Windows permissions.
- Browser UI and bridge controls do not yet share one unified durable job queue with transactional status/replay protection.
- Single pending action/session data can be replaced by another concurrent proposal; proper session-scoped task IDs are needed.

## Recommended manual smoke tests before trusting it with real documents
1. Reload unpacked Chrome extension; check popup primary action, agent dashboard and bridge panel, and no console errors.
2. Test bridge ping, disable, rejected app launch while disabled, then re-enable.
3. Gemini test: explicitly request the extension, review inserted protocol, send, capture a structured action, approve once, ensure it cannot be retriggered from the same response.
4. Type simple Hebrew text into a disposable Notepad window and confirm target identity and text integrity.
5. Create and replace a dummy .txt file, confirm backup, verify resulting content.
6. UI Automation: inspect a disposable allowed app, approve one harmless button, verify the result; test a changed/missing target.
7. Try two browser tabs concurrently and confirm whether pending actions collide (known limitation).
8. Check screen scaling 100%/150%, narrow windows, keyboard-only navigation, tab order, focus states and RTL rendering.

**Release gate:** QA status is **partial pass (automated)**, **manual interactive QA not performed**. Not a claim of complete UX/QA certification.
