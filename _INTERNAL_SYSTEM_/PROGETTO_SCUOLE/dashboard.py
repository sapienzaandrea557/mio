import os
import csv
import json
import imaplib
import threading
import time
import io
from datetime import datetime
from flask import Flask, render_template, jsonify, request, send_file
# Importiamo le funzioni dallo script principale
import scuole_sicurezza_stradale as core

app = Flask(__name__)

# --- STATO GLOBALE ---
process_status = {
    "running": False,
    "last_result": None,
    "progress": 0,
    "message": "In attesa...",
    "logs": []
}

def add_log(msg):
    timestamp = time.strftime("%H:%M:%S")
    process_status["logs"].append(f"[{timestamp}] {msg}")
    if len(process_status["logs"]) > 50:
        process_status["logs"].pop(0)
    process_status["message"] = msg

BASE_DIR = os.path.dirname(__file__)
CSV_SESSIONE = os.path.join(BASE_DIR, "scuole_contattate_sessione.csv")
CSV_STORICO = os.path.join(BASE_DIR, "database_scuole.csv")
SESSION_INFO = os.path.join(BASE_DIR, "session_info.json")

def conta_risposte():
    try:
        if not core.CONFIG["email_password"] or core.CONFIG["email_password"] == "tua_password_app":
            return 0
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(core.CONFIG["tua_email"], core.CONFIG["email_password"])
        mail.select("inbox")
        status, messages = mail.search(None, 'UNSEEN')
        count = len(messages[0].split()) if status == 'OK' else 0
        mail.logout()
        return count
    except:
        return 0

@app.route('/')
def index():
    scuole = []
    if os.path.exists(CSV_SESSIONE):
        with open(CSV_SESSIONE, mode="r", encoding="utf-8") as f:
            scuole = list(csv.DictReader(f))
    
    if os.path.exists(SESSION_INFO):
        with open(SESSION_INFO, "r", encoding="utf-8") as f:
            session_meta = json.load(f)
    else:
        session_meta = {"posizione_centro": "Nessuna", "raggio": 0, "tipo_scuole": "Tutte", "stato": "Pronto"}

    # Calcolo statistiche
    stats = {
        "totale": len(scuole),
        "con_email": len([s for s in scuole if s.get('email') and s.get('email') != '---']),
        "risposte": conta_risposte(), 
        "max_radius": 20 # Default
    }
    
    # Calcolo raggio massimo reale dai dati
    if scuole:
        radii = []
        for s in scuole:
            try:
                r = float(s.get('distanza_km', 0))
                radii.append(r)
            except:
                continue
        if radii:
            stats["max_radius"] = int(max(radii)) + 1

    return render_template('index.html', scuole=scuole, stats=stats, core=core)

@app.route('/api/update_config', methods=['POST'])
def update_config():
    data = request.json
    for key, value in data.items():
        if key in core.CONFIG:
            core.CONFIG[key] = value
    return jsonify({"status": "updated", "config": core.CONFIG})

@app.route('/api/update_email', methods=['POST'])
def update_email():
    data = request.json
    # Salviamo i nuovi valori globalmente nel modulo core
    core.OGGETTO_CUSTOM = data.get('subject', 'ciao')
    core.CORPO_CUSTOM = data.get('body', 'ciao')
    return jsonify({"status": "updated"})

@app.route('/api/start_search', methods=['POST'])
def start_search():
    if process_status["running"]:
        return jsonify({"error": "Un processo è già in corso"}), 400
    
    data = request.json
    mode = data.get('mode', 'new')
    addr = data.get('address')
    radius = int(data.get('radius', 20)) if data.get('radius') else None
    stype = data.get('type', 'tutte')
    regione = data.get('regione')
    provincia = data.get('provincia')
    denominazione = data.get('denominazione')

    def run_task():
        process_status["running"] = True
        process_status["logs"] = []
        
        if mode == 'reload':
            add_log("Ricaricamento dati sessione precedente...")
            add_log("Dati sessione ricaricati con successo. Operazione completata.")
            process_status["running"] = False
            return

        filter_desc = []
        if addr: filter_desc.append(f"Indirizzo: {addr} ({radius}km)")
        if regione: filter_desc.append(f"Regione: {regione}")
        if provincia: filter_desc.append(f"Provincia: {provincia}")
        if denominazione: filter_desc.append(f"Nome: {denominazione}")
        filter_desc.append(f"Tipo: {stype}")

        add_log(f"Inizio ricerca - {' | '.join(filter_desc)}")
        try:
            # Override temporaneo del print per catturare i log
            import builtins
            original_print = builtins.print
            def custom_print(*args, **kwargs):
                msg = " ".join(map(str, args))
                add_log(msg)
                original_print(*args, **kwargs)
            builtins.print = custom_print
            
            count = core.esegui_ricerca_e_salva(
                indirizzo=addr, 
                raggio=radius, 
                tipo_scuole=stype,
                regione=regione,
                provincia=provincia,
                denominazione=denominazione
            )
            
            builtins.print = original_print
            add_log(f"Ricerca completata! Trovate {count} scuole.")
        except Exception as e:
            add_log(f"ERRORE: {str(e)}")
        finally:
            process_status["running"] = False

    threading.Thread(target=run_task).start()
    return jsonify({"status": "started"})

# --- TRACKING APERTURE ---
TRACKING_LOGS = "DATA/email_tracking.json"

def log_email_open(email_id):
    if not os.path.exists(os.path.dirname(TRACKING_LOGS)):
        os.makedirs(os.path.dirname(TRACKING_LOGS))
    
    data = {}
    if os.path.exists(TRACKING_LOGS):
        with open(TRACKING_LOGS, "r") as f:
            data = json.load(f)
    
    if email_id not in data:
        data[email_id] = {
            "opens": 0,
            "first_open": None,
            "last_open": None,
            "history": []
        }
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data[email_id]["opens"] += 1
    if not data[email_id]["first_open"]:
        data[email_id]["first_open"] = now
    data[email_id]["last_open"] = now
    data[email_id]["history"].append({
        "timestamp": now,
        "ip": request.remote_addr,
        "ua": request.user_agent.string
    })
    
    with open(TRACKING_LOGS, "w") as f:
        json.dump(data, f, indent=4)

@app.route('/t/<email_id>.png')
def tracking_pixel(email_id):
    # Log dell'apertura
    try:
        log_email_open(email_id)
    except Exception as e:
        print(f"Errore log tracking: {e}")
    
    # Restituisce un'immagine 1x1 trasparente
    pixel_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
    return send_file(
        io.BytesIO(pixel_data),
        mimetype='image/png',
        download_name='pixel.png'
    )

@app.route('/api/stats/email')
def email_stats():
    stats = {
        "sent": 0,
        "opens": 0,
        "bounces": 0,
        "logs": []
    }
    
    # Conta email inviate dal CSV
    if os.path.exists(CSV_SESSIONE):
        with open(CSV_SESSIONE, mode="r", encoding="utf-8") as f:
            scuole = list(csv.DictReader(f))
            stats["sent"] = len([s for s in scuole if s.get("email_inviata") == "SI"])

    # Leggi tracking logs
    if os.path.exists(TRACKING_LOGS):
        with open(TRACKING_LOGS, "r") as f:
            tracking_data = json.load(f)
            for eid, info in tracking_data.items():
                stats["opens"] += info.get("opens", 0)
                for entry in info.get("history", []):
                    # Cerchiamo di associare l'ID alla scuola (in un'app reale useremmo un DB)
                    stats["logs"].append({
                        "timestamp": entry["timestamp"],
                        "scuola": info.get("scuola", "Scuola " + eid[:5]),
                        "email": info.get("email", "---"),
                        "ua": entry["ua"]
                    })
    
    # Ordina i log per data decrescente
    stats["logs"].sort(key=lambda x: x["timestamp"], reverse=True)
    stats["logs"] = stats["logs"][:15] # Solo gli ultimi 15
    
    return jsonify(stats)

@app.route('/api/export/csv')
def export_csv():
    if not os.path.exists(CSV_SESSIONE):
        return "Nessun dato da esportare", 404
    
    return send_file(
        CSV_SESSIONE,
        mimetype='text/csv',
        download_name=f'report_scuole_{datetime.now().strftime("%Y%m%d_%H%M")}.csv',
        as_attachment=True
    )

@app.route('/api/send_single', methods=['POST'])
def send_single():
    data = request.json
    email = data.get('email')
    nome = data.get('nome')
    citta = data.get('citta')
    count = int(data.get('count', 1))

    if not email:
        return jsonify({"error": "Email mancante"}), 400

    try:
        # Usiamo le funzioni del core
        success = False
        for _ in range(count):
            obj, text, html = core.crea_email(nome, citta)
            if core.invia_email(email, obj, text, html, ignora_test=False, nome_scuola=nome):
                success = True
                # Aggiorna CSV se necessario (omesso per brevità, ma idealmente andrebbe fatto)
        
        if success:
            return jsonify({"status": "sent"})
        else:
            return jsonify({"error": "Errore durante l'invio"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/status')
def get_status():
    return jsonify(process_status)

@app.route('/api/send_emails', methods=['POST'])
def send_emails():
    if process_status["running"]:
        return jsonify({"error": "Un processo è già in corso"}), 400

    def run_send():
        process_status["running"] = True
        add_log("Preparazione invio email...")
        try:
            scuole = []
            if os.path.exists(CSV_SESSIONE):
                with open(CSV_SESSIONE, mode="r", encoding="utf-8") as f:
                    scuole = list(csv.DictReader(f))
            
            con_email = [s for s in scuole if s.get('email') and s.get('email') != '---' and s.get('email_inviata') != 'SI']
            
            if not con_email:
                add_log("Nessuna email pronta per l'invio.")
                return

            import smtplib, ssl
            context = ssl.create_default_context()
            add_log(f"Connessione al server SMTP per {len(con_email)} email...")
            
            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls(context=context)
                server.login(core.CONFIG["tua_email"], core.CONFIG["email_password"])
                
                for i, s in enumerate(con_email):
                    dest = s.get('email')
                    nome = s.get('nome')
                    citta = s.get('citta')
                    
                    add_log(f"[{i+1}/{len(con_email)}] Invio a: {nome}...")
                    
                    obj, text, html = core.crea_email(nome, citta)
                    if core.invia_email(dest, obj, text, html, nome_scuola=nome):
                        # Aggiorniamo il CSV della sessione
                        s["email_inviata"] = "SI"
                        add_log(f"   [OK] Email inviata con successo.")
                    else:
                        add_log(f"   [ERRORE] Invio fallito.")
                    
                    # Pausa umana tra le email
                    import random
                    time.sleep(random.uniform(core.CONFIG["pausa_min_email"], core.CONFIG["pausa_max_email"]))

                # Salvataggio finale del CSV aggiornato
                with open(CSV_SESSIONE, mode="w", encoding="utf-8", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=scuole[0].keys())
                    writer.writeheader()
                    writer.writerows(scuole)
                
                add_log("Invio massivo completato con successo.")
        except Exception as e:
            add_log(f"ERRORE INVIO: {str(e)}")
        finally:
            process_status["running"] = False

    threading.Thread(target=run_send).start()
    return jsonify({"status": "sending_started"})

@app.route('/api/send_single', methods=['POST'])
def send_single():
    data = request.json
    email = data.get('email')
    nome = data.get('nome')
    citta = data.get('citta', '')
    count = int(data.get('count', 1))
    
    if not email or email == '---':
        return jsonify({"error": "Email non valida"}), 400
        
    sent_count = 0
    obj, body = core.crea_email(nome, citta)
    
    for i in range(count):
        if core.invia_email(email, obj, body):
            sent_count += 1
            if count > 1 and i < count - 1:
                # Utilizziamo i parametri random definiti nelle impostazioni per non sembrare un bot
                pausa = core.random.uniform(core.CONFIG["pausa_min_email"], core.CONFIG["pausa_max_email"])
                time.sleep(pausa)
        else:
            break # Se uno fallisce, ci fermiamo

    if sent_count > 0:
        # Aggiorniamo il CSV della sessione per marcare come inviata
        scuole = []
        if os.path.exists(CSV_SESSIONE):
            with open(CSV_SESSIONE, mode="r", encoding="utf-8") as f:
                scuole = list(csv.DictReader(f))
            for s in scuole:
                if s['email'] == email:
                    s['email_inviata'] = 'SI'
            core.esporta_csv(scuole, CSV_SESSIONE)
        return jsonify({"status": "success", "sent": sent_count})
    else:
        return jsonify({"status": "failed", "error": "Invio fallito"}), 500

@app.route('/api/deep_search', methods=['POST'])
def deep_search():
    if process_status["running"]:
        return jsonify({"error": "Un processo è già in corso"}), 400
    
    data = request.json
    nome = data.get('nome')
    citta = data.get('citta', '')
    
    def run_deep():
        process_status["running"] = True
        process_status["logs"] = []
        add_log(f"Inizio Ricerca Approfondita per: {nome}...")
        try:
            email, motore = core.cerca_email_web(nome, citta, approfondita=True)
            if email:
                add_log(f"   [OK] Email trovata tramite {motore}: {email}")
                # Aggiorniamo il CSV
                scuole = []
                if os.path.exists(CSV_SESSIONE):
                    with open(CSV_SESSIONE, mode="r", encoding="utf-8") as f:
                        scuole = list(csv.DictReader(f))
                    for s in scuole:
                        if s['nome'] == nome:
                            s['email'] = email
                            s['metodo'] = motore
                    core.esporta_csv(scuole, CSV_SESSIONE)
                add_log("Dati aggiornati con successo. Operazione completata.")
            else:
                add_log("   [FALLITO] Nessuna email trovata anche con ricerca profonda.")
                add_log("Operazione completata.")
        except Exception as e:
            add_log(f"ERRORE: {str(e)}")
        finally:
            process_status["running"] = False

    threading.Thread(target=run_deep).start()
    return jsonify({"status": "started"})

@app.route('/api/deep_search_all', methods=['POST'])
def deep_search_all():
    if process_status["running"]:
        return jsonify({"error": "Un processo è già in corso"}), 400
    
    def run_mass_deep():
        process_status["running"] = True
        process_status["logs"] = []
        add_log("Avvio Ricerca Profonda Massiva per tutte le scuole senza email...")
        
        try:
            scuole = []
            if os.path.exists(CSV_SESSIONE):
                with open(CSV_SESSIONE, mode="r", encoding="utf-8") as f:
                    scuole = list(csv.DictReader(f))
            
            senza_email = [s for s in scuole if not s.get('email') or s.get('email') == '---' or s.get('email') == '']
            
            if not senza_email:
                add_log("Nessuna scuola trovata senza email. Operazione completata.")
                return

            add_log(f"Trovate {len(senza_email)} scuole da analizzare. Procedo...")
            
            trovate = 0
            # Usiamo un piccolo pool per non essere troppo aggressivi con i motori di ricerca
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = {executor.submit(core.cerca_email_web, s['nome'], s['citta'], True): s for s in senza_email}
                
                for future in futures:
                    scuola = futures[future]
                    try:
                        email, motore = future.result()
                        if email:
                            scuola['email'] = email
                            scuola['metodo'] = motore
                            trovate += 1
                            add_log(f"   [OK] {scuola['nome']} -> {email} ({motore})")
                            # Salvataggio incrementale
                            core.esporta_csv(scuole, CSV_SESSIONE)
                    except Exception as e:
                        add_log(f"   [ERRORE] {scuola['nome']}: {str(e)}")
            
            add_log(f"Ricerca Massiva completata! Trovate {trovate} nuove email. Operazione completata.")
        except Exception as e:
            add_log(f"ERRORE MASSIVO: {str(e)}")
        finally:
            process_status["running"] = False

    threading.Thread(target=run_mass_deep).start()
    return jsonify({"status": "started"})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
