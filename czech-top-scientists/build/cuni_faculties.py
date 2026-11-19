"""Guess the Charles University faculty of each researcher listed under "Charles University".

Reads the affiliation text on the researcher's papers since 2022 in Crossref and takes the faculty
named most often. Usage: python3 -I cuni_faculties.py <czech-scientists.json> <faculty.json> [from-year]
With an existing faculty.json, only researchers still without a faculty are looked up again.
"""
import json, re, sys, time, unicodedata, urllib.parse, urllib.request
from collections import Counter

def norm(s):
    return unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()

CU = re.compile(r'charles univ|karlov|cuni|univ(?:ersity)? karlova|charles-univ')
FAC = [  # (faculty, pattern, needs a Charles University mention in the same string)
    ('First Faculty of Medicine', r'(first|1st|1\.?) (faculty of medicine|medical faculty)|1\.? lekarsk', False),
    ('Second Faculty of Medicine', r'(second|2nd|2\.?) (faculty of medicine|medical faculty)|2\.? lekarsk', False),
    ('Third Faculty of Medicine', r'(third|3rd|3\.?) (faculty of medicine|medical faculty)|3\.? lekarsk', False),
    ('Faculty of Medicine in Pilsen', r'(faculty of medicine|medical faculty)[^;]{0,25}(pilsen|plzen)|lekarska fakulta v plzni', True),
    ('Faculty of Medicine in Hradec Králové', r'(faculty of medicine|medical faculty)[^;]{0,25}hradec|lekarska fakulta v hradci', True),
    ('Faculty of Pharmacy in Hradec Králové', r'pharmac|farmaceut', True),
    ('Faculty of Mathematics and Physics', r'mathematics and physics|matematicko', True),
    ('Faculty of Science', r'faculty of (natural )?science\b|prirodovedeck', True),
    ('Faculty of Arts', r'faculty of arts|filozofick', True),
    ('Faculty of Social Sciences', r'social sciences|socialnich ved|institute of economic studies', True),
    ('Faculty of Education', r'faculty of education|pedagogick', True),
    ('Faculty of Physical Education and Sport', r'physical education and sport|telesne vychovy', True),
    ('Faculty of Law', r'faculty of law|pravnick', True),
    ('Faculty of Humanities', r'faculty of humanities|humanitnich', True),
    ('Catholic Theological Faculty', r'catholic theolog|katolick', True),
    ('Protestant Theological Faculty', r'protestant theolog|evangelick', True),
    ('Hussite Theological Faculty', r'hussite|husitsk', True),
    ('CERGE', r'\bcerge\b', True),
    ('BIOCEV', r'biocev', False),
]
FAC = [(f, re.compile(p), need) for f, p, need in FAC]

def faculty_of(aff):
    a = norm(aff)
    for f, rx, need in FAC:
        if rx.search(a) and (not need or CU.search(a)):
            return f
    return None

def fetch(url):
    for i in range(4):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'research-script/1.0'})
            return json.load(urllib.request.urlopen(req, timeout=60))
        except Exception as e:
            time.sleep(2 * (i + 1)); err = e
    raise err

rows = json.load(open(sys.argv[1]))
year = sys.argv[3] if len(sys.argv) > 3 else '2022'
try: out = json.load(open(sys.argv[2]))
except FileNotFoundError: out = {}
targets = sorted(n for n in {r['n'] for r in rows if r['i'] == 'Charles University'} if not (out.get(n) or {}).get('fac'))
for n, name in enumerate(targets, 1):
    fam, _, giv = re.sub(r'[\u0300-\u036f]', '', name).partition(', ')
    fam = fam.strip(); giv = giv.split()[0] if giv.split() else giv
    q = urllib.parse.urlencode({'query.author': f'{giv} {fam}', 'query.affiliation': 'Charles University',
                                'filter': f'from-pub-date:{year}-01-01', 'rows': 100, 'select': 'author'})
    items = fetch('https://api.crossref.org/works?' + q)['message']['items']
    nf, gi = norm(fam), norm(giv)[:1]
    votes = Counter(); papers = 0
    for it in items:
        for a in it.get('author', []):
            if norm(a.get('family', '')) == nf and norm(a.get('given', ''))[:1] == gi:
                fs = {faculty_of(x.get('name', '')) for x in a.get('affiliation', [])} - {None}
                if fs: papers += 1
                for f in fs: votes[f] += 1
                break
    old = out.get(name) or {}
    if not votes and old.get('votes'):
        continue
    if votes:
        f, k = votes.most_common(1)[0]
        out[name] = {'fac': f if k >= 2 else None, 'votes': dict(votes), 'papers': papers}
    else:
        out[name] = {'fac': None, 'votes': {}, 'papers': 0}
    print(n, name, out[name]['fac'], dict(votes), file=sys.stderr)
    time.sleep(0.4)
json.dump(out, open(sys.argv[2], 'w'), ensure_ascii=False, indent=1)
