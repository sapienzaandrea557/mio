# Creative Engineering Studio - Portfolio Wizard

Questo è un portfolio professionale moderno sviluppato con **Next.js 14**, focalizzato su performance, animazioni fluide e una gestione integrata dei contatti.

## 🚀 Stack Tecnologico
- **Frontend**: Next.js 14 (App Router), React, Tailwind CSS.
- **Animazioni**: GSAP (ScrollTrigger), Framer Motion.
- **Database/Backend**: Prisma ORM con SQLite (Locale).
- **Icone**: Lucide-React.

## 📂 Struttura del Progetto
- `/src/app`: Route del sito (Home, CRM, API).
- `/src/components`: Componenti UI riutilizzabili (Header, DynamicBackground, ServiceCard).
- `/src/lib`: Configurazioni core (Prisma client).
- `/prisma`: Schema del database e migrazioni.
- `/site_backup`: Backup della versione precedente del sito.

## 🛠️ Funzionalità Chiave
1. **Landing Page Dinamica**: Animazioni avanzate all'avvio e allo scroll.
2. **Sistema di Contatti**: Form integrato che salva i dati in un database locale tramite API Route (`/api/contact`).
3. **CRM Interno**: Dashboard riservata accessibile a `/crm` per visualizzare i messaggi ricevuti.
4. **Ottimizzazione SEO/IA**: Configurazione metadati avanzata per motori di ricerca e crawler IA (attualmente disabilitata via robots per privacy, ma configurata).

## 📊 Gestione Database (CRM)
Il progetto utilizza **Prisma** con un database SQLite locale (`dev.db`).
- **Visualizzazione Dati**: Accedere a `/crm` sul browser o eseguire `npx prisma studio`.
- **Produzione (Vercel)**: Per rendere persistente il salvataggio online, è necessario sostituire SQLite con un database Cloud (es. Supabase/Postgres) aggiornando la `DATABASE_URL` nel file `.env`.

## ⚙️ Comandi Utili
- `npm run dev`: Avvia il server di sviluppo.
- `npx prisma studio`: Apre l'interfaccia grafica per gestire il database.
- `npx prisma migrate dev`: Applica modifiche allo schema del database.

---
*Documentazione generata per futuri sviluppatori o assistenti AI.*
