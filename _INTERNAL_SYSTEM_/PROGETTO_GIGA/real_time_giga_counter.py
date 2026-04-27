import time
import os
import sys
import subprocess
from datetime import datetime, timedelta

# --- CONFIGURAZIONE E DIPENDENZE ---
def install_deps():
    deps = ['psutil', 'colorama']
    for dep in deps:
        try:
            __import__(dep)
        except ImportError:
            print(f"[!] Modulo '{dep}' non trovato. Installazione in corso...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", dep])

install_deps()
import psutil
import colorama
from colorama import Fore, Style
colorama.init()

def get_wifi_interface():
    """Trova automaticamente l'interfaccia Wi-Fi attiva"""
    addrs = psutil.net_if_addrs()
    stats = psutil.net_if_stats()
    
    # Cerca interfacce che hanno 'wi-fi', 'wlan' o 'wireless' nel nome e sono attive
    for interface, snics in addrs.items():
        if any(keyword in interface.lower() for keyword in ['wi-fi', 'wlan', 'wireless']):
            if interface in stats and stats[interface].isup:
                return interface
    
    # Fallback: prendi la prima interfaccia attiva che non sia Loopback
    for interface, stat in stats.items():
        if stat.isup and 'loopback' not in interface.lower():
            return interface
            
    return None

def get_usage(interface):
    """Ottiene i byte totali (inviati + ricevuti) per l'interfaccia specifica"""
    counters = psutil.net_io_counters(pernic=True)
    if interface in counters:
        return counters[interface].bytes_sent + counters[interface].bytes_recv
    return 0

def main():
    os.system('cls' if os.name == 'nt' else 'clear')
    print(Fore.CYAN + "========================================")
    print("    MONITOR HARDWARE GIGA (REAL-TIME)   ")
    print("========================================" + Style.RESET_ALL)
    
    interface = get_wifi_interface()
    if not interface:
        print(f"{Fore.RED}[!] Nessuna interfaccia Wi-Fi attiva trovata.{Style.RESET_ALL}")
        return

    print(f"{Fore.YELLOW}[*] Interfaccia rilevata: {interface}{Style.RESET_ALL}")
    
    try:
        current_giga_input = input("\nInserisci i Giga rimasti ora (es. 15.5) o premi Invio per 0: ")
        total_remaining_at_start = float(current_giga_input) if current_giga_input else 0.0
    except ValueError:
        print(f"{Fore.RED}[!] Valore non valido. Uso 0.0{Style.RESET_ALL}")
        total_remaining_at_start = 0.0

    initial_bytes = get_usage(interface)
    start_time = time.time()

    print(f"\n{Fore.GREEN}[OK] Monitoraggio avviato. Premi Ctrl+C per fermare.{Style.RESET_ALL}")
    time.sleep(2)

    try:
        while True:
            current_bytes = get_usage(interface)
            session_consumed_bytes = current_bytes - initial_bytes
            session_consumed_gb = session_consumed_bytes / (1024**3)
            
            # Calcolo giga rimanenti basato sul valore iniziale inserito
            actual_remaining = total_remaining_at_start - session_consumed_gb
            
            # Calcolo velocità istantanea (molto approssimativa su 1s)
            time.sleep(1)
            new_bytes = get_usage(interface)
            speed_mb = (new_bytes - current_bytes) / (1024*1024)
            
            os.system('cls' if os.name == 'nt' else 'clear')
            print(Fore.CYAN + "--- STATISTICHE HARDWARE REAL-TIME ---" + Style.RESET_ALL)
            print(f"Interfaccia: {Fore.WHITE}{interface}{Style.RESET_ALL}")
            print(f"\nConsumati in questa sessione: {Fore.RED}{session_consumed_gb:.4f} GB{Style.RESET_ALL}")
            
            if total_remaining_at_start > 0:
                color = Fore.GREEN if actual_remaining > 5 else Fore.YELLOW
                if actual_remaining < 1: color = Fore.RED
                print(f"Giga Rimanenti (STIMA REALE): {color}{actual_remaining:.4f} GB{Style.RESET_ALL}")
            
            print(f"Velocità attuale:             {Fore.YELLOW}{speed_mb:.2f} MB/s{Style.RESET_ALL}")
            print(f"Tempo trascorso:              {str(timedelta(seconds=int(time.time() - start_time)))}")
            print("\n" + "-"*38)
            print("I dati sono letti direttamente dalla scheda di rete.")
            print("Premi Ctrl+C per uscire.")
            
    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}[*] Monitoraggio terminato.{Style.RESET_ALL}")
        print(f"Totale consumato: {Fore.RED}{session_consumed_gb:.4f} GB{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
