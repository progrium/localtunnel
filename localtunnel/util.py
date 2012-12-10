import json
import getpass
import socket
import urllib2
import platform

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

def client_name():
    return "{0}@{1};{2}".format(
        getpass.getuser(), 
        socket.gethostname(),
        platform.system())

def discover_backend_port(hostname, frontend_port=80):
    try:
        data = urllib2.urlopen(urllib2.Request(
            "http://{0}:{1}/".format(hostname,frontend_port),
            headers={"Host": "_backend.{0}".format(hostname)}))
        return int(data.read())
    except urllib2.HTTPError:
        raise RuntimeError("Frontend failed to provide backend port")
