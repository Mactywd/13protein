/**
 * Verifica end-to-end dell'interfaccia con Playwright (Chromium preinstallato).
 *
 *   scripts/dev-local.sh && node scripts/e2e-ui.mjs
 *
 * Esegue a mano la stessa sequenza di scripts/e2e-mock.sh cliccando i bottoni e
 * scrivendo i testi, poi apre l'admin. Salva gli screenshot in
 * docs/superpowers/evidence/<data>/. Esce non-zero al primo controllo fallito.
 */
import fs from 'fs';
import path from 'path';

// Playwright non è una dipendenza del progetto: serve solo a questa verifica e
// il suo postinstall scaricherebbe un browser dentro l'immagine Docker.
//   npm i --no-save playwright && node scripts/e2e-ui.mjs
let chromium;
try {
  ({ chromium } = await import('playwright'));
} catch {
  console.error('playwright non installato. Esegui:  npm i --no-save playwright');
  process.exit(2);
}

const BASE = 'http://127.0.0.1:3000';
const DATE = new Date().toISOString().slice(0, 10);
const SHOTS = path.join('docs', 'superpowers', 'evidence', DATE);
fs.mkdirSync(SHOTS, { recursive: true });

const failures = [];
const ok = (msg) => console.log(`  ✓ ${msg}`);
const fail = (msg) => { console.log(`  ✗ ${msg}`); failures.push(msg); };
const check = (cond, msg) => (cond ? ok(msg) : fail(msg));

// I bottoni della chat sono <button> con il testo dell'etichetta. Si prende
// SEMPRE l'ultimo: lo stesso bottone ("Request a quote") ricompare a ogni giro
// di domande, e le righe vecchie restano nel transcript sopra a quella viva.
async function clickLabel(page, label) {
  const button = page.getByRole('button', { name: label, exact: true }).last();
  await button.waitFor({ state: 'visible', timeout: 15000 });
  await button.click();
}

async function type(page, text) {
  const box = page.locator('textarea').first();
  await box.waitFor({ state: 'visible', timeout: 15000 });
  // L'input è disabilitato finché il backend non riapre il turno.
  await page.waitForFunction(() => {
    const el = document.querySelector('textarea');
    return el && !el.disabled;
  }, null, { timeout: 15000 });
  await box.fill(text);
  await box.press('Enter');
}

// PLAYWRIGHT_BROWSERS_PATH punta a /opt/pw-browsers, ma la versione di
// chromium che ci trova può non essere quella che questo @playwright/test si
// aspetta: il primo binario presente va bene, non serve riscaricare nulla.
function chromiumPath() {
  const root = process.env.PLAYWRIGHT_BROWSERS_PATH || '/opt/pw-browsers';
  const candidates = fs.existsSync(root)
    ? fs.readdirSync(root)
        .filter((d) => d.startsWith('chromium'))
        .map((d) => path.join(root, d, 'chrome-linux', 'chrome'))
    : [];
  return candidates.find((p) => fs.existsSync(p));
}

const executablePath = chromiumPath();
const browser = await chromium.launch(executablePath ? { executablePath } : {});
const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
const page = await context.newPage();

const consoleErrors = [];
page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text()); });
page.on('pageerror', (e) => consoleErrors.push(String(e)));

try {
  console.log('1. landing');
  await page.goto(BASE, { waitUntil: 'networkidle' });
  check(await page.getByText('13 Protein').first().isVisible(), 'titolo della landing');
  await clickLabel(page, 'Start');

  console.log('2. qualificazione');
  await clickLabel(page, 'I have a product idea');
  await clickLabel(page, 'Proteins');
  // La card arriva con l'evento carousel, dopo il testo: va attesa, non
  // controllata subito dopo il click.
  await page.getByText('Protein Powders').first().waitFor({ timeout: 15000 });
  ok('card della categoria dal knowledgebase');
  await clickLabel(page, 'Powders');

  console.log('3. progetto');
  await type(page, 'A whey protein for gyms');
  await type(page, 'Target market Italy, 2 kg tubs, chocolate and vanilla, launch in spring');

  console.log('4. domanda sul knowledgebase');
  await type(page, 'Are you certified?');
  await page.getByText('Quality').first().waitFor({ timeout: 15000 });
  ok('la risposta cita la pagina Quality');

  console.log('5. preventivo e contatti');
  await clickLabel(page, 'Request a quote');
  await type(page, 'Mario Rossi, Rossi Nutrition, mario@example.com');
  await clickLabel(page, 'Confirm');

  console.log('6. riepilogo del lead');
  const summary = page.locator('.lead-summary');
  await summary.waitFor({ state: 'visible', timeout: 20000 });
  const text = await summary.innerText();
  check(text.includes('mario@example.com'), 'il riepilogo mostra l\'email');
  check(text.includes('Proteins') || text.includes('proteins'), 'il riepilogo mostra la categoria');
  await page.screenshot({ path: path.join(SHOTS, '01-lead-summary.png'), fullPage: true });
  ok('screenshot 01-lead-summary.png');

  console.log('7. admin');
  await page.goto(`${BASE}/admin`, { waitUntil: 'networkidle' });
  await page.getByPlaceholder('Utente').fill('tester');
  await page.getByPlaceholder('Password').fill('tester-13protein');
  await page.getByRole('button', { name: 'Accedi' }).click();
  await page.locator('.chat-admin-table').waitFor({ timeout: 20000 });
  ok('lista chat caricata');
  await page.locator('.chat-admin-row').first().click();
  await page.locator('.chat-admin-transcript').waitFor({ timeout: 20000 });
  const detail = await page.locator('.chat-admin-container').innerText();
  check(detail.includes('Profilo:'), 'il dettaglio mostra il profilo');
  check(detail.includes('Preventivo:'), 'il dettaglio mostra la richiesta di preventivo');
  await page.screenshot({ path: path.join(SHOTS, '02-admin-chat.png'), fullPage: true });
  ok('screenshot 02-admin-chat.png');

  console.log('8. resoconto');
  await page.goto(`${BASE}/admin/resoconto`, { waitUntil: 'networkidle' });
  await page.getByText('Traffico & Funnel').waitFor({ timeout: 20000 });
  await page.getByText('Qualificazione').first().waitFor({ timeout: 20000 });
  ok('sezioni del resoconto renderizzate');
  await page.screenshot({ path: path.join(SHOTS, '03-resoconto.png'), fullPage: true });
  ok('screenshot 03-resoconto.png');
} catch (err) {
  fail(`eccezione: ${err.message}`);
  await page.screenshot({ path: path.join(SHOTS, 'errore.png'), fullPage: true }).catch(() => {});
} finally {
  await browser.close();
}

console.log('\n9. console del browser');
// React in dev logga warning, non errori: qui la build è di produzione, quindi
// qualunque errore in console è un problema vero.
if (consoleErrors.length === 0) ok('nessun errore in console');
else { console.log(consoleErrors.slice(0, 10).map((e) => `    ${e}`).join('\n')); fail(`${consoleErrors.length} errori in console`); }

console.log();
if (failures.length === 0) console.log(`Tutti i controlli passati. Screenshot in ${SHOTS}`);
else console.log(`CONTROLLI FALLITI (${failures.length}). Screenshot in ${SHOTS}`);
process.exit(failures.length === 0 ? 0 : 1);
