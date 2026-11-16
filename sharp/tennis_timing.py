"""Mutable tennis schedules; immutable fixture identity and historical flag times.

A scheduled timestamp is an estimate, not evidence that a ball has been played.
Quotes need recent explicit pregame evidence; display can retain awaiting-start rows.
"""
import datetime as dt

UTC = dt.timezone.utc
STOP = {'live', 'finished', 'cancelled', 'suspended'}
PRIORITY = {'espn': 3, 'pinnacle': 2, 'novig': 1}


def timestamp(value):
    if isinstance(value, (float, int)):
        return dt.datetime.fromtimestamp(value / 1000 if value > 1e11 else value, UTC)
    return dt.datetime.fromisoformat(value.replace('Z', '+00:00'))


def state(value):
    s = str(value or '').lower()
    if any(x in s for x in ('final', 'finished', 'completed', 'walkover', 'retired')): return 'finished'
    if any(x in s for x in ('cancel', 'abandon')): return 'cancelled'
    if any(x in s for x in ('suspend', 'interrupt')): return 'suspended'
    if any(x in s for x in ('in_progress', 'in progress', 'inprogress', 'in_play')) or s == 'live': return 'live'
    if any(x in s for x in ('delay', 'postpon', 'scheduled', 'pregame')) or s in ('pending', 'pre'): return 'scheduled'
    return 'unknown'


def observe(event, start, source, status, now, checked_at=None):
    """Keep each source observation; choose a fresh schedule, preserving the fixture id.

    ESPN live/final beats a book still quoting pregame. A fresh Pinnacle estimate beats
    a coarse exchange timestamp. Unknown/stale status never authorizes live betting.
    """
    stamp = now.isoformat().replace('+00:00', 'Z')
    event.setdefault('original_start', event.get('start') or start)
    observations = event.setdefault('schedule_sources', {})
    observations[source] = {'start': start, 'state': state(status), 'checked_at': checked_at or stamp}
    fresh = [(src, obs) for src, obs in observations.items()
             if 0 <= (now - timestamp(obs['checked_at'])).total_seconds() <= 3600]
    # A confirmed final is sticky. Live/suspended needs fresh evidence; scheduled cannot
    # undo a fresh live observation from another source.
    finals = [(src, obs) for src, obs in observations.items() if obs['state'] in ('finished', 'cancelled')]
    stopped = [(src, obs) for src, obs in fresh if obs['state'] in STOP]
    choices = finals or stopped or fresh
    if not choices: return
    src, chosen = max(choices, key=lambda pair: (PRIORITY.get(pair[0], 0), pair[1]['checked_at']))
    old = event.get('start')
    if old and chosen['start'] != old:
        changes = event.setdefault('start_revisions', [])
        changes.append({'from': old, 'to': chosen['start'], 'source': src, 'checked_at': stamp})
        event['start_revisions'] = changes[-20:]
    event.update(start=chosen['start'], start_source=src, schedule_checked_at=chosen['checked_at'],
                 match_status=chosen['state'], status_source=src)


def pregame(event, now):
    """Fresh explicit scheduled evidence only (including delayed matches)."""
    if event.get('match_status') != 'scheduled': return False
    try: return 0 <= (now - timestamp(event['schedule_checked_at'])).total_seconds() <= 3600
    except (KeyError, ValueError, TypeError): return False


def retain(event, now):
    """Do not expire an unconfirmed match merely because its scheduled time passed."""
    if event.get('match_status') in ('finished', 'cancelled'): return False
    return timestamp(event['start']) > now - dt.timedelta(days=3)


def metadata(event, now):
    return dict(match_status=event.get('match_status', 'unknown'), start_source=event.get('start_source', event.get('source')),
                schedule_checked_at=event.get('schedule_checked_at'), original_start=event.get('original_start', event.get('start')),
                awaiting_start=timestamp(event['start']) <= now and event.get('match_status') not in STOP,
                pregame_confirmed=pregame(event, now))


def reconcile_bet(bet, events, now):
    """Reconcile ungraded tennis only. Preserve flag-time start and historical grades."""
    if bet.get('sport') != 'tennis' or bet.get('won') is not None: return
    event = events.get(str(bet.get('event_id')))
    if not event: return
    bet.setdefault('original_start', bet['start'])
    bet['start'] = event['start']
    bet.update(metadata(event, now))
