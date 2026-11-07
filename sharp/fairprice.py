"""Fair-price checks shared by every live feed that prices a bet against Pinnacle (Sean 11/7: "make sure ... we are devigging the
Pinnacle market and then devigging other options and measuring against that ... and anything else that flags late relative to Pinnacle").

  pin_fair(side, other)      Pinnacle's two-way no-vig probability for `side`: proportional (what the rules were backtested on) and power
                             (weights the vig toward the longshot, the better estimate on lopsided prices like -140 / +110).
  book_fair(side, other)     the same no-vig for the venue being bet, so the two markets compare fair-to-fair.
  check(...)                 one dict for a flag: both Pinnacle fairs, the venue's fair, the fair-to-fair gap, the EV at the price you get
                             (against the stricter of the two Pinnacle fairs), and a freshness verdict.
  fresh(pin_ts, book_ts)     Pinnacle's quote must be recent (<= 20 min old) and not older than the venue's by more than 10 min. A stale
                             Pinnacle number next to a moved book is a fake edge.
Decimal odds in, probabilities out. Timestamps are ISO strings (The Odds API last_update) or datetimes."""
import datetime as dt
from sharp.devig import devig_pair

MAX_PIN_AGE_MIN = 20
MAX_PIN_LAG_MIN = 10


def _ts(x):
    if x is None: return None
    if isinstance(x, dt.datetime): return x if x.tzinfo else x.replace(tzinfo=dt.timezone.utc)
    try: return dt.datetime.fromisoformat(str(x).replace('Z', '+00:00'))
    except Exception: return None


def pin_fair(dec_side, dec_other):
    a, b = 1 / dec_side, 1 / dec_other
    return dict(prop=a / (a + b), power=devig_pair(a, b, 'power'))


def book_fair(dec_side, dec_other):
    if not dec_side or not dec_other: return None
    a, b = 1 / dec_side, 1 / dec_other
    return a / (a + b)


def fresh(pin_ts, book_ts=None, now=None):
    now = now or dt.datetime.now(dt.timezone.utc); p, b = _ts(pin_ts), _ts(book_ts)
    if p is None: return True, 'no Pinnacle timestamp'            # the source gave none; do not block on it
    age = (now - p).total_seconds() / 60
    if age > MAX_PIN_AGE_MIN: return False, f'Pinnacle quote {age:.0f} min old'
    if b is not None and (b - p).total_seconds() / 60 > MAX_PIN_LAG_MIN:
        return False, f"Pinnacle quote {(b - p).total_seconds() / 60:.0f} min older than the book's"
    return True, ''


def check(pin_side, pin_other, price, book_side=None, book_other=None, pin_ts=None, book_ts=None, now=None):
    """price = decimal price you can get on the side. Returns the fields to store on a flag; ok=False when the edge is not there on the
    stricter Pinnacle fair or Pinnacle's quote is stale."""
    pf = pin_fair(pin_side, pin_other); fair_strict = min(pf['prop'], pf['power'])
    bf = book_fair(book_side, book_other)
    ok_f, why = fresh(pin_ts, book_ts, now)
    ev = fair_strict * price - 1
    return dict(pin_fair=round(pf['prop'], 4), pin_fair_power=round(pf['power'], 4), book_fair=round(bf, 4) if bf is not None else None,
                fair_gap=round(100 * (pf['prop'] - bf), 1) if bf is not None else None, ev_strict=round(100 * ev, 1),
                fresh=ok_f, stale_why=why or None, ok=ok_f and ev > 0)
