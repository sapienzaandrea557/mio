import subprocess
import sys
import os

# Configurazione percorso ADB (basato sulla struttura rilevata sul PC)
SCRCPY_DIR = r"D:\scrcpy-win64-v3.3.4"
ADB_PATH = os.path.join(SCRCPY_DIR, "adb.exe")

def lock_android(ip):
    # Forza l'output in UTF-8 per evitare crash su caratteri speciali in Windows
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print(f"--- TENTATIVO BLOCCO REALE ANDROID (IP: {ip}) ---")
    
    if not os.path.exists(ADB_PATH):
        print(f"❌ ERRORE: adb.exe non trovato in {SCRCPY_DIR}")
        return False

    try:
        # 1. Prova a connettersi al dispositivo via ADB sulla porta standard 5555
        subprocess.run([ADB_PATH, "connect", f"{ip}:5555"], capture_output=True, text=True, timeout=5)
        
        # 2. Invia il comando Keyevent 26 (Tasto Power)
        result = subprocess.run([ADB_PATH, "-s", f"{ip}:5555", "shell", "input", "keyevent", "26"], 
                               capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0:
            print(f"✅ COMANDO INVIATO CON SUCCESSO A {ip}")
            return True
        else:
            print(f"❌ ERRORE: Assicurati che il Debug Wireless sia attivo su {ip}")
            return False
    except Exception as e:
        print(f"❌ FALLIMENTO CRITICO: {str(e)}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        lock_android(sys.argv[1])
    else:
        print("Uso: python phone_adb_control.py [IP_TELEFONO]")
