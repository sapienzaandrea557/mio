# Documentazione Tecnica - Progetto Super Agents (Scuole & Giga)

## 1. Architettura del Sistema
Il progetto è diviso in due moduli principali:
- **CORE_SCUOLE**: Gestione ricerca scuole, email automation e dashboard.
- **CORE_GIGA**: Script per la saturazione della banda (ottimizzazione consumo Giga).

### CORE_SCUOLE
- `scuole_sicurezza_stradale.py`: Il motore principale. Gestisce le query a OSM Overpass, l'arricchimento dati tramite MIUR Open Data e l'invio email.
- `dashboard.py`: Web Server Flask che fornisce un'interfaccia UI per gestire le ricerche e visualizzare le statistiche.
- `templates/`: Contiene la UI (index.html) e i template email personalizzabili.
- `DATA/`: Database CSV, log di tracking e database MIUR locale.

### CORE_GIGA
- `bandwidth_eater_ultimate.py`: Script asincrono (aiohttp) per il download massivo da CDN veloci (Microsoft, Nvidia, Ubuntu, etc.) per massimizzare il consumo di dati.

## 2. Funzionalità Avanzate
### Ricerca Scuole
- **Filtri**: Supporto per Regione, Provincia, Denominazione e Tipo di Istituto (Medie, Superiori).
- **MIUR Integration**: Sincronizzazione automatica con gli Open Data del Ministero dell'Istruzione per ottenere email certificate (PEO/PEC) e codici meccanografici.

### Modulo Email
- **Tracking**: Pixel trasparente 1x1 inserito nelle email HTML per tracciare le aperture in tempo reale.
- **Bounce Management**: Funzione `controlla_bounce` che scansiona la casella IMAP alla ricerca di errori di consegna (DAEMON/Failure).
- **Template**: Sistema di placeholder `{{nome_scuola}}`, `{{citta}}` per email personalizzate.

### Dashboard
- **Statistiche**: Visualizzazione real-time di email inviate, aperture e bounce rate.
- **Export**: Generazione di report CSV dettagliati per sessione.

## 3. Installazione e Setup
1. Installa le dipendenze: `pip install -r requirements.txt`
2. Configura le credenziali in `scuole_sicurezza_stradale.py` (sezione CONFIG).
3. Avvia la dashboard: `python dashboard.py`
4. Accedi a `http://localhost:5000`

## 4. Procedure DevOps
### Monitoraggio
Lo script `monitor_system.py` può essere utilizzato per verificare lo stato dei servizi (Overpass API, SMTP Server, MIUR Data).

### Deployment
Per aggiornare il sistema:
1. `git pull origin main`
2. `pip install -r requirements.txt` (se ci sono nuovi pacchetti)
3. Riavviare il processo `dashboard.py`.

---
*Ultimo aggiornamento: Aprile 2026*
