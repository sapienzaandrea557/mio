=== SISTEMA DI BYPASS LIMITI GMAIL ===

Il limite di 500/2000 email al giorno di Gmail è un blocco del server.
Questo script ora supporta la ROTAZIONE DEGLI ACCOUNT per superare questo limite.

COME FUNZIONA:
1. Se un account viene bloccato da Google (errore 550 5.4.5), lo script lo segna in un file 'email_cooldown.json'.
2. L'account bloccato verrà escluso per le successive 24 ore.
3. Lo script passerà automaticamente all'account successivo disponibile.

COSA DEVI FARE:
1. Apri il file 'accounts_extra.json'.
2. Inserisci i dati di altri tuoi account Gmail (email e password app).
3. Salva il file e riavvia lo script.

In questo modo, se hai 3 account, potrai inviare fino a 1500-6000 email al giorno invece che solo 500-2000.

NOTA: Per ogni account Gmail, devi generare una "Password per l'App" nelle impostazioni di sicurezza di Google (2FA deve essere attiva).
