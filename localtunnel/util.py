import json
import getpass
import socket
import urllib2
import platform

import eventlet
import eventlet.greenpool

def join_sockets(a, b):
    """ socket joining implementation """
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
    """ semi-unique client identifier string """
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

def lookup_server_version(hostname):
    try:
        data = urllib2.urlopen(urllib2.Request(
            "http://{0}/".format(hostname),
            headers={"Host": "_version.{0}".format(hostname)}))
        return data.read()
    except urllib2.HTTPError:
        raise RuntimeError("Server failed to provide version")

def print_server_metrics(hostname):
    try:
        data = urllib2.urlopen(urllib2.Request(
            "http://{0}/".format(hostname),
            headers={"Host": "_metrics.{0}".format(hostname)}))
        metrics = json.loads(data.read())
        for metric in metrics:
            print "%(name) -40s %(value)s" % metric
    except urllib2.HTTPError:
        raise RuntimeError("Server failed to provide metrics")

