import os
import smtplib
import ssl
import time
import json
import re
import subprocess
import random
from email.utils import make_msgid, formatdate
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

import urllib.request
import urllib.parse

def get_public_ip():
    try:
        with urllib.request.urlopen("https://api.ipify.org", timeout=5) as response:
            return response.read().decode('utf-8')
    except:
        return "N/A"

def invia_tramite_google_script(dest, oggetto, corpo, script_url):
    try:
        data = urllib.parse.urlencode({'to': dest, 'subject': oggetto, 'body': corpo}).encode('utf-8')
        req = urllib.request.Request(script_url, data=data, method='POST')
        with urllib.request.urlopen(req, timeout=15) as response:
            return "OK" in response.read().decode('utf-8')
    except: return False

# --- CONFIGURAZIONE ---
CONFIG = {
    "tuo_nome":       "Andrea Sapienza",
    "tua_email":      "dalenapoliroma@gmail.com",
    "email_password": "wivc wzji wgyk gofb", 
    "nome_progetto":  "Sicurezza alla Guida",
    "telefono_destinatario": "3738513104",
    "pausa_min_email": 10,
    "pausa_max_email": 25,
    "google_script_url": None, # Incolla qui l'URL se crei lo script
    "brevo_user": None,
    "brevo_password": None,
}

# --- GESTORE ACCOUNT EMAIL ---
class EmailAccountManager:
    def __init__(self, primary_email, primary_password):
        self.accounts = [{"email": primary_email, "password": primary_password, "provider": "gmail"}]
        self.cooldown_file = os.path.join(os.path.dirname(__file__), "email_cooldown_test.json")
        self.blocked_accounts = {}
        self.providers_config = {
            "gmail": {"host": "smtp.gmail.com", "port": 587},
            "outlook": {"host": "smtp.office365.com", "port": 587},
            "hotmail": {"host": "smtp.office365.com", "port": 587},
            "yahoo": {"host": "smtp.mail.yahoo.com", "port": 587},
            "libero": {"host": "smtp.libero.it", "port": 465},
            "aruba": {"host": "smtps.aruba.it", "port": 465}
        }
        self._carica_account_extra()

    def _carica_account_extra(self):
        extra_path = os.path.join(os.path.dirname(__file__), "accounts_extra.json")
        if os.path.exists(extra_path):
            try:
                with open(extra_path, "r") as f:
                    extra = json.load(f)
                    if isinstance(extra, list):
                        for acc in extra:
                            if "email" in acc and "password" in acc:
                                acc["provider"] = "gmail" if "gmail" in acc["email"] else "other"
                                self.accounts.append(acc)
            except: pass

    def get_next_available(self):
        return self.accounts[0]

# --- TECNICHE DI UMANIZZAZIONE ---
def umanizza_testo(testo):
    variazioni = ["", " ", "  ", "\n", "."]
    return testo + random.choice(variazioni)

# --- INVIO DIRETTO MX ---
def invia_diretto_mx(dest, msg_as_string):
    try:
        dominio = dest.split("@")[-1]
        print(f"    [MX] Ricerca server per {dominio}...", end=" ", flush=True)
        
        mx_servers = []
        
        # Metodo 1: NSLOOKUP (standard)
        try:
            cmd = f"nslookup -type=mx {dominio}"
            output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode(errors='ignore')
            # Regex più flessibile per diversi formati (italiano/inglese/spazi)
            mx_servers = re.findall(r'(?:mail exchanger|scambiatore di posta)\s*=\s*([\w\.-]+)', output, re.IGNORECASE)
        except:
            pass

        # Metodo 2: PowerShell Resolve-DnsName (più affidabile su Windows moderno)
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
        
        mx_server = mx_servers[0].strip(".")
        print(f"Trovato: {mx_server}")
        
        # Se il destinatario è Gmail, dobbiamo stare attenti all'autenticazione
        is_gmail = "google.com" in mx_server.lower()
        sender_email = "info@sicurezza-stradale.it"
        if is_gmail:
            # Gmail è molto severa su SPF. Usiamo un mittente che non ha SPF rigido
            # o proviamo a simulare un invio da un dominio neutro
            sender_email = "test-system@sicurezza-stradale.it"

        print(f"    [MX] Tentativo di connessione a {mx_server} su porta 25...")
        with smtplib.SMTP(mx_server, 25, timeout=15) as server:
            # EHLO deve corrispondere al dominio del mittente
            server.ehlo("sicurezza-stradale.it") 
            server.sendmail(sender_email, dest, msg_as_string)
            print("    [MX] INVIO DIRETTO RIUSCITO!")
            return True
    except Exception as e:
        error_msg = str(e)
        if "timeout" in error_msg.lower():
            print(f"    [MX] ERRORE: Timeout (Porta 25 probabilmente bloccata dal tuo operatore internet)")
        elif "refused" in error_msg.lower():
            print(f"    [MX] ERRORE: Connessione rifiutata dal server destinatario")
        else:
            print(f"    [MX] ERRORE: {error_msg[:100]}")
        return False

def invia_via_form_telefono(num_telefono, messaggio, nome_mittente="Andrea"):
    """Bypass estremo via numero di telefono (SMS/Chiamate)."""
    import requests
    phone_targets = [
        {
            "nome": "ConvieneOnline",
            "url": "https://www.convieneonline.it/wp-admin/admin-ajax.php",
            "data": {"action": "richiedi_preventivo_veloce", "telefono": num_telefono, "nome": nome_mittente}
        },
        {
            "nome": "Prima.it",
            "url": "https://www.prima.it/api/v1/lead",
            "data": {"phone": num_telefono, "source": "organic"}
        }
    ]
    print(f"   [�] Tentativo di relay telefonico...")
    success = False
    for target in phone_targets:
        try:
            print(f"      -> {target['nome']}...", end=" ", flush=True)
            r = requests.post(target["url"], data=target["data"], timeout=8)
            if r.status_code < 400:
                print("OK")
                success = True
            else: print(f"SKIP ({r.status_code})")
        except: print("ERR")
    return success

# --- LOGICA DI TEST ---
def esegui_test(dest_email, manager):
    msg = MIMEMultipart()
    oggetti = [
        "[TEST] Prova invio intelligente",
        "Verifica tecnica sistema email",
        "Test di consegna bypass",
        "Controllo periodico invio"
    ]
    msg["Subject"] = random.choice(oggetti)
    msg["From"]    = f"{CONFIG['tuo_nome']} <{CONFIG['tua_email']}>"
    msg["To"]      = dest_email
    msg["Date"]    = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain="sicurezza-stradale.it")
    
    corpo = umanizza_testo("Questo è un test per verificare se il sistema di bypass funziona.")
    msg.attach(MIMEText(corpo, "plain"))

    print(f"Account principale: {CONFIG['tua_email']}")
    print(f"Destinatario test: {dest_email}")
    
    # 1. TENTATIVO SMTP STANDARD
    print(f"[1] Tentativo tramite SMTP Gmail...")
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=10) as server:
            server.starttls(context=context)
            server.login(CONFIG["tua_email"], CONFIG["email_password"])
            server.sendmail(CONFIG["tua_email"], dest_email, msg.as_string())
            print("    ✅ INVIO SMTP RIUSCITO!")
    except Exception as e:
        error_str = str(e)
        print(f"    ❌ ERRORE SMTP: {error_str}")
        
        if "Daily user sending limit exceeded" in error_str or "5.4.5" in error_str:
            print("\n[!] LIMITE RAGGIUNTO RILEVATO. Attivazione bypass...")
            
            # 2. TENTATIVO ROTAZIONE
            if len(manager.accounts) > 1:
                print(f"[2] Tentativo tramite ROTAZIONE...")
                acc_extra = manager.accounts[1]
                try:
                    with smtplib.SMTP("smtp.gmail.com", 587, timeout=10) as s2:
                        s2.starttls(context=context)
                        s2.login(acc_extra["email"], acc_extra["password"])
                        s2.sendmail(acc_extra["email"], dest_email, msg.as_string())
                        print(f"    ✅ INVIO ROTAZIONE RIUSCITO!")
                        return
                except: print("    ❌ ROTAZIONE FALLITA.")

            # 3. TENTATIVO BYPASS DIRETTO MX
            print(f"[3] Tentativo tramite BYPASS DIRETTO MX...")
            if invia_diretto_mx(dest_email, msg.as_string()):
                print("\n    🚀 BYPASS RIUSCITO!")
                return

            # 4. TENTATIVO GOOGLE SCRIPT (Bypass IP/VPS)
            if CONFIG.get("google_script_url"):
                print(f"[4] Tentativo tramite GOOGLE APPS SCRIPT (VPS Bypass)...")
                if invia_tramite_google_script(dest_email, msg["Subject"], corpo, CONFIG["google_script_url"]):
                    print("\n    🚀 GOOGLE SCRIPT BYPASS RIUSCITO!")
                    return
                else:
                    print("\n    ❌ GOOGLE SCRIPT FALLITO.")

            # 5. TENTATIVO BREVO (SMTP Relay)
            if CONFIG.get("brevo_user") and CONFIG.get("brevo_password"):
                print(f"[5] Tentativo tramite BREVO SMTP RELAY...")
                try:
                    with smtplib.SMTP("smtp-relay.brevo.com", 587, timeout=10) as b_server:
                        b_server.starttls()
                        b_server.login(CONFIG["brevo_user"], CONFIG["brevo_password"])
                        b_server.sendmail(CONFIG["brevo_user"], dest_email, msg.as_string())
                        print("\n    🚀 BREVO SMTP RELAY RIUSCITO!")
                        return
                except Exception as e:
                    print(f"    ❌ BREVO FALLITO: {str(e)[:50]}...")

            # 6. TENTATIVO RELAY TELEFONICO (SMS/CHIAMATE)
            num_tel = CONFIG.get("telefono_destinatario", "")
            if num_tel:
                print(f"[6] Tentativo tramite RELAY TELEFONICO su {num_tel}...")
                if invia_via_form_telefono(num_tel, corpo[:100], CONFIG["tuo_nome"]):
                    print("\n    🚀 RELAY TELEFONICO INVIATO!")
                    return
            else:
                print(f"[6] Salto RELAY TELEFONICO (Manca 'telefono_destinatario' in CONFIG)")

            print("\n    💀 TUTTI I METODI HANNO FALLITO.")
        else:
            print("\n    💀 ERRORE NON DI LIMITE. CONTROLLA CREDENZIALI.")

def test_invio(dest_email):
    manager = EmailAccountManager(CONFIG["tua_email"], CONFIG["email_password"])
    print(f"\n--- AVVIO TEST BYPASS EMAIL (VERSIONE UMANIZZATA) ---")
    print(f"IP PUBBLICO ATTUALE: {get_public_ip()}")
    print("   [💡] Se l'IP è segnalato (es. Spamhaus), usa una VPN o riavvia il router.")
    attesa = random.uniform(2, 5)
    print(f"[*] Simulazione attività umana (attesa {attesa:.1f}s)...")
    time.sleep(attesa)
    esegui_test(dest_email, manager)

if __name__ == "__main__":
    email_prova = input("Inserisci la tua email per ricevere il test: ").strip()
    if email_prova:
        test_invio(email_prova)
    else:
        print("Email non valida.")
