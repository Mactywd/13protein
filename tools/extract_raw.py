#!/usr/bin/env python3
"""Stage 1 — pull the tables we care about out of the full MySQL dump.

The source is a phpMyAdmin dump of the whole WordPress database (~76 tables).
We whitelist the handful that carry content: posts / postmeta / options, plus
the taxonomy tables (the blog now has real categories) and the WPML language
tables. Everything else — form submissions, users, Wordfence logs, translation
job queues — is dropped here and never reaches the KB.

Writes .cache/raw.json so stage 2 never re-reads the 1 GB file (~25 s).
"""
import re, sys, json, os, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sqldump

ROOT  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SQL   = os.path.join(ROOT, "proteitobu6d54as_bovu1.sql")
CACHE = os.path.join(ROOT, ".cache")

PFX = 'uytw_'          # this export's table prefix; a new export may differ
T = lambda n: PFX + n
WANTED = {T(n) for n in ('posts', 'postmeta', 'options', 'terms', 'term_taxonomy',
                         'term_relationships', 'icl_languages', 'icl_translations')}

# post types that carry no reusable knowledge
SKIP_TYPES = {'revision', 'acf-field', 'acf-field-group', 'acf-post-type', 'customize_changeset',
              'wp_global_styles', 'custom_css', 'oembed_cache', 'nav_menu_item', 'wp_navigation'}

# options are a dumping ground for plugin state; keep only what stage 2 reads
OPT_KEEP = {'blogname', 'blogdescription', 'siteurl', 'home', 'WPLANG', 'template',
            'stylesheet', 'page_on_front', 'show_on_front', 'permalink_structure',
            'active_plugins', 'category_base', 'posts_per_page', 'timezone_string'}
OPT_PREFIX = ('elementor_', 'options_', 'acf_')     # theme/global settings and ACF option pages
OPT_DROP = re.compile(r'^(_?_?site_)?_?transient|^wordfence|^wf|^limit_login|^itsec|_notice|_cache$')


def main():
    posts, meta, options = {}, collections.defaultdict(dict), {}
    terms, taxonomy, rels, languages, translations = {}, {}, [], [], []
    stats = collections.Counter()

    for table, r in sqldump.iter_rows(SQL, WANTED):
        name = table[len(PFX):]
        stats[name] += 1
        if name == 'posts':
            if r['post_type'] in SKIP_TYPES:
                stats['skipped_' + r['post_type']] += 1
                continue
            posts[r['ID']] = r
        elif name == 'postmeta':
            meta[r['post_id']][r['meta_key']] = r['meta_value']
        elif name == 'options':
            k = r['option_name']
            if k in OPT_KEEP or (k.startswith(OPT_PREFIX) and not OPT_DROP.match(k)):
                options[k] = r['option_value']
        elif name == 'terms':
            terms[r['term_id']] = r
        elif name == 'term_taxonomy':
            taxonomy[r['term_taxonomy_id']] = r
        elif name == 'term_relationships':
            rels.append(r)
        elif name == 'icl_languages':
            if r['active'] == '1':
                languages.append(r)
        elif name == 'icl_translations':
            translations.append(r)

    meta = {k: v for k, v in meta.items() if k in posts}   # drop meta of skipped posts
    rels = [x for x in rels if x['object_id'] in posts]
    translations = [t for t in translations
                    if t['element_type'].startswith('post_') and t['element_id'] in posts]

    os.makedirs(CACHE, exist_ok=True)
    json.dump({'posts': posts, 'meta': meta, 'options': options, 'terms': terms,
               'taxonomy': taxonomy, 'rels': rels, 'languages': languages,
               'translations': translations},
              open(os.path.join(CACHE, 'raw.json'), 'w'))

    print(f"posts kept {len(posts)} · meta {len(meta)} · options {len(options)} · "
          f"terms {len(terms)} · lingue attive {len(languages)}")
    for k, v in stats.most_common():
        print(f"  {k:<32} {v}")


if __name__ == '__main__':
    main()
