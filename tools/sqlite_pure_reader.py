"""Minimal dependency-free SQLite 3 table reader (read-only, rollback-journal
files only), written to size the effort of a MATLAB/Octave port.

Walks the table b-tree from the root page, follows overflow chains, decodes
records. No index support, no WAL, no freelist. Verified against sqlite3.
"""
import struct, sys, time, sqlite3


def varint(b, i):
    v = 0
    for k in range(8):
        c = b[i + k]
        v = (v << 7) | (c & 0x7F)
        if c < 0x80:
            return v, i + k + 1
    v = (v << 8) | b[i + 8]
    return v, i + 9


class DB:
    def __init__(self, path):
        self.f = open(path, 'rb')
        h = self.f.read(100)
        assert h[:16] == b'SQLite format 3\x00'
        ps = struct.unpack('>H', h[16:18])[0]
        self.ps = 65536 if ps == 1 else ps
        self.reserved = h[20]
        assert h[18] == 1 and h[19] == 1, 'WAL-mode file: not supported by this reader'
        self.enc = {1: 'utf-8', 2: 'utf-16-le', 3: 'utf-16-be'}[struct.unpack('>I', h[56:60])[0]]
        self.usable = self.ps - self.reserved

    def page(self, n):
        self.f.seek((n - 1) * self.ps)
        return self.f.read(self.ps)

    def read_payload(self, pg, off, total):
        """Return the full payload of a table-leaf cell starting at pg[off]."""
        U = self.usable
        X = U - 35
        M = ((U - 12) * 32 // 255) - 23
        if total <= X:
            return pg[off:off + total]
        K = M + ((total - M) % (U - 4))
        local = K if K <= X else M
        out = bytearray(pg[off:off + local])
        nxt = struct.unpack('>I', pg[off + local:off + local + 4])[0]
        while nxt:
            p = self.page(nxt)
            nxt = struct.unpack('>I', p[:4])[0]
            out += p[4:4 + min(U - 4, total - len(out))]
        return bytes(out)

    def decode_record(self, payload):
        hsize, i = varint(payload, 0)
        types = []
        while i < hsize:
            t, i = varint(payload, i)
            types.append(t)
        vals, i = [], hsize
        for t in types:
            if t == 0: vals.append(None)
            elif t in (1, 2, 3, 4, 5, 6):
                n = {1: 1, 2: 2, 3: 3, 4: 4, 5: 6, 6: 8}[t]
                vals.append(int.from_bytes(payload[i:i + n], 'big', signed=True)); i += n
            elif t == 7: vals.append(struct.unpack('>d', payload[i:i + 8])[0]); i += 8
            elif t == 8: vals.append(0)
            elif t == 9: vals.append(1)
            elif t >= 12 and t % 2 == 0:
                n = (t - 12) // 2; vals.append(payload[i:i + n]); i += n
            else:
                n = (t - 13) // 2; vals.append(payload[i:i + n].decode(self.enc)); i += n
        return vals

    def rows(self, root):
        """Yield (rowid, values) for every row of the table b-tree rooted at page root."""
        stack = [root]
        while stack:
            n = stack.pop()
            pg = self.page(n)
            hdr = 100 if n == 1 else 0
            ptype = pg[hdr]
            ncells = struct.unpack('>H', pg[hdr + 3:hdr + 5])[0]
            if ptype == 0x05:                       # interior table page
                right = struct.unpack('>I', pg[hdr + 8:hdr + 12])[0]
                ptrs = struct.unpack('>%dH' % ncells, pg[hdr + 12:hdr + 12 + 2 * ncells])
                kids = [struct.unpack('>I', pg[p:p + 4])[0] for p in ptrs] + [right]
                stack.extend(reversed(kids))     # keep rowid order
            elif ptype == 0x0D:                     # leaf table page
                ptrs = struct.unpack('>%dH' % ncells, pg[hdr + 8:hdr + 8 + 2 * ncells])
                for p in ptrs:
                    total, i = varint(pg, p)
                    rowid, i = varint(pg, i)
                    yield rowid, self.decode_record(self.read_payload(pg, i, total))
            else:
                raise ValueError('unexpected page type 0x%02x' % ptype)

    def schema(self):
        return {r[1]: r for _, r in self.rows(1)}  # name -> (type, name, tbl_name, rootpage, sql)


if __name__ == '__main__':
    path = sys.argv[1]
    db = DB(path)
    print('page size', db.ps, 'encoding', db.enc)
    sch = db.schema()
    print('tables:', sorted(n for n, r in sch.items() if r[0] == 'table'))
    root = sch['FrameInfo'][3]
    t0 = time.time()
    mine = {r[1]: r[2] for _, r in db.rows(root)}        # FrameKey -> Data  (ezdata) / Offset (index)
    t1 = time.time()
    con = sqlite3.connect('file:%s?mode=ro&immutable=1' % path, uri=True)
    cols = [c[1] for c in con.execute('pragma table_info(FrameInfo)')]
    ref = {r[0]: r[1] for r in con.execute('select %s, %s from FrameInfo' % (cols[1], cols[2]))}
    print('rows', len(mine), 'match sqlite3:', mine == ref, 'pure-python time %.2fs' % (t1 - t0))
