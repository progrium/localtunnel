import json

import gevent
import gevent.pool

def group(greenlets):
    class _codependents(gevent.pool.Group):
        def discard(self, greenlet):
            super(_codependents, self).discard(greenlet)
            if not hasattr(self, '_killing'):
                self._killing = True
                gevent.spawn(self.kill)
    return _codependents(greenlets)

def join_sockets(a, b):
    def _pipe(from_, to):
        while True:
            data = from_.recv(4096)
            if not data:
                break
            try:
                to.sendall(data)
            except:
                from_.close()
                break
        try:
            to.close()
        except: pass
    return group([
        gevent.spawn(_pipe, a, b),
        gevent.spawn(_pipe, b, a),
    ])

def recv_json(socket, max_size=256):
    buffer = bytearray()
    byte = None
    while byte != "\n" and len(buffer) < max_size:
        byte = socket.recv(1)
        buffer.extend(byte)
    try:
        return json.loads(str(buffer[0:-1]))
    except ValueError:
        return
