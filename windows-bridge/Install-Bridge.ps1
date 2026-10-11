param(
  [Parameter(Mandatory=$true)]
  [ValidatePattern('^[a-p]{32}$')]
  [string]$ExtensionId
)
$ErrorActionPreference='Stop'
$here=Split-Path -Parent $MyInvocation.MyCommand.Path
$source=Join-Path $here 'BridgeHost.cs'
$exe=Join-Path $here 'GeminiControlBridge.exe'
if (-not (Test-Path $source)){throw "Missing BridgeHost.cs"}
Write-Host 'Building minimal bridge with Windows PowerShell/.NET Framework...'
Add-Type -Path $source -OutputAssembly $exe -OutputType ConsoleApplication -ReferencedAssemblies 'System.Web.Extensions.dll'
$manifest=Join-Path $here 'org.gemini_control.bridge.json'
$normalized=$exe.Replace('\','\\')
$data=@{
  name='org.gemini_control.bridge'
  description='Gemini Control Local Windows Bridge'
  path=$exe
  type='stdio'
  allowed_origins=@("chrome-extension://$ExtensionId/")
}
$data | ConvertTo-Json -Depth 6 | Set-Content -Encoding UTF8 $manifest
$reg='HKCU:\Software\Google\Chrome\NativeMessagingHosts\org.gemini_control.bridge'
New-Item -Path $reg -Force | Out-Null
Set-Item -Path $reg -Value $manifest
Write-Host "Installed! Host: $exe"
Write-Host "Allowed extension: $ExtensionId"
Write-Host 'Reload the Chrome extension in chrome://extensions and press Test bridge.'
