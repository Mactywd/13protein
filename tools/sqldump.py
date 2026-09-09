#!/usr/bin/env python3
"""Streaming reader for phpMyAdmin / mysqldump `.sql` files.

The dump is ~1 GB and a single `_elementor_data` value can be 300 KB, so we
never load the file (or a whole statement) into memory: we keep a sliding
window and parse tuple by tuple. Values are MySQL string literals — quoted
with `'`, backslash-escaped, newlines written as `\\n` — so a naive split on
`),(` would corrupt any JSON containing those sequences.
"""
import re

CHUNK = 1 << 22          # 4 MB reads; a single value must fit in the window
ESCAPES = {'0': '\0', 'b': '\b', 'n': '\n', 'r': '\r', 't': '\t', 'Z': '\x1a'}
INSERT = re.compile(r"INSERT INTO `([^`]+)` \(([^)]*)\) VALUES")


class _Window:
    """File cursor that guarantees `n` readable chars ahead when it can."""

    def __init__(self, fh):
        self.fh, self.buf, self.i, self.eof = fh, '', 0, False

    def fill(self, n=CHUNK):
        while not self.eof and len(self.buf) - self.i < n:
            data = self.fh.read(CHUNK)
            if not data:
                self.eof = True
                break
            if self.i:                       # drop what we already consumed
                self.buf = self.buf[self.i:]
                self.i = 0
            self.buf += data

    def find(self, needle):
        """Advance to the next occurrence of `needle`; False at EOF."""
        while True:
            j = self.buf.find(needle, self.i)
            if j >= 0:
                self.i = j
                return True
            if self.eof:
                return False
            self.i = max(self.i, len(self.buf) - len(needle))
            self.fill()

    def match(self, rx):
        self.fill(1 << 16)
        return rx.match(self.buf, self.i)


def _read_value(w):
    """Parse one MySQL literal at the cursor; returns str, or None for NULL."""
    w.fill(64)
    c = w.buf[w.i]
    if c != "'":                                     # NULL / number / keyword
        j = w.i
        while True:
            if j >= len(w.buf):
                w.fill()
                if j >= len(w.buf):
                    break
            if w.buf[j] in ',)':
                break
            j += 1
        tok = w.buf[w.i:j].strip()
        w.i = j
        return None if tok.upper() == 'NULL' else tok

    w.i += 1
    parts, start = [], w.i
    while True:
        if w.i >= len(w.buf):
            parts.append(w.buf[start:])
            w.fill()
            if w.i >= len(w.buf):
                break                                # truncated dump
            start = w.i
        c = w.buf[w.i]
        if c == '\\':
            parts.append(w.buf[start:w.i])
            w.fill(4)
            nxt = w.buf[w.i + 1] if w.i + 1 < len(w.buf) else ''
            parts.append(ESCAPES.get(nxt, nxt))
            w.i += 2
            start = w.i
        elif c == "'":
            parts.append(w.buf[start:w.i])
            w.i += 1
            # doubled '' is a literal quote, not the end of the string
            w.fill(2)
            if w.i < len(w.buf) and w.buf[w.i] == "'":
                parts.append("'")
                w.i += 1
                start = w.i
                continue
            break
        else:
            w.i += 1
    return ''.join(parts)


def _skip_ws(w):
    while True:
        w.fill(16)
        if w.i < len(w.buf) and w.buf[w.i] in ' \t\r\n':
            w.i += 1
        else:
            return


def iter_rows(path, wanted):
    """Yield (table, {col: value}) for every INSERT row of a table in `wanted`.

    Statements for other tables are skipped without parsing their values.
    """
    with open(path, encoding='utf-8', errors='replace') as fh:
        w = _Window(fh)
        while w.find('INSERT INTO `'):
            m = w.match(INSERT)
            if not m:
                w.i += 1
                continue
            table = m.group(1)
            cols = [c.strip(' `') for c in m.group(2).split(',')]
            w.i = m.end()
            if table not in wanted:
                continue                 # next find() lands on the next INSERT
            while True:
                _skip_ws(w)
                if w.i >= len(w.buf) or w.buf[w.i] != '(':
                    break
                w.i += 1
                vals = []
                while True:
                    _skip_ws(w)
                    vals.append(_read_value(w))
                    _skip_ws(w)
                    if w.i >= len(w.buf):
                        break
                    if w.buf[w.i] == ',':
                        w.i += 1
                        continue
                    if w.buf[w.i] == ')':
                        w.i += 1
                    break
                yield table, dict(zip(cols, vals))
                _skip_ws(w)
                if w.i < len(w.buf) and w.buf[w.i] == ',':
                    w.i += 1
                    continue
                break                    # `;` — statement over
