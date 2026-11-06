"""Read a .jsonl.gz built by appending gzip members, tolerating broken members.
A runner killed mid-write leaves a truncated member; gzip.open stops there and everything appended after it becomes unreadable. This
walks the raw bytes member by member, keeps every complete line, and resyncs at the next gzip header after a broken member."""
import zlib

MAGIC = b'\x1f\x8b\x08'


def lines(path):
    data = open(path, 'rb').read(); i = 0; n = len(data)
    while i < n:
        j = data.find(MAGIC, i)
        if j < 0: return
        d = zlib.decompressobj(31); out = []; ok = False; k = j
        try:
            while k < n:
                out.append(d.decompress(data[k:k + 65536])); k += 65536
                if d.eof: ok = True; break
        except zlib.error:
            ok = False
        buf = b''.join(out)
        if ok: i = n - len(d.unused_data) if k >= n else k - len(d.unused_data)
        else: i = j + 3                    # broken member: keep its complete lines, then look for the next header
        text = buf.decode('utf-8', 'ignore').split('\n')
        if not ok and text: text = text[:-1]          # last line of a broken member may be cut
        for l in text:
            if l.strip(): yield l
