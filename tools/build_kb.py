#!/usr/bin/env python3
"""Stage 2 — turn .cache/raw.json into a readable knowledgebase.

Page bodies live as Elementor JSON in wp_postmeta._elementor_data. We walk that
tree and emit markdown per widget type, keeping content settings and discarding
the ~95% that is styling. Product pages carry no Elementor data — their content
is in ACF repeater fields on wp_postmeta instead.

Output: knowledgebase/{pages,products,site}/*.md + knowledgebase.md + .jsonl
"""
import json, re, os, html, csv, sys, collections
import phpser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT  = os.path.join(ROOT, "knowledgebase")
SITE = "https://13protein.tobugroup.com"      # origin of the dump (staging)

raw = json.load(open(os.path.join(ROOT, ".cache", "raw.json")))
posts, meta, options = raw['posts'], raw['meta'], raw['options']

# stage 1 keeps the raw WP column names; alias them to the short names used below
ALIAS = {'post_type': 'type', 'post_mime_type': 'mime', 'post_name': 'name',
         'post_modified': 'modified', 'post_status': 'status', 'post_title': 'title',
         'post_content': 'content', 'post_excerpt': 'excerpt', 'post_date': 'date',
         'post_parent': 'parent', 'post_author': 'author'}
for _p in posts.values():
    for _k, _short in ALIAS.items():
        if _k in _p: _p[_short] = _p[_k]

# ---------------------------------------------------------------- helpers
def html2md(s):
    if not s: return ""
    s = s.replace('\r\n', '\n').replace('\r', '\n')     # source HTML is CRLF
    s = re.sub(r'<(style|script)[^>]*>.*?</\1>', '', s, flags=re.I | re.S)
    s = re.sub(r'</t[hd]>', ' | ', s, flags=re.I)          # tables -> pipe rows
    s = re.sub(r'</tr>', '\n', s, flags=re.I)
    s = re.sub(r'<h([1-6])[^>]*>(.*?)</h\1>', lambda m: "\n"+"#"*min(int(m.group(1))+2,6)+" "+m.group(2)+"\n", s, flags=re.I|re.S)
    s = re.sub(r'<a\b[^>]*href="([^"]*)"[^>]*>(.*?)</a>', r'[\2](\1)', s, flags=re.I|re.S)
    # match emphasis in pairs so nested/unclosed tags don't leak stray markers
    for tag, mark in (('strong|b', '**'), ('em|i', '*')):
        s = re.sub(rf'<({tag})\b[^>]*>(.*?)</\1>', rf'{mark}\2{mark}', s, flags=re.I | re.S)
        s = re.sub(rf'</?({tag})\b[^>]*>', '', s, flags=re.I)
    s = re.sub(r'<br\s*/?>', '\n', s, flags=re.I)
    s = re.sub(r'</p\s*>', '\n\n', s, flags=re.I)
    s = re.sub(r'<li[^>]*>', '- ', s, flags=re.I)
    s = re.sub(r'</li>', '\n', s, flags=re.I)
    s = re.sub(r'</?(ul|ol)[^>]*>', '\n', s, flags=re.I)
    s = re.sub(r'<[^>]+>', '', s)
    s = html.unescape(s)
    s = re.sub(r'[ \t\xa0]+', ' ', s)
    s = re.sub(r'^[ \t]+|[ \t]+$', '', s, flags=re.M)     # div indentation
    lines = []
    for l in s.split("\n"):
        if not l.strip(' |*'): continue
        if l.count('**') % 2: l = l.replace('**', '', 1)   # source HTML has unclosed <strong>
        lines.append(l)
    s = "\n".join(lines)
    s = re.sub(r'^(#{1,6} .*)$', r'\n\1\n', s, flags=re.M)   # breathe around headings
    s = re.sub(r'\n{3,}', '\n\n', s)
    return s.strip()

def clean(s):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', s or ''))).strip()

JUNK = re.compile(r'^(?:[\W\d_]*|lorem ipsum.*|%%.*)$', re.I)

EMAIL = re.compile(r'[\w.+-]+@[\w.-]+\.\w+')
PUBLIC_MAIL = re.compile(r'@13protein\.com$', re.I)
def redact_mail(s):
    """Keep the public 13protein.com addresses, mask internal/personal ones —
    this KB is meant to be fed to an agent that answers end users."""
    return EMAIL.sub(lambda m: m.group() if PUBLIC_MAIL.search(m.group()) else '[email interna redatta]', s or '')
def useful(s):
    return bool(s) and len(s) > 1 and not JUNK.match(s)

# ------------------------------------------------- attachments / media map
media = {}
for pid, p in posts.items():
    if p['type'] == 'attachment':
        f = meta.get(pid, {}).get('_wp_attached_file') or p['guid'].split('/uploads/')[-1]
        media[pid] = {'id': pid, 'file': f, 'mime': p['mime'], 'title': p['title'],
                      'alt': meta.get(pid, {}).get('_wp_attachment_image_alt', ''),
                      'url': p['guid']}
def mref(v):
    """Resolve an image setting (dict with id/url) or a bare attachment id."""
    if isinstance(v, dict):
        i = str(v.get('id') or '')
        if i in media: return media[i]['file']
        return (v.get('url') or '').split('/uploads/')[-1]
    v = str(v)
    return media[v]['file'] if v in media else ''

# ---------------------------------------------------------- elementor walk
HEAD_TAG = {'h1':'#','h2':'##','h3':'###','h4':'####','h5':'#####','h6':'######'}

def widget_md(el, out, forms):
    st = el.get('settings') or {}
    w  = el.get('widgetType')
    if w == 'heading':
        t = clean(st.get('title'))
        if useful(t):
            lvl = HEAD_TAG.get(str(st.get('header_size') or st.get('html_tag') or 'h3').lower(), '###')
            out.append(f"{lvl} {t}")
    elif w == 'text-editor':
        t = html2md(st.get('editor'))
        if useful(t): out.append(t)
    elif w == 'button':
        t = clean(st.get('text')); link = (st.get('link') or {}).get('url', '') if isinstance(st.get('link'), dict) else ''
        if useful(t): out.append(f"[CTA] {t}" + (f" -> {link}" if link else ""))
    elif w == 'icon-box':
        t, d = clean(st.get('title_text')), html2md(st.get('description_text'))
        if useful(t) or useful(d): out.append(f"**{t}**" + (f" — {d}" if useful(d) else ""))
    elif w == 'icon-list':
        items = [clean(i.get('text')) for i in (st.get('icon_list') or []) if useful(clean(i.get('text')))]
        if items: out.append("\n".join(f"- {i}" for i in items))
    elif w == 'counter':
        g = lambda k: '' if isinstance(st.get(k), (dict, list)) else str(st.get(k, '') or '')
        num = f"{g('prefix')}{g('ending_number')}{g('suffix')}".strip()
        t = clean(st.get('title'))
        if num or useful(t): out.append(f"**{num}** {t}".strip())
    elif w == 'image':
        f = mref(st.get('image')); alt = clean(st.get('caption'))
        if f: out.append(f"![{alt}]({f})")
    elif w in ('image-carousel', 'media-carousel', 'nested-carousel'):
        for s in (st.get('carousel') or st.get('slides') or []):
            t = clean(s.get('slide_title') or s.get('title'))
            f = mref(s.get('image') or s.get('background_image') or {})
            if useful(t) or f: out.append(f"- slide: {t} {('['+f+']') if f else ''}".strip())
    elif w == 'form':
        forms.append(st)
        out.append(f"[FORM] {clean(st.get('form_name')) or 'form'} — campi: " +
                   ", ".join(clean(f.get('field_label') or f.get('placeholder') or f.get('field_type'))
                             for f in (st.get('form_fields') or [])))
    elif w == 'mega-menu':
        items = [clean(i.get('item_title')) for i in (st.get('menu_items') or []) if useful(clean(i.get('item_title')))]
        if items: out.append(f"[MENU {clean(st.get('menu_name'))}] " + " | ".join(items))
    elif w == 'loop-grid':
        out.append(f"[LOOP DINAMICO] post_type={st.get('post_query_post_type') or 'post'}")
    elif w == 'google_maps':
        out.append(f"[MAPPA] {clean(st.get('address'))}")
    elif w in ('html', 'shortcode'):
        # some pages (e.g. the nutrition sheets) are built entirely from raw HTML
        t = html2md(st.get('html') or st.get('shortcode') or '')
        t = re.sub(r'\n?\s*\|\s*\n', '\n', t)              # drop empty table cells
        if useful(t): out.append(t)
    elif w in ('social-icons',):
        links = []
        for i in (st.get('social_icon_list') or []):
            icon = (i.get('social_icon') or {}).get('value', '')
            if isinstance(icon, dict): icon = icon.get('url', '').split('/')[-1]
            url = (i.get('link') or {}).get('url') or ''
            if url or icon: links.append(f"{icon} {url}".strip())
        if links: out.append("[SOCIAL] " + " | ".join(links))

def walk(node, out, forms):
    if isinstance(node, list):
        for c in node: walk(c, out, forms)
    elif isinstance(node, dict):
        if node.get('elType') == 'widget':
            try: widget_md(node, out, forms)
            except Exception as e: out.append(f"<widget {node.get('widgetType')} non estratto: {e}>")
        # nested repeaters that themselves hold elements (tabs, carousels, accordions)
        for it in ((node.get('settings') or {}).get('tabs') or []):
            t = clean(it.get('tab_title')); c = html2md(it.get('tab_content'))
            if useful(t): out.append(f"**{t}**")
            if useful(c): out.append(c)
        for c in (node.get('elements') or []): walk(c, out, forms)

def page_md(pid):
    d = meta.get(pid, {}).get('_elementor_data')
    out, forms = [], []
    if d:
        try: walk(json.loads(d), out, forms)
        except Exception as e: out.append(f"<errore parsing elementor: {e}>")
    if not out:                                  # classic editor fallback
        out = [html2md(posts[pid]['content'])]
    seen, ded = set(), []
    for b in out:
        b = b.strip()
        if b and b not in seen:
            seen.add(b); ded.append(b)
    return "\n\n".join(ded), forms

# ---------------------------------------------------------------- ACF
ACF_SKIP = re.compile(r'^(_|footnotes$|ao_post_optimize$)')
def acf(pid):
    return {k: v for k, v in meta.get(pid, {}).items()
            if not ACF_SKIP.match(k) and not k.startswith(('_elementor', '_yoast', '_wp', 'inline_featured'))
            and v not in ('', 'field_')}

def seo(pid):
    m = meta.get(pid, {})
    return {'seo_title': m.get('_yoast_wpseo_title', ''), 'seo_description': m.get('_yoast_wpseo_metadesc', ''),
            'focus_keyword': m.get('_yoast_wpseo_focuskw', '')}

def unphp(v):
    try:
        d = phpser.loads(v)
        return list(d.values()) if isinstance(d, dict) else d
    except Exception:
        return v

# ================================================================ OUTPUT
for d in ('pages', 'products', 'site'):
    os.makedirs(f"{OUT}/{d}", exist_ok=True)

def slugfile(p):
    return re.sub(r'[^a-z0-9-]+', '-', (p['name'] or p['ID']).lower()).strip('-') or p['ID']

def fm(**kw):
    lines = ["---"]
    for k, v in kw.items():
        if v in ('', None, []): continue
        if isinstance(v, list): v = "[" + ", ".join(f'"{x}"' for x in v) + "]"
        else: v = json.dumps(str(v), ensure_ascii=False)
        lines.append(f"{k}: {v}")
    return "\n".join(lines + ["---", ""])

docs = []          # for the consolidated md + jsonl
all_forms = []

# ---------------------------------------------------------------- PAGES
pages = sorted([p for p in posts.values() if p['type'] == 'page' and p['status'] == 'publish'],
               key=lambda p: int(p['ID']))
blog  = sorted([p for p in posts.values() if p['type'] == 'post' and p['status'] == 'publish'],
               key=lambda p: int(p['ID']))

for p in pages + blog:
    body, forms = page_md(p['ID'])
    all_forms += [(p['name'], f) for f in forms]
    s = seo(p['ID']); a = acf(p['ID'])
    head = fm(title=p['title'], slug=p['name'], url=f"/{p['name']}", type=p['type'],
              post_id=p['ID'], updated=p['modified'][:10], **{k: v for k, v in s.items() if v})
    extra = ""
    if a:
        extra = "\n\n## Campi ACF\n\n" + "\n".join(f"- **{k}**: {clean(str(unphp(v)))[:300]}" for k, v in sorted(a.items()))
    md = f"{head}# {p['title']}\n\n{body}{extra}\n"
    open(f"{OUT}/pages/{slugfile(p)}.md", 'w').write(md)
    docs.append(dict(kind=p['type'], id=p['ID'], title=p['title'], slug=p['name'],
                     url=f"{SITE}/{p['name']}", updated=p['modified'][:10], **s, body=body))

# ---------------------------------------------------------------- PRODUCTS
prods = sorted([p for p in posts.values() if p['type'] == 'product' and p['status'] == 'publish'],
               key=lambda p: int(p['ID']))
for p in prods:
    a = acf(p['ID'])
    def rep(prefix, field='testo'):
        """collect ACF repeater rows: <prefix>_<n>_<field>"""
        rows = []
        for k, v in a.items():
            m = re.match(rf'^{prefix}_(\d+)_{field}$', k)
            if m and clean(v): rows.append((int(m.group(1)), clean(v)))
        return [t for _, t in sorted(rows)]
    cats   = rep('customization_options_list')
    fmts   = rep('list_format_and_packaging')
    imgs   = [media.get(str(i), {}).get('file', str(i)) for i in (unphp(a.get('slideshow_iniziale', '')) or []) if i]
    head = fm(title=clean(p['title']), slug=p['name'], url=f"/{p['name']}", type="product_category",
              post_id=p['ID'], updated=p['modified'][:10], **{k: v for k, v in seo(p['ID']).items() if v})
    md = [head, f"# {clean(p['title'])}", ""]
    if a.get('titolo'):  md += [f"**{clean(a['titolo'])}**", ""]
    if a.get('testo'):   md += [html2md(a['testo']), ""]
    if cats: md += ["## Categorie di prodotto / formulazioni", ""] + [f"- {c}" for c in cats] + [""]
    if fmts: md += ["## Formati e packaging disponibili", ""] + [f"- {c}" for c in fmts] + [""]
    if a.get('frase_finale'): md += ["## Claim di chiusura", "", clean(a['frase_finale']), ""]
    if imgs: md += ["## Media", ""] + [f"- {i}" for i in imgs] + [""]
    body = "\n".join(md[1:])
    open(f"{OUT}/products/{slugfile(p)}.md", 'w').write("\n".join(md))
    docs.append(dict(kind='product_category', id=p['ID'], title=clean(p['title']), slug=p['name'],
                     url=f"{SITE}/{p['name']}", updated=p['modified'][:10], **seo(p['ID']), body=body,
                     categories=cats, formats=fmts))

# ---------------------------------------------------------------- SITE META
plugins = list(unphp(options.get('active_plugins', '')) or [])
site_md = [fm(title="Site metadata", type="site"), "# Metadati del sito", "",
    f"- **Nome**: {options.get('blogname','')}",
    f"- **URL (staging del dump)**: {options.get('siteurl','')}",
    f"- **Lingua admin**: {options.get('WPLANG','')} — contenuti in inglese",
    f"- **Tema**: {options.get('template','')} / child `{options.get('stylesheet','')}`",
    f"- **Pagina iniziale**: post {options.get('page_on_front','')} ({options.get('show_on_front','')})",
    f"- **Struttura permalink**: `{options.get('permalink_structure','')}`",
    "", "## Plugin attivi", ""] + [f"- {x}" for x in plugins] + ["",
    "## Inventario contenuti", "",
    f"- Pagine pubblicate: {len(pages)}",
    f"- Categorie prodotto: {len(prods)}",
    f"- Articoli blog: {len(blog)} (tutti duplicati dello stesso placeholder)",
    f"- Media: {len(media)}", ""]
open(f"{OUT}/site/site-meta.md", 'w').write("\n".join(site_md))

# ---------------------------------------------------------------- NAVIGATION
navs = [p for p in posts.values() if p['type'] == 'elementor_library' and p['status'] == 'publish'
        and re.search(r'header|footer', p['name'] or '', re.I)]
nav_md = [fm(title="Navigazione (header/footer)", type="site"), "# Navigazione", ""]
for p in sorted(navs, key=lambda x: int(x['ID'])):
    b, _ = page_md(p['ID'])
    nav_md += [f"## {p['title']} (`/{p['name']}`)", "", b, ""]
open(f"{OUT}/site/navigation.md", 'w').write("\n".join(nav_md))

# ---------------------------------------------------------------- FORMS
f_md = [fm(title="Form di contatto", type="site"), "# Form del sito", "",
        "_Solo la definizione dei campi. Le 23 submission con dati personali sono escluse dal knowledgebase._", ""]
seen_forms = set()
for page_slug, st in all_forms:
    nm = clean(st.get('form_name'))
    if nm in seen_forms: continue
    seen_forms.add(nm)
    f_md += [f"## {nm}  (su `/{page_slug}`)", "",
             f"- Destinatario: `{redact_mail(st.get('email_to',''))}`",
             f"- Oggetto: {st.get('email_subject','')}",
             f"- Messaggio di successo: {clean(st.get('success_message'))}", "", "### Campi", ""]
    for fl in (st.get('form_fields') or []):
        req = " *(obbligatorio)*" if fl.get('required') in ('true', True, 'yes') else ""
        opt = f" — opzioni: {clean(fl.get('field_options')).replace(chr(10),' / ')}" if fl.get('field_options') else ""
        f_md.append(f"- **{clean(fl.get('field_label')) or clean(fl.get('placeholder')) or fl.get('custom_id','?')}** "
                    f"({fl.get('field_type','text')}){req}{opt}")
    f_md.append("")
open(f"{OUT}/site/forms.md", 'w').write("\n".join(f_md))

# ---------------------------------------------------------------- MEDIA
with open(f"{OUT}/site/media.csv", 'w', newline='') as fh:
    w = csv.writer(fh); w.writerow(['id', 'file', 'mime', 'title', 'alt'])
    for m in sorted(media.values(), key=lambda x: int(x['id'])):
        w.writerow([m['id'], m['file'], m['mime'], m['title'], m['alt']])

# ---------------------------------------------------------------- BUNDLES
with open(f"{OUT}/knowledgebase.md", 'w') as fh:
    fh.write("# 13 Protein — knowledgebase\n\nEstratto da `proteitobu6d54as_cjgw1.csv`. "
             "Un documento per pagina/categoria prodotto.\n\n---\n\n")
    for d in docs:
        fh.write(f"# {d['title']}\n\n> {d['kind']} · `{d['url']}` · agg. {d['updated']}\n\n{d['body']}\n\n---\n\n")

def chunks(d):
    """split a doc into section-level chunks on markdown headings"""
    parts, cur, head = [], [], d['title']
    for line in d['body'].split("\n"):
        if re.match(r'^#{1,4} ', line) and cur:
            parts.append((head, "\n".join(cur).strip())); cur, head = [], line.lstrip('# ').strip()
        elif re.match(r'^#{1,4} ', line):
            head = line.lstrip('# ').strip()
        else:
            cur.append(line)
    if cur: parts.append((head, "\n".join(cur).strip()))
    return [(h, t) for h, t in parts if t]

with open(f"{OUT}/knowledgebase.jsonl", 'w') as fh:
    for d in docs:
        for i, (h, t) in enumerate(chunks(d)):
            fh.write(json.dumps({'id': f"{d['slug']}#{i}", 'doc': d['slug'], 'kind': d['kind'],
                                 'url': d['url'], 'page_title': d['title'], 'section': h,
                                 'text': t, 'updated': d['updated']}, ensure_ascii=False) + "\n")

print(f"pagine {len(pages)} · prodotti {len(prods)} · blog {len(blog)} · media {len(media)}")
print(f"chunk jsonl: {sum(len(chunks(d)) for d in docs)}")

# ---------------------------------------------------------------- INDEX
idx = ["# Knowledgebase 13 Protein", "",
       "Generato da `tools/build_kb.py` a partire da `proteitobu6d54as_cjgw1.csv`.",
       "**Non modificare a mano**: ogni rigenerazione sovrascrive.", "",
       "Escluso di proposito: revisioni, config plugin, log Wordfence, utenti WP,",
       "submission dei form (dati personali).", "",
       "## Pagine", ""]
for d in docs:
    if d['kind'] == 'page':
        idx.append(f"- [{d['title']}](pages/{d['slug']}.md) — `{d['url'].replace(SITE,'')}` · {len(d['body'])} B")
idx += ["", "## Categorie prodotto", ""]
for d in docs:
    if d['kind'] == 'product_category':
        idx.append(f"- [{d['title']}](products/{d['slug']}.md) — "
                   f"{len(d.get('categories',[]))} formulazioni, {len(d.get('formats',[]))} formati")
idx += ["", "## Articoli blog", "",
        f"- {len([d for d in docs if d['kind']=='post'])} post, tutti copie dello stesso placeholder "
        "\"Our culture, our values\" — nessun contenuto reale.", "",
        "## Sito", "",
        "- [site/site-meta.md](site/site-meta.md) — stack, plugin, inventario",
        "- [site/navigation.md](site/navigation.md) — header e footer",
        "- [site/forms.md](site/forms.md) — campi dei form (senza submission)",
        "- [site/media.csv](site/media.csv) — 336 allegati", "",
        "## Bundle", "",
        "- [knowledgebase.md](knowledgebase.md) — tutto in un file",
        f"- [knowledgebase.jsonl](knowledgebase.jsonl) — {sum(len(chunks(d)) for d in docs)} chunk "
        "a livello di sezione, pronti per l'ingest", ""]
open(f"{OUT}/README.md", 'w').write("\n".join(idx))
