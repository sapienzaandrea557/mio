Add-Type -AssemblyName System.Runtime.WindowsRuntime

# 1. Rileva profilo di rete
$profile = [Windows.Networking.Connectivity.NetworkInformation, Windows.Networking.Connectivity, ContentType=WindowsRuntime]::GetInternetConnectionProfile()
if ($null -eq $profile) {
    $profiles = [Windows.Networking.Connectivity.NetworkInformation, Windows.Networking.Connectivity, ContentType=WindowsRuntime]::GetConnectionProfiles()
    if ($profiles.Count -gt 0) {
        $profile = $profiles[0]
        Write-Host "Uso profilo: $($profile.ProfileName)" -ForegroundColor Gray
    }
}

if ($null -eq $profile) {
    Write-Host "Nessun profilo di rete trovato!" -ForegroundColor Red
    exit 1
}

# 2. Inizializza manager
$tetheringManager = [Windows.Networking.NetworkOperators.NetworkOperatorTetheringManager, Windows.Networking.NetworkOperators, ContentType=WindowsRuntime]::CreateFromConnectionProfile($profile)

# 3. Leggi argomenti
$mode = $args[0]
$customSsid = $args[1]
$customPass = $args[2]

if ($mode -eq 'on') {
    Write-Host 'Attivazione Hotspot...' -ForegroundColor Cyan
    try {
        $config = $tetheringManager.GetCurrentAccessPointConfiguration()
        if ($customSsid) {
            $config.Ssid = $customSsid
        }
        if ($customPass) {
            $config.Passphrase = $customPass
        }
        $null = $tetheringManager.ConfigureAccessPointAsync($config)
        Write-Host "SSID: $($config.Ssid)" -ForegroundColor Gray

        $state = [string]$tetheringManager.TetheringOperationalState
        if ($state -ne 'On' -and $state -ne '1') {
            $null = $tetheringManager.StartTetheringAsync()
            Start-Sleep -Seconds 2
        }
        Write-Host "Hotspot Attivo" -ForegroundColor Green
    } catch {
        Write-Host "Errore: $($_.Exception.Message)" -ForegroundColor Red
    }
} elseif ($mode -eq 'off') {
    Write-Host 'Disattivazione...' -ForegroundColor Yellow
    try {
        $null = $tetheringManager.StopTetheringAsync()
        Write-Host "Hotspot Spento" -ForegroundColor Green
    } catch {
        Write-Host "Errore: $($_.Exception.Message)" -ForegroundColor Red
    }
} else {
    $curr = [string]$tetheringManager.TetheringOperationalState
    Write-Host "Stato attuale: $curr" -ForegroundColor Gray
}
