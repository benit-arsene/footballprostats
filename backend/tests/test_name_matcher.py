import sys
sys.path.insert(0,'C:/src/flutter/flutter_windows_3.35.6-stable/football-pro-stats/backend')
from matching.name_matcher import normalize, score

def test_accent():
    assert normalize('Jose')=='jose'

def test_punct():
    assert normalize("O'Brien!")=='o brien'

def test_initials():
    r=score('J. Pedro','Joao Pedro')
    assert r['score']>0

def test_order():
    r=score('Pedro Neto','Neto Pedro')
    assert 'reversed_order' in r['signals']

def test_token():
    r=score('Bruno Fernandes','Bruno Fernandes')
    assert r['score']==1.0

def test_conflict():
    r=score('A B','A B', team_a='X', team_b='Y')
    assert r['team_conflict'] is True

def test_diff():
    r=score('Alice Smith','Bob Jones')
    assert r['score']<0.5
