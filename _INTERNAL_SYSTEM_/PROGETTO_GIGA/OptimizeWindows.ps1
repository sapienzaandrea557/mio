# WINDOWS PERFECT OPTIMIZER - Ultimate Performance Edition
# Eseguire come AMMINISTRATORE

$ErrorActionPreference = 'SilentlyContinue'

Write-Host '============================================================' -ForegroundColor Cyan
Write-Host '       WINDOWS PERFECT OPTIMIZER - DEBUGGED & PERFECTED      ' -ForegroundColor Cyan
Write-Host '============================================================' -ForegroundColor Cyan

# 1. Verifica Privilegi
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host '[*] ERRORE: Devi eseguire questo script come AMMINISTRATORE!' -ForegroundColor Red
    exit
}

# --- 2. OTTIMIZZAZIONE KERNEL & LATENZA ---
Write-Host '[1/10] Ottimizzazione Latenza Kernel (BCD)...' -ForegroundColor Green
& bcdedit /set disabledynamictick yes
& bcdedit /set useplatformtick yes
& bcdedit /set tscsyncpolicy Enhanced

# --- 3. OTTIMIZZAZIONE ENERGIA ---
Write-Host '[2/10] Attivazione Piano Energia Performance...' -ForegroundColor Green
& powercfg -duplicatescheme e9a42b02-d5df-448d-aa00-03f14749eb61
$schemes = & powercfg /l
$targetScheme = $schemes | Select-String 'Prestazioni eccellenti'
if ($targetScheme) {
    # Estrazione sicura del GUID tramite regex
    if ($targetScheme -match '([a-z0-9]{8}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{12})') {
        $guid = $matches[1]
        & powercfg /setactive $guid
    }
} else {
    & powercfg /setactive SCHEME_MIN
}
& powercfg -h off

# --- 4. DISABILITAZIONE DEFENDER ---
Write-Host '[3/10] Rimozione colli di bottiglia Defender...' -ForegroundColor Green
Set-MpPreference -DisableRealtimeMonitoring $true
Set-MpPreference -DisableBehaviorMonitoring $true
Set-MpPreference -DisableIOAVProtection $true
Set-MpPreference -DisableScriptScanning $true
Set-MpPreference -SubmitSamplesConsent 2
Set-MpPreference -MAPSReporting 0
Set-MpPreference -HighPriorityBackgroundScan $false
Get-ScheduledTask -TaskPath '\Microsoft\Windows\Windows Defender\*' | Disable-ScheduledTask

# --- 5. DISABILITAZIONE SERVIZI ---
Write-Host '[4/10] Killing servizi non necessari...' -ForegroundColor Green
$Services = 'DiagTrack', 'dmwappushservice', 'Fax', 'RemoteRegistry', 'SysMain', 'WSearch', 'MapsBroker', 'PcaSvc', 'TrkWks', 'WbioSrvc', 'BBSvc', 'XblAuthManager', 'XblGameSave', 'XboxNetApiSvc', 'WpcMonSvc'
foreach ($s in $Services) {
    Stop-Service $s -Force
    Set-Service $s -StartupType Disabled
}

# --- 6. NETWORK TURBO ---
Write-Host '[5/10] Network Stack Tuning...' -ForegroundColor Green
# Impostazioni Globali supportate su Windows 10/11 moderno
netsh int tcp set global autotuninglevel=normal
netsh int tcp set global ecncapability=enabled
netsh int tcp set global timestamps=disabled
netsh int tcp set global rss=enabled
netsh int tcp set global fastopen=enabled
netsh int tcp set global initialrto=2000
netsh int tcp set global rsc=enabled
netsh int tcp set global nonsackrttresiliency=disabled

# Impostazione del Congestion Provider tramite comando moderno
netsh int tcp set supplemental template=custom congestionprovider=ctcp 2>$null
netsh int tcp set supplemental template=internet congestionprovider=ctcp 2>$null

# --- 7. OTTIMIZZAZIONE DISCO ---
Write-Host '[6/10] Ottimizzazione I/O Disco...' -ForegroundColor Green
fsutil behavior set DisableDeleteNotify 0
fsutil behavior set disablelastaccess 1
fsutil behavior set disable8dot3 1

# --- 8. PULIZIA DISM ---
Write-Host '[7/10] Pulizia componenti Windows...' -ForegroundColor Green
$choice = Read-Host 'Vuoi eseguire la pulizia PROFONDA di WinSXS? (Potrebbe richiedere molto tempo) [S/N]'
if ($choice -eq 'S' -or $choice -eq 's') {
    Write-Host 'Avvio pulizia PROFONDA (StartComponentCleanup)...' -ForegroundColor Yellow
    & Dism /Online /Cleanup-Image /StartComponentCleanup /Quiet /NoRestart
} else {
    Write-Host 'Eseguo pulizia VELOCE (CheckHealth)...' -ForegroundColor Cyan
    & Dism /Online /Cleanup-Image /CheckHealth /Quiet /NoRestart
}

# --- 9. RIMOZIONE BLOATWARE ---
Write-Host '[8/10] Rimozione App spazzatura...' -ForegroundColor Green
$Apps = '*ZuneVideo*', '*ZuneMusic*', '*SkypeApp*', '*Messaging*', '*OneConnect*', '*Office.OneNote*', '*BingNews*', '*BingWeather*', '*GetHelp*', '*YourPhone*'
foreach ($a in $Apps) { Get-AppxPackage $a | Remove-AppxPackage }

# --- 10. OTTIMIZZAZIONE RAM ---
Write-Host '[9/10] Ottimizzazione RAM...' -ForegroundColor Green
Disable-MMAgent -MemoryCompression
$VisualPath = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects'
if (-not (Test-Path $VisualPath)) { New-Item -Path $VisualPath -Force | Out-Null }
Set-ItemProperty -Path $VisualPath -Name 'VisualFXSetting' -Value 2

# --- 11. PULIZIA FINALE ---
Write-Host '[10/10] Svuotamento Cache e Temp...' -ForegroundColor Green
$tmp = $env:TEMP
if (Test-Path $tmp) { Get-ChildItem $tmp | Remove-Item -Recurse -Force }
$winTemp = Join-Path $env:SystemRoot 'Temp'
if (Test-Path $winTemp) { Get-ChildItem $winTemp | Remove-Item -Recurse -Force }
$prefetch = Join-Path $env:SystemRoot 'Prefetch'
if (Test-Path $prefetch) { Get-ChildItem $prefetch | Remove-Item -Recurse -Force }
ipconfig /flushdns
Clear-RecycleBin -Confirm:$false

Write-Host ' '
Write-Host '[*] OTTIMIZZAZIONE COMPLETATA!' -ForegroundColor Cyan
Write-Host '[*] RIAVVIA IL PC ORA.' -ForegroundColor Yellow
