import json
import getpass
import socket
import urllib2

import eventlet
import eventlet.greenpool

def leave_socket_open():
    eventlet.getcurrent()._exit_funcs = [] 

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
    pool = eventlet.greenpool.GreenPool(size=2)
    pool.spawn_n(_pipe, a, b)
    pool.spawn_n(_pipe, b, a)
    return pool

def recv_json(socket, max_size=256):
    buffer = bytearray()
    byte = None
    while byte != "\n" and len(buffer) < max_size:
        byte = socket.recv(1)
        if not byte:
            print "no byte"
            return
        buffer.extend(byte)
    try:
        return json.loads(str(buffer[0:-1]))
    except ValueError:
        return

def client_name():
    return "{0}@{1}".format(getpass.getuser(), socket.gethostname())

def discover_backend_port(hostname, frontend_port=80):
    try:
        data = urllib2.urlopen(urllib2.Request(
            "http://{0}:{1}/".format(hostname,frontend_port),
            headers={"Host": "_backend.{0}".format(hostname)}))
        return int(data.read())
    except urllib2.HTTPError:
        raise RuntimeError("Frontend failed to provide backend port")
