# 13protein — agente AI

Agente conversazionale per **13protein.com**. Il knowledgebase è già stato estratto;
l'agente stesso non è ancora stato costruito.

## Cos'è davvero 13 Protein

Non vende integratori a consumatori né a palestre. È un **contract manufacturer B2B
europeo**: produce integratori per conto di altri brand. L'interlocutore dell'agente è
un'azienda che cerca un produttore, non chi compra proteine per allenarsi.

- Ragione sociale: 13 e Protein Import AB (Svezia) · attiva dal 1997
- Sede/stabilimento: Speditionsvägen 45, 142 50 Skogås · contatto pubblico: info@13protein.com
- Tre linee commerciali: **Private Label** (formula su misura), **White Label**
  (prodotti pronti a scaffale), **Rebranding** (formula e packaging pronti, spedizione 48-72h)
- 7 categorie prodotto: Protein Powders · Performance & Training · Health & Wellness ·
  Weight Management & Meal Solutions · Drinks, Shots & Gels · Stick Packs & Single Servings ·
  Skincare & Cosmetics
- Numeri dichiarati: la home e la About Us ne espongono **due set diversi**, non riconciliati.
  Home: 800+ materie prime a stock, 150+ formule custom, 10M+ unità/anno, 30+ paesi.
  About Us: 5 stabilimenti, 55K sqm di produzione, 4K+ prodotti sviluppati/anno, 400+ clienti
  B2B. Se l'agente cita numeri, deve dire da quale pagina vengono.

Il form contatti in `knowledgebase/site/forms.md` è di fatto il **flusso di qualificazione
lead** che il sito usa oggi (chi sei → cosa vuoi creare → formato preferito → descrizione
progetto). È il riferimento più utile per progettare la conversazione dell'agente.

## Struttura

```
proteitobu6d54as_bovu1.sql   sorgente, 1 GB — dump MySQL completo, NON committare
tools/sqldump.py             lettore streaming del dump .sql
tools/extract_raw.py         stage 1 — whitelist delle tabelle
tools/build_kb.py            stage 2 — markdown + bundle
knowledgebase/               output generato, 312 KB — NON modificare a mano
.cache/raw.json              intermedio, 5 MB — rigenerabile

backend/                     FastAPI: state machine, agent, prompt, servizi
server/                      Express: proxy SSE, admin, analytics, retention
src/                         React/Vite: chat cliente e pannello admin
docs/superpowers/            spec e piani di implementazione
```

## Rigenerare il knowledgebase

```bash
python3 tools/extract_raw.py && python3 tools/build_kb.py
```

Stage 1 legge il dump da 1 GB (~2 min) e scrive `.cache/raw.json`. Stage 2 lavora solo sulla
cache ed è istantaneo: durante l'iterazione sull'estrattore serve rilanciare solo il secondo.
Nessuna dipendenza esterna, solo stdlib.

Stage 2 **svuota `pages/`, `products/`, `site/` prima di riscriverli**: senza questo, una
pagina che passa a bozza resterebbe come file orfano (è successo con `insights`).

Output: `knowledgebase/pages/*.md`, `products/*.md`, `site/*.md`, più due bundle —
`knowledgebase.md` (tutto in un file) e `knowledgebase.jsonl` (173 chunk a livello di
sezione, pronti per l'ingest).

## Com'è fatto il sorgente

Dump phpMyAdmin dell'intero database (76 tabelle, prefisso `uytw_`), con extended INSERT.
`sqldump.py` lo legge in streaming con una finestra scorrevole: **non** si può splittare su
`),(` né caricare uno statement intero in memoria — un solo `_elementor_data` arriva a 300 KB
e contiene sia `),(` sia `\n` dentro stringhe quotate.

Il prefisso `uytw_` è di questo export e cambia a ogni nuova installazione: sta in `PFX` in
cima a `extract_raw.py`, è l'unica cosa da toccare se arriva un dump da un altro sito.

6.608 dei 7.059 post sono revisioni. **Testo utile: ~300 KB su 1 GB.** Se un numero sembra
grande, quasi certamente stai contando revisioni.

I contenuti delle pagine stanno in `_elementor_data`; quelli delle 7 categorie prodotto **no**
— stanno in campi ripetitore ACF (`customization_options_list_N_testo`,
`list_format_and_packaging_N_testo`). Sono due percorsi di estrazione distinti in `build_kb.py`.

Elementor scrive anche `copied_media_ids` / `referenced_media_ids` su ogni pagina: sono liste
di ID, non contenuto — `ACF_SKIP` le scarta, altrimenti finiscono in coda a ogni pagina.

L'HTML dentro Elementor è CRLF e ha tag `<strong>` non chiusi: `html2md()` normalizza i line
ending e riequilibra gli asterischi per riga. Se aggiungi widget, aggiungi un handler in
`widget_md()` — il walk cattura le eccezioni per widget, quindi un widget rotto lascia una
nota `<widget ... non estratto>` invece di svuotare la pagina. Dopo ogni modifica:

```bash
grep -rn "non estratto\|errore parsing" knowledgebase/
```

## Dati personali

Il dump contiene submission di form con nomi/email/telefoni/IP (`uytw_e_submissions*`),
utenti WP con **hash delle password** (`uytw_users`, `uytw_usermeta`), log Wordfence con IP
e secret 2FA (`uytw_wf*`, `uytw_wfls_*`). Stage 1 lavora per **whitelist**, non per
esclusione: entra solo `posts`, `postmeta`, `options`, le tabelle di tassonomia e
`icl_languages`/`icl_translations`. Tutto il resto non viene nemmeno letto. Le email
non-`@13protein.com` vengono mascherate anche quando compaiono nella configurazione dei form.

`options` è a sua volta filtrato per nome (`OPT_KEEP` / `OPT_PREFIX` in `extract_raw.py`):
la tabella è il deposito di stato di tutti i plugin, compresi Wordfence e i login limiter.

Il knowledgebase generato è pulito — verificabile con:

```bash
grep -rhoE '[a-zA-Z0-9._+-]+@[a-zA-Z0-9.-]+\.[a-z]{2,}' knowledgebase/ | sort -u
```

Deve restituire solo `info@13protein.com`. Se estendi la pipeline ad altre tabelle, ricontrolla.

## Buchi noti nel contenuto

Da non colmare inventando: se l'agente deve rispondere su questi temi, servono informazioni
dal cliente.

- **Nessun prezzo, MOQ o lead time** in tutto il sito, tranne le 48-72h del Rebranding:
  ogni percorso finisce su un CTA "Get a Quote"
- **Certificazioni: solo nel footer, mai nel testo.** La pagina Quality parla genericamente di
  "internationally recognized standards"; i certificati veri sono linkati nel footer
  (`site/navigation.md`) — FSSC 22000 per i due stabilimenti (SKRUV e Skogås/Stockholm) e
  produzione biologica (Ekologisk Produktion). Esistono anche le Condizioni Generali
  White Label B2B in PDF.
- **I PDF non sono nel dump.** È un dump del database: `wp-content/uploads/` non c'è.
  Certificati, cataloghi e condizioni generali sono solo riferimenti in `site/media.csv`. Per
  metterne il contenuto nel knowledgebase servono i file veri dal cliente.
- **Blog ancora vuoto, ma ora pianificato**: i 10 post sono sempre la stessa copia placeholder
  Lorem ipsum "Our culture, our values". Sono però stati categorizzati (Product & formulation
  insights ×8, Market & brand strategy, Manufacturing & compliance, più i tag Brand building
  tips / Top in the community). Le tassonomie dicono su quali temi il cliente *vuole* parlare;
  non sono contenuto che l'agente possa citare.
- **Insights è tornato bozza** ed è sparito dal menu header/footer. Il file
  `pages/insights.md` è marcato `status: draft` — non è contenuto live.
- **WPML installato, contenuti non tradotti.** Sono attive 4 lingue (en, es, it, sv) ma
  esistono solo traduzioni dei nomi di categoria: pagine, prodotti e post stanno solo in `en`.
  Il sito è di fatto monolingua. Se l'agente deve rispondere in italiano o spagnolo, traduce
  lui — non c'è copy approvato dal cliente in quelle lingue.
- **Una sola scheda prodotto reale** (Vitamin C Effervescent Stick, con tabella nutrizionale);
  le 7 "categorie prodotto" sono pagine di capability, non SKU
- Il dump viene dallo staging `ai.13protein.tobugroup.com` (non più `13protein.tobugroup.com`):
  gli URL interni e quelli dei PDF puntano lì, non a `13protein.com`
- Su staging restano pubblicate o in bozza 7 copie superate della home (`home-500`,
  `home-old`, `home-old-1..5`). La pipeline le esclude (`LEGACY` in `build_kb.py`): sono
  duplicati del copy della home e sporcherebbero l'indice di retrieval.
