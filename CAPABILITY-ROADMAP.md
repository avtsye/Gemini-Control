# Agent capability roadmap (incremental, compatibility-first)

This document tracks the requested expansion of Gemini-Control. It distinguishes implemented features from planned integration. Keep the existing ChatGPT sign-in, HTML UI, history database and approval model compatible.

## Wave 1 — low-risk local tools (implemented on feature branch)
- Workspace ZIP creation, extraction with traversal and overwrite rejection, and textual file diffs.
- Expose these operations through the existing DesktopAgent and agent tool schema.
- Add regression tests for successful behavior and rejection paths.
- Not yet: 7z, unrestricted filesystem access, automatic process installation or remote browser execution.

## Wave 2 — tool registry and reliable tasks
- Central typed tool registry: name, JSON input schema, capability discovery, risk tier and execution adapter.
- Structured agent plans and task state persisted to SQLite; resumable steps and explicit cancellation.
- Structured step-by-step activity reporting; user confirmation on system-modifying actions.
- Integrate enabled reviewed capabilities as discoverable callable tools with version pinning and rollback.
- No unreviewed generated Python running directly with user OS privileges.

## Wave 3 — safe plugin development
- Generate capability source and test suite; install dependencies in isolated per-capability virtual environments.
- Verify dependency inventory and consent; lockfile and reversible installs.
- Use a real OS security boundary (separate low-privilege account/sandbox) before auto-running generated code.
- Smoke tests, version snapshots, disable/update/rollback and visible execution logs.

## Wave 4 — documents and media
- DOCX/PPTX/XLSX generation/editing, Arabic/Hebrew RTL where supported, scanned PDF OCR (including Hebrew language packs), local indexing.
- File conversion via explicit adapters, 7z with validated provider installation and bounded extraction.
- Audio transcription and TTS adapters; images and MP4 editing with locally available engines and clear optional dependencies.
- Detect missing libraries and report unavailable engines truthfully.

## Wave 5 — computer / browser automation
- Add observation-to-action feedback loop with permissioned screenshots and UI Automation fallback.
- Structured browser connector with URL/host and download boundaries, form review before submission.
- Windows package-management adapters with preview, elevation awareness and explicit user approval.
- PowerShell: reviewed scripts, subprocess output, allowlisted workspace scope, and safeguards against destructive commands.

## Wave 6 — development, memory, scheduling
- GitHub connector with explicit repository access scopes, code checks, branches, PR review.
- Project scaffolding, test runner, build recipes and Windows EXE packaging.
- Searchable local memory, user-controlled deletion/export, scheduled tasks and bounded sub-agents.
- Privacy-first semantic search with local embedding provider if available.

## Release gates for each wave
1. Static checks and focused unit tests pass.
2. Existing tests for sign-in, conversations, plugins, tools and UI pass.
3. Security review covers path traversal, consent, secret leakage and cancellation.
4. Windows 11 interactive smoke tests and manual review of irreversible actions.
5. Merge only after approval; all changes made on isolated feature branches.

**Current reality:** wave 1 changes have been committed, but no Windows interactive acceptance testing or CI execution has been verified yet. All other waves are planning, not complete.
