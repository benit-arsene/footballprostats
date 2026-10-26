import unicodedata, re

def normalize(name):
    s=unicodedata.normalize('NFKD', name or '')
    s=''.join(c for c in s if not unicodedata.combining(c))
    s=re.sub(r'[^a-z0-9\s]', ' ', s.lower())
    return re.sub(r'\s+', ' ', s).strip()

def tokens(name):
    return normalize(name).split()

def score(a, b, team_a=None, team_b=None):
    ta=tokens(a); tb=tokens(b)
    common=set(ta)&set(tb)
    base=len(common)/max(len(set(ta)|set(tb)),1)
    signals=[]
    if common: signals.append('shared_tokens:'+','.join(sorted(common)))
    # order variation
    if ta and tb and ta[::-1]==tb:
        base=min(1.0, base+0.2); signals.append('reversed_order')
    # initials
    if len(ta)==len(tb) and all(x[0]==y[0] for x,y in zip(ta,tb) if x and y):
        base=min(1.0, base+0.1); signals.append('initials_match')
    team_conflict=False
    if team_a and team_b and team_a!=team_b:
        base=max(0.0, base-0.2); team_conflict=True; signals.append('team_conflict')
    else:
        if team_a and team_b: signals.append('team_match')
    return {'score':round(base,3), 'signals':signals, 'team_conflict':team_conflict}
