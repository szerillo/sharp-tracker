"""Signed requests to the Novig v3 API (NOVIG-V3 scheme, Ed25519). Docs: docs.novig.com/api/signing.
Credentials come from the environment only: NOVIG_KEY_ID and NOVIG_PRIVATE_KEY (PKCS#8 PEM, newlines or literal "\\n").
Every request is signed, including GETs. Canonical string = 6 LF-joined lines:
  NOVIG-V3 / timestamp ms / METHOD / path / canonical query / sha256-hex(body bytes)."""
import os, json, time, hashlib, base64, urllib.request, urllib.parse
from cryptography.hazmat.primitives import serialization

HOST = os.environ.get('NOVIG_HOST', 'https://api.novig.com')
_KEY = None


def _key():
    global _KEY
    if _KEY is None:
        pem = os.environ['NOVIG_PRIVATE_KEY'].replace('\\n', '\n').encode()
        _KEY = serialization.load_pem_private_key(pem, password=None)
    return _KEY


def _enc(s):
    return urllib.parse.quote(s, safe='-._~')


def canonical_query(raw):
    if not raw: return ''
    pairs = []
    for part in raw.split('&'):
        if part == '': continue
        k, _, v = part.partition('=')
        pairs.append((_enc(urllib.parse.unquote(k)), _enc(urllib.parse.unquote(v))))
    pairs.sort(key=lambda kv: (kv[0].encode(), kv[1].encode()))
    return '&'.join(f'{k}={v}' for k, v in pairs)


def string_to_sign(ts, method, path, query, body):
    return '\n'.join(['NOVIG-V3', str(ts), method.upper(), path, canonical_query(query), hashlib.sha256(body or b'').hexdigest()])


def request(method, path, query='', body=None, timeout=30):
    ts = int(time.time() * 1000)
    data = json.dumps(body, separators=(',', ':')).encode() if body is not None else None
    sig = base64.b64encode(_key().sign(string_to_sign(ts, method, path, query, data).encode())).decode()
    url = HOST + path + (('?' + query) if query else '')
    hdr = {'Novig-Key-Id': os.environ['NOVIG_KEY_ID'], 'Novig-Timestamp': str(ts), 'Novig-Signature': sig, 'User-Agent': 'sharp-tracker'}
    if data is not None: hdr['Content-Type'] = 'application/json'
    req = urllib.request.Request(url, data=data, method=method.upper(), headers=hdr)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r: return r.status, json.loads(r.read() or b'null')
    except urllib.error.HTTPError as e:
        return e.code, (e.read() or b'')[:300].decode(errors='replace')


def available():
    return bool(os.environ.get('NOVIG_KEY_ID') and os.environ.get('NOVIG_PRIVATE_KEY'))


if __name__ == '__main__':
    print('time', request('GET', '/v3/time'))
    print('echo', request('POST', '/v3/echo', body={'ping': 1}))
    print('keys', request('GET', '/v3/keys'))
    print('throttle', request('GET', '/v3/throttle'))
