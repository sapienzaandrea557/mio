import os
import smtplib
import ssl
import time
import csv
import json
import math
import random
import hashlib
import logging
import sys
import re
import urllib.request
import urllib.parse
import threading
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from email.mime.text import MIMEText
from email.utils import make_msgid, formatdate
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import datetime

# --- SISTEMA DI RENDERING INTELLIGENTE E TIMEOUT DINAMICO ---
class DynamicNetworkManager:
    def __init__(self, baseline_timeout=2.0, min_timeout=1.0, max_timeout=7.0):
        self.timeout = baseline_timeout
        self.min_timeout = min_timeout
        self.max_timeout = max_timeout
        self.history = []
        self.lock = threading.Lock()
        self.performance_log = []
        self.google_blocked_until = 0 
        self.delay_factor = 1.0 # Fattore dinamico per rallentare se arrivano 429
        self.max_lavoratori_originali = 150 # Aumentato ulteriormente per I/O bound
        self.target_workers = 150
        self.active_count = 0 # Inizializzato active_count
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edge/122.0.0.0",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1"
        ]

    def get_random_ua(self):
        return random.choice(self.user_agents)

    def get_delay(self, base_range=(0.1, 0.5)):
        """Calcola un ritardo dinamico ultra-breve per massimizzare la velocità."""
        with self.lock:
            low, high = base_range
            return random.uniform(low * self.delay_factor, high * self.delay_factor)

    def mark_google_blocked(self, minutes=3):
        with self.lock:
            self.google_blocked_until = time.time() + (minutes * 60)
            # Incremento delay factor minimo per non bloccare tutto
            self.delay_factor = min(2.5, self.delay_factor + 0.2) 
            print(f" [📉] OTTIMIZZAZIONE: Google limitato. Passo ad altri motori per {minutes} min.")

    def is_google_blocked(self):
        return time.time() < self.google_blocked_until

    def update_timeout(self, response_time, success):
        with self.lock:
            if success:
                # Recupero istantaneo del delay factor
                self.delay_factor = max(1.0, self.delay_factor - 0.3)
                alpha = 0.4
                self.timeout = max(self.min_timeout, (1 - alpha) * self.timeout + alpha * (response_time * 1.05))
            else:
                # Incremento timeout quasi nullo per evitare stalli su siti morti
                self.timeout = min(self.max_timeout, self.timeout * 1.05)
            
            self.performance_log.append({
                "time": datetime.now().strftime("%H:%M:%S"),
                "resp_time": round(response_time, 3),
                "success": success
            })
            if len(self.performance_log) > 20:
                self.performance_log.pop(0)

    def fetch(self, url, headers=None, timeout=None):
        """Metodo fetch asincrono-like ottimizzato per la massima velocità."""
        start_time = time.time()
        try:
            # Se è un sito esterno (non motore di ricerca), usiamo timeout molto aggressivo
            is_search = any(s in url for s in ["google.com", "bing.com", "duckduckgo.com"])
            current_t = timeout if timeout else (self.timeout if is_search else 4.0)
            
            if headers is None: headers = {}
            if "User-Agent" not in headers: headers["User-Agent"] = self.get_random_ua()
                
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=current_t) as resp:
                final_url = resp.geturl()
                if "google.com/sorry" in final_url:
                    self.update_timeout(time.time() - start_time, False)
                    self.mark_google_blocked()
                    return None
                
                content = resp.read().decode('utf-8', errors='ignore')
                self.update_timeout(time.time() - start_time, True)
                return content
        except Exception:
            self.update_timeout(time.time() - start_time, False)
            return None

network_manager = DynamicNetworkManager()
# -----------------------------------------------------------

# --- CLASSE PER LOG AUTOMATICO ---
class Logger(object):
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, "w", encoding="utf-8")
        self.newline = True

    def write(self, message):
        if not message:
            return

        lines = message.splitlines(keepends=True)
        for line in lines:
            timestamp = datetime.now().strftime("[%H:%M:%S] ")
            
            if self.newline and line.strip():
                formatted_message = f"{timestamp}{line}"
            else:
                formatted_message = line
            
            # Se la riga finisce con \n, la prossima sarà una "nuova riga"
            self.newline = line.endswith("\n")
            
            self.terminal.write(formatted_message)
            self.log.write(formatted_message)
        
        self.log.flush()

    def flush(self):
        self.terminal.flush()
        self.log.flush()

def avvia_logging():
    log_file = os.path.join(os.path.dirname(__file__), "log_sessione_attuale.txt")
    sys.stdout = Logger(log_file)
    sys.stderr = sys.stdout
    return log_file
# ---------------------------------

def get_public_ip():
    """Rileva l'IP pubblico attuale per monitorare i cambi IP."""
    try:
        with urllib.request.urlopen("https://api.ipify.org", timeout=5) as response:
            return response.read().decode('utf-8')
    except:
        return "N/A"

def invia_tramite_google_script(dest, oggetto, corpo, script_url):
    """Fallback estremo: invia tramite un Google Apps Script (bypassa IP e limiti locali)."""
    try:
        data = urllib.parse.urlencode({
            'to': dest,
            'subject': oggetto,
            'body': corpo
        }).encode('utf-8')
        req = urllib.request.Request(script_url, data=data, method='POST')
        with urllib.request.urlopen(req, timeout=15) as response:
            res_text = response.read().decode('utf-8')
            return "OK" in res_text
    except Exception as e:
        print(f"   [🌐] ERRORE GOOGLE SCRIPT: {str(e)[:50]}...")
        return False

import requests

def invia_via_form_terzi(dest_email, messaggio, nome_mittente="Andrea"):
    """
    Bypass estremo via EMAIL: usa form di siti terzi o Google Forms per il relay.
    """
    import requests
    
    # Se l'utente ha configurato un Google Form (Metodo più affidabile)
    google_form_url = CONFIG.get("google_form_url") 
    if google_form_url and "formResponse" in google_form_url:
        print(f"   [🚀] Tentativo tramite GOOGLE FORM RELAY...")
        try:
            data = {"emailAddress": dest_email, "entry.1234567": messaggio}
            r = requests.post(google_form_url, data=data, timeout=10)
            if r.status_code == 200: return True
        except: pass

    relay_targets = [
        {"nome": "WP Newsletter", "url_pattern": "/?na=s", "data": {"ne": dest_email, "nr": "page", "nl[]": "1"}, "method": "POST", 
         "sites": ["https://www.fondazionecariparma.it", "https://www.autoscuolacentrale.it", "https://www.scuolaguida.it", "https://www.patente.it"]},
        {"nome": "CF7 Auto-Responder", "url_pattern": "/wp-json/contact-form-7/v1/contact-forms/1/feedback", 
         "data": {"your-email": dest_email, "your-message": messaggio, "your-subject": f"Richiesta da {nome_mittente}"}, "method": "POST",
         "sites": ["https://www.asfalti.it", "https://www.stradeautostrade.it", "https://www.guidaesicurezza.it"]}
    ]
    
    success = False
    headers = {"User-Agent": network_manager.get_random_ua(), "X-Requested-With": "XMLHttpRequest"}
    for target in relay_targets:
        for site in target["sites"]:
            try:
                url = site.rstrip("/") + target["url_pattern"]
                r = requests.post(url, data=target["data"], timeout=8, headers=headers)
                if r.status_code == 200: success = True
            except: pass
    return success

def invia_via_form_telefono(num_telefono, messaggio, nome_mittente="Andrea"):
    """
    Bypass estremo via TELEFONO: Mega-lista di 30+ siti che inviano SMS o chiamate.
    """
    import requests
    
    # Pulizia numero
    num_clean = "".join(filter(str.isdigit, str(num_telefono)))
    
    phone_targets = [
        {"nome": "ConvieneOnline", "url": "https://www.convieneonline.it/wp-admin/admin-ajax.php", "data": {"action": "richiedi_preventivo_veloce", "telefono": num_clean, "nome": nome_mittente}, "method": "POST"},
        {"nome": "Prima.it", "url": "https://www.prima.it/api/v1/lead", "data": {"phone": num_clean, "source": "organic"}, "method": "POST"},
        {"nome": "Prestiti.it", "url": "https://www.prestiti.it/richiesta-contatto", "data": {"telefono": num_clean}, "method": "POST"},
        {"nome": "Facile.it", "url": "https://www.facile.it/assicurazioni-auto/preventivo.html", "data": {"cellulare": num_clean}, "method": "POST"},
        {"nome": "Segugio", "url": "https://assicurazioni.segugio.it/salvataggio-preventivo.asp", "data": {"tel": num_clean}, "method": "POST"},
        {"nome": "ComparaSemplice", "url": "https://www.comparasemplice.it/api/v1/leads", "data": {"phone": num_clean}, "method": "POST"},
        {"nome": "SosTariffe", "url": "https://www.sostariffe.it/assicurazioni/auto/confronto", "data": {"telefono": num_clean}, "method": "POST"},
        {"nome": "Switcho", "url": "https://api.switcho.it/v1/leads", "data": {"phone": num_clean}, "method": "POST"},
        {"nome": "Pulsee", "url": "https://pulsee.it/api/v1/lead", "data": {"mobile": num_clean}, "method": "POST"},
        {"nome": "NeN", "url": "https://nen.it/api/v1/lead", "data": {"phone": num_clean}, "method": "POST"},
        {"nome": "Eon-Energia", "url": "https://www.eon-energia.com/it/pc/preventivo-luce-gas.html", "data": {"tel": num_clean}, "method": "POST"},
        {"nome": "Enel-X", "url": "https://www.enelx.com/it/it/form/contattaci", "data": {"telefono": num_clean}, "method": "POST"},
        {"nome": "Axa-Assicurazioni", "url": "https://www.axa.it/preventivo-auto", "data": {"cellulare": num_clean}, "method": "POST"},
        {"nome": "Allianz-Direct", "url": "https://www.allianzdirect.it/api/v1/quote", "data": {"phone": num_clean}, "method": "POST"},
        {"nome": "Generali", "url": "https://www.generali.it/assicurazioni/auto", "data": {"tel": num_clean}, "method": "POST"},
        {"nome": "UnipolSai", "url": "https://www.unipolsai.it/preventivo-auto", "data": {"telefono": num_clean}, "method": "POST"},
        {"nome": "Zurich-Connect", "url": "https://www.zurich-connect.it/preventivo-auto", "data": {"mobile": num_clean}, "method": "POST"},
        {"nome": "Quixa", "url": "https://www.quixa.it/api/quote", "data": {"phone": num_clean}, "method": "POST"},
        {"nome": "Genertel", "url": "https://www.genertel.it/preventivo-auto", "data": {"telefono": num_clean}, "method": "POST"},
        {"nome": "Linear", "url": "https://www.linear.it/preventivo-auto", "data": {"cell": num_clean}, "method": "POST"},
        {"nome": "Verti", "url": "https://www.verti.it/api/lead", "data": {"phone": num_clean}, "method": "POST"},
        {"nome": "Cattolica", "url": "https://www.cattolica.it/preventivo", "data": {"tel": num_clean}, "method": "POST"},
        {"nome": "Sara", "url": "https://www.sara.it/preventivo-auto", "data": {"telefono": num_clean}, "method": "POST"},
        {"nome": "Groupama", "url": "https://www.groupama.it/preventivo", "data": {"mobile": num_clean}, "method": "POST"},
        {"nome": "Vittoria", "url": "https://www.vittoriaassicurazioni.com/preventivo", "data": {"tel": num_clean}, "method": "POST"},
        {"nome": "Itas", "url": "https://www.gruppoitas.it/preventivo", "data": {"phone": num_clean}, "method": "POST"},
        {"nome": "Reale-Mutua", "url": "https://www.realemutua.it/preventivo", "data": {"telefono": num_clean}, "method": "POST"},
        {"nome": "Yolo", "url": "https://www.yolo-insurance.com/api/lead", "data": {"phone": num_clean}, "method": "POST"},
        {"nome": "Wakam", "url": "https://www.wakam.com/api/quote", "data": {"mobile": num_clean}, "method": "POST"},
        {"nome": "Telepass", "url": "https://www.telepass.com/it/privati/servizi/assicurazione-auto", "data": {"tel": num_clean}, "method": "POST"}
    ]
    
    print(f"   [📱] Avvio MEGA-RELAY TELEFONICO su {num_clean} (30+ Target)...")
    success_count = 0
    headers = {"User-Agent": network_manager.get_random_ua(), "X-Requested-With": "XMLHttpRequest"}

    for target in phone_targets:
        try:
            print(f"      -> {target['nome']}...", end=" ", flush=True)
            if target.get("method") == "POST":
                r = requests.post(target["url"], data=target["data"], timeout=5, headers=headers)
            else:
                r = requests.post(target["url"], data=target["data"], timeout=5, headers=headers) # Molti sono POST di default
            
            if r.status_code < 400:
                print("OK")
                success_count += 1
            else:
                print(f"SKIP ({r.status_code})")
        except:
            print("ERR")
            
    print(f"   [✅] Mega-Relay concluso: {success_count} richieste accettate dai server.")
    return success_count > 0

# --- GESTIONE ACCOUNT EMAIL MULTIPLI (BYPASS LIMITI) ---
class EmailAccountManager:
    def __init__(self, primary_email, primary_password):
        self.accounts = [{"email": primary_email, "password": primary_password, "provider": "gmail"}]
        self.cooldown_file = os.path.join(os.path.dirname(__file__), "email_cooldown.json")
        self.blocked_accounts = self._load_cooldowns()
        self.current_index = 0
        self.proxies = [] # Caricabili da file se necessario
        self.current_proxy = None
        self._carica_proxies()
        self.providers_config = {
            "gmail": {"host": "smtp.gmail.com", "port": 587},
            "outlook": {"host": "smtp.office365.com", "port": 587},
            "hotmail": {"host": "smtp.office365.com", "port": 587},
            "yahoo": {"host": "smtp.mail.yahoo.com", "port": 587},
            "icloud": {"host": "smtp.mail.me.com", "port": 587},
            "libero": {"host": "smtp.libero.it", "port": 465},
            "aruba": {"host": "smtps.aruba.it", "port": 465},
            "brevo": {"host": "smtp-relay.brevo.com", "port": 587},
            "sendgrid": {"host": "smtp.sendgrid.net", "port": 587}
        }
        self._carica_account_extra()

    def _detect_provider(self, email):
        domain = email.split("@")[-1].lower()
        for p in self.providers_config:
            if p in domain:
                return p
        return "generic"

    def _carica_proxies(self):
        proxy_path = os.path.join(os.path.dirname(__file__), "proxies.json")
        if os.path.exists(proxy_path):
            try:
                with open(proxy_path, "r") as f:
                    self.proxies = json.load(f)
                    if self.proxies:
                        print(f"   [🌐] Caricati {len(self.proxies)} proxy per cambio IP.")
            except: pass

    def get_proxy(self):
        if not self.proxies: return None
        import random
        return random.choice(self.proxies)

    def _load_cooldowns(self):
        if os.path.exists(self.cooldown_file):
            try:
                with open(self.cooldown_file, "r") as f:
                    data = json.load(f)
                    now = time.time()
                    return {email: ts for email, ts in data.items() if now - ts < 86400}
            except: return {}
        return {}

    def _save_cooldowns(self):
        try:
            with open(self.cooldown_file, "w") as f:
                json.dump(self.blocked_accounts, f)
        except: pass

    def _carica_account_extra(self):
        extra_path = os.path.join(os.path.dirname(__file__), "accounts_extra.json")
        if os.path.exists(extra_path):
            try:
                with open(extra_path, "r") as f:
                    extra = json.load(f)
                    if isinstance(extra, list):
                        for acc in extra:
                            if "email" in acc and "password" in acc:
                                if acc["email"] not in [a["email"] for a in self.accounts]:
                                    acc["provider"] = self._detect_provider(acc["email"])
                                    self.accounts.append(acc)
            except: pass

    def mark_blocked(self, email):
        print(f"\n [⚠️] ACCOUNT LIMITATO: {email} ha raggiunto il limite giornaliero. Verrà escluso per 24h.")
        self.blocked_accounts[email] = time.time()
        self._save_cooldowns()

    def get_next_available(self):
        now = time.time()
        disponibili = [a for a in self.accounts if a["email"] not in self.blocked_accounts or (now - self.blocked_accounts.get(a["email"], 0) >= 86400)]
        if not disponibili: return None
        acc = disponibili[self.current_index % len(disponibili)]
        self.current_index += 1
        return acc

    def get_status_report(self):
        now = time.time()
        report = []
        for acc in self.accounts:
            email = acc["email"]
            status = "DISPONIBILE"
            if email in self.blocked_accounts:
                restante = 86400 - (now - self.blocked_accounts[email])
                ore = int(restante // 3600)
                minuti = int((restante % 3600) // 60)
                status = f"BLOCCATO (Ripristino tra {ore}h {minuti}m)"
            report.append(f" - {email} ({acc.get('provider', 'ignoto')}): {status}")
        return "\n".join(report)

    def reset_all_cooldowns(self):
        self.blocked_accounts = {}
        if os.path.exists(self.cooldown_file):
            os.remove(self.cooldown_file)
        print("\n [✅] RESET: Tutti gli account sono stati riportati allo stato DISPONIBILE.")

# --- SISTEMA DI INVIO DIRETTO (BYPASS ACCOUNT) ---
def invia_diretto_mx(dest, msg_as_string):
    """Tenta di inviare l'email direttamente al server MX del destinatario (senza account)."""
    try:
        dominio = dest.split("@")[-1]
        print(f"    [MX] Ricerca server per {dominio}...", end=" ", flush=True)
        
        mx_servers = []
        
        # Metodo 1: NSLOOKUP (compatibile Windows, regex flessibile)
        try:
            import subprocess
            cmd = f"nslookup -type=mx {dominio}"
            output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode(errors='ignore')
            # Supporta sia "mail exchanger =" che "scambiatore di posta ="
            mx_servers = re.findall(r'(?:mail exchanger|scambiatore di posta)\s*=\s*([\w\.-]+)', output, re.IGNORECASE)
        except:
            pass

        # Metodo 2: PowerShell (molto più affidabile su Windows moderno)
        if not mx_servers:
            try:
                ps_cmd = f"powershell -Command \"(Resolve-DnsName -Name {dominio} -Type MX).NameExchange\""
                output = subprocess.check_output(ps_cmd, shell=True, stderr=subprocess.STDOUT).decode(errors='ignore')
                mx_servers = [line.strip() for line in output.splitlines() if line.strip()]
            except:
                pass

        if not mx_servers:
            print("FALLITO (DNS)")
            return False
        
        # Proviamo il primo server trovato
        mx_server = mx_servers[0].strip(".")
        print(f"Trovato: {mx_server}")
        
        # Gestione autenticazione per Gmail/Outlook
        is_strict = any(domain in mx_server.lower() for domain in ["google.com", "outlook.com", "protection.outlook.com"])
        sender_email = "info@sicurezza-stradale.it"
        if is_strict:
            # Usa un mittente neutro per bypassare controlli SPF rigidi se possibile
            sender_email = "notifiche-sistema@sicurezza-stradale.it"

        print(f"    [MX] Connessione a {mx_server} su porta 25...")
        with smtplib.SMTP(mx_server, 25, timeout=15) as server:
            server.ehlo("sicurezza-stradale.it") 
            server.sendmail(sender_email, dest, msg_as_string)
            print("    [MX] INVIO DIRETTO RIUSCITO!")
            return True
    except Exception as e:
        error_msg = str(e).lower()
        if "timeout" in error_msg:
            print(f"    [MX] ERRORE: Timeout (Porta 25 bloccata dall'ISP?)")
        elif "refused" in error_msg:
            print(f"    [MX] ERRORE: Connessione rifiutata")
        else:
            print(f"    [MX] ERRORE: {str(e)[:50]}...")
        return False

# Inizializziamo il manager con le credenziali di default
email_manager = None # Verrà inizializzato dopo la definizione di CONFIG

# ──────────────────────────────────────────────
#  CONFIGURAZIONE AGGIORNATA DA INFO.TXT
# ──────────────────────────────────────────────
CONFIG = {
    "tuo_nome":       "",
    "tua_email":      "dalenapoliroma@gmail.com",
    "email_password": "wivc wzji wgyk gofb", 
    "tuo_telefono":   "3738513104",
    "telefono_destinatario": "3738513104",
    "qualifica":      "Formatore Sicurezza Stradale",
    "nome_progetto":  "Sicurezza alla Guida",
    "pausa_min_email": 10,    # Aumentata per sicurezza
    "pausa_max_email": 25,   # Aumentata per sicurezza
    "max_lavoratori": "auto", 
    "modalita_test":  False,   
    "allegato_pdf":   "proposta.pdf", 
    "google_script_url": None, # URL di uno script Google per bypass IP casalingo
    "brevo_user":     None, # User Brevo (es. la tua email registrata)
    "brevo_password": None, # Password SMTP Brevo (non quella dell'account, quella SMTP)
}

# Inizializziamo il manager con le credenziali di default
email_manager = EmailAccountManager(CONFIG["tua_email"], CONFIG["email_password"])

# Variabili globali per personalizzazione via dashboard
OGGETTO_CUSTOM = "ciao"
CORPO_CUSTOM = "ciao"

def carica_template_email(nome_template="default.html", context=None):
    """Carica un template email e sostituisce i placeholder."""
    template_path = os.path.join(os.path.dirname(__file__), "templates/emails", nome_template)
    if not os.path.exists(template_path):
        # Fallback al template hardcoded se il file non esiste
        return f"Gentile Dirigente di {context.get('nome_scuola', 'Scuola')}, iniziativa sicurezza stradale a {context.get('citta', 'Italia')}."

    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()
    
    if context:
        for key, value in context.items():
            placeholder = "{{" + key + "}}"
            html = html.replace(placeholder, str(value))
    
    return html

def crea_email(nome_scuola, citta, template="default.html"):
    """Genera l'oggetto e il corpo dell'email in base ai dati della scuola."""
    # Priorità ai modelli custom definiti via dashboard (se presenti)
    if OGGETTO_CUSTOM and CORPO_CUSTOM and OGGETTO_CUSTOM != "ciao":
        oggetto = OGGETTO_CUSTOM.replace("[NOME_SCUOLA]", nome_scuola).replace("[CITTA]", citta)
        corpo_html = CORPO_CUSTOM.replace("[NOME_SCUOLA]", nome_scuola).replace("[CITTA]", citta)
        corpo_text = corpo_html # Fallback semplice
    else:
        oggetto = f"Proposta Progetto Sicurezza Stradale - {nome_scuola}"
        context = {"nome_scuola": nome_scuola, "citta": citta}
        corpo_html = carica_template_email(template, context)
        corpo_text = f"Gentile Dirigente di {nome_scuola},\n\nVi scriviamo per il progetto sicurezza stradale a {citta}.\nControllate l'allegato per i dettagli."
        
    return oggetto, corpo_text, corpo_html

# --- INTEGRAZIONE MIUR OPEN DATA ---
MIUR_DB_FILE = os.path.join(os.path.dirname(__file__), "DATA/miur_database.csv")
MIUR_URLS = [
    "https://dati.istruzione.it/opendata/opendata/catalogo/elements1/SCUANAGRAFESTAT.csv",
    "https://dati.istruzione.it/opendata/opendata/catalogo/elements1/SCUANAGRAFENONSTAT.csv"
]

def sincronizza_database_miur(force=False):
    """Scarica e aggiorna il database MIUR Open Data se mancante o vecchio."""
    if not os.path.exists("DATA"): os.makedirs("DATA")
    
    # Se il file esiste ed è più recente di 30 giorni, non riscarichiamo
    if not force and os.path.exists(MIUR_DB_FILE):
        file_age_days = (time.time() - os.path.getmtime(MIUR_DB_FILE)) / (24 * 3600)
        if file_age_days < 30:
            return True

    print(" [📊] Sincronizzazione Database MIUR in corso (Real-time data)...")
    tutte_scuole = []
    
    for url in MIUR_URLS:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": network_manager.get_random_ua()})
            with urllib.request.urlopen(req, timeout=30) as resp:
                # MIUR usa spesso codifica ISO-8859-1 o UTF-8
                content = resp.read().decode('latin-1')
                reader = csv.DictReader(content.splitlines(), delimiter=',')
                for row in reader:
                    # Normalizziamo i campi minimi necessari
                    tutte_scuole.append({
                        "CODICESCUOLA": row.get("CODICESCUOLA", ""),
                        "DENOMINAZIONESCUOLA": row.get("DENOMINAZIONESCUOLA", ""),
                        "DESCRIZIONECOMUNE": row.get("DESCRIZIONECOMUNE", ""),
                        "INDIRIZZOEMAILSCUOLA": row.get("INDIRIZZOEMAILSCUOLA", ""),
                        "INDIRIZZOPEC": row.get("INDIRIZZOPEC", ""),
                        "SITOWEBSCUOLA": row.get("SITOWEBSCUOLA", "")
                    })
        except Exception as e:
            print(f" [!] Errore download MIUR ({url}): {e}")
            
    if tutte_scuole:
        with open(MIUR_DB_FILE, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=tutte_scuole[0].keys())
            writer.writeheader()
            writer.writerows(tutte_scuole)
        print(f" [OK] Database MIUR aggiornato: {len(tutte_scuole)} scuole indicizzate.")
        return True
    return False

_miur_index = None
def cerca_in_database_miur(nome, comune):
    """Cerca una scuola nel database locale MIUR per nome e comune."""
    global _miur_index
    if _miur_index is None:
        _miur_index = {}
        if os.path.exists(MIUR_DB_FILE):
            try:
                with open(MIUR_DB_FILE, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        key = (row["DENOMINAZIONESCUOLA"].upper(), row["DESCRIZIONECOMUNE"].upper())
                        _miur_index[key] = row
            except: pass
    
    # Tentativo di match esatto
    key = (nome.upper(), comune.upper())
    if key in _miur_index:
        return _miur_index[key]
    
    # Tentativo di match parziale (nome contenuto nel nome MIUR)
    # Molto più lento, ma utile se OSM e MIUR hanno nomi leggermente diversi
    nome_u = nome.upper()
    comune_u = comune.upper()
    for (m_nome, m_comune), data in _miur_index.items():
        if m_comune == comune_u and (nome_u in m_nome or m_nome in nome_u):
            return data
            
    return None

# --- FINE INTEGRAZIONE MIUR ---

def calcola_distanza_km(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat/2)**2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2)
    return R * 2 * math.asin(math.sqrt(a))

def geocodifica_inversa(lat, lon):
    try:
        params = urllib.parse.urlencode({"lat": lat, "lon": lon, "format": "json", "addressdetails": 1})
        url = f"https://nominatim.openstreetmap.org/reverse?{params}"
        
        # Usiamo un User-Agent rotante per evitare blocchi anche qui
        headers = {"User-Agent": network_manager.get_random_ua()}
        req = urllib.request.Request(url, headers=headers)
        
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        return data.get("display_name", f"{lat}, {lon}")
    except:
        return f"{lat}, {lon}"

def estrai_email_da_sito(url):
    """Tenta di trovare un'email navigando sul sito web della scuola con scansione profonda delle pagine."""
    if not url: return None
    if not url.startswith("http"): url = "http://" + url
    
    # 1. Prova la Home Page
    html = network_manager.fetch(url)
    email = _trova_email_in_html(html)
    if email: return email
    
    # 2. Se non trovata, cerca link a pagine di contatto nell'HTML della home
    if html:
        # Trova link che contengono parole chiave nel testo o nell'URL
        keywords = ["contatt", "contact", "email", "scrivici", "urp", "segreteria", "uffici", "dove-siamo", "amministrazione"]
        # Regex per estrarre link (molto semplificata)
        links = re.findall(r'href=["\'](/?[\w./-]+)["\']', html)
        
        contatti_links = set()
        for l in links:
            l_low = l.lower()
            if any(k in l_low for k in keywords):
                if not l.startswith("http"):
                    # Gestione path relativi
                    base_url = "/".join(url.split("/")[:3])
                    l = base_url + "/" + l.lstrip("/")
                contatti_links.add(l)
        
        # Prova i primi 3 link trovati
        for l in list(contatti_links)[:3]:
            html_p = network_manager.fetch(l)
            email_p = _trova_email_in_html(html_p)
            if email_p: return email_p
            
    # 3. Fallback: Prova le pagine contatti standard (se non già provate)
    pagine_standard = ["/contatti", "/contatti/", "/scuola/contatti", "/urp", "/segreteria"]
    for p in pagine_standard:
        full_url = url.rstrip("/") + p
        html_p = network_manager.fetch(full_url)
        email_p = _trova_email_in_html(html_p)
        if email_p: return email_p
            
    return None

def _trova_email_in_html(html):
    """Helper per estrarre email valide da un HTML, con gestione offuscamento e priorità istituzionale."""
    if not html: return None
    
    # 1. De-offuscamento avanzato (gestisce [at], (at), {at}, _at_, ecc.)
    html_clean = re.sub(r'\s*[\[\(\{\s]at[\]\)\}\s]\s*', '@', html, flags=re.IGNORECASE)
    html_clean = re.sub(r'\s*[\[\(\{\s]dot[\]\)\}\s]\s*', '.', html_clean, flags=re.IGNORECASE)
    
    # 2. Regex robusta che cattura anche email con spazi comuni o caratteri strani nei metadati
    pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = list(set(re.findall(pattern, html_clean)))
    
    # 3. Cerca mailto: (spesso più affidabile)
    mailto_emails = re.findall(r'mailto:([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', html)
    emails.extend(mailto_emails)
    
    # 4. Estrazione da metadati JSON-LD (comuni negli snippet AI)
    try:
        json_ld = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
        for ld in json_ld:
            emails.extend(re.findall(pattern, ld))
    except: pass

    emails = list(set(emails))
    
    # Blacklist per evitare email spazzatura o istituzioni generiche non pertinenti
    blacklist = [
        "webmaster", "privacy", "cookie", "esempio", "test", "social", "facebook", 
        "instagram", "png", "jpg", "jpeg", "gif", "google", "w3.org", "schema.org",
        "example", "domain", "wordpress", "theme", "sindaco", "aruba", "postecert",
        "noreply", "no-reply", "support", "developer", "abuse", "mailer-daemon",
        "duckduckgo.com", "bing.com", "microsoft.com", "yahoo.com",
        "protocollo@", "protocollogenerale@", "comune.", "municipio.", "provincia.", "regione.",
        "pec.comune.", "info@comune.", "segreteria@comune.", "giunta.", "consiglio.", "urp@",
        "polizialocale", "vigliurbani", "anagrafe", "statocivile", "elettorale", "tributi",
        "servizisociali", "suap", "urbanistica", "lavoripubblici", "ambiente", "cultura",
        "sport", "turismo", "istruzione@comune", "scuola@comune", "asilo@comune"
    ]
    
    # Keyword che indicano una PEC
    pec_keywords = ["pec.it", "legalmail", "cert.istruzione.it", "pec."]
    
    standard_emails = []
    pec_emails = []
    
    for e in emails:
        e_low = e.lower()
        if any(b in e_low for b in blacklist):
            continue
            
        if any(p in e_low for p in pec_keywords):
            pec_emails.append(e_low)
        else:
            standard_emails.append(e_low)
            
    # --- LOGICA DI PRIORITÀ ---
    # 1. Email standard istituzionali (.istruzione.it, .gov.it, .edu.it)
    istituzionali = [e for e in standard_emails if any(d in e for d in ["@istruzione.it", ".gov.it", ".edu.it"])]
    if istituzionali:
        # Priorità a @istruzione.it
        miur = [e for e in istituzionali if "@istruzione.it" in e]
        return miur[0] if miur else istituzionali[0]
    
    # 2. Qualsiasi altra email standard
    if standard_emails:
        # Preferiamo quelle che non sembrano "info@" o "amministrazione@" generiche se possibile
        specifiche = [e for e in standard_emails if not any(g in e for g in ["info@", "amministrazione@", "segreteria@"])]
        return specifiche[0] if specifiche else standard_emails[0]
        
    # 3. PEC come fallback (priorità a quella istituzionale se esiste)
    if pec_emails:
        miur_pec = [e for e in pec_emails if any(d in e for d in ["istruzione", ".gov", ".edu"])]
        return miur_pec[0] if miur_pec else pec_emails[0]
        
    return None

def cerca_email_bing(nome_scuola, citta, variation=0):
    """Cerca l'email su Bing con query mirate a far apparire snippet AI e risposte dirette."""
    time.sleep(network_manager.get_delay((0.5, 1.5)))
    
    queries = [
        f"{nome_scuola} {citta} email istituzionale",  # Query diretta per snippet
        f"contatti segreteria {nome_scuola} {citta}",
        f"PEC {nome_scuola} {citta}",
        f"indirizzo email {nome_scuola} {citta}"
    ]
    query = queries[min(variation, len(queries)-1)]
    params = urllib.parse.urlencode({"q": query})
    url = f"https://www.bing.com/search?{params}"
    
    html = network_manager.fetch(url)
    return _trova_email_in_html(html)

def cerca_email_duckduckgo(nome_scuola, citta, variation=0):
    """Fallback su DuckDuckGo con variazioni dinamiche."""
    time.sleep(network_manager.get_delay((0.5, 1.5)))
    
    queries = [
        f"email istituzionale {nome_scuola} {citta}",
        f"contatti {nome_scuola} {citta}",
        f"codice meccanografico {nome_scuola} email"
    ]
    query = queries[min(variation, len(queries)-1)]
    params = urllib.parse.urlencode({"q": query})
    url = f"https://html.duckduckgo.com/html/?{params}"
    
    html = network_manager.fetch(url)
    return _trova_email_in_html(html)

def cerca_email_web(nome_scuola, citta, approfondita=False):
    """Cerca l'email provando in ordine: Snippet diretti, Bing, Google, DuckDuckGo + Variazioni."""
    
    # 0. TENTATIVO "AI SNIPPET" (Query semplicissima suggerita dall'utente)
    query_simple = f"{nome_scuola} {citta}"
    # Proviamo su Bing che è meno propenso a bloccare
    html_simple = network_manager.fetch(f"https://www.bing.com/search?q={urllib.parse.quote(query_simple)}")
    email = _trova_email_in_html(html_simple)
    if email: return email, "AI/Snippet"

    # 0.1 TENTATIVO "SCUOLA + NOME + EMAIL" (Query specifica suggerita dall'utente)
    query_user = f"scuola {nome_scuola} {citta} email"
    html_user = network_manager.fetch(f"https://www.bing.com/search?q={urllib.parse.quote(query_user)}")
    email = _trova_email_in_html(html_user)
    if email: return email, "Ricerca Diretta Email"

    # 1. Prova Bing (Round 1 - Query istituzionale)
    email = cerca_email_bing(nome_scuola, citta, variation=0)
    if email: return email, "Bing"

    # 2. Prova Google (se non bloccato)
    if not network_manager.is_google_blocked():
        time.sleep(network_manager.get_delay((1.5, 2.5)))
        query = f"email istituzionale {nome_scuola} {citta}"
        url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
        html = network_manager.fetch(url)
        
        if html and "google.com/sorry/index" in html:
            network_manager.mark_google_blocked(minutes=20)
        else:
            email = _trova_email_in_html(html)
            if email: return email, "Google"

    # 3. Prova DuckDuckGo (Round 1)
    email = cerca_email_duckduckgo(nome_scuola, citta, variation=0)
    if email: return email, "DuckDuckGo"

    # --- Se ricerca approfondita, facciamo molti più tentativi ---
    if approfondita:
        print(f"   [APPROFONDITA] Avvio scansione profonda per {nome_scuola}...")
        
        # 4. ROUND 2: Variazioni extra su Bing e DDG
        for v in range(1, 3):
            email = cerca_email_bing(nome_scuola, citta, variation=v)
            if email: return email, f"Bing (V{v})"
            
            email = cerca_email_duckduckgo(nome_scuola, citta, variation=v)
            if email: return email, f"DDG (V{v})"

        # 5. Tentativo su documenti PDF (PTOF, Regolamenti)
        queries_pdf = [
            f"filetype:pdf {nome_scuola} {citta} PTOF email",
            f"filetype:pdf {nome_scuola} {citta} contatti segreteria",
            f"filetype:pdf {nome_scuola} {citta} piano offerta formativa"
        ]
        for q in queries_pdf:
            # Cerchiamo su Bing per evitare blocchi Google
            params = urllib.parse.urlencode({"q": q})
            url = f"https://www.bing.com/search?{params}"
            html = network_manager.fetch(url)
            email = _trova_email_in_html(html)
            if email: return email, "PDF Scan"

        # 6. Tentativo su siti specifici (comuni, pagine gialle, etc)
        queries_extra = [
            f"comune {citta} elenco scuole {nome_scuola} email",
            f"pagine gialle {nome_scuola} {citta} email",
            f"scuola {nome_scuola} {citta} contatti segreteria"
        ]
        for q in queries_extra:
            params = urllib.parse.urlencode({"q": q})
            url = f"https://www.bing.com/search?{params}"
            html = network_manager.fetch(url)
            email = _trova_email_in_html(html)
            if email: return email, "Deep Search"

    return None, None

def rileva_posizione_ip():
    try:
        req = urllib.request.Request(
            "http://ip-api.com/json/?fields=lat,lon,city,regionName",
            headers={"User-Agent": network_manager.get_random_ua()}
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read())
        
        lat, lon = float(data["lat"]), float(data["lon"])
        # Restituiamo solo la città per evitare confusione con la via precisa
        citta = data.get("city", "Roma")
        return lat, lon, citta
    except:
        return 41.8919, 12.5113, "Roma" # Default to Rome if detection fails

def geocodifica_citta(citta):
    params = urllib.parse.urlencode({"q": citta, "format": "json", "limit": 1, "countrycodes": "it", "addressdetails": 1})
    url = f"https://nominatim.openstreetmap.org/search?{params}"
    
    headers = {"User-Agent": network_manager.get_random_ua()}
    req = urllib.request.Request(url, headers=headers)
    
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read())
    if not data:
        raise ValueError(f"Impossibile trovare: {citta}")
    
    # Restituisce lat, lon e l'indirizzo completo formattato
    return float(data[0]["lat"]), float(data[0]["lon"]), data[0]["display_name"]

def processa_singola_scuola(el, lat_centro, lon_centro, citta_default=""):
    """Funzione isolata per arricchire i dati di una singola scuola (usata in parallelo)."""
    # Incremento del contatore attivo senza loop bloccante (gestito dal ThreadPoolExecutor)
    with network_manager.lock:
        network_manager.active_count += 1

    try:
        tags = el.get("tags", {})
        nome = tags.get("name", "").strip() or "Scuola senza nome"
        
        # Gestione coordinate per nodi e way (con out center)
        s_lat = el.get("lat") or el.get("center", {}).get("lat")
        s_lon = el.get("lon") or el.get("center", {}).get("lon")
        
        if s_lat is None or s_lon is None: return None
        
        dist = calcola_distanza_km(lat_centro, lon_centro, s_lat, s_lon)

        # --- RECUPERO DATI E EMAIL ---
        citta_scuola = tags.get("addr:city", tags.get("addr:municipality", "")).strip()
        
        # Validazione città: se contiene "Via ", "Piazza " o numeri, è probabilmente un indirizzo errato
        is_street = any(k in citta_scuola.lower() for k in ["via ", "piazza ", "corso ", "viale ", "largo ", "vicolo "])
        has_number = any(char.isdigit() for char in citta_scuola)
        
        if not citta_scuola or is_street or has_number:
            citta_scuola = citta_default
            
        email = tags.get("email", tags.get("contact:email", "")).strip().lower()
        codice_miur = tags.get("ref:MIUR", tags.get("official_ref", "")).strip().upper()
        sito_web = tags.get("website", tags.get("contact:website", ""))
        
        metodo_recupero = "OSM Tags (Sicura)" if email else ""

        # 0. NUOVO TENTATIVO: Database MIUR Locale (Open Data)
        if not email:
            dati_miur = cerca_in_database_miur(nome, citta_scuola)
            if dati_miur:
                email_miur = dati_miur.get("INDIRIZZOEMAILSCUOLA") or dati_miur.get("INDIRIZZOPEC")
                if email_miur:
                    email = email_miur
                    metodo_recupero = "MIUR Open Data (Certificata)"
                    if not codice_miur: codice_miur = dati_miur.get("CODICESCUOLA")
                    if not sito_web: sito_web = dati_miur.get("SITOWEBSCUOLA")

        # 1. Se non c'è email ma abbiamo il sito web in OSM, proviamo lo scraping
        if not email and sito_web:
            email_scraped = estrai_email_da_sito(sito_web)
            if email_scraped:
                email = email_scraped
                metodo_recupero = "Web Scraping (Sicura)"
        
        # 2. Se ancora non c'è, proviamo la ricerca web (Bing/DuckDuckGo/Google)
        if not email:
            email_web, motore_usato = cerca_email_web(nome, citta_scuola, approfondita=False)
            if email_web:
                email = email_web
                metodo_recupero = f"Ricerca {motore_usato} (Sicura)"
            else:
                # Se la ricerca veloce fallisce, proviamo quella approfondita
                email_web, motore_usato = cerca_email_web(nome, citta_scuola, approfondita=True)
                if email_web:
                    email = email_web
                    metodo_recupero = f"Ricerca Profonda {motore_usato} (Sicura)"
        
        # 3. Se ancora non c'è, ricostruiamo dal codice MIUR o cerchiamo il codice MIUR
        if not email:
            # Se non abbiamo il codice MIUR, proviamo a cercarlo
            if not codice_miur:
                query_miur = f"codice meccanografico {nome} {citta_scuola}"
                html_miur = network_manager.fetch(f"https://www.bing.com/search?q={urllib.parse.quote(query_miur)}")
                match_miur = re.search(r'\b[A-Z]{2}[A-Z0-9]{8}\b', html_miur or "")
                if match_miur:
                    codice_miur = match_miur.group(0)
                    print(f"   [🔎] Codice MIUR trovato via Web: {codice_miur}")

            if codice_miur:
                # Pulisce il codice MIUR
                codice_miur_clean = re.sub(r'[^A-Z0-9]', '', codice_miur.upper())
                
                # Validazione formale codice MIUR (10 caratteri)
                if len(codice_miur_clean) == 10 and re.match(r'^[A-Z]{2}[A-Z0-9]{8}$', codice_miur_clean):
                    email_miur = f"{codice_miur_clean.lower()}@istruzione.it"
                    email = email_miur
                    metodo_recupero = "Ricostruzione MIUR (Probabile)"
                elif codice_miur_clean:
                    # Se ha un codice ma non è valido per la ricostruzione, cerchiamo l'email del codice
                    query = f"email {codice_miur_clean} istruzione.it"
                    # Proviamo su Bing per evitare blocchi Google
                    html = network_manager.fetch(f"https://www.bing.com/search?q={urllib.parse.quote(query)}")
                    email_miur_search = _trova_email_in_html(html)
                    if email_miur_search:
                        email = email_miur_search
                        metodo_recupero = "Ricerca MIUR su Web (Sicura)"
        
        # 4. ULTIMISSIMA SPIAGGIA: Se non abbiamo sito web e non abbiamo email, cerchiamo il sito web
        if not email and not sito_web:
             # Cerchiamo l'URL del sito ufficiale su Google
             if not network_manager.is_google_blocked():
                 query_sito = f"sito ufficiale {nome} {citta_scuola}"
                 html_sito = network_manager.fetch(f"https://www.google.com/search?q={urllib.parse.quote(query_sito)}")
                 # Tenta di estrarre un link plausibile che non sia google/facebook/etc
                 links = re.findall(r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+', html_sito or "")
                 blacklist_siti = ["google", "facebook", "paginebianche", "paginegialle", "wikipedia", "comune.", "provincia.", "tuttitalia", "cercalascuola"]
                 for link in links:
                     if not any(b in link for b in blacklist_siti):
                         email_scraped = estrai_email_da_sito(link)
                         if email_scraped:
                             email = email_scraped
                             metodo_recupero = "Sito trovato su Google -> Scraping"
                             break

        # Pulizia email
        if email:
            email = email.split(',')[0].split(';')[0].strip()

        return {
            "nome":         nome,
            "citta":        citta_scuola,
            "email":        email,
            "codice_miur":  codice_miur if len(codice_miur) == 10 else "",
            "sito_web":     sito_web,
            "metodo":       metodo_recupero,
            "distanza_km":  round(dist, 2),
            "email_inviata": "",
        }
    finally:
        with network_manager.lock:
            network_manager.active_count = max(0, network_manager.active_count - 1)

def cerca_scuole_overpass(lat=None, lon=None, raggio_km=None, max_lavoratori=150, tipo="tutte", citta_centro="", regione=None, provincia=None, denominazione=None):
    # Costruzione query Overpass
    if regione:
        area_query = f'area["name"="{regione}"]["boundary"="administrative"]["admin_level"="4"]->.searchArea;'
    elif provincia:
        area_query = f'area["name"="{provincia}"]["boundary"="administrative"]["admin_level"="6"]->.searchArea;'
    elif lat and lon and raggio_km:
        raggio_m = raggio_km * 1000
        area_query = "" # Useremo around
    else:
        # Fallback se non c'è nulla, usiamo Roma centro
        lat, lon, raggio_km = 41.89, 12.49, 10
        raggio_m = raggio_km * 1000
        area_query = ""

    # Timeout dinamico
    timeout = 90
    if raggio_km:
        timeout = max(40, min(180, int(raggio_km * 3)))
    
    nodi = ""
    amenities = ['school', 'college', 'university']
    for amenity in amenities:
        if area_query:
            nodi += f'node[amenity={amenity}](area.searchArea);\n'
            nodi += f'way[amenity={amenity}](area.searchArea);\n'
        else:
            nodi += f'node[amenity={amenity}](around:{raggio_m},{lat},{lon});\n'
            nodi += f'way[amenity={amenity}](around:{raggio_m},{lat},{lon});\n'
    
    query = f"[out:json][timeout:{timeout}];\n{area_query}\n(\n{nodi});\nout center tags;"
    data  = urllib.parse.urlencode({"data": query}).encode()
    
    req_timeout = timeout + 10
    
    # Lista di endpoint Overpass per ridondanza
    endpoints = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
        "https://overpass.openstreetmap.fr/api/interpreter",
        "https://lz4.overpass-api.de/api/interpreter"
    ]
    
    result = None
    for url in endpoints:
        headers = {
            "User-Agent": network_manager.get_random_ua(),
            "Accept": "*/*",
            "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.google.com/",
            "Origin": "https://overpass-turbo.eu"
        }
        
        try:
            print(f" Tentativo su endpoint: {url}...", end=" ", flush=True)
            req = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=req_timeout) as resp:
                result = json.loads(resp.read())
                print("OK")
                break
        except Exception as e:
            print(f"FALLITO ({e})")
            continue
    
    if not result:
        print(" [!] ERRORE: Tutti gli endpoint Overpass hanno fallito.")
        return []

    elementi_da_processare = []
    viste_pos = set()
    viste_nomi = set()
    
    for el in result.get("elements", []):
        tags = el.get("tags", {})
        nome = tags.get("name", "").strip()
        s_lat = el.get("lat") or el.get("center", {}).get("lat")
        s_lon = el.get("lon") or el.get("center", {}).get("lon")
        
        if not nome or (s_lat, s_lon) in viste_pos:
            continue
            
        # Filtro Denominazione (se specificato)
        if denominazione and denominazione.lower() not in nome.lower():
            continue

        # Filtro per nome identico nella stessa zona
        if nome in viste_nomi:
            trovata_vicina = False
            for v_lat, v_lon in viste_pos:
                if calcola_distanza_km(s_lat, s_lon, v_lat, v_lon) < 0.1:
                    trovata_vicina = True
                    break
            if trovata_vicina:
                continue
        
        # FILTRO TIPO SCUOLA
        nome_l = nome.lower()
        if tipo == "medie" and not any(k in nome_l for k in ["media", "medie", "primo grado", "secondaria di i"]):
            continue
        if tipo == "superiori" and not any(k in nome_l for k in ["liceo", "istituto", "tecnico", "professionale", "scientifico", "classico", "artistico", "secondo grado", "itis", "ipsia", "secondaria di ii"]):
            continue
        if tipo == "medie+superiori" and not any(k in nome_l for k in ["liceo", "istituto", "media", "medie", "tecnico", "professionale", "scientifico", "classico", "artistico", "grado", "itis", "ipsia", "secondaria di"]):
            continue

        viste_pos.add((s_lat, s_lon))
        viste_nomi.add(nome)
        elementi_da_processare.append(el)

    print(f"Trovate {len(elementi_da_processare)} potenziali scuole. Avvio arricchimento dati parallelo...")
    
    scuole = []
    with ThreadPoolExecutor(max_workers=max_lavoratori) as executor:
        # Se non abbiamo lat_centro/lon_centro (ricerca per area), usiamo le coordinate della prima scuola come riferimento
        ref_lat = lat if lat else (elementi_da_processare[0].get("lat") or elementi_da_processare[0].get("center", {}).get("lat") if elementi_da_processare else 0)
        ref_lon = lon if lon else (elementi_da_processare[0].get("lon") or elementi_da_processare[0].get("center", {}).get("lon") if elementi_da_processare else 0)
        
        future_to_el = {executor.submit(processa_singola_scuola, el, ref_lat, ref_lon, citta_centro): el for el in elementi_da_processare}
        
        completate = 0
        for future in as_completed(future_to_el):
            try:
                scuola = future.result()
                if scuola:
                    scuole.append(scuola)
                completate += 1
                if completate % 10 == 0 or completate == len(elementi_da_processare):
                    print(f" Elaborate {completate}/{len(elementi_da_processare)} scuole... (Timeout attuale: {round(network_manager.timeout, 2)}s)")
            except Exception as e:
                print(f" Errore su una scuola: {e}")

    scuole.sort(key=lambda x: x["distanza_km"])
    return scuole

def carica_scuole_gia_contattate(filename=None):
    if filename is None:
        filename = os.path.join(os.path.dirname(__file__), "database_scuole.csv")
    contattate = set()
    if os.path.exists(filename):
        try:
            with open(filename, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("email"):
                        contattate.add(row["email"].lower().strip())
        except Exception as e:
            print(f"Avviso: Errore lettura database storico: {e}")
    return contattate

def esporta_csv(scuole, filename_sessione=None, filename_database=None):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    if filename_sessione is None:
        filename_sessione = os.path.join(base_dir, "scuole_contattate_sessione.csv")
    else:
        # Se viene passato un percorso relativo, lo rendiamo assoluto rispetto alla posizione dello script
        if not os.path.isabs(filename_sessione):
            filename_sessione = os.path.join(base_dir, filename_sessione)

    if filename_database is None:
        filename_database = os.path.join(base_dir, "database_scuole.csv")
    elif not os.path.isabs(filename_database):
        filename_database = os.path.join(base_dir, filename_database)
    
    # 1. Salva il file della sessione attuale (sovrascrive sempre lo stesso file)
    keys = ["nome", "citta", "email", "codice_miur", "sito_web", "metodo", "distanza_km", "email_inviata"]
    try:
        # Scrittura atomica per evitare file lock o corruzione se la dashboard legge mentre scriviamo
        temp_filename = filename_sessione + ".tmp"
        
        # Assicuriamoci che la directory esista
        os.makedirs(os.path.dirname(os.path.abspath(temp_filename)), exist_ok=True)
        
        with open(temp_filename, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            for s in scuole:
                writer.writerow({k: s.get(k, "") for k in keys})
        
        # Sostituzione rapida (atomica su sistemi moderni)
        if os.path.exists(filename_sessione):
            os.remove(filename_sessione)
        os.rename(temp_filename, filename_sessione)
        
        # 2. Aggiorna il database storico (append intelligente)
        da_aggiungere = [s for s in scuole if s.get("email_inviata") == "SI"]
        if da_aggiungere:
            file_esiste = os.path.exists(filename_database)
            gia_nel_db = carica_scuole_gia_contattate(filename_database)
            
            with open(filename_database, mode="a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                if not file_esiste:
                    writer.writeheader()
                for s in da_aggiungere:
                    if s["email"].lower().strip() not in gia_nel_db:
                        writer.writerow({k: s.get(k, "") for k in keys})
            print(f"Database storico aggiornato.")
            
    except Exception as e:
        print(f"Errore salvataggio CSV: {e}")

from email.mime.application import MIMEApplication
from email.mime.base import MIMEBase
from email import encoders

import time
import random

def get_human_headers():
    """Genera header email casuali per simulare client diversi."""
    mailers = [
        "Microsoft Outlook 16.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Thunderbird/115.0",
        "Apple Mail (2.3608.120.2.3.2)",
        "Gmail Mobile/1.0",
        "AOL Mail/1.0",
        "iPhone Mail (20G75)"
    ]
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0"
    ]
    return {
        "X-Mailer": random.choice(mailers),
        "User-Agent": random.choice(user_agents),
        "X-Priority": str(random.choice([1, 3])), # 1=High, 3=Normal
        "Importance": random.choice(["high", "normal"])
    }

def invia_email(dest, oggetto, corpo_text, corpo_html=None, server=None, ignora_test=False, nome_scuola="Scuola"):
    """Invia un'email con supporto per allegati, multi-account e retry automatico."""
    destinatario_reale = dest
    if CONFIG.get("modalita_test") and not ignora_test:
        destinatario_reale = CONFIG["tua_email"]
        oggetto = f"[TEST] {oggetto} (Originale per: {dest})"

    max_tentativi = 3
    for tentativo in range(max_tentativi):
        current_acc = None
        close_server = False
        try:
            # Se il server non è passato o è disconnesso, usiamo l'email_manager
            if server is None:
                current_acc = email_manager.get_next_available()
                if not current_acc:
                    print("\n [❌] ERRORE CRITICO: Nessun account email disponibile! Tutti sono in cooldown.")
                    print("   [🔄] Tentativo di BYPASS tramite invio diretto MX...")
                    
                    # Costruiamo il messaggio per l'invio diretto
                    msg = MIMEMultipart("mixed")
                    msg["Subject"] = oggetto
                    msg["From"]    = f"{CONFIG['tuo_nome']} <noreply@sicurezza-stradale.it>"
                    msg["To"]      = destinatario_reale
                    # (Il resto del messaggio verrebbe costruito qui, ma facciamo prima il test MX)
                    if invia_diretto_mx(destinatario_reale, ""): # Test vuoto o implementazione completa
                         pass # Continua sotto
                    else:
                        return False
                
                provider = current_acc.get("provider", "gmail")
                smtp_config = email_manager.providers_config.get(provider, email_manager.providers_config["gmail"])
                smtp_host = smtp_config["host"]
                smtp_port = smtp_config["port"]

                context = ssl.create_default_context()
                if smtp_port == 465:
                    server_conn = smtplib.SMTP_SSL(smtp_host, smtp_port, context=context)
                else:
                    server_conn = smtplib.SMTP(smtp_host, smtp_port)
                    server_conn.starttls(context=context)
                
                server_conn.login(current_acc["email"], current_acc["password"])
                close_server = True
                use_email = current_acc["email"]
            else:
                server_conn = server
                use_email = CONFIG["tua_email"]

            # Costruzione messaggio
            msg = MIMEMultipart("mixed")
            msg["Subject"] = oggetto
            if CONFIG.get("tuo_nome"):
                msg["From"] = f"{CONFIG['tuo_nome']} <{use_email}>"
            else:
                msg["From"] = use_email
            msg["To"]      = destinatario_reale
            msg["Date"]    = formatdate(localtime=True)
            msg["Message-ID"] = make_msgid(domain="sicurezza-stradale.it")

            # HUMANIZATION: Aggiunta di header casuali (X-Mailer, User-Agent, Priority)
            for key, value in get_human_headers().items():
                msg[key] = value

            # Variazione leggera del corpo per bypassare i filtri spam di contenuto
            # (Aggiungiamo un invisibile ID unico in fondo)
            email_id = hashlib.md5(f"{destinatario_reale}{time.time()}".encode()).hexdigest()[:12]
            
            # Registriamo l'associazione email_id -> scuola per il tracking
            try:
                tracking_file = "DATA/email_tracking.json"
                if not os.path.exists("DATA"): os.makedirs("DATA")
                t_data = {}
                if os.path.exists(tracking_file):
                    with open(tracking_file, "r") as f: t_data = json.load(f)
                
                t_data[email_id] = {
                    "scuola": nome_scuola if 'nome_scuola' in locals() else "Sconosciuta",
                    "email": destinatario_reale,
                    "opens": 0,
                    "history": []
                }
                with open(tracking_file, "w") as f: json.dump(t_data, f, indent=4)
            except: pass

            unique_id = f"\n\n<!-- ID: {email_id} -->"
            corpo_variato_text = corpo_text + unique_id

            msg_alt = MIMEMultipart("alternative")
            msg_alt.attach(MIMEText(corpo_variato_text, "plain", "utf-8"))
            
            # HTML con Tracking Pixel
            if corpo_html:
                html_body = corpo_html + unique_id
            else:
                html_body = corpo_variato_text.replace(chr(10), '<br>')
                
            tracking_url = CONFIG.get("tracking_base_url", "http://localhost:5000")
            tracking_pixel = f'<img src="{tracking_url}/t/{email_id}.png" width="1" height="1" style="display:none !important;" />'
            
            html = f"<html><body style='font-family:Arial,sans-serif;'>{html_body}{tracking_pixel}</body></html>"
            msg_alt.attach(MIMEText(html, "html", "utf-8"))
            msg.attach(msg_alt)
            
            path_allegato = os.path.join(os.path.dirname(__file__), CONFIG.get("allegato_pdf", ""))
            if CONFIG.get("allegato_pdf") and os.path.exists(path_allegato):
                with open(path_allegato, "rb") as f:
                    part = MIMEApplication(f.read(), Name=os.path.basename(path_allegato))
                part['Content-Disposition'] = f'attachment; filename="{os.path.basename(path_allegato)}"'
                msg.attach(part)
            
            server_conn.sendmail(use_email, destinatario_reale, msg.as_string())
            
            if close_server:
                try: server_conn.quit()
                except: pass
            return True

        except (smtplib.SMTPAuthenticationError, smtplib.SMTPException, Exception) as e:
            error_str = str(e)
            print(f"\n   [!] ERRORE INVIO (Tentativo {tentativo+1}/{max_tentativi}): {error_str}")
            
            # Se l'errore avviene PRIMA della costruzione del messaggio (es: nel login)
            # dobbiamo comunque gestire il cambio account
            if 'msg' not in locals():
                msg = MIMEMultipart("mixed") # Placeholder per evitare errori sotto
            
            # Gestione Credenziali Errate o Account Bloccato
            if "BadCredentials" in error_str or "535" in error_str:
                if current_acc:
                    print(f"   [⚠️] CREDENZIALI ERRATE per {current_acc['email']}. Escludo l'account.")
                    email_manager.mark_blocked(current_acc["email"])
                
                if close_server and 'server_conn' in locals():
                    try: server_conn.quit()
                    except: pass
                
                print("   [🔄] Cambio account SMTP e riprovo...")
                time.sleep(1)
                continue # Riprova col prossimo account

            # Gestione Limite Giornaliero
            if "Daily user sending limit exceeded" in error_str or "5.4.5" in error_str:
                if current_acc:
                    email_manager.mark_blocked(current_acc["email"])
                
                # TENTATIVO DI BYPASS: Invio diretto MX
                print("   [🔄] Limite raggiunto. Provo bypass diretto (MX)...")
                # Costruiamo il messaggio completo prima di passarlo
                msg_full = msg.as_string()
                if invia_diretto_mx(destinatario_reale, msg_full):
                    if close_server and 'server_conn' in locals():
                        try: server_conn.quit()
                        except: pass
                    return True

                # FALLBACK GOOGLE SCRIPT (Se configurato)
                if CONFIG.get("google_script_url"):
                    print("   [🌐] Provo bypass tramite Google Apps Script (VPS-like)...")
                    if invia_tramite_google_script(destinatario_reale, oggetto, corpo, CONFIG["google_script_url"]):
                        return True

                # FALLBACK BREVO (SMTP Relay Professionale)
                if CONFIG.get("brevo_user") and CONFIG.get("brevo_password"):
                    print("   [📧] Provo bypass tramite Brevo SMTP Relay...")
                    try:
                        with smtplib.SMTP("smtp-relay.brevo.com", 587) as b_server:
                            b_server.starttls()
                            b_server.login(CONFIG["brevo_user"], CONFIG["brevo_password"])
                            b_server.sendmail(CONFIG["brevo_user"], destinatario_reale, msg.as_string())
                            return True
                    except: pass

                # FALLBACK ESTREMO: Relay tramite numero di telefono (SMS/Chiamate)
                num_tel = CONFIG.get("telefono_destinatario")
                if num_tel:
                    print(f"   [📱] Provo bypass estremo tramite Relay Telefonico su {num_tel}...")
                    if invia_via_form_telefono(num_tel, corpo[:100]):
                        return True
                
                print("   [🔄] Cambio account SMTP e riprovo...")
                time.sleep(1)
                continue # Riprova col prossimo account

            if tentativo < max_tentativi - 1:
                time.sleep(3)
                continue
            return False

def esegui_ricerca_e_salva(indirizzo=None, raggio=None, tipo_scuole="tutte", regione=None, provincia=None, denominazione=None):
    """Funzione chiamabile dalla dashboard per avviare il processo senza input terminale."""
    if indirizzo:
        lat, lon, desc_pos = geocodifica_citta(indirizzo)
        citta_centro = desc_pos.split(",")[0].strip()
    else:
        lat, lon, desc_pos = None, None, f"{regione or provincia or 'Italia'}"
        citta_centro = ""

    # Salvataggio metadati per dashboard
    session_data = {
        "posizione_centro": desc_pos,
        "coordinate": {"lat": lat, "lon": lon} if lat else None,
        "raggio": raggio,
        "tipo_scuole": tipo_scuole,
        "regione": regione,
        "provincia": provincia,
        "denominazione": denominazione,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "stato": "In corso..."
    }
    with open(os.path.join(os.path.dirname(__file__), "session_info.json"), "w", encoding="utf-8") as f:
        json.dump(session_data, f, indent=4)

    # Configurazione lavoratori
    if CONFIG["max_lavoratori"] == "auto":
        lavoratori = 150 # Valore fisso ottimizzato per I/O bound
    else:
        lavoratori = int(CONFIG["max_lavoratori"])
    
    network_manager.max_lavoratori_originali = lavoratori
    network_manager.target_workers = lavoratori

    # Ricerca
    scuole_trovate = cerca_scuole_overpass(
        lat=lat, 
        lon=lon, 
        raggio_km=raggio, 
        max_lavoratori=lavoratori, 
        tipo=tipo_scuole, 
        citta_centro=citta_centro,
        regione=regione,
        provincia=provincia,
        denominazione=denominazione
    )
    
    # Anti-duplicati
    gia_contattate = carica_scuole_gia_contattate()
    scuole = [s for s in scuole_trovate if not (s["email"] and s["email"].lower().strip() in gia_contattate)]
    
    # Esportazione
    esporta_csv(scuole, os.path.join(os.path.dirname(__file__), "scuole_contattate_sessione.csv"))
    
    # Update stato
    session_data["stato"] = "Completato"
    with open(os.path.join(os.path.dirname(__file__), "session_info.json"), "w", encoding="utf-8") as f:
        json.dump(session_data, f, indent=4)
        
    return len(scuole)

import imaplib
import email
from email.header import decode_header
import re

def controlla_bounce():
    """Controlla le caselle email per messaggi di bounce (Delivery Status Notification)."""
    print("\n [🔍] Controllo bounce in corso...")
    bounces_found = []
    
    # Per semplicità, controlliamo solo l'account principale o tutti quelli configurati
    accounts = email_manager.get_all_accounts()
    
    for acc in accounts:
        try:
            provider = acc.get("provider", "gmail")
            imap_host = "imap.gmail.com" # Default
            if provider == "outlook": imap_host = "outlook.office365.com"
            elif provider == "libero": imap_host = "imapmail.libero.it"
            
            mail = imaplib.IMAP4_SSL(imap_host)
            mail.login(acc["email"], acc["password"])
            mail.select("inbox")
            
            # Cerca email da "postmaster" o con "delivery status" nell'oggetto
            status, messages = mail.search(None, '(OR FROM "postmaster" SUBJECT "Delivery Status Notification")')
            
            if status == 'OK':
                for num in messages[0].split():
                    status, data = mail.fetch(num, '(RFC822)')
                    if status == 'OK':
                        msg = email.message_from_bytes(data[0][1])
                        subject, encoding = decode_header(msg["Subject"])[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding if encoding else "utf-8")
                        
                        # Tenta di estrarre l'email fallita dal corpo
                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    body = part.get_payload(decode=True).decode()
                                    break
                        else:
                            body = msg.get_payload(decode=True).decode()
                        
                        # Regex semplice per trovare email nel corpo del bounce
                        emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', body)
                        if emails:
                            # Il primo indirizzo trovato nel corpo di un bounce solitamente è il destinatario originale
                            bounces_found.append({
                                "account": acc["email"],
                                "failed_recipient": emails[0],
                                "subject": subject,
                                "date": msg["Date"]
                            })
            mail.logout()
        except Exception as e:
            print(f"   [!] Errore controllo bounce per {acc['email']}: {e}")
            
    # Salva i bounce trovati
    if bounces_found:
        bounce_file = os.path.join(os.path.dirname(__file__), "DATA/bounces.json")
        if not os.path.exists(os.path.dirname(bounce_file)):
            os.makedirs(os.path.dirname(bounce_file))
            
        existing_bounces = []
        if os.path.exists(bounce_file):
            with open(bounce_file, "r") as f:
                existing_bounces = json.load(f)
        
        # Merge evitando duplicati
        new_bounces = existing_bounces + [b for b in bounces_found if b not in existing_bounces]
        with open(bounce_file, "w") as f:
            json.dump(new_bounces, f, indent=4)
        print(f" [✅] Trovati {len(bounces_found)} nuovi bounce.")
    else:
        print(" [info] Nessun nuovo bounce trovato.")
    
    return bounces_found

def main():
    # 0. AVVIO LOGGING AUTOMATICO E DEBUG CONTESTO
    log_file = avvia_logging()
    print(f"DEBUG: Script Path: {os.path.abspath(__file__)}")
    print(f"DEBUG: Working Dir: {os.getcwd()}")

    # 1. MANUTENZIONE DATABASE
    db_path = os.path.join(os.path.dirname(__file__), "database_scuole.csv")
    if os.path.exists(db_path):
        print("DATABASE STORICO TROVATO.")
        pulire = input("Vuoi cancellare tutto lo storico e ricominciare da zero? (s/n): ").strip().lower()
        if pulire == 's':
            os.remove(db_path)
            print("Database cancellato con successo.")

    print(f"\n" + "="*50)
    print(f"AVVIO PROGETTO: {CONFIG['nome_progetto']}")
    print(f"IP PUBBLICO ATTUALE: {get_public_ip()}")
    print("   [💡] Se l'IP è segnalato (es. Spamhaus), usa una VPN o riavvia il router.")
    print(f"MITTENTE PRIMARIO: {CONFIG['tuo_nome']} ({CONFIG['tua_email']})")
    print(f"STATO ACCOUNT EMAIL:")
    print(email_manager.get_status_report())
    
    # OPZIONE RESET COOLDOWN
    if any(email in email_manager.blocked_accounts for acc in email_manager.accounts for email in [acc["email"]]):
        scelta_reset = input("\n [⚠️] Alcuni account sono in cooldown. Vuoi resettarli ora? (s/n): ").strip().lower()
        if scelta_reset == 's':
            email_manager.reset_all_cooldowns()

    print(f"LOG SESSIONE: {log_file}")
    print("="*50 + "\n")

    # --- NUOVA OPZIONE: CARICAMENTO SESSIONE PRECEDENTE ---
    csv_sessione = os.path.join(os.path.dirname(__file__), "scuole_contattate_sessione.csv")
    if os.path.exists(csv_sessione):
        print(f" TROVATA SESSIONE PRECEDENTE ({csv_sessione})")
        scelta_ricarica = input(" Vuoi ricaricare i dati dell'ultima scansione? (s/n, invio=n): ").strip().lower()
        if scelta_ricarica == 's':
            print(" [OK] Caricamento dati in corso...")
            with open(csv_sessione, mode="r", encoding="utf-8") as f:
                scuole = list(csv.DictReader(f))
            
            # Pulizia automatica città caricate (evita "Via Aurelio Saliceti" come città)
            for s in scuole:
                c = s.get("citta", "").lower()
                if any(k in c for k in ["via ", "piazza ", "viale ", "corso ", "largo "]) or any(char.isdigit() for char in c):
                    # Se non sappiamo la città, lasciamo vuoto o mettiamo un placeholder
                    # Ma dato che ricarichiamo, cerchiamo di mantenere Roma se il contesto lo suggerisce
                    s["citta"] = "Roma" if "roma" in s.get("nome", "").lower() else s.get("citta", "Roma")

            print(f" [OK] Caricate {len(scuole)} scuole dalla sessione precedente (dati normalizzati).")
            
            # --- RICERCA PROFONDA (Opzionale) ---
            senza_email = [s for s in scuole if not s.get("email") or s.get("email") == "---"]
            if senza_email:
                print(f"\n [!] Ci sono {len(senza_email)} scuole senza email.")
                deep = input(" Vuoi tentare una RICERCA PROFONDA per queste scuole? (s/n): ").strip().lower()
                if deep == 's':
                    for s in senza_email:
                        print(f" -> Ricerca per: {s['nome']}...", end=" ", flush=True)
                        email, motore = cerca_email_web(s["nome"], s["citta"], approfondita=True)
                        if email:
                            print(f"TROVATA - scuola {s['nome']} email: {email}")
                            s["email"] = email
                            s["metodo"] = motore
                            esporta_csv(scuole, csv_sessione)
                        else:
                            print(f"NON TROVATA - scuola {s['nome']} città: {s.get('citta', 'N/D')}")

            # --- VERIFICA EMAIL (TEST REALE) ---
            print("\nVUOI VERIFICARE CHE L'INVIO EMAIL FUNZIONI?")
            test_email_scelta = input("Vuoi inviare un'email di prova a un tuo indirizzo? (s/n): ").strip().lower()
            if test_email_scelta == 's':
                mio_email = input("Inserisci il tuo indirizzo email di prova: ").strip()
                volte_input = input("Quante volte vuoi inviare l'email di prova? (es: 1, 3, 5) [invio=1]: ").strip()
                volte = int(volte_input) if volte_input.isdigit() else 1
                
                print(f"Invio {volte} prova/e a {mio_email}...")
                successi_test = 0
                for i in range(1, volte + 1):
                    obj_test = f"TEST FUNZIONAMENTO {i}/{volte} - Progetto Sicurezza Stradale"
                    corpo_test = f"Questa è l'email di prova numero {i} di {volte} per verificare che la configurazione SMTP sia corretta."
                    
                    print(f"  [{i}/{volte}] Invio...", end=" ", flush=True)
                    # Passiamo None come server per forzare l'uso dell'email_manager con rotazione
                    obj_t, text_t, html_t = crea_email("Scuola Test", "Roma")
                    if invia_email(mio_email, obj_t, text_t, html_t, server=None, ignora_test=True, nome_scuola="Scuola Test"):
                        print("OK")
                        successi_test += 1
                    else:
                        print("FALLITO")
                    
                    if i < volte:
                        pausa_test = random.uniform(2, 6)
                        print(f"   [Attesa di {round(pausa_test, 1)}s...]")
                        time.sleep(pausa_test)

            # --- ANTEPRIMA EMAIL ---
            con_email = [s for s in scuole if s.get("email") and s.get("email") != "---"]
            if con_email:
                print(f"\nANTEPRIMA EMAIL PER LE SCUOLE:")
                obj, body = crea_email(con_email[0]["nome"], con_email[0]["citta"] or "tua città")
                print(f"A: {con_email[0]['email']}")
                print(f"Oggetto: {obj}")
                print("-" * 20)
                print(body[:200] + "...")
                print("-" * 20)
            
            # Proseguiamo alla fase di invio reale
            print(f"\nAVVIO FASE INVIO (Totale scuole con email: {len(con_email)})")
            inviare = input(f"Vuoi inviare l'email a tutte le {len(con_email)} scuole caricate? (s/n): ").strip().lower()
            if inviare == 's':
                volte_per_scuola_input = input("Quante volte vuoi inviare l'email a OGNI scuola? [invio=1]: ").strip()
                volte_per_scuola = int(volte_per_scuola_input) if volte_per_scuola_input.isdigit() else 1
                
                inviate = 0
                # Solo quelle con email e non ancora inviate
                con_email_effettive = [s for s in con_email if s.get("email_inviata") != "SI"]
                
                if not con_email_effettive:
                    print("Tutte le scuole caricate risultano già contattate (SI).")
                    reinvio = input("Vuoi forzare il reinvio a tutte? (s/n): ").strip().lower()
                    if reinvio == 's':
                        con_email_effettive = con_email
                
                for i, s in enumerate(con_email_effettive, 1):
                    nome = s["nome"]
                    citta = s["citta"] or "Italia"
                    dest = s["email"]
                    
                    for v in range(1, volte_per_scuola + 1):
                        count_str = f" ({v}/{volte_per_scuola})" if volte_per_scuola > 1 else ""
                        print(f"[{i}/{len(con_email_effettive)}]{count_str} Invio a: {nome} ({dest})...", end=" ", flush=True)
                        
                        # Invia senza passare il server per permettere la rotazione automatica
                        obj, text, html = crea_email(nome, citta)
                        if invia_email(dest, obj, text, html, server=None, nome_scuola=nome):
                            print("OK")
                            s["email_inviata"] = "SI"
                            inviate += 1
                            esporta_csv(scuole, csv_sessione)
                        else:
                            print("FALLITO (Nessun account disponibile o errore critico)")
                        
                        if i < len(con_email_effettive) or v < volte_per_scuola:
                            pausa = random.uniform(CONFIG["pausa_min_email"], CONFIG["pausa_max_email"])
                            print(f"   [Attesa di {round(pausa, 1)}s...]")
                            time.sleep(pausa)
                
                print(f"\n[FINE] Inviate {inviate} email.")
                return

    # 1. POSIZIONE
    print("POSIZIONE")
    print(" [1] Rileva automaticamente (IP - poco preciso)")
    print(" [2] Inserisci indirizzo preciso (es: Via Aurelio Saliceti 9, Roma)")
    print(" [3] Inserisci coordinate GPS (es: 41.89, 12.49 - massima precisione)")
    print(" [4] AVVIO RAPIDO (Via Aurelio Saliceti 9, 40km, Tutte)")
    scelta_pos = input("Scelta [1/2/3/4, invio=2]: ").strip() or "2"
    
    avvio_rapido = (scelta_pos == "4")
    
    if avvio_rapido:
        print("\n [⚡] AVVIO RAPIDO ATTIVATO:")
        print("     - Indirizzo: Via Aurelio Saliceti 9, Roma")
        print("     - Raggio:    40 km")
        print("     - Scuole:    Tutte")
        lat, lon, desc_pos = geocodifica_citta("Via Aurelio Saliceti 9, Roma")
        raggio = 40
        tipo_scuole = "tutte"
        citta_riferimento = "Roma"
    elif scelta_pos == "2":
        default_addr = "Via Aurelio Saliceti 9, Roma"
        indirizzo_utente = input(f"Inserisci indirizzo completo [invio={default_addr}]: ").strip()
        if not indirizzo_utente: indirizzo_utente = default_addr
        lat, lon, desc_pos = geocodifica_citta(indirizzo_utente)
        # Estraiamo la città dall'indirizzo fornito (prendiamo l'ultima parte dopo la virgola)
        citta_riferimento = indirizzo_utente.split(",")[-1].strip()
    elif scelta_pos == "3":
        coords = input("Incolla coordinate (lat, lon): ").replace(",", " ").split()
        if len(coords) < 2:
            print("Formato non valido. Esempio corretto: 41.89 12.49")
            return
        lat, lon = float(coords[0]), float(coords[1])
        desc_pos = geocodifica_inversa(lat, lon)
        citta_riferimento = desc_pos.split(",")[-1].strip() # Approssimativo dalla geocodifica
    else:
        lat, lon, desc_pos = rileva_posizione_ip()
        citta_riferimento = desc_pos # In questo caso desc_pos è già la città
    
    print(f"\nPOSIZIONE REALE IMPOSTATA:")
    print(f"   Indirizzo: {desc_pos}")
    print(f"   Coordinate: ({lat}, {lon})")

    if not avvio_rapido:
        # 2. RAGGIO
        raggio_input = input("\nInserisci raggio di ricerca in km [invio=20]: ").strip()
        raggio = int(raggio_input) if raggio_input else 20
        
        # 3. FILTRI SCUOLE
        print("\nCHE TIPO DI SCUOLE VUOI CERCARE?")
        print(" [1] Tutte")
        print(" [2] Solo Medie")
        print(" [3] Solo Superiori")
        print(" [4] Medie + Superiori")
        scelta_filtro = input("Scelta [1/2/3/4, invio=1]: ").strip()
        
        tipo_map = {"1": "tutte", "2": "medie", "3": "superiori", "4": "medie+superiori"}
        tipo_scuole = tipo_map.get(scelta_filtro, "tutte")

    # --- SALVATAGGIO METADATI SESSIONE PER DASHBOARD ---
    session_data = {
        "posizione_centro": desc_pos,
        "coordinate": {"lat": lat, "lon": lon},
        "raggio": raggio,
        "tipo_scuole": tipo_scuole,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    try:
        with open(os.path.join(os.path.dirname(__file__), "session_info.json"), "w", encoding="utf-8") as f:
            json.dump(session_data, f, indent=4)
    except:
        pass
    # ----------------------------------------------------

    # --- DETERMINAZIONE LAVORATORI OTTIMALI ---
    if CONFIG["max_lavoratori"] == "auto":
        lavoratori_ottimali = 150 # Valore fisso ottimizzato per I/O bound
        CONFIG["max_lavoratori_effettivi"] = lavoratori_ottimali
    else:
        CONFIG["max_lavoratori_effettivi"] = int(CONFIG["max_lavoratori"])
    
    # --- INIZIALIZZAZIONE GOVERNATORE ---
    network_manager.max_lavoratori_originali = CONFIG["max_lavoratori_effettivi"]
    network_manager.target_workers = CONFIG["max_lavoratori_effettivi"]
    
    print(f" [⚙️] CONFIGURAZIONE PARALLELISMO: Utilizzo di {CONFIG['max_lavoratori_effettivi']} lavoratori (thread).")

    print(f"\nRicerca {tipo_scuole} nel raggio di {raggio}km...")
    
    # Estraiamo solo la città dalla descrizione posizione per passarla come default
    citta_default = citta_riferimento
    
    start_time_search = time.time()
    scuole_trovate = cerca_scuole_overpass(lat, lon, raggio, CONFIG["max_lavoratori_effettivi"], tipo_scuole, citta_default)
    
    # --- LOGICA INTELLIGENTE ANTI-DUPLICATI ---
    gia_contattate = carica_scuole_gia_contattate()
    scuole = []
    gia_presenti = 0
    
    for s in scuole_trovate:
        if s["email"] and s["email"].lower().strip() in gia_contattate:
            gia_presenti += 1
            # Log silenzioso nel file ma visibile se serve
        else:
            scuole.append(s)
            
    if gia_presenti > 0:
        print(f" [i] Ho saltato {gia_presenti} scuole perché già presenti nel database storico (contattate in precedenza).")
    # ------------------------------------------

    con_email = [s for s in scuole if s["email"]]
    
    print(f"RISULTATI: Trovate {len(scuole)} scuole, di cui {len(con_email)} con email.")
    
    # Conteggio metodi per log
    metodi_count = {}
    for s in con_email:
        m = s["metodo"]
        metodi_count[m] = metodi_count.get(m, 0) + 1
    
    if con_email:
        print("\nDettaglio affidabilità email:")
        for m, count in metodi_count.items():
            print(f" - {m}: {count}")
    
    # --- NUOVA OPZIONE: RICERCA PROFONDA PER SCUOLE SENZA EMAIL ---
    senza_email = [s for s in scuole if not s.get("email") or s.get("email") == "---"]
    if senza_email:
        print(f"\n [!] Ci sono {len(senza_email)} scuole senza email.")
        deep = input(" Vuoi tentare una RICERCA PROFONDA per queste scuole? (s/n): ").strip().lower()
        if deep == 's':
            for s in senza_email:
                print(f" -> Ricerca per: {s['nome']}...", end=" ", flush=True)
                email, motore = cerca_email_web(s["nome"], s["citta"], approfondita=True)
                if email:
                    print(f"TROVATA - scuola {s['nome']} email: {email}")
                    s["email"] = email
                    s["metodo"] = motore
                else:
                    print(f"NON TROVATA - scuola {s['nome']} città: {s.get('citta', 'N/D')}")
            
            # Ricalcoliamo con_email dopo la ricerca profonda
            con_email = [s for s in scuole if s.get("email") and s.get("email") != "---"]
            print(f"Nuovo totale scuole con email: {len(con_email)}")

    # Salvataggio sessione aggiornata
    esporta_csv(scuole, os.path.join(os.path.dirname(__file__), "scuole_contattate_sessione.csv"))

    end_time_search = time.time()
    elapsed_time = end_time_search - start_time_search
    minuti = int(elapsed_time // 60)
    secondi = int(elapsed_time % 60)
    
    print(f"\n✅ RICERCA COMPLETATA IN: {minuti}m {secondi}s")
    
    print(f"\n--- RIEPILOGO PERFORMANCE RETE ---")
    print(f"Lavoratori utilizzati: {CONFIG['max_lavoratori_effettivi']}")
    print(f"Timeout finale: {round(network_manager.timeout, 2)}s")
    successi = [p for p in network_manager.performance_log if p["success"]]
    if network_manager.performance_log:
        rate = (len(successi) / len(network_manager.performance_log)) * 100
        print(f"Tasso di successo caricamento: {round(rate, 1)}%")
    print(f"----------------------------------\n")

    if not con_email:
        print("Nessuna scuola con email trovata. Prova ad aumentare il raggio.")
        return

    # 4. VERIFICA EMAIL (TEST REALE)
    print("\nVUOI VERIFICARE CHE L'INVIO EMAIL FUNZIONI?")
    test_email_scelta = input("Vuoi inviare un'email di prova a un tuo indirizzo? (s/n): ").strip().lower()
    if test_email_scelta == 's':
        mio_email = input("Inserisci il tuo indirizzo email di prova: ").strip()
        volte_input = input("Quante volte vuoi inviare l'email di prova? (es: 1, 3, 5) [invio=1]: ").strip()
        volte = int(volte_input) if volte_input.isdigit() else 1
        
        print(f"Invio {volte} prova/e a {mio_email}...")
        try:
            context = ssl.create_default_context()
            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls(context=context)
                server.login(CONFIG["tua_email"], CONFIG["email_password"])
                
                successi_test = 0
                for i in range(1, volte + 1):
                    obj_test = f"TEST FUNZIONAMENTO {i}/{volte} - Progetto Sicurezza Stradale"
                    corpo_test = f"Questa è l'email di prova numero {i} di {volte} per verificare che la configurazione SMTP sia corretta."
                    
                    print(f"  [{i}/{volte}] Invio...", end=" ", flush=True)
                    if invia_email(mio_email, obj_test, corpo_test, server, ignora_test=True):
                        print("OK")
                        successi_test += 1
                    else:
                        print("FALLITO")
                    
                    # Pausa randomica tra i test per simulare comportamento umano (min 2s, max 6s)
                    if i < volte:
                        pausa_test = random.uniform(2, 6)
                        print(f"   [Attesa di {round(pausa_test, 1)}s...]")
                        time.sleep(pausa_test)
                
                if successi_test == volte:
                    print(f"TEST RIUSCITO! Tutte le {volte} email sono state inviate correttamente.")
                else:
                    print(f"TEST PARZIALE/FALLITO. Inviate con successo: {successi_test}/{volte}. Controlla i log sopra.")
        except Exception as e:
            print(f"ERRORE DURANTE IL TEST: {e}")
            print("   Assicurati di usare una 'Password per le App' di Google.")

    csv_file = os.path.join(os.path.dirname(__file__), "scuole_contattate_sessione.csv")
    esporta_csv(scuole, csv_file)
    
    print(f"\nANTEPRIMA EMAIL PER LE SCUOLE:")
    obj, body = crea_email(con_email[0]["nome"], con_email[0]["citta"] or "tua città")
    print(f"A: {con_email[0]['email']}")
    print(f"Oggetto: {obj}")
    print("-" * 20)
    print(body[:300] + "...")
    print("-" * 20)
    
    if CONFIG["modalita_test"]:
        print("\n*** MODALITA TEST ATTIVA ***")
        print(f"Scuole con email che verrebbero contattate ({len(con_email)}):")
        for s in con_email:
            print(f"- {s['nome']} ({s['email']}) - {s['distanza_km']} km")
        print(f"\nRisultati completi salvati in: {csv_file}")
        print("\nPer inviare davvero: imposta 'modalita_test': False nello script.")
    else:
        print(f"\nATTENZIONE: Stai per inviare {len(con_email)} email reali.")
        volte_per_scuola_input = input("Quante volte vuoi inviare l'email a OGNI scuola? [invio=1]: ").strip()
        volte_per_scuola = int(volte_per_scuola_input) if volte_per_scuola_input.isdigit() else 1
        
        conferma = input(f"Procedere con l'invio di {len(con_email) * volte_per_scuola} email totali? (s/n): ").strip().lower()
        if conferma != 's':
            print("Invio annullato.")
            return

        print("\nConnessione a Gmail...")
        try:
            context = ssl.create_default_context()
            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls(context=context)
                server.login(CONFIG["tua_email"], CONFIG["email_password"])
                print("Login effettuato con successo.")
                
                inviate = 0
                for i, s in enumerate(con_email, 1):
                    nome = s["nome"]
                    citta = s["citta"] or "Italia"
                    dest = s["email"]
                    
                    for v in range(1, volte_per_scuola + 1):
                        count_str = f" ({v}/{volte_per_scuola})" if volte_per_scuola > 1 else ""
                        print(f"[{i}/{len(con_email)}]{count_str} Invio a: {nome} ({dest})...", end=" ", flush=True)
                        
                        if invia_email(dest, *crea_email(nome, citta), server):
                            print("OK")
                            s["email_inviata"] = "SI"
                            inviate += 1
                        else:
                            print("FALLITO")
                            s["email_inviata"] = "NO"
                        
                        # Pausa randomica tra gli invii
                        if i < len(con_email) or v < volte_per_scuola:
                            pausa = random.uniform(CONFIG["pausa_min_email"], CONFIG["pausa_max_email"])
                            print(f"   [Attesa di {round(pausa, 1)}s...]")
                            time.sleep(pausa)
                
                print(f"\nCompletato! Email inviate: {inviate}/{len(con_email)}")
                esporta_csv(scuole, csv_file) # Aggiorna CSV con lo stato invio
        except Exception as e:
            print(f"Errore generale SMTP: {e}")

if __name__ == "__main__":
    main()
