import subprocess
import re
import os
from datetime import datetime

print("=" * 50)
print("     WIFI PASSWORD GRABBER")
print("=" * 50)

output = subprocess.run(["netsh", "wlan", "show", "profiles"],
                        capture_output=True, text=True).stdout

profiles = re.findall(r"Profilo Tutti gli utenti\s*:\s*(.+)", output)
if not profiles:
    profiles = re.findall(r"All User Profile\s*:\s*(.+)", output)

results = []
print(f"\nTrovati {len(profiles)} profili WiFi:\n")

for profile in profiles:
    profile = profile.strip()
    detail = subprocess.run(
        ["netsh", "wlan", "show", "profile", profile, "key=clear"],
        capture_output=True, text=True).stdout

    pwd_match = re.search(r"Contenuto chiave\s*:\s*(.+)", detail)
    if not pwd_match:
        pwd_match = re.search(r"Key Content\s*:\s*(.+)", detail)

    password = pwd_match.group(1).strip() if pwd_match else "N/D"
    print(f"  SSID    : {profile}")
    print(f"  Password: {password}")
    print()
    results.append((profile, password))

# salva sul desktop
path = os.path.join(os.path.expanduser("~"), "Desktop", "wifi_passwords.txt")
with open(path, "w", encoding="utf-8") as f:
    f.write(f"WiFi Passwords — {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
    f.write("=" * 50 + "\n\n")
    for ssid, pwd in results:
        f.write(f"SSID    : {ssid}\n")
        f.write(f"Password: {pwd}\n")
        f.write("-" * 30 + "\n")

print(f"Salvato in: {path}")
input("\nPremi INVIO per uscire...")
