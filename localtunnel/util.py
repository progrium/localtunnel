import json
import getpass
import socket
import urllib2
import platform

import requests

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

def lookup_server_version(hostname):
    try:
        data = urllib2.urlopen(urllib2.Request(
            "http://{0}/".format(hostname),
            headers={"Host": "_version.{0}".format(hostname)}))
        return data.read()
    except urllib2.HTTPError:
        raise RuntimeError("Server failed to provide version")


class StatHat(object):
    """The StatHat API wrapper."""
    STATHAT_URL = 'http://api.stathat.com'

    def __init__(self, key=None, prefix=None):
        self.key = key
        self.prefix = prefix or ''
        # Enable keep-alive and connection-pooling.
        self.session = requests.session()

    def _http_post(self, path, data):
        url = self.STATHAT_URL + path
        r = self.session.post(url, data=data, prefetch=True)
        return r

    def value(self, name, value):
        r = self._http_post('/ez', {
            'ezkey': self.key, 
            'stat': ''.join([self.prefix, name]), 
            'value': value})
        return r.ok

    def count(self, name, count):
        r = self._http_post('/ez', {
            'ezkey': self.key, 
            'stat': ''.join([self.prefix, name]), 
            'count': count})
        return r.ok
