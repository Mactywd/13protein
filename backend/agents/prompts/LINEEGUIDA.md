# Linee guida per la scrittura dei prompt

Queste linee guida valgono per **tutti** i file `*.txt` in questa cartella. Servono a due
scopi distinti che NON vanno confusi:

1. **Leggibilità del PROMPT** (il file `.txt`): il prompt deve essere leggibile a colpo
   d'occhio da chi lo scrive/mantiene.
2. **Leggibilità dell'OUTPUT** (il messaggio mostrato all'utente finale): per i prompt che
   generano testo conversazionale, l'output deve essere chiaro, scansionabile e d'impatto.

---

## 1. Struttura del file di prompt (leggibilità per chi mantiene)

- **Sezioni in `#`/`##`** con titoli espliciti: `# Role`, `## Task`, `## Requirements`,
  `## Examples`, `## Notes`, `# Language`, `# Input`.
- **Bullet point** per requisiti, regole, vincoli — mai muri di prosa.
- **Grassetto** sulle parole chiave di ogni bullet (`**Language**`, `**Tone**`, `**Format**`).
- **Compatto**: niente ripetizioni, niente frasi ridondanti. Se due regole dicono la stessa
  cosa, fondile. Preferisci una riga densa a tre righe vaghe.
- **Esempi separati per lingua** (Italian / English) e, dove rilevante, per stato/variabile.
- **Placeholder invariati**: ogni `{placeholder}` va lasciato byte-identico (il loader li
  riempie con `str.replace`). Non rinominare, non aggiungere/togliere spazi dentro le graffe.
  Verifica con `backend/scripts/check_prompt_placeholders.py`.

## 2. Struttura dell'OUTPUT generato (leggibilità per l'utente)

Per i prompt che producono un **messaggio conversazionale mostrato all'utente** (non per i
prompt di estrazione/classificazione che restituiscono JSON o una singola parola), chiedi
esplicitamente un output:

- **Scansionabile a colpo d'occhio**: l'utente deve capire cosa fare in 2 secondi.
- **Bullet point (`•`)** quando si elenca più di una cosa (opzioni, dettagli richiesti,
  domande multiple). Mai elenchi "in prosa con virgole" quando un bullet è più chiaro.
- **Grassetto** sulle parole portanti (azioni, concetti chiave, parole su cui far cadere
  l'occhio: **preventivo**, **formato**, **volumi**, **private label**).
- **Frasi brevi**, tono professionale e concreto (dare del "lei" in italiano), mai gergale.
- **Niente muri di testo**: spezza con righe vuote tra blocchi logici.
- **Una CTA chiara** alla fine quando l'utente deve agire (scrivere / cliccare un bottone).

> Eccezione: i prompt di **estrazione/parsing** (`extract_*`, `parse_*`, `filter_*`,
> `generate_*_query`, validator) restituiscono dati strutturati e NON devono adottare lo stile
> conversazionale: per loro vale solo la sezione 1.

## 3. Variazione

- Fornire **più esempi** e chiedere esplicitamente di **ruotare** formulazioni/terminologia
  per evitare ripetizioni tra un turno e l'altro.
- Mantenere però **fissi** gli elementi non negoziabili (CTA esatte, nomi prodotto, struttura
  a bullet) anche quando il resto varia.

## 4. Coerenza di brand

- Lingua: scrivere **interamente** in `{default_language}`, tranne il nome brand
  "13 Protein" e i nomi delle categorie prodotto (restano come da knowledgebase).
- Pubblico: **aziende che cercano un produttore** (brand owner, startup, distributori), mai
  consumatori finali.
- Tono: consulente di produzione competente e concreto, mai robotico, mai venditore aggressivo.
- **Mai inventare** prezzi, MOQ, lead time, certificazioni o numeri: se richiesti, dire che
  serve un preventivo. I due set di numeri del sito (home e About Us) non sono riconciliati:
  se si cita un numero, dire da quale pagina viene.
