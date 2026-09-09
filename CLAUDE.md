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
  Weight Management & Meal Solutions · Drinks, Shots & Gels · Stick Packs · Skincare & Cosmetics
- Numeri dichiarati sul sito: 800+ materie prime a stock, 150+ formule custom sviluppate,
  10M+ unità/anno, 30+ paesi serviti

Il form contatti in `knowledgebase/site/forms.md` è di fatto il **flusso di qualificazione
lead** che il sito usa oggi (chi sei → cosa vuoi creare → formato preferito → descrizione
progetto). È il riferimento più utile per progettare la conversazione dell'agente.

## Struttura

```
proteitobu6d54as_cjgw1.csv   sorgente, 767 MB — dump WordPress, NON committare
tools/                       pipeline di estrazione
knowledgebase/               output generato, 304 KB — NON modificare a mano
.cache/raw.json              intermedio, 5 MB — rigenerabile
```

## Rigenerare il knowledgebase

```bash
python3 tools/extract_raw.py && python3 tools/build_kb.py
```

Stage 1 legge il CSV da 767 MB (~30 s) e scrive `.cache/raw.json`. Stage 2 lavora solo sulla
cache ed è istantaneo: durante l'iterazione sull'estrattore serve rilanciare solo il secondo.
Nessuna dipendenza esterna, solo stdlib.

Output: `knowledgebase/pages/*.md`, `products/*.md`, `site/*.md`, più due bundle —
`knowledgebase.md` (tutto in un file) e `knowledgebase.jsonl` (176 chunk a livello di
sezione, pronti per l'ingest).

## Com'è fatto il sorgente

Il CSV **non è una tabella**: sono ~76 tabelle WordPress concatenate, ognuna preceduta dal
proprio header. `extract_raw.py` le riconosce dalla firma dell'header e resetta il parsing
quando ne inizia una sconosciuta — non usare offset di riga, cambiano a ogni nuovo export.

Il 92% del file è una sola colonna: `wp_postmeta._elementor_data`, il JSON del page builder,
per il 95% styling. E 5.456 dei 5.892 post sono revisioni (la sola home ne ha ~700 da 330 KB).
**Testo utile: ~40 KB su 767 MB.** Se un numero sembra grande, quasi certamente stai contando
revisioni.

I contenuti delle pagine stanno in `_elementor_data`; quelli delle 7 categorie prodotto **no**
— stanno in campi ripetitore ACF (`customization_options_list_N_testo`,
`list_format_and_packaging_N_testo`). Sono due percorsi di estrazione distinti in `build_kb.py`.

L'HTML dentro Elementor è CRLF e ha tag `<strong>` non chiusi: `html2md()` normalizza i line
ending e riequilibra gli asterischi per riga. Se aggiungi widget, aggiungi un handler in
`widget_md()` — il walk cattura le eccezioni per widget, quindi un widget rotto lascia una
nota `<widget ... non estratto>` invece di svuotare la pagina. Dopo ogni modifica:

```bash
grep -rn "non estratto\|errore parsing" knowledgebase/
```

## Dati personali

Il dump contiene 23 submission di form con nomi/email/telefoni/IP, 2 utenti WP con **hash
delle password**, e log Wordfence con IP. La pipeline scarta tutto questo a monte, in stage 1:
tiene solo `wp_posts`, `wp_postmeta`, `wp_options`. Le email non-`@13protein.com` vengono
mascherate anche quando compaiono nella configurazione dei form.

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
- **I PDF non sono nel dump.** Il CSV è un dump del database: `wp-content/uploads/` non c'è.
  Certificati, cataloghi e condizioni generali sono solo riferimenti in `site/media.csv`. Per
  metterne il contenuto nel knowledgebase servono i file veri dal cliente.
- **Blog vuoto**: i 10 post sono la stessa copia placeholder "Our culture, our values"
- **Una sola scheda prodotto reale** (Vitamin C Effervescent Stick, con tabella nutrizionale);
  le 7 "categorie prodotto" sono pagine di capability, non SKU
- Il dump viene dallo staging `13protein.tobugroup.com`: gli URL interni puntano lì, non a
  `13protein.com`
