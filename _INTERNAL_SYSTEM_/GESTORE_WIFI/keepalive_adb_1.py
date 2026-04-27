import subprocess
import time
import sys

ADB = r"C:\Users\pc\Desktop\scrcpy-win64-v3.3.4\adb.exe"
IP  = "192.168.1.32"  # IP del tuo telefono
PORT = "5555"

def is_connected():
    out = subprocess.run([ADB, "devices"], capture_output=True, text=True).stdout
    for line in out.splitlines():
        if IP in line and "device" in line and "offline" not in line:
            return True
    return False

def reconnect():
    subprocess.run([ADB, "connect", f"{IP}:{PORT}"], capture_output=True)

print(f"=== ADB KEEPALIVE ===")
print(f"Monitoraggio connessione a {IP}:{PORT}")
print(f"Il programma riconnette automaticamente se si disconnette.")
print(f"Premi Ctrl+C per fermare.\n")

while True:
    if is_connected():
        print(f"\r[OK] Connesso a {IP}    ", end="", flush=True)
    else:
        print(f"\r[!!] Disconnesso, riconnessione...", end="", flush=True)
        reconnect()
        time.sleep(2)
        if is_connected():
            print(f"\r[OK] Riconnesso a {IP}  ", end="", flush=True)
        else:
            print(f"\r[!!] Riconnessione fallita, riprovo...", end="", flush=True)
    time.sleep(5)
