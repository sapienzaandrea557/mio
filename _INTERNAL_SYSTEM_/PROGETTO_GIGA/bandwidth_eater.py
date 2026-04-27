import asyncio
import aiohttp
import time
import sys
import subprocess
import random
import json
import os
import logging
from datetime import datetime, timedelta

# --- CONFIGURAZIONE E DIPENDENZE ---
def install_deps():
    deps = ['aiohttp', 'colorama', 'psutil']
    for dep in deps:
        try:
            __import__(dep)
        except ImportError:
            print(f"[!] Modulo '{dep}' non trovato. Installazione in corso...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", dep])

install_deps()
import colorama
from colorama import Fore, Style
import psutil
colorama.init()

# Setup Logging professionale
logging.basicConfig(
    filename='bandwidth_extreme.log',
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# URLs GOD-MODE (CDN Massive e Verificate 2026)
TEST_URLS = [
    "https://officecdn.microsoft.com/pr/492350f6-3a01-4f97-b9c0-c7c6ddf67d60/media/en-us/ProPlus2021Retail.img",
    "https://download.visualstudio.microsoft.com/download/pr/893592a6/VSCodeUserSetup-x64-1.85.1.exe",
    "https://it.download.nvidia.com/Windows/551.86/551.86-desktop-win10-win11-64bit-international-dch-whql.exe",
    "https://releases.ubuntu.com/22.04.4/ubuntu-22.04.4-desktop-amd64.iso",
    "https://download.fedoraproject.org/pub/fedora/linux/releases/39/Workstation/x86_64/iso/Fedora-Workstation-Live-x86_64-39-1.5.iso",
    "https://mirror.init7.net/archlinux/iso/latest/archlinux-x86_64.iso",
    "http://ipv4.download.thinkbroadband.com/1GB.zip",
    "https://cdimage.debian.org/debian-cd/current/amd64/iso-cd/debian-12.5.0-amd64-netinst.iso"
]

class SmartBandwidthEngine:
    def __init__(self, mode=None, limit=0, is_slave=False, skip_analysis=False):
        self.total_bytes = 0
        self.last_check_bytes = 0
        self.start_time = None
        self.target_gb = limit if mode == '1' else None
        self.target_minutes = limit if mode == '2' else None
        self.is_running = True
        self.errors = 0
        self.consecutive_errors = 0
        self.active_workers = 0
        self.is_slave = is_slave
        self.skip_analysis = skip_analysis
        
        # Parametri adattivi basati sull'analisi rete
        self.workers_limit = 40
        self.min_workers = 10
        self.max_workers = 150
        self.chunk_size = 1024 * 512 # 512KB default
        self.url_performance = {url: {"success": 0, "bytes": 0, "latency": 0, "errors": 0} for url in TEST_URLS}
        self.worker_tasks = []
        self.session = None

    def format_bytes(self, n):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if n < 1024: return f"{n:.2f} {unit}"
            n /= 1024

    async def analyze_network(self):
        """Analisi profonda di ogni CDN per scegliere i parametri migliori per l'Hotspot attuale"""
        if self.is_slave or self.skip_analysis:
            # Gli slave o master pre-analizzati ereditano parametri base o impostati esternamente
            if self.is_slave:
                self.workers_limit = 50
                self.chunk_size = 1024 * 512
            return

        print(f"{Fore.YELLOW}[*] AVVIO DEEP ANALYSIS RETE (Saturazione di prova)...{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Analizzo latenza e velocità reale su ogni CDN per ottimizzare i worker...{Style.RESET_ALL}")
        
        best_speed = 0
        total_latencies = []
        
        async with aiohttp.ClientSession() as session:
            for url in TEST_URLS:
                try:
                    start_time = time.time()
                    # Test di 3 secondi per ogni URL per misurare velocità reale (più tempo = più precisione)
                    async with session.get(url, timeout=7) as resp:
                        latency = (time.time() - start_time) * 1000
                        total_latencies.append(latency)
                        
                        test_bytes = 0
                        test_start = time.time()
                        # Scarica per max 3 secondi
                        while time.time() - test_start < 3:
                            chunk = await resp.content.read(1024 * 512)
                            if not chunk: break
                            test_bytes += len(chunk)
                        
                        duration = time.time() - test_start
                        speed = test_bytes / duration if duration > 0 else 0
                        self.url_performance[url]["latency"] = latency
                        self.url_performance[url]["bytes"] = test_bytes 
                        
                        if speed > best_speed: best_speed = speed
                        
                        print(f"  > CDN: {url[:30]}... | Latenza: {latency:.1f}ms | Speed: {self.format_bytes(speed)}/s")
                except:
                    self.url_performance[url]["latency"] = 5000
                    self.url_performance[url]["errors"] += 1
                    print(f"  {Fore.RED}> CDN: {url[:30]}... | OFFLINE o LENTA{Style.RESET_ALL}")

        avg_latency = sum(total_latencies) / len(total_latencies) if total_latencies else 999
        
        # LOGICA AGGRESSIVA SCELTA PARAMETRI (Priorità alla Velocità sopra la Latenza)
        self.recommended_terminals = 1
        
        # Se la velocità è alta (> 5MB/s), ignoriamo la latenza alta (tipica di 4G/5G)
        if best_speed > 15 * 1024 * 1024: # > 15MB/s (Fibra o 5G Top)
            self.workers_limit = 100
            self.max_workers = 250
            self.chunk_size = 1024 * 1024
            self.recommended_terminals = 4
            status = "ULTRA-FIBRA / 5G FULL"
        elif best_speed > 4 * 1024 * 1024: # > 4MB/s (4G/5G Standard)
            self.workers_limit = 60
            self.max_workers = 150
            self.chunk_size = 1024 * 512
            self.recommended_terminals = 2
            status = "HOTSPOT 4G/5G VELOCE"
        elif avg_latency < 150 or best_speed > 1 * 1024 * 1024: # ADSL o 4G instabile
            self.workers_limit = 40
            self.max_workers = 100
            self.chunk_size = 1024 * 256
            self.recommended_terminals = 1
            status = "HOTSPOT STANDARD"
        else: # Solo se tutto è sotto 1MB/s e latenza alta
            self.workers_limit = 25
            self.max_workers = 60
            self.chunk_size = 1024 * 128
            self.recommended_terminals = 1
            status = "HOTSPOT CRITICO / 3G"

        logging.info(f"Deep Analysis: {status} | Avg Latency: {avg_latency:.2f}ms | Max Speed: {self.format_bytes(best_speed)}/s | Rec Terms: {self.recommended_terminals}")
        print(f"\n{Fore.GREEN}[OK] Analisi completata: {Fore.CYAN}{status}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Configurazione: {Fore.YELLOW}{self.workers_limit} Workers{Fore.WHITE} | Chunk: {Fore.YELLOW}{self.format_bytes(self.chunk_size)}{Fore.WHITE} | Terminali ottimali: {Fore.YELLOW}{self.recommended_terminals}{Style.RESET_ALL}\n")
        time.sleep(1)

    async def manage_workers(self):
        """Intelligenza Artificiale di Scaling: Aumenta o diminuisce worker in base a errori e velocità"""
        while self.is_running:
            await asyncio.sleep(5) # Controlla ogni 5 secondi
            
            # Calcola velocità degli ultimi 5 secondi
            current_bytes = self.total_bytes
            delta = current_bytes - self.last_check_bytes
            speed = delta / 5
            self.last_check_bytes = current_bytes
            
            # Se abbiamo pochi errori e la velocità è stabile o crescente, aggiungi worker
            if self.consecutive_errors < 5 and self.active_workers < self.workers_limit:
                to_add = min(5, self.workers_limit - self.active_workers)
                for _ in range(to_add):
                    task = asyncio.create_task(self.download_worker(self.session))
                    self.worker_tasks.append(task)
                if not self.is_slave:
                    logging.info(f"Scaling UP: +{to_add} workers (Tot: {self.active_workers}) | Speed: {self.format_bytes(speed)}/s")
            
            # Se gli errori aumentano, riduci worker per non saturare i socket inutilmente
            elif self.consecutive_errors > 15 and self.active_workers > self.min_workers:
                to_remove = 10
                self.consecutive_errors = 0 # Reset contatore
                if not self.is_slave:
                    logging.warning(f"Scaling DOWN: -{to_remove} workers per troppi errori (Tot: {self.active_workers})")
            
            # Reset errori periodico
            if self.consecutive_errors > 0:
                self.consecutive_errors -= 1

    async def download_worker(self, session):
        self.active_workers += 1
        while self.is_running:
            # Selezione URL intelligente basata su performance reale
            if any(self.url_performance[u]["bytes"] > 0 for u in TEST_URLS):
                weights = []
                for u in TEST_URLS:
                    perf = self.url_performance[u]
                    # Peso base proporzionale ai MB scaricati
                    speed_weight = perf["bytes"] / (1024 * 1024)
                    if speed_weight > 50: speed_weight *= 5 
                    
                    weight = 0.1 + speed_weight 
                    
                    # Penalità pesantissima per errori recenti su questa specifica CDN
                    if perf["errors"] > 0:
                        weight /= (perf["errors"] + 1)
                        # Diminuiamo lentamente il contatore errori per permettere ri-test
                        if random.random() < 0.1: perf["errors"] = max(0, perf["errors"] - 1)

                    if perf["latency"] > 1000: weight *= 0.1
                    weights.append(weight)
                
                url = random.choices(TEST_URLS, weights=weights, k=1)[0]
            else:
                url = random.choice(TEST_URLS)
            
            try:
                headers = {'User-Agent': f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/{random.randint(115,125)}.0.0.0'}
                start_req = time.time()
                async with session.get(url, timeout=12, headers=headers) as response:
                    if response.status != 200:
                        self.errors += 1
                        self.consecutive_errors += 1
                        self.url_performance[url]["errors"] += 1
                        await asyncio.sleep(1)
                        continue
                    
                    self.url_performance[url]["latency"] = (time.time() - start_req) * 1000
                    self.consecutive_errors = max(0, self.consecutive_errors - 2) # Riduzione rapida se successo
                    
                    while self.is_running:
                        if self.chunk_size >= 512*1024:
                            chunk = await response.content.readany()
                        else:
                            chunk = await response.content.read(self.chunk_size)
                            
                        if not chunk: break
                        
                        chunk_len = len(chunk)
                        self.total_bytes += chunk_len
                        self.url_performance[url]["bytes"] += chunk_len
                        
                        if self.target_gb and (self.total_bytes / (1024**3)) >= self.target_gb:
                            self.is_running = False
                            break
            except Exception:
                self.errors += 1
                self.consecutive_errors += 1
                self.url_performance[url]["errors"] += 1
                await asyncio.sleep(0.1)
        self.active_workers -= 1

    async def monitor(self):
        self.start_time = time.time()
        last_bytes = 0
        
        if not self.is_slave:
            print(Fore.CYAN + "\n+" + "-"*75 + "+")
            print(f"| {Fore.MAGENTA}ULTIMATE BANDWIDTH ENGINE - {Fore.GREEN}MONITORAGGIO ATTIVO{Fore.CYAN}                     |")
            print("+" + "-"*75 + "+" + Style.RESET_ALL)

        try:
            while self.is_running:
                await asyncio.sleep(1)
                now = time.time()
                elapsed = now - self.start_time
                
                delta_bytes = self.total_bytes - last_bytes
                speed = delta_bytes # byte/s
                
                if self.target_minutes and elapsed >= (self.target_minutes * 60):
                    self.is_running = False
                    break
                
                if not self.is_slave:
                    status_intel = f"{Fore.YELLOW}SCALING{Style.RESET_ALL}" if self.consecutive_errors > 5 else f"{Fore.GREEN}STABLE{Style.RESET_ALL}"
                    out = f"\r| {Fore.GREEN}{self.format_bytes(self.total_bytes)}{Style.RESET_ALL} | {Fore.CYAN}{self.format_bytes(speed)}/s{Style.RESET_ALL} | Wrk: {self.active_workers}/{self.workers_limit} | Err: {self.errors} | Intel: {status_intel} | T: {str(timedelta(seconds=int(elapsed)))} "
                    sys.stdout.write(out.ljust(110))
                    sys.stdout.flush()
                
                # Log ogni 10 secondi
                if int(elapsed) % 10 == 0:
                    logging.info(f"Status: {self.format_bytes(self.total_bytes)} | Speed: {self.format_bytes(speed)}/s | Workers: {self.active_workers}")
                
                last_bytes = self.total_bytes
        except:
            pass
        finally:
            self.is_running = False

    async def run(self):
        await self.analyze_network()
        
        connector = aiohttp.TCPConnector(
            limit=300, 
            limit_per_host=60, 
            force_close=False, 
            ttl_dns_cache=1200,
            use_dns_cache=True
        )
        
        async with aiohttp.ClientSession(connector=connector) as session:
            self.session = session
            # Avvia i worker iniziali (metà del limite per permettere lo scaling dinamico)
            initial_workers = max(self.min_workers, self.workers_limit // 2)
            
            for _ in range(initial_workers):
                task = asyncio.create_task(self.download_worker(session))
                self.worker_tasks.append(task)
            
            # Avvia monitoraggio e gestore dinamico worker
            await asyncio.gather(
                self.monitor(), 
                self.manage_workers(),
                *self.worker_tasks
            )

async def main():
    # Gestione Multi-Terminal Auto-Spawn
    if "--slave" in sys.argv:
        mode = sys.argv[2]
        limit = float(sys.argv[3])
        engine = SmartBandwidthEngine(mode, limit, is_slave=True)
        await engine.run()
        return

    print(Fore.RED + Style.BRIGHT + r"""
    █ █ █   ▀█▀ █ █▄ ▄█ ██▀ ██▀   ██▀ █▄ █ █▀  █ █▄ █ ██▀
    █▄█ █▄▄  █  █ █ ▀ █ █▄▄ █▄▄   █▄▄ █ ▀█ █▄█ █ █ ▀█ █▄▄
    [ SISTEMA DI CONSUMO DATI INTELLIGENTE - V4.0 ]
    """ + Style.RESET_ALL)

    print(f"{Fore.WHITE}1. Limite GB")
    print(f"2. Limite Minuti")
    print(f"3. Nessun limite")
    print(f"4. AUTO-SPAWN (Avvia più terminali ottimizzati){Style.RESET_ALL}")
    
    choice = input("> ")
    
    if choice == '4':
        # Eseguiamo l'analisi prima dello spawn per sapere quanti aprirne
        print(f"{Fore.YELLOW}[*] Analisi rete preliminare per determinare carico ottimale...{Style.RESET_ALL}")
        temp_engine = SmartBandwidthEngine()
        await temp_engine.analyze_network()
        
        num_terms = temp_engine.recommended_terminals
        print(f"{Fore.CYAN}[!] L'analisi suggerisce {num_terms} terminali per questa rete.{Style.RESET_ALL}")
        
        # Avvia num_terms - 1 slave
        # Passiamo i parametri dell'analisi agli slave per evitare che la rifacciano
        for i in range(num_terms - 1):
            subprocess.Popen(['start', 'cmd', '/k', 'python', sys.argv[0], '--slave', '3', '0'], shell=True)
            time.sleep(0.3)
            
        # Questa istanza eredita i parametri dell'analisi e diventa il master
        engine = SmartBandwidthEngine('3', 0, skip_analysis=True)
        engine.workers_limit = temp_engine.workers_limit
        engine.chunk_size = temp_engine.chunk_size
        engine.url_performance = temp_engine.url_performance # Passiamo i risultati dell'analisi
        await engine.run()
    else:
        limit = 0
        if choice in ['1', '2']:
            limit = float(input("Inserisci valore: "))
        engine = SmartBandwidthEngine(choice, limit)
        await engine.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Fore.RED}Arresto totale... Controlla bandwidth_extreme.log per il riepilogo.{Style.RESET_ALL}")
