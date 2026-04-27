# Progetto Scuole (Lead Generation & Email Automation)

Questo progetto contiene gli script per la ricerca automatizzata di scuole e l'invio di email.

## File Contenuti
- **scuole_sicurezza_stradale.py**: Lo script principale. Gestisce scraping, estrazione email e invio automatico.
- **dashboard.py**: Script per la visualizzazione dei dati o gestione dell'interfaccia.
- **extract_data.py**: Script ausiliario per l'estrazione dei dati.
- **test_bypass_email.py**: Script di test per le funzionalità di bypass SMTP.
- **database_scuole.csv**: Il database delle scuole contattate.
- **accounts_extra.json**: Configurazioni per account email aggiuntivi.
- **email_cooldown.json**: Stato dei cooldown per gli account email.
- **proxies.json**: Elenco dei proxy utilizzati per evitare blocchi IP.
- **templates/**: Cartella contenente i file HTML per la dashboard (es. `index.html`).
- **AVVIO.BAT**: File batch per avviare la dashboard web in un click.
- **AVVIO_CLI.BAT**: File batch per avviare lo script da riga di comando.
- **MANUALE_... .txt**: Guide tecniche sull'uso del bypass IP e dei relay.

## Come Iniziare
1. **Dashboard Web**: Eseguire `AVVIO.BAT`. L'interfaccia si aprirà automaticamente nel browser all'indirizzo `http://127.0.0.1:5000`.
2. **Riga di Comando**: Eseguire `AVVIO_CLI.BAT` per avviare direttamente la scansione.

## Note Tecniche
Lo script principale e la dashboard sono stati aggiornati per utilizzare percorsi relativi (`os.path.dirname(__file__)`). Tutti i file necessari ("collegati") sono ora raggruppati in questa cartella (`D:\Progetti\Scuole`) per garantire la portabilità del progetto.
