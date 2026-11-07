"""Match a schedule team to a Polymarket title or bet text (11/7).
The old matcher keyed each team on the last word of its short name. For 'Oklahoma St' and 'Kansas St' that word is 'st', which sits
inside 'Morgan State vs. Delaware State' and 'Stetson vs. Davidson', so two FCS flags were filed under Oklahoma State @ Kansas State.
Here a team matches only on whole words: its school/city ('oklahoma state', 'miami'), its short name with 'St' spelled out, or its
mascot ('cowboys'), never a token under 4 letters. A school name does not match when the title continues it into a longer school name
('kansas' inside 'kansas state', 'miami' inside 'miami (oh)')."""
import re

_EXT = re.compile(r"^\s*(state\b|st\b|tech\b|a&m\b|\((oh|ohio)\))", re.I)   # 'kansas' in 'kansas state', 'miami' in 'miami (oh)'; 'miami (fl)' is Miami


def names(team):
    t = team or {}
    out = []
    for k in ('location', 'shortDisplayName', 'displayName', 'name'):
        v = (t.get(k) or '').strip().lower()
        if not v: continue
        v = re.sub(r'\bst\.?$', 'state', v)              # 'oklahoma st' -> 'oklahoma state'
        # 4+ letters, or a short school code like LSU / TCU / BYU / UCF (matched whole-word only, so 'st' never counts)
        if (len(v.replace(' ', '')) >= 4 or (k in ('location', 'shortDisplayName') and len(v) == 3 and v.isalpha())) and v not in out: out.append(v)
    return out


def hit(team, text):
    """True when one of the team's names appears in `text` as whole words and is not the start of a longer school name."""
    low = (text or '').lower()
    for n in names(team):
        for m in re.finditer(r'(?<![a-z0-9])' + re.escape(n) + r'(?![a-z0-9])', low):
            rest = low[m.end():]
            if not n.endswith('state') and _EXT.match(rest): continue
            return True
    return False


def side(away, home, text):
    """'away' / 'home' when exactly one team's name is in `text` (a bet like 'Stetson ML'), else None."""
    a, h = hit(away, text), hit(home, text)
    return 'away' if a and not h else 'home' if h and not a else None
