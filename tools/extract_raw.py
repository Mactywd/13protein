#!/usr/bin/env python3
"""Stage 1 — pull the tables we care about out of the concatenated WP dump.

The source CSV is ~76 WordPress tables glued together, each preceded by its own
header row. We locate them by header signature (not by byte offset) and keep
only wp_posts / wp_postmeta / wp_options. Everything else — revisions, Wordfence
logs, form submissions, users — is dropped here and never reaches the KB.

Writes .cache/raw.json (~1.5 MB) so stage 2 never re-reads the 767 MB file.
"""
import csv, re, sys, json, os, collections

ROOT  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV   = os.path.join(ROOT, "proteitobu6d54as_cjgw1.csv")
CACHE = os.path.join(ROOT, ".cache")
csv.field_size_limit(sys.maxsize)

HEADERS = {
    ('option_id', 'option_name', 'option_value', 'autoload'): 'options',
    ('meta_id', 'post_id', 'meta_key', 'meta_value'): 'postmeta',
    ('ID', 'post_author', 'post_date', 'post_date_gmt', 'post_content', 'post_title'): 'posts',
}
IDENT = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')
def is_header(row):
    """A row whose every field is a bare identifier starts a new table."""
    return len(row) >= 2 and all(IDENT.match(f or '') for f in row)

POST_COLS = ['ID','post_author','post_date','post_date_gmt','post_content','post_title','post_excerpt',
             'post_status','comment_status','ping_status','post_password','post_name','to_ping','pinged',
             'post_modified','post_modified_gmt','post_content_filtered','post_parent','guid','menu_order',
             'post_type','post_mime_type','comment_count']
# post types that carry no reusable knowledge
SKIP_TYPES = {'revision','acf-field','acf-field-group','acf-post-type','customize_changeset',
              'wp_global_styles','custom_css','oembed_cache','nav_menu_item'}

def main():
    posts, meta, options = {}, collections.defaultdict(dict), {}
    mode, stats = None, collections.Counter()

    with open(CSV, newline='', encoding='utf-8', errors='replace') as f:
        for row in csv.reader(f):
            key = tuple(row[:6]) if len(row) >= 6 else tuple(row)
            hit = HEADERS.get(tuple(row)) or HEADERS.get(key)
            if hit:
                mode = hit
                continue
            if is_header(row):        # some other table begins — stop collecting
                mode = None
                continue
            if mode == 'options' and len(row) == 4:
                options[row[1]] = row[2]
            elif mode == 'postmeta' and len(row) == 4:
                meta[row[1]][row[2]] = row[3]
            elif mode == 'posts' and len(row) == len(POST_COLS):
                p = dict(zip(POST_COLS, row))
                if p['post_type'] in SKIP_TYPES:
                    stats['skipped_' + p['post_type']] += 1
                    continue
                posts[p['ID']] = p
            stats[mode or 'other'] += 1

    meta = {k: v for k, v in meta.items() if k in posts}   # drop meta of skipped posts
    os.makedirs(CACHE, exist_ok=True)
    json.dump({'posts': posts, 'meta': meta, 'options': options},
              open(os.path.join(CACHE, 'raw.json'), 'w'))
    print(f"posts kept {len(posts)} · meta {len(meta)} · options {len(options)}")
    for k, v in stats.most_common():
        print(f"  {k:<32} {v}")

if __name__ == '__main__':
    main()
