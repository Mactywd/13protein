"""Minimal PHP unserialize() — handles a/s/i/d/b/N as produced by WordPress."""
class Err(ValueError): pass

def loads(s):
    v, i = _val(s, 0)
    return v

def _val(s, i):
    t = s[i]
    if t == 'N': return None, i + 2
    if t == 'b':
        j = s.index(';', i); return s[i+2:j] == '1', j + 1
    if t == 'i':
        j = s.index(';', i); return int(s[i+2:j]), j + 1
    if t == 'd':
        j = s.index(';', i); return float(s[i+2:j]), j + 1
    if t == 's':
        j = s.index(':', i + 2); n = int(s[i+2:j])
        start = j + 2
        return s[start:start+n], start + n + 2
    if t in 'aO':
        if t == 'O':                       # object: O:len:"Name":count:{...}
            j = s.index(':', i + 2); n = int(s[i+2:j]); i = j + 2 + n + 1
            j = s.index(':', i); cnt = int(s[i+1:j]); i = j + 2
        else:
            j = s.index(':', i + 2); cnt = int(s[i+2:j]); i = j + 2
        out = {}
        for _ in range(cnt):
            k, i = _val(s, i)
            v, i = _val(s, i)
            out[k] = v
        return out, i + 1
    raise Err(f"tipo non gestito {t!r} a {i}")
