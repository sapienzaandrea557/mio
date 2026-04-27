Set WshShell = CreateObject("WScript.Shell")
' Esegue il batch silenzioso che pre-imposta l'opzione 2 e l'URL
WshShell.Run "cmd.exe /c avvio_silent_mode2.bat", 0, false
