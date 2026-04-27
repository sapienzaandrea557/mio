import requests
import time
import os
import socket
from colorama import Fore, Style, init

init(autoreset=True)

SERVICES = [
    {"name": "Dashboard Flask", "url": "http://localhost:5000", "type": "http"},
    {"name": "Overpass API (Main)", "url": "https://overpass-api.de/api/interpreter", "type": "http_post"},
    {"name": "MIUR Open Data", "url": "https://dati.istruzione.it/opendata/opendata/catalogo/elements1/SCUANAGRAFESTAT.csv", "type": "http_head"}
]

def check_http(service):
    try:
        if service["type"] == "http":
            r = requests.get(service["url"], timeout=5)
        elif service["type"] == "http_post":
            r = requests.post(service["url"], data="out json;", timeout=5)
        else:
            r = requests.head(service["url"], timeout=5)
            
        if r.status_code < 400:
            return True, f"Status: {r.status_code}"
        else:
            return False, f"Status: {r.status_code}"
    except Exception as e:
        return False, str(e)

def monitor():
    print(Fore.CYAN + "=== MONITORAGGIO SISTEMA SUPER AGENTS ===")
    print(f"Data: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    all_ok = True
    for s in SERVICES:
        ok, msg = check_http(s)
        status_str = Fore.GREEN + "[OK]" if ok else Fore.RED + "[FALLITO]"
        print(f"{status_str} {s['name']:<20} | {msg}")
        if not ok: all_ok = False
        
    if not all_ok:
        print("\n" + Fore.RED + "!!! ALERT: Alcuni servizi critici sono offline !!!")
        # Qui si potrebbe integrare un invio Telegram o Email di alert
    else:
        print("\n" + Fore.GREEN + "Tutti i sistemi sono operativi.")

if __name__ == "__main__":
    monitor()
