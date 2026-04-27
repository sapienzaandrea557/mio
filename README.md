# 🚀 SUPER AGENTE WEB v9.1 (Intelligent Search AI)

Questo progetto è un agente di automazione web intelligente basato su **Playwright** e **TypeScript**. L'obiettivo è navigare qualsiasi sito web per raggiungere obiettivi descritti in linguaggio naturale (es. "fai abbonamento annuale pro+").

## 🧠 Architettura del Sistema

L'agente non usa selettori statici, ma un **Motore Semantico Universale** che analizza il DOM in tempo reale ad ogni passo.

### 1. Motore di Scoring (Semantic Scoring Engine)
Ogni elemento cliccabile viene valutato secondo diversi criteri:
- **Intento Transazionale**: Priorità assoluta a termini come "buy", "upgrade", "select", "checkout".
- **Eredità Contestuale**: Se un bottone è dentro un container (es. una card) che contiene la parola chiave dell'obiettivo (es. "Pro+"), riceve un bonus massiccio.
- **Heuristics Visuali**: Analisi CSS per identificar "veri" bottoni (background-color, bordi arrotondati, cursore pointer).
- **Anti-Loop**: Esclusione automatica di elementi già cliccati che non hanno portato a cambi di stato.
- **Penalizzazione Opposti**: Se l'utente vuole il piano "annuale", l'agente penalizza attivamente i bottoni che contengono "mensile".

### 2. Auto-Debug (Deep DOM Fallback)
Se il motore standard non trova azioni valide, scatta la fase di **Deep Debug**:
- L'IA analizza i blocchi di contenuto (Pricing Cards, Sezioni) invece dei singoli bottoni.
- Identifica il blocco più pertinente e forza il click sul bottone principale all'interno di quel blocco.

### 3. Gestione Moduli v8.6 (Novità)
- **Login Proattivo**: L'IA rileva campi di input (Email/Password) in tempo reale. Se serve un account per procedere, si ferma e chiede i dati all'utente.
- **Supporto Step-by-Step**: Gestisce login divisi su più pagine (es. prima Email, poi Password) premendo automaticamente "Next" o "Continua".
- **Dati di Pagamento**: Rileva campi per carte di credito durante il checkout.

### 4. Analisi Semantica v9.1 (Novità)
- **Comando `analizza [query]`**: Ricerca intelligente di elementi (es. `analizza telefono`).
- **Persistence & Auto-Refresh**: Dopo aver selezionato un numero, l'agente aggiorna **automaticamente** la lista dei risultati in tempo reale, mantenendo la stessa query di ricerca.
- **Cache Invalidation**: Ogni analisi forza una scansione fresca del DOM per garantire che i dati riflettano sempre lo stato più recente della pagina.
- **Ordinamento per Rilevanza**: I risultati sono pesati in base all'intento semantico e ai sinonimi (es. `telefono` -> `phone`, `mobile`).

### 5. Apprendimento (Self-Learning)
L'agente salva i successi e i fallimenti nel file `memory.json`.
- **Successo**: Rafforza l'associazione tra obiettivo e testo del bottone.
- **Fallimento**: Genera un report in `ai_fail_report.json` con lo storico delle azioni.

## 📂 Struttura File
- `web_explorer.ts`: Cuore pulsante dell'IA.
- `memory.json`: Database della conoscenza acquisita.
- `README.md`: Documentazione tecnica (questa guida).
- `start_agent.bat`: Script di installazione e avvio completo.
- `avvio_rapido.bat`: Lancio immediato (URL di Trae predefinito).

## 🚀 Avvio
1. Esegui `start_agent.bat` per la prima volta.
2. All'avvio, puoi premere **INVIO** per andare subito su `https://www.trae.ai/`.

---
*Creato per essere intelligente, variabile e pronto a tutto.*
