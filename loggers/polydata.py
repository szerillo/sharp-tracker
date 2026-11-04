#!/usr/bin/env python3
"""Polymarket Data API v2 (11/4: v1 was retired and returns HTTP 410 since 11/2 evening, which silently stopped the sharp-account
logger). One helper for every caller: trades by account (user=) or by market (condition=), taker fills only by default, cursor
paging. Rows come back in the v1 shape the callers already use (proxyWallet, conditionId, timestamp, price, size, side, outcome,
outcomeIndex, transactionHash, slug, title), so the rest of the code is unchanged.
v2: GET /v2/trades?user=|condition=&limit=&takerOnly=&cursor= -> {data: [...snake_case...], pagination: {has_more, next_cursor}}."""
import json, time, urllib.request, urllib.error, urllib.parse

BASE = "https://data-api.polymarket.com/v2"


def _get(url):
    for i in range(4):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'sharp-tracker'}), timeout=25))
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(2 * (i + 1)); continue
            if e.code in (400, 404, 410): return None
            time.sleep(1 + i)
        except Exception: time.sleep(1 + i)
    return None


def _v1(t):
    return dict(proxyWallet=t.get('proxy_wallet'), conditionId=t.get('condition_id'), timestamp=t.get('timestamp'), price=t.get('price'),
                size=t.get('size'), side=t.get('side'), outcome=t.get('outcome'), outcomeIndex=t.get('outcome_index'), asset=t.get('token_id'),
                transactionHash=t.get('transaction_hash'), slug=t.get('slug'), eventSlug=t.get('event_slug'), title=t.get('title'))


def trades(user=None, condition=None, limit=100, max_rows=None, taker_only=True):
    """Newest first. max_rows defaults to one page (limit); pass a larger number to page with the cursor."""
    q = dict(limit=min(limit, 500))
    if user: q['user'] = user
    if condition: q['condition'] = condition
    if taker_only: q['takerOnly'] = 'true'
    out = []; cursor = None; cap = max_rows or limit
    while True:
        qq = dict(q, **({'cursor': cursor} if cursor else {}))
        d = _get(f"{BASE}/trades?{urllib.parse.urlencode(qq)}")
        if not d: break
        rows = d.get('data') or []
        out += [_v1(t) for t in rows]
        pg = d.get('pagination') or {}
        cursor = pg.get('next_cursor')
        if not rows or not pg.get('has_more') or not cursor or len(out) >= cap: break
    return out[:cap]
