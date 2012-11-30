import json
import getpass
import socket

import gevent
import gevent.pool
import gevent.socket

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
            try:
                data = from_.recv(64 * 1024)
                if not data:
                    break
                try:
                    to.sendall(data)
                except:
                    from_.close()
                    break
            except:
                break
        try:
            to.close()
        except: 
            pass
    return group([
        gevent.spawn(_pipe, a, b),
        gevent.spawn(_pipe, b, a),
    ])

def recv_json(socket, max_size=256):
    buffer = bytearray()
    byte = None
    while byte != "\n" and len(buffer) < max_size:
        byte = socket.recv(1)
        if not byte:
            return
        buffer.extend(byte)
    try:
        return json.loads(str(buffer[0:-1]))
    except ValueError:
        return

def client_name():
    return "{0}@{1}".format(getpass.getuser(), socket.gethostname())

def discover_backend_port(hostname, frontend_port=80):
    client = gevent.socket.create_connection((hostname, frontend_port))
    client.sendall("Host: _backend.{0}".format(hostname))
    port = client.recv(8)
    if not port:
        raise RuntimeError("Frontend failed to provide backend port")
    client.close()
    return int(port.strip())
