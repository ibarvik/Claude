"""Build czech-scientists.json from the rows extracted from the dataset xlsx files.

Usage: python3 -I build_data.py <extracted.json> <group-overrides.json> <out.json>

Groups:
  cz   latest affiliation in Czechia (dataset field cntry == cze)
  top  latest affiliation abroad, but Czechia is the most frequent country of their career papers
  p10  latest affiliation abroad, Czechia has at least 10% of their career papers
group-overrides.json maps "Name|Institution" (or just "Name") to a group, to move people by hand.
"""
import json, sys
ORDER = {'cz': 0, 'top': 1, 'p10': 2}
d = json.load(open(sys.argv[1]))
over = json.load(open(sys.argv[2]))
P = {}
for which, nck in (('career', 'nc9625'), ('single', 'nc2525')):
    for r in d[which]['rows']:
        cn = str(r['cntry']).lower()
        g = 'cz' if cn == 'cze' else 'top' if r['top_cntry_career'] == 'CZE' else 'p10'
        p = P.setdefault((r['authfull'], r['inst_name']), {'n': r['authfull'], 'i': r['inst_name'] or '', 'g': g})
        if ORDER[g] < ORDER[p['g']]: p['g'] = g
        sr, cnt = int(r['rank sm-subfield-1']), int(r['sm-subfield-1 count'])
        p[which[0]] = {'rk': int(r['rank']), 'c': round(float(r['c']), 3), 'h': int(r['h25']), 'nc': int(r[nck]),
                       'sf': round(float(r['self%']) * 100, 1), 'srk': sr, 'pct': round(100 * sr / cnt, 2)}
        if which == 'career' or 'f' not in p:
            ts = r['top_cntry_share']
            p.update({'np': int(r['np6025']), 'f': r['sm-field'] or '', 's1': r['sm-subfield-1'] or '',
                      'y0': int(r['firstyr']), 'y1': int(r['lastyr']), 'cc': cn.upper(),
                      'k10': r['cntry_10pct'] or '', 'tc': r['top_cntry_career'] or '',
                      'ts': round(float(ts) * 100) if ts not in (None, '', 'None') else None})
moved = 0
for p in P.values():
    g = over.get(f"{p['n']}|{p['i']}") or over.get(p['n'])
    if g:
        assert g in ORDER, g
        p['g'] = g; p['mv'] = 1; moved += 1
rows = sorted(P.values(), key=lambda p: (p.get('c', {}).get('rk', 10**9), p.get('s', {}).get('rk', 10**9)))
open(sys.argv[3], 'w').write('[\n' + ',\n'.join(json.dumps(r, ensure_ascii=False, separators=(',', ':')) for r in rows) + '\n]\n')
from collections import Counter
print(len(rows), Counter(p['g'] for p in rows), 'moved by hand:', moved)
