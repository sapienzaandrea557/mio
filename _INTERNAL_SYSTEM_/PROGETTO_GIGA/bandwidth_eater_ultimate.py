import asyncio
import aiohttp
import time
import sys
import subprocess
import random
from datetime import datetime, timedelta

# Auto-install dependencies
def install_deps():
    deps = ['aiohttp', 'colorama']
    for dep in deps:
        try:
            __import__(dep)
        except ImportError:
            subprocess.check_call([sys.executable, "-m", "pip", "install", dep])

install_deps()
import colorama
from colorama import Fore, Style
colorama.init()

# URLs GOD-MODE (CDN Massive e Verificate 2026)
TEST_URLS = [
    "https://officecdn.microsoft.com/pr/492350f6-3a01-4f97-b9c0-c7c6ddf67d60/media/en-us/ProPlus2021Retail.img",
    "https://download.visualstudio.microsoft.com/download/pr/893592a6/VSCodeUserSetup-x64-1.85.1.exe",
    "https://it.download.nvidia.com/Windows/551.86/551.86-desktop-win10-win11-64bit-international-dch-whql.exe",
    "https://releases.ubuntu.com/22.04.4/ubuntu-22.04.4-desktop-amd64.iso",
    "https://download.fedoraproject.org/pub/fedora/linux/releases/39/Workstation/x86_64/iso/Fedora-Workstation-Live-x86_64-39-1.5.iso",
    "https://mirror.init7.net/archlinux/iso/latest/archlinux-x86_64.iso",
    "http://ipv4.download.thinkbroadband.com/1GB.zip",
    "https://cdimage.debian.org/debian-cd/current/amd64/iso-cd/debian-12.5.0-amd64-netinst.iso",
    "https://speed.hetzner.de/10GB.bin",
    "http://speedtest.tele2.net/10GB.zip"
]

class UltimateBandwidthEater:
    def __init__(self):
        self.total_bytes = 0
        self.start_time = None
        self.target_gb = None
        self.target_minutes = None
        self.is_running = True
        self.errors = 0
        self.active_workers = 0
        self.workers_limit = 100 # Aumentato per saturazione estrema
        self.chunk_size = 1024 * 1024 # 1MB chunks
        self.session_timeout = 30
        
    def format_bytes(self, n):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if n < 1024: return f"{n:.2f} {unit}"
            n /= 1024

    async def download_worker(self, session, worker_id):
        self.active_workers += 1
        while self.is_running:
            url = random.choice(TEST_URLS)
            try:
                # Rotazione User-Agent per evitare rate limiting lato CDN
                headers = {
                    'User-Agent': f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(110,125)}.0.0.0 Safari/537.36',
                    'Accept-Encoding': 'identity', # Evita compressione CPU-intensive
                    'Connection': 'keep-alive'
                }
                async with session.get(url, timeout=self.session_timeout, headers=headers) as response:
                    if response.status != 200:
                        self.errors += 1
                        await asyncio.sleep(0.5)
                        continue
                    
                    # Lettura a pezzi grandi per massimizzare throughput
                    while self.is_running:
                        chunk = await response.content.read(self.chunk_size)
                        if not chunk: break
                        
                        chunk_len = len(chunk)
                        self.total_bytes += chunk_len
                        
                        if self.target_gb and (self.total_bytes / (1024**3)) >= self.target_gb:
                            self.is_running = False
                            break
            except:
                self.errors += 1
                await asyncio.sleep(0.2) # Breve pausa in caso di errore
        self.active_workers -= 1

    async def monitor(self):
        self.start_time = time.time()
        last_bytes = 0
        print(Fore.CYAN + "\n+" + "-"*75 + "+")
        print(f"| {Fore.YELLOW}GOD-MODE BANDWIDTH EATER {Fore.RED}v3.0{Fore.YELLOW} - SATURAZIONE TOTALE (NO-ARIA){Fore.CYAN}         |")
        print("+" + "-"*75 + "+" + Style.RESET_ALL)
        try:
            while self.is_running:
                await asyncio.sleep(1)
                now = time.time()
                delta_bytes = self.total_bytes - last_bytes
                speed = delta_bytes / 1.0 # 1 second interval
                
                if self.target_minutes and (now - self.start_time) >= (self.target_minutes * 60):
                    self.is_running = False
                    break
                
                # Barra di progresso se c'è un target GB
                progress_bar = ""
                if self.target_gb:
                    percent = min(100, (self.total_bytes / (self.target_gb * 1024**3)) * 100)
                    filled = int(percent / 5)
                    progress_bar = f" | [{Fore.GREEN}{'#'*filled}{Style.RESET_ALL}{'-'*(20-filled)}]"

                sys.stdout.write(f"\r| {Fore.GREEN}{self.format_bytes(self.total_bytes):>10}{Style.RESET_ALL} | {Fore.CYAN}{self.format_bytes(speed):>10}/s{Style.RESET_ALL} | Wrk: {self.active_workers:3} | Err: {self.errors:4} | T: {str(timedelta(seconds=int(now - self.start_time))):>8}{progress_bar} ")
                sys.stdout.flush()
                last_bytes = self.total_bytes
        except: pass
        finally: 
            self.is_running = False
            print("\n\n" + Fore.GREEN + "[!] Target raggiunto o interrotto." + Style.RESET_ALL)

    async def main(self):
        # ... (ASCII ART e input) ...

    async def main(self):
        print(Fore.RED + Style.BRIGHT + r"""
    ██╗   ██╗██╗     ████████╗██╗███╗   ███╗ █████╗ ████████╗███████╗
    ██║   ██║██║     ╚══██╔══╝██║████╗ ████║██╔══██╗╚══██╔══╝██╔════╝
    ██║   ██║██║        ██║   ██║██╔████╔██║███████║   ██║   █████╗  
    ██║   ██║██║        ██║   ██║██║╚██╔╝██║██╔══██║   ██║   ██╔══╝  
    ╚██████╔╝███████╗   ██║   ██║██║ ╚═╝ ██║██║  ██║   ██║   ███████╗
     ╚═════╝ ╚══════╝   ╚═╝   ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝   ╚═╝   ╚══════╝
    [!] VERSIONE DEFINITIVA - SENZA LIMITI - GOD MODE ATTIVO [!]
        """ + Style.RESET_ALL)
        try:
            print("1. Limite GB\n2. Limite Minuti\n3. Nessun limite")
            scelta = input("> ")
            if scelta == '1': self.target_gb = float(input("GB: "))
            elif scelta == '2': self.target_minutes = float(input("Minuti: "))
            
            # Connettore ottimizzato per saturazione estrema
            connector = aiohttp.TCPConnector(
                limit=500, 
                limit_per_host=100, 
                force_close=False, 
                enable_cleanup_closed=True,
                ttl_dns_cache=300
            )
            
            async with aiohttp.ClientSession(connector=connector) as session:
                workers = [self.download_worker(session, i) for i in range(self.workers_limit)]
                await asyncio.gather(self.monitor(), *workers)
        except KeyboardInterrupt: self.is_running = False

if __name__ == "__main__":
    eater = UltimateBandwidthEater()
    try: asyncio.run(eater.main())
    except: pass
