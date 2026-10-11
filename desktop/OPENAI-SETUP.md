# AI Control Desktop — Sign in with ChatGPT (preview)

The primary Windows EXE now uses **OpenAI's official open-source Sign in with ChatGPT flow**, not Gemini, a copied ChatGPT browser session, or a separate API key.

## What is implemented
- "Continue with ChatGPT" opens the **system browser** for official OAuth authorization.
- First-time dynamic client registration, loopback redirect (127.0.0.1), state, nonce, PKCE S256, code exchange, signed ID-token verification, permission-scope check.
- Model list loaded using the authorized account; user selects a listed model.
- Responses API inference uses the user's explicitly authorized ChatGPT plan via an OAuth bearer credential with `store:false`, `stream:true`; incomplete responses are treated as failures.
- Application interface in Hebrew RTL with authentication, chat and errors.
- Credentials are **kept in RAM only** for this preview. Restarting requires a new sign-in. Host ID remains on the machine. The app does not access ChatGPT's existing conversations or memory.
- Old Gemini code remains in the repository for reference, but is no longer the default EXE entry point.

## Important limitations
**This initial release validates the account integration and chat only. It does not yet execute the AI's computer instructions.** The prior allowlisted file/app operations remain available in `desktop/agent_core.py`, and a permissioned tool-call adapter can be added after authenticated chat is verified.

ChatGPT plan usage is subject to eligibility and usage limits. No additional API key is needed; the app does consume **eligible plan usage**, and should not be described as unlimited or zero-usage. If sign-in is denied, do not pretend it succeeded or fall back to paid API calls.

The embedded Gemini site is not used in this variant. No HTTPS verification bypasses are enabled; on filtered networks configure the official trusted local root certificate instead.

## Build
Use [Build Gemini Control Desktop EXE](https://github.com/avtsye/Gemini-Control/actions/workflows/build-desktop.yml), download the `GeminiControlDesktop-Windows` artifact and launch `GeminiControlDesktop.exe`.
For local Python runs:
```powershell
py -m pip install -r desktop/requirements.txt
py desktop/app_openai.py
```

## References
- https://developers.openai.com/siwc/token-sharing-open-source
- https://developers.openai.com/siwc/token-sharing-open-source/sign-in
- https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference

## QA
CI checks syntax and unit-tested mocked model-stream responses, plus file-tool permissions. Real account sign-in and model availability require user consent and cannot be confirmed by CI. Verify interactively before enabling local computer actions.
