# Gemini Control Windows Bridge (experimental)

A lightweight Native Messaging host. The source is C# compiled against Windows' .NET Framework; no Node.js, web server, or administrator rights required.

## Install
1. Load the unpacked Chrome extension from the repository and copy its ID in `chrome://extensions`.
2. Download the repository as ZIP and extract to a **permanent folder**.
3. Open Windows PowerShell in `windows-bridge` and run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Install-Bridge.ps1 -ExtensionId "PASTE_YOUR_32_CHARACTER_EXTENSION_ID"
```

4. Reload the Chrome extension and use the workspace's Windows bridge panel.

The installer registers a native host under the current user's Chrome registry hive; it does not require administrator privileges. It compiles a tiny EXE using Windows PowerShell's Add-Type and .NET Framework.

## Initial actions
- `ping`: check connection
- `list_apps`: read the approved app list
- `open_app`: open **Notepad**, **Calculator** or **File Explorer** without arguments; launched only from a user-clicked button and after confirmation in the extension.
- No arbitrary paths, command execution, shell, elevation, or remote listeners.

Native Messaging has direct access to a local program, so **do not install unknown modifications of this host**. The Chrome extension ID is restricted in the native-host manifest. The website alone cannot call the host; only the explicitly installed extension can.
