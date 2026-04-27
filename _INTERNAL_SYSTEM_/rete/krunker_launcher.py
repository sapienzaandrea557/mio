import subprocess
import os
import time

def launch_god_mode():
    """
    Lancia Chrome con sicurezza disabilitata per permettere l'iniezione del God Mode.
    """
    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    if not os.path.exists(chrome_path):
        chrome_path = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"

    print("🚀 Lancio di Krunker God-Mode Browser...")
    print(">>> Istruzioni: Una volta aperto, incolla il contenuto di GodMode.js in console (F12)")

    # Parametri per bypassare le protezioni del browser
    cmd = [
        chrome_path,
        "https://krunker.io",
        "--disable-web-security",
        "--user-data-dir=C:/temp/krunker_profile",
        "--no-sandbox",
        "--disable-features=IsolateOrigins,site-per-process"
    ]

    try:
        subprocess.Popen(cmd)
    except Exception as e:
        print(f"❌ Errore durante il lancio: {e}")

if __name__ == "__main__":
    launch_god_mode()
