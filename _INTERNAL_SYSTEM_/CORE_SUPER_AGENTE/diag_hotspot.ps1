$ErrorActionPreference = "Stop"

Write-Host "--- DIAGNOSTICA ---"

# 1. ICS Service
try {
    $ics = Get-Service -Name "SharedAccess"
    Write-Host "Servizio ICS: $($ics.Status)"
} catch {
    Write-Host "Servizio ICS non trovato."
}

# 2. Network Profile
try {
    $profile = [Windows.Networking.Connectivity.NetworkInformation, Windows.Networking.Connectivity, ContentType=WindowsRuntime]::GetInternetConnectionProfile()
    if ($null -eq $profile) {
        Write-Host "Nessun profilo internet."
    } else {
        Write-Host "Profilo: $($profile.ProfileName)"
        
        # 3. Tethering Manager
        $tm = [Windows.Networking.NetworkOperators.NetworkOperatorTetheringManager, Windows.Networking.NetworkOperators, ContentType=WindowsRuntime]::CreateFromConnectionProfile($profile)
        Write-Host "Hotspot pronto."
        Write-Host "Stato (Direct): $($tm.TetheringOperationalStatus)"
        Write-Host "Stato (Casted): $([string]$tm.TetheringOperationalStatus)"
        
        # Ispezione membri
        Write-Host "--- Membri TetheringManager ---"
        $tm | Get-Member | ForEach-Object { "$($_.Name) ($($_.MemberType))" }
        
        # Capability
        $cap = $tm.GetTetheringCapability()
        Write-Host "Capability: $cap"
    }
} catch {
    Write-Host "Errore: $($_.Exception.Message)"
    Write-Host "StackTrace: $($_.ScriptStackTrace)"
}
